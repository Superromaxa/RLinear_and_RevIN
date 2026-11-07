"""Run the preregistered RLinear checks on ETTh1 using the pinned RTSF model."""

import argparse
import json
import platform
import random
import sys
from copy import deepcopy
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset


SEEDS = (1024, 1025, 1026)
HORIZON = 96
BATCH_SIZE = 128
MAX_HISTORY = 336
CONDITIONS = {
    "long_revin": (MAX_HISTORY, True),
    "long_no_revin": (MAX_HISTORY, False),
    "short_revin": (96, True),
}
TRAIN_END, VALIDATION_END, TEST_END = (months * 30 * 24 for months in (12, 16, 20))


class ForecastWindows(Dataset):
    def __init__(self, data, history, start, stop):
        self.data = data
        self.history = history
        self.origins = range(start, stop - HORIZON + 1)

    def __len__(self):
        return len(self.origins)

    def __getitem__(self, index):
        origin = self.origins[index]
        return self.data[origin - self.history:origin], self.data[origin:origin + HORIZON]


@torch.no_grad()
def window_errors(model, loader, shift=0):
    model.eval()
    rows = []
    for inputs, targets in loader:
        predictions, _ = model(inputs + shift, targets + shift)
        errors = (predictions - (targets + shift)).double()
        rows.append(torch.stack((errors.square().mean((1, 2)), errors.abs().mean((1, 2))), dim=1))
    return torch.cat(rows)


def metrics(errors):
    mse, mae = errors.mean(dim=0).tolist()
    return {"mse": mse, "mae": mae, "windows": len(errors)}


def run_condition(model_class, data, seed, history, revin):
    started = perf_counter()
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    config = SimpleNamespace(seq_len=history, pred_len=HORIZON,
                             channel=data.shape[1], individual=False, drop=0.1, rev=revin)
    model = model_class(config)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    train = DataLoader(ForecastWindows(data, history, MAX_HISTORY, TRAIN_END),
                       batch_size=BATCH_SIZE, shuffle=True,
                       generator=torch.Generator().manual_seed(seed))
    validation = DataLoader(ForecastWindows(data, history, TRAIN_END, VALIDATION_END),
                            batch_size=BATCH_SIZE)
    test = DataLoader(ForecastWindows(data, history, VALIDATION_END, TEST_END),
                      batch_size=BATCH_SIZE)
    best_mse = float("inf")
    for epoch in range(1, 21):
        model.train()
        for inputs, targets in train:
            optimizer.zero_grad()
            _, loss = model(inputs, targets)
            loss.backward()
            optimizer.step()
        validation_mse = metrics(window_errors(model, validation))["mse"]
        if validation_mse < best_mse:
            best_mse = validation_mse
            best_epoch = epoch
            best_weights = deepcopy(model.state_dict())
        if epoch - best_epoch == 5:
            break

    model.load_state_dict(best_weights)
    clean_errors = window_errors(model, test)
    result = {
        "seed": seed, "history": history, "revin": revin,
        "best_epoch": best_epoch, "epochs": epoch, "validation_mse": best_mse,
        "train_windows": len(train.dataset), "validation_windows": len(validation.dataset),
        "test": metrics(clean_errors),
    }
    if history == MAX_HISTORY:
        result["shifted_test"] = metrics(window_errors(model, test, shift=2))
        if revin:
            complete_batches = len(clean_errors) // BATCH_SIZE
            result["truncated_test"] = metrics(clean_errors[:complete_batches * BATCH_SIZE])
    result["seconds"] = perf_counter() - started
    return result


def summarize(runs):
    conditions = {}
    for name, (history, revin) in CONDITIONS.items():
        rows = [row for row in runs if (row["history"], row["revin"]) == (history, revin)]
        aggregate = {}
        for key in ("test", "shifted_test", "truncated_test"):
            if key in rows[0]:
                aggregate[key] = {
                    metric: {"mean": mean(row[key][metric] for row in rows),
                             "sample_sd": stdev(row[key][metric] for row in rows)}
                    for metric in ("mse", "mae")
                }
        conditions[name] = aggregate

    long_on = conditions["long_revin"]["test"]["mse"]["mean"]
    long_off = conditions["long_no_revin"]["test"]["mse"]["mean"]
    short_on = conditions["short_revin"]["test"]["mse"]["mean"]
    drop_changes = [
        100 * (row["truncated_test"]["mse"] / row["test"]["mse"] - 1)
        for row in runs if "truncated_test" in row
    ]
    return {
        "conditions": conditions,
        "rlinear_revin_mse_reduction_pct": 100 * (1 - long_on / long_off),
        "rlinear_long_history_mse_reduction_pct": 100 * (1 - long_on / short_on),
        "drop_last_signed_mse_change_pct_by_seed": dict(zip(SEEDS, drop_changes)),
        "drop_last_median_abs_mse_change_pct": median(map(abs, drop_changes)),
        "shift_mse_change_pct": {
            "revin_on": 100 * (conditions["long_revin"]["shifted_test"]["mse"]["mean"] / long_on - 1),
            "revin_off": 100 * (conditions["long_no_revin"]["shifted_test"]["mse"]["mean"] / long_off - 1),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtsf", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.rtsf))
    from models.RLinear import Model

    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    values = pd.read_csv(args.dataset).iloc[:TEST_END, 1:].to_numpy()
    if values.shape != (TEST_END, 7) or not np.isfinite(values).all():
        parser.error("ETTh1 must contain at least 14,400 rows and seven finite data channels")
    scaler = StandardScaler().fit(values[:TRAIN_END])
    data = torch.tensor(scaler.transform(values), dtype=torch.float32)
    runs = []
    for seed in SEEDS:
        for history, revin in CONDITIONS.values():
            row = run_condition(Model, data, seed, history, revin)
            print(json.dumps(row), flush=True)
            runs.append(row)
    report = {
        "dataset": "ETTh1", "horizon": HORIZON, "seeds": SEEDS, "device": "cpu",
        "platform": platform.platform(), "pytorch": torch.__version__,
        "test_origins": {
            "indexing": "zero-based index of the first target in the CSV data rows",
            "full": [VALIDATION_END, TEST_END - HORIZON],
            "truncated": [VALIDATION_END, VALIDATION_END + runs[0]["truncated_test"]["windows"] - 1],
        },
        "runs": runs, "summary": summarize(runs),
    }
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
