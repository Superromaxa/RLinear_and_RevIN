# RLinear и RevIN

Репозиторий для воспроизведения статьи *Revisiting Long-term Time Series Forecasting: An Investigation on Affine Mapping*. В проекте мы проверяем, действительно ли простая линейная модель с RevIN работает на стандартных временных рядах почти так же хорошо, как PatchTST и TimesNet, и насколько итоговые числа зависят от протокола оценки.

Сейчас готов авторский пилот RLinear на ETTh1 и несколько дополнительных проверок этой же модели. Основные запуски пяти архитектур ещё не проводились. Полный план и ожидания записаны в [`PRE_REGISTRATION.md`](PRE_REGISTRATION.md).

## Структура

- `pilot/`: stdout исходной и исправленной команд авторов;
- `results/`: первые контролируемые проверки RLinear;
- `scripts/run_pilot.sh`: загрузка зафиксированных версий кода и данных и запуск пилота;
- `scripts/check_rlinear.py`: проверки RevIN, `drop_last`, длины истории и сдвига уровня;
- `requirements-pilot.txt`: окружение, в котором выполнялся пилот.

## Как повторить пилот

Для запуска нужен Python 3.11:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-pilot.txt
```

Исходная команда из `script.md` авторов падает с `KeyError: 'Linear'`. Это поведение можно повторить так:

```bash
bash scripts/run_pilot.sh original
```

Исправленный запуск использует зарегистрированное имя `RLinear`:

```bash
bash scripts/run_pilot.sh rlinear
```

Дополнительные проверки на трёх сидах запускаются отдельно:

```bash
bash scripts/run_pilot.sh controlled
```

Скрипт сам скачивает RTSF и ETTh1, проверяет SHA-256 файлов и печатает путь к новому логу. Используются commit `0fec00104f754f4fbf795b9b4da5fa2459b32e76` для RTSF и commit `11ab373cf9c9f5be7698e219a5a170e1b1c8a930` для ETTDataset. На Apple M2 Pro исправленный авторский запуск занял около 24 секунд.

