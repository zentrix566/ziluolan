import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://webapi.blizzard.cn/hs-violet-hold-activity/map/flip"
DEFAULT_CONFIG = "flip_config.json"


def load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pick_value(name: str, args, config: dict, default=None):
    value = getattr(args, name, None)
    if value is not None:
        return value
    if name in config:
        return config[name]
    return default


def request_flip(token: str, floor: int, x: int, y: int) -> dict:
    body = json.dumps({"floor": floor, "x": x, "y": y}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "Xcxtoken": token,
            "ccc-channel": "xcx",
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Origin": "https://hs.blizzard.cn",
            "Referer": "https://hs.blizzard.cn/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 "
                "MicroMessenger/7.0.20.1781 MiniProgramEnv/Windows"
            ),
        },
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        text = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"code": -1, "message": "non-json response", "raw": text}


def print_result_hint(result: dict) -> None:
    data = result.get("data")
    if not isinstance(data, dict):
        message = result.get("message", "")
        if message:
            print(f"\n=> 没有返回格子数据：{message}")
        else:
            print("\n=> 没有返回格子数据")
        return

    cell = data.get("cell")
    if not isinstance(cell, dict):
        print("\n=> 没有返回 cell 数据")
        return

    box_type = cell.get("box_type")
    box_id = cell.get("box_id")
    if box_type == 9 or box_id == 40053:
        print("\n=> 这是出口 / 传送门")
    elif box_type == 0 and box_id == 0:
        print("\n=> 普通空格")
    else:
        print(f"\n=> 事件格：box_type={box_type}, box_id={box_id}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Flip a Violet Hold maze cell.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config JSON path, default: {DEFAULT_CONFIG}")
    parser.add_argument("--floor", type=int, help="Floor number")
    parser.add_argument("--x", type=int, help="Cell x coordinate")
    parser.add_argument("--y", type=int, help="Cell y coordinate")
    parser.add_argument("--token", default=os.environ.get("XCXTOKEN"), help="Xcxtoken value")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    token = pick_value("token", args, config) or os.environ.get("XCXTOKEN")
    floor = pick_value("floor", args, config, 3)
    x = pick_value("x", args, config)
    y = pick_value("y", args, config)

    if not token:
        token = getpass.getpass("Xcxtoken: ").strip()
    missing = [name for name, value in [("token", token), ("x", x), ("y", y)] if value in (None, "")]
    if missing:
        print(f"Missing config value(s): {', '.join(missing)}", file=sys.stderr)
        print(f"Put them in {args.config}, or pass --x/--y/--token.", file=sys.stderr)
        return 2

    floor = int(floor)
    x = int(x)
    y = int(y)

    print(f"POST {API_URL}")
    print(f"payload: floor={floor}, x={x}, y={y}")

    try:
        result = request_flip(token, floor, x, y)
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print_result_hint(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
