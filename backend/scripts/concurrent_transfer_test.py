from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--from-wallet-id", required=True)
    parser.add_argument("--to-wallet-id", required=True)
    parser.add_argument("--amount", default="20.00")
    parser.add_argument("--requests", type=int, default=10)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    url = f"{base_url}/api/transfer"
    payload = {
        "from_wallet_id": args.from_wallet_id,
        "to_wallet_id": args.to_wallet_id,
        "amount": args.amount,
    }

    n = int(args.requests)
    barrier = threading.Barrier(n)

    def do_request(i: int):
        barrier.wait()
        with httpx.Client(timeout=20.0) as client:
            try:
                r = client.post(url, json=payload)
                return i, r.status_code, r.text
            except Exception as e:
                return i, 0, str(e)

    ok = 0
    fail = 0
    with ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(do_request, i) for i in range(n)]
        for fut in as_completed(futures):
            i, status, body = fut.result()
            if 200 <= status < 300:
                ok += 1
            else:
                fail += 1
            try:
                parsed = json.loads(body)
                detail = parsed.get("detail")
            except Exception:
                detail = body[:120]
            print(f"#{i}: status={status} detail={detail}")

    print(f"Итог: success={ok}, failed={fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


