#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  original) model=Linear; extra=() ;;
  rlinear) model=RLinear; extra=(--num_workers 0) ;;
  controlled) ;;
  *) printf 'Usage: %s original|rlinear|controlled\n' "$0" >&2; exit 2 ;;
esac

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${D3_PYTHON:-$project_dir/.venv/bin/python}"
python_bin="$(command -v "$python_bin")" || {
  printf 'Set up .venv as described in README.md, or set D3_PYTHON.\n' >&2
  exit 1
}
python_bin="$(cd "$(dirname "$python_bin")" && pwd)/$(basename "$python_bin")"

work_dir="${D3_WORK_DIR:-$project_dir/.work}"
mkdir -p "$work_dir/cache" "$work_dir/runs"
work_dir="$(cd "$work_dir" && pwd)"

rtsf_commit=0fec00104f754f4fbf795b9b4da5fa2459b32e76
ett_commit=11ab373cf9c9f5be7698e219a5a170e1b1c8a930
archive="$work_dir/cache/RTSF-$rtsf_commit.tar.gz"
dataset="$work_dir/cache/ETTh1.csv"

check_sha256() {
  local actual
  actual="$(shasum -a 256 < "$1")"
  if [[ "${actual%% *}" != "$2" ]]; then
    printf 'SHA-256 mismatch: %s\n' "$1" >&2
    return 1
  fi
}

fetch() {
  local target="$1" url="$2" digest="$3" temp
  if [[ -f "$target" ]]; then
    check_sha256 "$target" "$digest"
    return
  fi
  temp="$(mktemp "$target.XXXXXX")"
  if ! curl --fail --location --silent --show-error --retry 2 "$url" -o "$temp" ||
    ! check_sha256 "$temp" "$digest"; then
    rm -f "$temp"
    return 1
  fi
  mv "$temp" "$target"
}

fetch "$archive" "https://codeload.github.com/plumprc/RTSF/tar.gz/$rtsf_commit" \
  8fcedc4849bd7aba7285a0969e11c90731437ce3b19d4052dceb8f77afecfd8e
fetch "$dataset" "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/$ett_commit/ETT-small/ETTh1.csv" \
  f18de3ad269cef59bb07b5438d79bb3042d3be49bdeecf01c1cd6d29695ee066

run_dir="$(mktemp -d "$work_dir/runs/$1.XXXXXX")"
tar -xzf "$archive" -C "$run_dir"
mkdir -p "$run_dir/dataset" "$run_dir/matplotlib"
ln -s "$dataset" "$run_dir/dataset/ETTh1.csv"
cd "$run_dir"
export MPLBACKEND=Agg MPLCONFIGDIR="$run_dir/matplotlib" OMP_NUM_THREADS=2

if [[ "$1" == controlled ]]; then
  command=("$python_bin" -u "$project_dir/scripts/check_rlinear.py"
    --rtsf "$run_dir/RTSF-$rtsf_commit" --dataset "$dataset" --output "$run_dir/results.json")
else
  # Retain the GPU index from the author command unless the caller overrides it.
  gpu="${D3_GPU:-3}"
  command=("$python_bin" -u "$run_dir/RTSF-$rtsf_commit/run.py"
    --is_training 1 --data_path ETTh1.csv --data ETTh1 --features M --channel 7
    --itr 1 --batch_size 128 --learning_rate 0.005 --model "$model" --rev
    --seq_len 336 --pred_len 96 --gpu "$gpu" ${extra[@]+"${extra[@]}"})
fi

printf 'Log: %s\n' "$run_dir/run.log"
{
  printf 'RTSF commit: %s\nETTh1 commit: %s\n' "$rtsf_commit" "$ett_commit"
  "$python_bin" -c 'import platform, sys; from importlib.metadata import version; print(platform.platform()); print(sys.version.split()[0]); print(", ".join(f"{p}=={version(p)}" for p in ("torch", "numpy", "pandas", "scikit-learn", "matplotlib", "einops")))'
  printf 'Command:'
  printf ' %q' "${command[@]}"
  printf '\n'
  status=0
  /usr/bin/time -p "${command[@]}" || status=$?
  printf 'Exit status: %s\n' "$status"
  exit "$status"
} 2>&1 | tee "$run_dir/run.log"
