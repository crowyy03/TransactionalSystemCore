# Transactional System Core (Django + DRF + Celery + Redis + PostgreSQL)

Тестовое задание: отказоустойчивое ядро транзакций (переводы между кошельками) с защитой от **double spending** при высокой конкуренции.

## Что реализовано

- **POST `/api/transfer`** — перевод между кошельками с комиссией
  - комиссия **10%** если `amount > 1000.00`
  - комиссия зачисляется на технический кошелёк **`admin`**
  - **атомарно**: списание A, зачисление B, зачисление комиссии admin — всё в одной транзакции БД
  - защита от race condition / double spending:
    - `transaction.atomic()`
    - `select_for_update()` с **фиксированным порядком блокировок** по `id` (анти-deadlock)
    - проверка баланса **после** взятия блокировки
    - изменения балансов через `F()` на уровне БД
- **Celery task** `send_notification` после успешной транзакции:
  - `time.sleep(5)`
  - симуляция падения ~30%
  - auto-retry: `countdown=3`, `max_retries=3`
  - запуск **после коммита**: `transaction.on_commit(...)`
- **Демо конкурентности**: `python manage.py demo_race_condition`
  - создаёт кошельки A/B/admin, кладёт A=100.00
  - делает 10 параллельных запросов по 20.00
  - показывает, что баланс A не уходит в минус
- Минимальные тесты: успешный перевод, комиссия, недостаточно средств, конкурентный (service-level)

## Быстрый старт (Docker Compose)

### 1) Поднять сервисы

Из папки `TransactionalSystemCore/`:

```bash
docker compose up --build
```

Сервис `backend` поднимется на `http://localhost:8000`.

### 2) Миграции (если нужно вручную)

```bash
docker compose exec backend python manage.py migrate
```

### 3) Быстрые sanity-check проверки (рекомендуется)

Проверить, что модели и миграции синхронизированы (должно быть `No changes detected`):

```bash
docker compose exec backend python manage.py makemigrations --check --dry-run
```

Проверить DB constraints прямо в PostgreSQL (видно `wallet_balance_non_negative`, `tx_amount_gt_zero`, `tx_fee_non_negative`):

```bash
docker compose exec db psql -U tsc -d tsc -c "\\d wallets_wallet"
docker compose exec db psql -U tsc -d tsc -c "\\d wallets_transaction"
```

## API: перевод

Endpoint: **POST** `http://localhost:8000/api/transfer`

Пример:

```bash
curl -s -X POST http://localhost:8000/api/transfer \
  -H 'Content-Type: application/json' \
  -d '{
    "from_wallet_id": "PUT_UUID_HERE",
    "to_wallet_id": "PUT_UUID_HERE",
    "amount": "1500.00"
  }' | jq
```

## Как быстро получить UUID кошельков для ручного curl

Самый быстрый путь — запустить демо-команду, она создаст кошельки `A`, `B`, `admin` и выведет UUID’ы:

```bash
docker compose exec backend python manage.py demo_race_condition --requests 1 --amount 1.00
```

Ответ (примерно):

```json
{
  "transaction_id": "...",
  "amount": "1500.00",
  "fee": "150.00",
  "total_debited": "1650.00",
  "balances": {
    "from_wallet": {"id": "...", "balance": "8350.00"},
    "to_wallet": {"id": "...", "balance": "1500.00"},
    "admin_wallet": {"id": "...", "balance": "150.00"}
  }
}
```

## Celery worker

В compose он уже определён как сервис `worker`.

Логи можно смотреть:

```bash
docker compose logs -f worker
```

## Демо конкурентности (10 параллельных запросов)

Важно: `demo_race_condition` шлёт HTTP-запросы в API, поэтому **backend должен быть запущен**.

```bash
docker compose exec backend python manage.py demo_race_condition --requests 10 --amount 20.00
```

Ожидаемо: около **5 успехов / 5 ошибок** (insufficient funds), и финальный баланс A == `0.00` (не отрицательный).

Альтернатива (скрипт, если у вас уже есть UUID кошельков):

```bash
docker compose exec backend python scripts/concurrent_transfer_test.py \
  --from-wallet-id PUT_UUID_HERE \
  --to-wallet-id PUT_UUID_HERE \
  --requests 10 --amount 20.00
```

## Тесты

```bash
docker compose exec backend python manage.py test --keepdb
```
