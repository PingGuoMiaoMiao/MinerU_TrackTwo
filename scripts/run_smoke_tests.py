import argparse
import subprocess
import sys
import time
from contextlib import suppress

import httpx


def wait_for_health(base_url: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with suppress(Exception):
            response = httpx.get(f"{base_url}/health", timeout=3)
            if response.status_code == 200 and response.json().get("status") == "ok":
                return True
        time.sleep(0.5)
    return False


def start_server(host: str, port: int) -> subprocess.Popen:
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def run_task(base_url: str, timeout: float) -> dict:
    payload = {
        "goal": "抽取文本中的公司、金额和风险，输出结构化 JSON，并标注证据来源",
        "text": "甲公司2026年一季度收入1200万元，净利润180万元。主要风险是海外交付周期延长。",
    }
    created = httpx.post(f"{base_url}/v1/tasks", data=payload, timeout=10)
    created.raise_for_status()
    task_id = created.json()["task_id"]

    deadline = time.time() + timeout
    while time.time() < deadline:
        response = httpx.get(f"{base_url}/v1/tasks/{task_id}", timeout=10)
        response.raise_for_status()
        task = response.json()
        if task["status"] in {"succeeded", "failed"}:
            return task
        time.sleep(1)
    raise TimeoutError(f"Task did not finish within {timeout} seconds: {task_id}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Run a minimal API smoke test.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--no-start", action="store_true", help="Use an already running server.")
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"
    process = None

    try:
        if not args.no_start and not wait_for_health(base_url, 3):
            process = start_server(args.host, args.port)
        if not wait_for_health(base_url, args.timeout):
            print(f"FAIL health check: {base_url}", file=sys.stderr)
            return 1

        task = run_task(base_url, args.timeout)
        if task["status"] != "succeeded":
            print(f"FAIL task status: {task['status']} error={task.get('error')}", file=sys.stderr)
            return 1
        result = task.get("result") or {}
        checks = (result.get("quality") or {}).get("checks") or []
        if "schema_valid" not in checks or "source_text_available" not in checks:
            print(f"FAIL quality checks missing: {checks}", file=sys.stderr)
            return 1

        print("PASS smoke test")
        print(f"task_id={task['task_id']}")
        print(f"summary={result.get('summary', '')[:160]}")
        return 0
    finally:
        if process is not None:
            process.terminate()
            with suppress(Exception):
                process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
