# ziluolan

炉石传说小程序活动「紫罗兰大冒险」抓包数据分析与辅助脚本。

这个仓库用于整理迷宫地图、任务、奖励、剧情事件，以及手动调用翻格接口来确认格子类型。当前结论是：出口坐标没有在初始地图数据里直接暴露，只能翻开格子后看服务器返回是否为出口。

## 文件说明

- `info.json`：当前楼层迷宫状态数据样例。
- `task.json`：活动配置，包含守卫盘问、特殊任务、剧情事件、抉择事件、结识角色事件、宝箱、传送门等配置。
- `yige.json`：翻格接口返回样例。
- `4-2.json`：翻开 `(4,2)` 的返回样例，结果为剧情事件格。
- `4-3.json`：翻开 `(4,3)` 的返回样例，结果为普通空格。
- `puzzle.js`：页面加载脚本样例。
- `flip_cell.py`：翻格请求脚本，默认读取 `flip_config.json`。
- `scan_all_cells.py`：批量请求 25 个坐标并输出 Markdown 扫描结果。
- `flip_config.example.json`：配置文件示例，不包含真实 token。
- `剧情事件统计.md`：已整理的 400 系列事件表。
- `迷宫坐标参照图.svg` / `迷宫坐标参照图.png`：迷宫坐标参考图。
- `LICENSE`：开源许可证。

## 使用翻格脚本

先复制示例配置：

```powershell
Copy-Item .\flip_config.example.json .\flip_config.json
```

编辑 `flip_config.json`：

```json
{
  "token": "paste-your-Xcxtoken-here",
  "floor": 3,
  "x": 1,
  "y": 0
}
```

运行：

```powershell
py .\flip_cell.py
```

也可以临时覆盖坐标：

```powershell
py .\flip_cell.py --x 2 --y 1
```

脚本会打印接口返回，并额外提示格子类型：

- `box_type: 9` 或 `box_id: 40053`：出口 / 传送门。
- `box_type: 0` 且 `box_id: 0`：普通空格。
- 其他情况：事件格。
- 如果返回 `data: null`，例如“格子已翻开”，脚本会正常提示，不会报错退出。

## 批量扫描全部坐标

`scan_all_cells.py` 会从 `(0,0)` 到 `(4,4)` 请求全部 25 个格子，并把汇总和原始返回写入 Markdown 文档：

```powershell
py .\scan_all_cells.py
```

默认输出：

```text
scan_results.md
```

也可以指定输出文件：

```powershell
py .\scan_all_cells.py --output floor3_scan.md
```

注意：这个脚本会连续调用翻格接口。未翻开的格子可能会消耗活动体力或改变服务器状态，运行前请确认。

## 敏感文件

`flip_config.json` 会包含你的 `Xcxtoken`，不要提交或公开。仓库已通过 `.gitignore` 忽略：

- `flip_config.json`
- `flip_local.py`
- `__pycache__/`
- `*.py[cod]`

## 作者

zentrix566
