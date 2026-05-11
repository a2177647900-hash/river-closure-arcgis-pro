# -*- coding: utf-8 -*-
import arcpy
import os
import math
import itertools

arcpy.env.overwriteOutput = True


# =========================================================
# 只需要改这里
# =========================================================

# 输入河流双线
IN_RIVER = r"E:\河流原数据\aa\投影后.shp"

# 河流名称字段或河流编码字段
# 例如："NAME"、"河流名称"、"RIVER_NAME"、"HYD_NAME"
GROUP_FIELD = "HHDM"

# 输出 GDB
OUT_GDB = r"E:\河流原数据\aa\result.gdb"

# 最大封口距离，单位是米
# 0 表示不限制
# 建议第一次可以填 0，成功后再根据实际情况改成 200、500、1000 等
MAX_CLOSE_DIST = 0


# =========================================================
# 工具函数
# =========================================================

def msg(text):
    arcpy.AddMessage(text)
    print(text)


def check_input():
    if not arcpy.Exists(IN_RIVER):
        raise RuntimeError("输入河流线不存在，请检查 IN_RIVER 路径。")

    fields = [f.name for f in arcpy.ListFields(IN_RIVER)]
    if GROUP_FIELD not in fields:
        raise RuntimeError(f"找不到分组字段：{GROUP_FIELD}，请检查字段名是否正确。")

    desc = arcpy.Describe(IN_RIVER)
    sr = desc.spatialReference

    if sr is None or sr.name == "Unknown":
        raise RuntimeError("输入数据没有定义坐标系，请先定义投影。")

    if sr.type == "Geographic":
        raise RuntimeError(
            "输入数据是地理坐标系，经纬度单位不是米。\n"
            "请先在 ArcGIS Pro 中使用 Project 工具投影到米制坐标系后再运行。\n"
            "例如 CGCS2000 高斯克吕格投影、UTM、地方投影坐标系等。"
        )

    return sr


def create_gdb_if_not_exists(gdb_path):
    folder = os.path.dirname(gdb_path)
    gdb_name = os.path.basename(gdb_path)

    if not arcpy.Exists(gdb_path):
        arcpy.management.CreateFileGDB(folder, gdb_name)
        msg(f"已创建输出数据库：{gdb_path}")


def safe_delete(path):
    if arcpy.Exists(path):
        arcpy.management.Delete(path)


def get_first_last_point(polyline):
    """
    获取线要素的起点和终点
    """
    if polyline is None:
        return None, None

    first = polyline.firstPoint
    last = polyline.lastPoint

    if first is None or last is None:
        return None, None

    return first, last


def distance(p1, p2):
    return math.sqrt((p1.X - p2.X) ** 2 + (p1.Y - p2.Y) ** 2)


def greedy_pair_points(points):
    """
    最近距离贪心配对。
    points: [(group_value, point_geometry, source_oid, endpoint_type), ...]
    返回：[(point1, point2, dist), ...]
    """
    remaining = points[:]
    pairs = []

    while len(remaining) >= 2:
        min_d = None
        min_pair = None

        for i, j in itertools.combinations(range(len(remaining)), 2):
            p1 = remaining[i][1]
            p2 = remaining[j][1]
            d = distance(p1, p2)

            if min_d is None or d < min_d:
                min_d = d
                min_pair = (i, j)

        i, j = min_pair

        # 判断是否超过最大封口距离
        if MAX_CLOSE_DIST and min_d > MAX_CLOSE_DIST:
            break

        # 注意先取值，再删除
        item1 = remaining[i]
        item2 = remaining[j]

        pairs.append((item1, item2, min_d))

        # 从大索引开始删，防止索引变化
        for index in sorted([i, j], reverse=True):
            remaining.pop(index)

    return pairs, remaining


# =========================================================
# 主程序
# =========================================================

def main():
    msg("开始处理河流双线封闭...")

    sr = check_input()
    create_gdb_if_not_exists(OUT_GDB)
    repaired = os.path.join(OUT_GDB, "r01_repair_geometry")
    single_1 = os.path.join(OUT_GDB, "r02_singlepart")
    dissolve = os.path.join(OUT_GDB, "r03_dissolve_by_river")
    single_2 = os.path.join(OUT_GDB, "r04_dissolve_singlepart")
    endpoints_fc = os.path.join(OUT_GDB, "r05_endpoints")
    close_line_fc = os.path.join(OUT_GDB, "r06_close_lines")
    closed_boundary = os.path.join(OUT_GDB, "r07_closed_boundary")
    river_polygon = os.path.join(OUT_GDB, "r08_river_polygon")

    # 清理旧结果
    for fc in [
        repaired,
        single_1,
        dissolve,
        single_2,
        endpoints_fc,
        close_line_fc,
        closed_boundary,
        river_polygon
    ]:
        safe_delete(fc)

    # 1. 复制一份并修复几何
    msg("1/8 复制并修复几何...")
    arcpy.management.CopyFeatures(IN_RIVER, repaired)
    arcpy.management.RepairGeometry(repaired)

    # 2. 多部件至单部件
    msg("2/8 多部件至单部件...")
    arcpy.management.MultipartToSinglepart(repaired, single_1)

    # 3. 按河流名称或编码融合
    msg("3/8 按河流名称或编码融合...")
    arcpy.management.Dissolve(
        in_features=single_1,
        out_feature_class=dissolve,
        dissolve_field=[GROUP_FIELD],
        multi_part="SINGLE_PART",
        unsplit_lines="DISSOLVE_LINES"
    )

    # 4. 再次多部件至单部件
    msg("4/8 再次多部件至单部件...")
    arcpy.management.MultipartToSinglepart(dissolve, single_2)

    # 5. 提取两端点
    msg("5/8 提取河流线两端点...")
    arcpy.management.FeatureVerticesToPoints(
        in_features=single_2,
        out_feature_class=endpoints_fc,
        point_location="BOTH_ENDS"
    )

    # 6. 创建封口线图层
    msg("6/8 创建封口线...")
    arcpy.management.CreateFeatureclass(
        out_path=OUT_GDB,
        out_name=os.path.basename(close_line_fc),
        geometry_type="POLYLINE",
        spatial_reference=sr
    )

    arcpy.management.AddField(close_line_fc, GROUP_FIELD, "TEXT", field_length=100)
    arcpy.management.AddField(close_line_fc, "CLOSE_LEN", "DOUBLE")
    arcpy.management.AddField(close_line_fc, "NOTE", "TEXT", field_length=100)

    # 7. 读取端点并按河流分组
    msg("7/8 按河流分组连接最近端点...")

    grouped_points = {}

    fields = ["OID@", "SHAPE@", GROUP_FIELD]

    with arcpy.da.SearchCursor(endpoints_fc, fields) as cursor:
        for oid, geom, group_value in cursor:
            if group_value is None:
                continue

            p = geom.firstPoint
            if p is None:
                continue

            grouped_points.setdefault(group_value, []).append(
                (group_value, p, oid, "END")
            )

    total_pairs = 0
    skipped_groups = []

    insert_fields = ["SHAPE@", GROUP_FIELD, "CLOSE_LEN", "NOTE"]

    with arcpy.da.InsertCursor(close_line_fc, insert_fields) as icur:
        for group_value, pts in grouped_points.items():

            if len(pts) < 2:
                skipped_groups.append((group_value, len(pts), "端点少于2个"))
                continue

            if len(pts) % 2 != 0:
                skipped_groups.append((group_value, len(pts), "端点数量为奇数，可能存在异常"))

            pairs, remaining = greedy_pair_points(pts)

            if not pairs:
                skipped_groups.append((group_value, len(pts), "未生成封口线，可能超过最大封口距离"))
                continue

            for item1, item2, d in pairs:
                p1 = item1[1]
                p2 = item2[1]

                array = arcpy.Array([p1, p2])
                line = arcpy.Polyline(array, sr)

                note = "auto_close"
                icur.insertRow([line, str(group_value), d, note])
                total_pairs += 1

            if remaining:
                skipped_groups.append((group_value, len(remaining), "有剩余未配对端点"))

    msg(f"已生成封口线数量：{total_pairs}")

    if skipped_groups:
        msg("以下河流可能需要人工检查：")
        for item in skipped_groups[:50]:
            msg(f"  河流：{item[0]}，端点数/剩余数：{item[1]}，原因：{item[2]}")

        if len(skipped_groups) > 50:
            msg(f"  还有 {len(skipped_groups) - 50} 条未显示。")

    # 8. 合并原河流线和封口线
    msg("8/8 合并闭合边界并线转面...")

    arcpy.management.Merge(
        inputs=[single_2, close_line_fc],
        output=closed_boundary
    )

    # 线转面
    arcpy.management.FeatureToPolygon(
        in_features=[closed_boundary],
        out_feature_class=river_polygon
    )

    msg("处理完成！")
    msg(f"封口线：{close_line_fc}")
    msg(f"闭合边界线：{closed_boundary}")
    msg(f"河流面：{river_polygon}")

    msg("建议下一步检查 08_river_polygon 是否有异常大面、碎面、漏面。")


if __name__ == "__main__":
    main()
