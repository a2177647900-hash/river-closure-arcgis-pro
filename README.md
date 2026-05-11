# River Closure Tool for ArcGIS Pro

## 项目简介

本项目是基于 ArcGIS Pro、Python 和 ArcPy 开发的河流双线闭合处理工具，主要用于河流线要素的端点检查、几何修复、辅助闭合线生成与 GIS 数据质量检查。

该工具适用于自然资源、水利、农业农村、国土空间数据整理等场景，可用于提升河流线数据处理效率，减少人工检查和手动编辑成本。

## 功能特点

- 支持河流线要素的复制与几何修复
- 支持按河流名称字段进行分组处理
- 支持河流线端点识别与辅助闭合处理
- 支持输出 File Geodatabase 结果数据
- 支持投影坐标系检查，避免经纬度单位导致的距离计算误差
- 适用于 GIS 数据质检、空间数据整理和河流双线闭合处理流程

## 技术环境

- ArcGIS Pro
- Python
- ArcPy
- File Geodatabase
- Shapefile / Feature Class

## 文件说明

| 文件名 | 说明 |
|---|---|
| `river_closure_tool.py` | 河流双线闭合处理主脚本 |
| `README.md` | 项目说明文档 |

## 使用方法

1. 准备河流线数据。
2. 确保输入数据为投影坐标系，单位建议为米。
3. 打开 `river_closure_tool.py` 文件。
4. 修改脚本中的输入路径、输出路径和河流名称字段。
5. 在 ArcGIS Pro 的 Python 窗口、Notebook 或 Python 环境中运行脚本。
6. 检查输出结果数据库中的闭合处理结果。

## 需要修改的参数

运行前需要根据自己的数据修改以下参数：

```python
IN_RIVER = r"你的河流线数据路径"
GROUP_FIELD = "河流名称字段"
OUT_GDB = r"输出结果数据库路径"

