# -*- coding: utf-8 -*-
"""
从富特征仿真主数据派生 A→B→C 交接文件（符合《数据格式规范 v1.1》）
====================================================================
输入: sim_battery_cycles.csv   (建模主数据, 32列富特征, 保持不动)
输出: battery_timeseries.csv   (全时序: 规范9字段在前 + 富特征列保留)
      battery_final_states.csv (每电池末行 + RUL/grade 占位, 供成员B/C填)

字段映射 (旧名 -> 规范名):
  soh                     -> SOH        (观测容量保持率, 含噪声/容量再生)
  internal_resistance_ohm -> resistance
  temperature_C           -> T
  charge_rate_C           -> c_rate     (充电倍率; 放电倍率另存 discharge_rate_C)
  dod_pct (80)            -> dod (0.8)  (**小数**, 规范强制)
  phase_label (1/2/3)     -> 保留为建模列; stage 按规范 SOH 阈值函数生成
  battery_id              -> cond_id (0-based 电池编号) + condition (工况串)

派生文件不改动主数据, 问题1/2 建模仍读 sim_battery_cycles.csv;
A 成员用本脚本产出交接文件, B/C 在其上填 RUL / grade。

用法: python convert_to_spec.py
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "数据")   # 支撑材料/数据


def get_stage(soh: float) -> str:
    """规范 v1.1 阶段划分（SOH 阈值法，接口标准）"""
    if soh >= 0.90:
        return "正常运行"
    elif soh >= 0.80:
        return "性能劣化"
    else:
        return "失效临界"


def get_condition(T, c_rate, dod) -> str:
    """工况串: T{温度}_C{倍率}_D{放电深度(小数)}，如 T23_C1.0_D0.8"""
    return f"T{int(T)}_C{c_rate:.1f}_D{dod:.1f}"


def main():
    src = pd.read_csv(os.path.join(DATA, "sim_battery_cycles.csv"))

    # ---- 编号: cond_id 按 battery_id 首次出现顺序 0-based ----
    order = src["battery_id"].drop_duplicates().tolist()
    cid = {b: i for i, b in enumerate(order)}
    src["cond_id"] = src["battery_id"].map(cid)
    src["condition"] = [
        get_condition(T, C, D)
        for T, C, D in zip(src["temperature_C"], src["charge_rate_C"], src["dod_pct"] / 100.0)
    ]

    # ---- 规范字段（顺序与规范表一致） ----
    spec = pd.DataFrame({
        "cycle":     src["cycle"],
        "SOH":       src["soh"],
        "resistance":src["internal_resistance_ohm"],
        "T":         src["temperature_C"],
        "c_rate":    src["charge_rate_C"],
        "dod":       src["dod_pct"] / 100.0,
        "condition": src["condition"],
        "cond_id":   src["cond_id"],
        "stage":     [get_stage(s) for s in src["soh"]],
    })

    # ---- 富特征保留列（规范未覆盖的建模字段, 原样附带） ----
    EXTRAS = ["battery_id", "soh_t", "capacity_Ah", "q_ref_Ah", "ccct_min", "cvct_min",
              "ce", "phase_label", "knee_cycle", "rul_cycles", "is_eol", "reached_eol",
              "chemistry", "cell_format", "rated_capacity_Ah", "nominal_voltage_V",
              "discharge_rate_C", "soc_window", "charging_strategy", "v_upper_V",
              "v_lower_V", "eol_threshold_pct", "batch_id", "is_abnormal",
              "source_id", "source_ref"]
    for c in EXTRAS:
        spec[c] = src[c].values

    # ---- 最终状态表: 每电池最后一行(到达EOL) + RUL/grade 占位 ----
    last = src.sort_values(["cond_id", "cycle"]).groupby("cond_id").tail(1).copy()
    final = pd.DataFrame({
        "cycle":     last["cycle"],
        "SOH":       last["soh"],
        "resistance":last["internal_resistance_ohm"],
        "T":         last["temperature_C"],
        "c_rate":    last["charge_rate_C"],
        "dod":       last["dod_pct"] / 100.0,
        "condition": last["condition"],
        "cond_id":   last["cond_id"],
        "stage":     [get_stage(s) for s in last["soh"]],
        "RUL":       np.nan,   # 成员B计算后填入
        "grade":     "",       # 成员C分级后填入
    })
    for c in EXTRAS:
        final[c] = last[c].values

    ts_path  = os.path.join(DATA, "battery_timeseries.csv")
    fs_path  = os.path.join(DATA, "battery_final_states.csv")
    spec.to_csv(ts_path, index=False, encoding="utf-8-sig")
    final.to_csv(fs_path, index=False, encoding="utf-8-sig")

    # ---- 摘要校验 ----
    print(f"battery_timeseries : {len(spec):,} 行 x {spec.shape[1]} 列 -> {ts_path}")
    print(f"battery_final_states: {len(final)} 行 x {final.shape[1]} 列 -> {fs_path}")
    print(f"电池数(cond_id): {spec['cond_id'].nunique()}  工况串数: {spec['condition'].nunique()}")
    print(f"dod 范围: {spec['dod'].min()} ~ {spec['dod'].max()} (小数)")
    print(f"SOH 范围: {spec['SOH'].min():.4f} ~ {spec['SOH'].max():.4f}")
    print("stage 分布:", spec["stage"].value_counts().to_dict())
    print("condition 示例:", sorted(spec["condition"].unique())[:4], "...")
    assert spec["dod"].between(0, 1).all(), "dod 必须为小数且在 [0,1]"
    assert spec["SOH"].between(0.68, 1.01).all(), "SOH 越界"
    print("校验通过 [OK]")


if __name__ == "__main__":
    main()
