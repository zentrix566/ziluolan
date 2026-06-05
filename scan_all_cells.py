import argparse
import json
import time
import urllib.error
from datetime import datetime

from flip_cell import DEFAULT_CONFIG, load_config, request_flip


DEFAULT_OUTPUT = "scan_results.md"


def classify_result(result: dict) -> str:
    data = result.get("data")
    if not isinstance(data, dict):
        return result.get("message") or "no cell data"

    cell = data.get("cell")
    if not isinstance(cell, dict):
        return "no cell data"

    box_type = cell.get("box_type")
    box_id = cell.get("box_id")
    if box_type == 9 or box_id == 40053:
        return "出口 / 传送门"
    if box_type == 0 and box_id == 0:
        return "普通空格"
    return f"事件格 box_type={box_type}, box_id={box_id}"


def cell_summary(x: int, y: int, result: dict) -> dict:
    data = result.get("data")
    cell = data.get("cell") if isinstance(data, dict) else None
    event = data.get("event") if isinstance(data, dict) else None
    cell = cell if isinstance(cell, dict) else {}
    event = event if isinstance(event, dict) else {}
    return {
        "x": x,
        "y": y,
        "code": result.get("code"),
        "message": result.get("message"),
        "box_type": cell.get("box_type"),
        "box_id": cell.get("box_id"),
        "event_done": cell.get("event_done"),
        "need_choose": event.get("need_choose"),
        "stamina": data.get("stamina") if isinstance(data, dict) else None,
        "summary": classify_result(result),
    }


def write_markdown(path: str, floor: int, rows: list[dict]) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# 紫罗兰大冒险翻格扫描结果",
        "",
        f"- 生成时间：{generated_at}",
        f"- floor：{floor}",
        "",
        "## 汇总",
        "",
        "| 坐标 | code | message | box_type | box_id | need_choose | stamina | 判断 |",
        "| --- | ---: | --- | ---: | ---: | --- | ---: | --- |",
    ]

    for row in rows:
        coord = f"({row['x']},{row['y']})"
        lines.append(
            "| {coord} | {code} | {message} | {box_type} | {box_id} | {need_choose} | {stamina} | {summary} |".format(
                coord=coord,
                code=row.get("code", ""),
                message=row.get("message", ""),
                box_type="" if row.get("box_type") is None else row.get("box_type"),
                box_id="" if row.get("box_id") is None else row.get("box_id"),
                need_choose="" if row.get("need_choose") is None else row.get("need_choose"),
                stamina="" if row.get("stamina") is None else row.get("stamina"),
                summary=row.get("summary", ""),
            )
        )

    lines.extend(["", "## 原始返回", ""])
    for row in rows:
        lines.extend(
            [
                f"### ({row['x']},{row['y']})",
                "",
                "```json",
                json.dumps(row["raw"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan all 25 Violet Hold maze cells.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config JSON path, default: {DEFAULT_CONFIG}")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Markdown output path, default: {DEFAULT_OUTPUT}")
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests in seconds, default: 0.2")
    args = parser.parse_args()

    config = load_config(args.config)
    token = config.get("token")
    floor = int(config.get("floor", 3))
    if not token:
        raise SystemExit(f"Missing token in {args.config}")

    rows = []
    for y in range(5):
        for x in range(5):
            print(f"request floor={floor}, x={x}, y={y}")
            try:
                result = request_flip(token, floor, x, y)
            except urllib.error.HTTPError as exc:
                result = {
                    "code": -1,
                    "message": f"HTTP {exc.code}",
                    "data": exc.read().decode("utf-8", errors="replace"),
                }
            except urllib.error.URLError as exc:
                result = {"code": -1, "message": f"Request failed: {exc}", "data": None}

            row = cell_summary(x, y, result)
            row["raw"] = result
            rows.append(row)
            print(f"  => {row['summary']}")
            if args.delay > 0:
                time.sleep(args.delay)

    write_markdown(args.output, floor, rows)
    print(f"\nWrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
