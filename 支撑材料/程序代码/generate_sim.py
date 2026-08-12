# -*- coding: utf-8 -*-
"""
仿真数据集生成器 —— A题 问题1/问题2 统一数据格式
=================================================
依据: 资料/数据汇总/02_统一数据集格式_可直接入模.md 的 Schema
模型: 问题1 §7 多因子容量衰减模型 + 问题1 §3/§4 退化特征与三阶段 + 容量再生

每个模型参数均标注文献来源(来源键速查见 01_数据来源清单.md):
  [U2]=Ver22  [U5]=Sto19  [U6]=Str24  [U1]=Mad25
  [U4]=Wil20  [L1]=本地精读(湘潭大学,NASA)  [L2]=本地精读(FastClustering)
  [Sev19]=Severson2019 Nature Energy   [Zha20]=Zhang2020 Nature Commun.

输出(UTF-8 with BOM, 可直接 pandas.read_csv):
  sim_battery_cycles.csv  宽表: 每行 = 电池x循环, 含全部静态工况+健康特征+标签 (问题1/2 直接入模)
  battery_meta.csv        电池静态档案: 每电池一行 (子表)
  eis_spectrum.csv        简化EIS谱: 每电池x若干SOH点x10频点 (可选, 退化模式辨识用)

用法: python generate_sim.py
"""
import numpy as np, pandas as pd, os

rng = np.random.default_rng(20260810)   # 固定种子, 可复现
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "数据")   # 支撑材料/数据

# =====================================================================
# 1. 化学体系规格  (额定容量/电压: [L1] NASA 2Ah; [Sev19] LFP 1.1Ah; [U6] NCM 4.9Ah)
# =====================================================================
CHEM = {
    "NCM": dict(cell_format="21700", rated=4.9, volt=3.6, v_up=4.2, v_low=2.5,
                R0=0.015, ccct0=90.0, dispC=1.0, ce0=0.9985, src="Str24;Ver22;Sto19"),
    "LCO": dict(cell_format="18650", rated=2.0, volt=3.7, v_up=4.2, v_low=2.7,
                R0=0.150, ccct0=110.0, dispC=1.0, ce0=0.9985, src="L1(NASA);Ver22;Wil20"),
    "LFP": dict(cell_format="18650", rated=1.1, volt=3.3, v_up=3.6, v_low=2.0,
                R0=0.020, ccct0=60.0, dispC=4.0, ce0=0.9995, src="Sev19(MIT);Ver22"),
}

# =====================================================================
# 2. 多因子容量衰减模型  [U2 Ver22 式11] + [U5 Sto19] + [U6 Str24]
#    Q_loss = f(SoC,T,C,DoD) * n^z  ;  每循环损失率 r0 = 0.035 * f_T * f_C * f_D
# =====================================================================
R0_BASE = 0.035                      # 基准每循环损失率(%/循环), 校准: 温和工况约600-2000循环到EOL
EOL_THR = 0.70                       # EOL 阈值 = 额定容量70% [L1] + 题设
KNEE_SOH_LO, KNEE_SOH_HI = 0.82, 0.85  # SOH 82-85% 加速拐点 [U5 Sto19]
PHASE1_N, PHASE1_MUL = 25, 1.8       # 第一阶段: 前25循环初始陡降 [U5 Sto19]
PHASE3_MUL = 2.2                     # 第三阶段: 拐点后加速 [U5 Sto19]
CAP_REGEN_P = 0.05                   # 容量再生概率 [L1]
CAP_REGEN_LO, CAP_REGEN_HI = 0.4, 1.2  # 尖刺幅度 = (0.4~1.2) x 单循环损失(相对回升, 可逆)
CAP_NOISE = 0.0004                   # 容量测量噪声 σ (AR(1) 自相关, 模拟可逆波动)
AR_RHO = 0.90                        # AR(1) 自回归系数(低频平缓摆动, 曲线接近真实NASA形态)

def f_T(T):   return {10: 0.55, 23: 1.0, 35: 1.9, 45: 3.0}.get(T, 1.0)          # 10°C翻倍法则 [U2]
def f_C(C):   return 0.45 + 0.55 * (C ** 1.1)                                  # 倍率指数增长, >2C加速 [U2]
def f_D(DoD): return (DoD / 80.0) ** 2.2                                       # Wöhler, 80-90%加速显著 [U2][U5]

# =====================================================================
# 3. 试验设计矩阵  (对应 01_数据来源清单 §三/§五)
#    NCM 全因子: T x C x DoD  (Str24 温度范围 + Sto19 DOE矩阵)
#    LCO 补充:   T x C        (NASA风格, DoD 固定80)
#    LFP 快充:   C 1/2/3C     (Sev19 快充策略风格, T 23/35, DoD 固定80)
# =====================================================================
PLANS = [
    ("NCM", [(T, C, D) for T in (10, 23, 35, 45) for C in (0.5, 1.0, 2.0) for D in (70, 80, 90)], 3),
    ("LCO", [(T, C, 80) for T in (23, 35, 45) for C in (0.5, 1.0, 2.0)], 3),
    ("LFP", [(T, C, 80) for T in (23, 35) for C in (1.0, 2.0, 3.0)], 3),
]

SOC_WINDOW = {70: "15-85", 80: "10-90", 90: "5-95"}   # DoD->SoC窗口, 对应 [U5 Sto19] 试验设计
BATCH_SHIFT = {1: 0.000, 2: 0.008, 3: -0.006}         # 批次系统偏差 [L2 FastClustering]

# =====================================================================
# 4. 单电池循环生成
# =====================================================================
def gen_one(chem, T, C, DoD, rep, group_idx):
    spec = CHEM[chem]
    batch = (rep % 3) + 1
    # ---- 初始状态(批次差异 + 异常电池) [L2] ----
    q0 = spec["rated"] * (1 + BATCH_SHIFT[batch] + rng.normal(0, 0.015))
    is_abn = rng.random() < 0.02                      # 2% 异常电池(初始容量偏低) [L2]
    if is_abn: q0 *= 0.95
    r0 = R0_BASE * f_T(T) * f_C(C) * f_D(DoD)        # 每循环基准损失率
    knee = rng.uniform(KNEE_SOH_LO, KNEE_SOH_HI)     # 该电池拐点SOH
    R_end = spec["R0"] + (0.012 if chem != "NCM" else 0.0) + (0.16 + 0.12 * (DoD - 70) / 20.0) * (1 if chem != "LFP" else 0.15)
    # 内阻终点: 简单工况0.19Ω / 变DoD 0.31-0.35Ω [U4 Wil20]
    if chem == "LFP": R_end = spec["R0"] + 0.02

    bid = f"SIM-{chem}-{group_idx:02d}-{rep:02d}"
    rows, ar, soh_t = [], 0.0, 1.0
    eol_cycle, knee_cycle = None, None
    while soh_t > EOL_THR and len(rows) < 12000:          # 按趋势容量判定EOL(真值)
        n = len(rows) + 1
        mul = PHASE1_MUL if n <= PHASE1_N else (PHASE3_MUL if soh_t < knee else 1.0)
        loss = r0 * mul / 100.0
        soh_t -= loss                                     # 趋势容量(无噪声无尖刺) -> q_ref 真值
        ar = AR_RHO * ar + rng.normal(0, CAP_NOISE)       # AR(1) 测量/可逆波动
        spike = (rng.uniform(CAP_REGEN_LO, CAP_REGEN_HI) * loss
                 if rng.random() < CAP_REGEN_P else 0.0)  # 容量再生尖刺(相对loss短暂回升) [L1]
        soh = min(soh_t + ar + spike, 1.005)              # 观测容量(含噪声+尖刺)
        if knee_cycle is None and soh_t < knee: knee_cycle = n
        rows.append((n, soh, soh_t))
    if knee_cycle is None: knee_cycle = rows[-1][0]
    eol_cycle = rows[-1][0]

    # ---- 健康特征派生(自变量用趋势 soh_t, 特征单调、无NaN) [U4 Wil20] [U1 Mad25] ----
    d = pd.DataFrame(rows, columns=["cycle", "soh", "soh_t"])
    d["battery_id"] = bid
    d["capacity_Ah"] = d["soh"] * q0
    d["q_ref_Ah"] = d["soh_t"] * q0
    d["internal_resistance_ohm"] = (spec["R0"] + (R_end - spec["R0"])
        * ((1.0 - d["soh_t"]) / (1.0 - EOL_THR))) * (1 + rng.normal(0, 0.02, len(d)))
    d["ccct_min"] = spec["ccct0"] * (d["soh_t"]) ** 1.8 + rng.normal(0, 2.0, len(d))
    cv = (1.0 - d["soh_t"]).clip(lower=0.0)               # clamp, 避免早期soh>1时负数NaN
    d["cvct_min"] = 40.0 + 45.0 * cv ** 1.2 + rng.normal(0, 3.0, len(d))
    d["ce"] = spec["ce0"] - 0.006 * cv + rng.normal(0, 0.0002, len(d))
    d["phase_label"] = np.where(d["cycle"] <= PHASE1_N, 1,
                        np.where(d["soh_t"] < knee, 3, 2))
    d["knee_cycle"] = knee_cycle
    d["reached_eol"] = True
    d["rul_cycles"] = eol_cycle - d["cycle"]
    d["is_eol"] = d["cycle"] == eol_cycle
    # ---- 静态工况(广播到每行, 直接入模) ----
    strategy = (f"Fast2step_{int(C*2):d}C-{int(C):d}C" if chem == "LFP" else "CC-CV")
    d["chemistry"] = chem; d["cell_format"] = spec["cell_format"]
    d["rated_capacity_Ah"] = spec["rated"]; d["nominal_voltage_V"] = spec["volt"]
    d["temperature_C"] = T; d["charge_rate_C"] = C
    d["discharge_rate_C"] = spec["dispC"]; d["dod_pct"] = DoD
    d["soc_window"] = SOC_WINDOW[DoD]; d["charging_strategy"] = strategy
    d["v_upper_V"] = spec["v_up"]; d["v_lower_V"] = spec["v_low"]
    d["eol_threshold_pct"] = EOL_THR * 100
    d["batch_id"] = batch; d["is_abnormal"] = is_abn
    d["source_id"] = "SIM"; d["source_ref"] = spec["src"] + ";SIM"
    return d, (bid, chem, T, C, DoD, batch, is_abn, q0, r0, knee, eol_cycle, True)

# =====================================================================
# 5. 组装
# =====================================================================
meta_rows, frames, group_idx = [], [], 0
for chem, combos, reps in PLANS:
    for (T, C, D) in combos:
        group_idx += 1
        for rep in range(1, reps + 1):
            df, m = gen_one(chem, T, C, D, rep, group_idx)
            frames.append(df)
            meta_rows.append(m)

wide = pd.concat(frames, ignore_index=True)
meta = pd.DataFrame(meta_rows, columns=["battery_id", "chemistry", "temperature_C",
    "charge_rate_C", "dod_pct", "batch_id", "is_abnormal", "rated_capacity_Ah",
    "r0_pct_per_cyc", "knee_soh", "eol_cycle", "reached_eol"])

# =====================================================================
# 6. 简化EIS谱 (每电池 若干SOH点 x 10频点) [Zha20] [U1 ICA/DVA思路]
# =====================================================================
freq = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000.0]
soh_levels = [0.95, 0.90, 0.85, 0.80, 0.75, 0.70]
eis_rows = []
for bid, g in wide.groupby("battery_id"):
    r0_ohm = g["internal_resistance_ohm"].iloc[0] / 3  # 近似: R0 ≈ 首循环内阻
    for lv in soh_levels:
        row = g.loc[(g["soh"] - lv).abs().idxmin()]
        for f_ in freq:
            zr = row["internal_resistance_ohm"] * (1 + rng.normal(0, 0.01))
            zi = -(0.012 + 0.004 * np.log10(f_ / 10.0)) * (1 + 0.3 * (1 - row["soh"])) + rng.normal(0, 0.001)
            eis_rows.append((bid, int(row["cycle"]), round(row["soh"], 4), f_, round(zr, 6), round(zi, 6)))
eis = pd.DataFrame(eis_rows, columns=["battery_id", "cycle", "soh", "freq_Hz", "z_real_ohm", "z_imag_ohm"])

# =====================================================================
# 7. 写出 (utf-8-sig 兼容Excel) 与 摘要
# =====================================================================
wide.to_csv(os.path.join(DATA, "sim_battery_cycles.csv"), index=False, encoding="utf-8-sig")
meta.to_csv(os.path.join(DATA, "battery_meta.csv"), index=False, encoding="utf-8-sig")
eis.to_csv(os.path.join(DATA, "eis_spectrum.csv"), index=False, encoding="utf-8-sig")

nb = meta.shape[0]
life = meta.groupby("chemistry")["eol_cycle"].agg(["count", "min", "median", "max"])
not_reached = int((~meta["reached_eol"]).sum())
print(f"batteries: {nb}, rows: {len(wide):,}, not reaching EOL(70%): {not_reached}")
print("cycles-to-EOL by chemistry  count/min/median/max:")
print(life.to_string())
print("files:")
for f in ["sim_battery_cycles.csv", "battery_meta.csv", "eis_spectrum.csv"]:
    p = os.path.join(DATA, f); print(f"  {f}: {os.path.getsize(p)/1e6:.2f} MB")
