import argparse
import json
import os
import time
import urllib.error
from datetime import datetime

from flip_cell import DEFAULT_CONFIG, load_config, request_flip


DEFAULT_OUTPUT_DIR = "scan_results"
ALREADY_OPENED_MESSAGE = "格子已翻开"


def all_targets() -> list[tuple[int, int]]:
    return [(x, y) for y in range(5) for x in range(5)]


def classify_result(result: dict) -> str:
    data = result.get("data")
    if not isinstance(data, dict):
        return result.get("message") or "无格子数据"

    cell = data.get("cell")
    if not isinstance(cell, dict):
        return "无 cell 数据"

    box_type = cell.get("box_type")
    box_id = cell.get("box_id")
    if box_type == 9 or box_id == 40053:
        return "出口 / 传送门"
    if box_type == 0 and box_id == 0:
        return "普通空格"
    return f"事件格 box_type={box_type}, box_id={box_id}"


def is_already_opened(row: dict) -> bool:
    return row.get("code") == 30002 or row.get("message") == ALREADY_OPENED_MESSAGE


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


def resolve_output_path(output: str | None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output:
        return f"{DEFAULT_OUTPUT_DIR}/scan_{timestamp}.md"

    if "{timestamp}" in output:
        return output.replace("{timestamp}", timestamp)

    candidate = output
    if not os.path.exists(candidate):
        return candidate

    stem, ext = os.path.splitext(candidate)
    ext = ext or ".md"
    index = 2
    while True:
        next_candidate = f"{stem}_{index}{ext}"
        if not os.path.exists(next_candidate):
            return next_candidate
        index += 1


def format_cell_list(cells: list[tuple[int, int]]) -> str:
    if not cells:
        return "无"
    return "、".join(f"({x},{y})" for x, y in cells)


def append_rows(lines: list[str], rows: list[dict]) -> None:
    lines.extend(
        [
            "| 坐标 | code | message | box_type | box_id | need_choose | stamina | 判断 |",
            "| --- | ---: | --- | ---: | ---: | --- | ---: | --- |",
        ]
    )
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


def write_markdown(path: str, floor: int, targets: list[tuple[int, int]], rows: list[dict]) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active_rows = [row for row in rows if not is_already_opened(row)]
    opened_rows = [row for row in rows if is_already_opened(row)]

    lines = [
        "# 紫罗兰大冒险翻格扫描结果",
        "",
        f"- 生成时间：{generated_at}",
        f"- floor：{floor}",
        f"- 扫描坐标：{format_cell_list(targets)}",
        f"- 重点结果数量：{len(active_rows)}",
        f"- 已翻开数量：{len(opened_rows)}",
        "",
        "## 重点结果（非“格子已翻开”）",
        "",
    ]
    append_rows(lines, active_rows)

    lines.extend(["", "## 已翻开格子", ""])
    append_rows(lines, opened_rows)

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

    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan all 25 Violet Hold maze cells.")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Config JSON path, default: {DEFAULT_CONFIG}")
    parser.add_argument(
        "--output",
        help=(
            "Markdown output path. Default: scan_results/scan_<timestamp>.md. "
            "Use {timestamp} in the name for a timestamp placeholder."
        ),
    )
    parser.add_argument("--delay", type=float, default=0.2, help="Delay between requests in seconds, default: 0.2")
    args = parser.parse_args()

    config = load_config(args.config)
    token = config.get("token")
    floor = int(config.get("floor", 3))
    if not token:
        raise SystemExit(f"Missing token in {args.config}")

    targets = all_targets()
    output = resolve_output_path(args.output)
    print("扫描范围：全部 25 个格子")
    print(f"扫描坐标：{format_cell_list(targets)}")

    rows = []
    for x, y in targets:
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

    write_markdown(output, floor, targets, rows)
    print(f"\nWrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
