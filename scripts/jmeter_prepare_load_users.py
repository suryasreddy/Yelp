#!/usr/bin/env python3
"""
Create CSV users for JMeter review load tests.

Each virtual user must be a distinct account so they can all POST a review for the
same restaurant_id once (Lab 1 rule: one review per user per restaurant).

Usage:
  python scripts/jmeter_prepare_load_users.py --base-url http://localhost:8000 --count 500

Requires: backend running, /auth/signup available.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import urllib.error
import urllib.request


def post_json(url: str, payload: dict) -> tuple[int, str]:
    data = __import__("json").dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8000"))
    p.add_argument("--count", type=int, default=500)
    p.add_argument(
        "--csv-out",
        default=os.path.join(os.path.dirname(__file__), "..", "jmeter", "data", "jmeter_users.csv"),
    )
    p.add_argument("--password", default="password123")
    args = p.parse_args()
    base = args.base_url.rstrip("/")
    os.makedirs(os.path.dirname(os.path.abspath(args.csv_out)), exist_ok=True)

    rows = []
    for i in range(1, args.count + 1):
        email = f"jmeter_load{i:04d}@example.com"
        name = f"JMeter Load {i}"
        status, body = post_json(
            f"{base}/auth/signup",
            {
                "name": name,
                "email": email,
                "password": args.password,
                "role": "user",
            },
        )
        if status in (200, 201):
            pass
        elif status == 400 and "already" in body.lower():
            pass  # idempotent re-run
        else:
            print(f"FAIL signup {email}: {status} {body[:200]}", file=sys.stderr)
            sys.exit(1)
        rows.append({"email": email, "password": args.password})
        if i % 50 == 0:
            print(f"  ... {i}/{args.count}")

    with open(args.csv_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["email", "password"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} users to {args.csv_out}")
    print("All users share password; each JMeter thread uses one row (unique email).")


if __name__ == "__main__":
    main()
