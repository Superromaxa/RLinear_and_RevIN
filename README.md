# RLinear and RevIN: reproduction project

Репозиторий для проекта D3 по воспроизведению статьи *Revisiting Long-term Time Series Forecasting: An Investigation on Affine Mapping*.

На этапе предрегистрации здесь находятся:

- план экспериментов — `PRE_REGISTRATION.md`;
- скрипт воспроизведения авторского пилота — `scripts/run_pilot.sh`;
- исходный и исправленный логи — `pilot/`;
- exploratory-проверки RLinear — `results/` (они не считаются результатами, полученными после фиксации предрегистрации).

## Быстрый старт

Требуется Python 3.11. Команды ниже создают отдельное окружение:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-pilot.txt
```

Скрипт сам загружает зафиксированную версию RTSF и ETTh1 и проверяет SHA-256 файлов.

Исходная команда из `script.md` авторов (ожидаемо завершается с `KeyError: 'Linear'`):

```bash
bash scripts/run_pilot.sh original
```

Минимально исправленный авторский запуск:

```bash
bash scripts/run_pilot.sh rlinear
```

Exploratory-проверки RLinear на трёх сидах:

```bash
bash scripts/run_pilot.sh controlled
```

Путь к новому логу печатается в начале запуска. Время исправленного пилота на Apple M2 Pro CPU — около 25 секунд; на другой машине оно может отличаться.

## Зафиксированные внешние версии

- RTSF: `0fec00104f754f4fbf795b9b4da5fa2459b32e76`
- ETTh1 из ETTDataset: `11ab373cf9c9f5be7698e219a5a170e1b1c8a930`

## Статус

На текущем этапе воспроизведён один авторский запуск RLinear на ETTh1 (`L=336`, `H=96`, seed 1024). Основное ядро с пятью архитектурами ещё не выполнялось.

