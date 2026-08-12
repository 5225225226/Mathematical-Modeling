# -*- coding: utf-8 -*-
"""
A题 问题1 全流程求解脚本 —— 退化特征分析与影响因子辨识
=====================================================
对应论文: 问题一《退化特征分析与影响因子辨识》全章节
数据:     支撑材料/数据/  (battery_meta / battery_timeseries / battery_final_states)
输出:     支撑材料/图表/q1_*.png (4 张问题一配图)
          支撑材料/数据/q1_results.json (问题一全部量化结果, 供论文表格取值核对)
运行:     python 支撑材料/程序代码/q1_solution.py

模块与论文章节对照:
  §1 多维退化特征体系           -> CCCT/CVCT 典型电池特征变化 (表 tab:feat 数据支撑)
  §2 退化规律可视化与分析       -> fig:q1_decay / fig:q1_resistance
  §3 退化三阶段划分模型         -> fig:q1_phase / 拐点统计 / stage 三阶段占比
  §4 影响因子量化模型           -> fig:q1_importance / 表 tab:factor_quant
                                  (随机森林 + Pearson + Spearman + 灰色关联 + 熵权 + 组合权重)
  §5 多因子综合退化模型         -> eq:loss_rate 参数标定 (r0 = r_base*f_T*f_C*f_D, m_phase)
  §6 仿真数据合理性验证         -> 表 tab:temp_life / tab:factor_life / 内阻增幅 / 容量再生
"""
import os, json, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.stats import pearsonr, spearmanr
from sklearn.ensemble import RandomForestRegressor

# ---------------- 环境与路径 ----------------
for f in font_manager.fontManager.ttflist:
    if f.name == "Microsoft YaHei":
        plt.rcParams["font.family"] = f.name
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("MM_ROOT", os.path.dirname(HERE))      # 支撑材料/
FIG  = os.path.join(ROOT, "图表")
DATA = os.path.join(ROOT, "数据")
os.makedirs(FIG, exist_ok=True)

# ---------------- 数据读取 ----------------
meta = pd.read_csv(os.path.join(DATA, "battery_meta.csv"), encoding="utf-8-sig")
fin  = pd.read_csv(os.path.join(DATA, "battery_final_states.csv"), encoding="utf-8-sig")
ts   = pd.read_csv(os.path.join(DATA, "battery_timeseries.csv"), encoding="utf-8-sig",
                   usecols=["battery_id","cycle","SOH","soh_t","resistance","T","c_rate",
                            "dod","ccct_min","cvct_min","ce","phase_label","knee_cycle",
                            "stage","chemistry"])
ts = ts.sort_values(["battery_id","cycle"]).reset_index(drop=True)

results = {}


# =====================================================================
# §1 多维退化特征体系 —— 典型电池 CCCT/CVCT 特征变化 (论文表 tab:feat 数据支撑)
# =====================================================================
# 选取第一块 NCM 电池作为示例 (与论文"以某典型 NCM 电池为例"一致)
bid_ex = meta[meta["chemistry"] == "NCM"]["battery_id"].iloc[0]
s_ex = ts[ts["battery_id"] == bid_ex]
ccct0, ccct1 = s_ex["ccct_min"].iloc[0], s_ex["ccct_min"].iloc[-1]
cvct0, cvct1 = s_ex["cvct_min"].iloc[0], s_ex["cvct_min"].iloc[-1]
results["q1_feature_example"] = {
    "battery": bid_ex,
    "ccct_min": [round(ccct0,1), round(ccct1,1), round((ccct1/ccct0-1)*100,1)],
    "cvct_min": [round(cvct0,1), round(cvct1,1), round((cvct1/cvct0-1)*100,1)],
}


# =====================================================================
# §2 退化规律可视化与分析
# =====================================================================
# 2.1 不同温度下容量(SOH)衰减曲线 —— fig:q1_decay
sel = meta.groupby("temperature_C").head(1)["battery_id"].tolist()[:6]
sample = ts[ts["battery_id"].isin(sel)]
fig, ax = plt.subplots(figsize=(6.6, 4.2))
for bid, g in sample.groupby("battery_id"):
    T = g["T"].iloc[0]
    ax.plot(g["cycle"], g["SOH"], lw=1.4, label=f"T={int(T)}°C")
ax.axhline(0.70, ls="--", c="red", lw=1.2, label="EOL (SOH=70%)")
ax.set_xlabel("循环次数 n"); ax.set_ylabel("SOH")
ax.set_title("容量衰减曲线（不同环境温度）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "q1_decay.png"), dpi=160); plt.close(fig)

# 2.2 内阻随循环增长曲线 (按温度着色) —— fig:q1_resistance
sel_r = meta[meta["chemistry"] == "NCM"].groupby("temperature_C").head(1)["battery_id"].tolist()
sample_r = ts[ts["battery_id"].isin(sel_r)]
fig, ax = plt.subplots(figsize=(6.6, 4.2))
for bid, g in sample_r.groupby("battery_id"):
    ax.plot(g["cycle"], g["resistance"], lw=1.4, label=f"T={int(g['T'].iloc[0])}°C")
ax.set_xlabel("循环次数 n"); ax.set_ylabel("内阻 $R$ (Ω)")
ax.set_title("内阻随循环增长曲线（NCM 体系，不同温度）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "q1_resistance.png"), dpi=160); plt.close(fig)

# 2.3 全批/分体系内阻增幅统计 (论文: 全批平均增幅约11.2倍, NCM由0.016增至0.236约15倍)
r0 = ts.groupby("battery_id")["resistance"].first()
rn = ts.groupby("battery_id")["resistance"].last()
fold = rn / r0
res_stats = {"fold_mean_all": round(float(fold.mean()), 2), "fold_median_all": round(float(fold.median()), 2)}
for chem in ["NCM", "LCO", "LFP"]:
    ids = meta[meta["chemistry"] == chem]["battery_id"]
    res_stats[f"{chem}_r0_mean"] = round(float(r0[ids].mean()), 3)
    res_stats[f"{chem}_rn_mean"] = round(float(rn[ids].mean()), 3)
    res_stats[f"{chem}_fold_mean"] = round(float(fold[ids].mean()), 2)
results["q1_resistance"] = res_stats


# =====================================================================
# §3 退化三阶段划分模型
# =====================================================================
# 3.1 单电池三阶段划分示例 —— fig:q1_phase (用 phase_label 真实三阶段着色)
g = ts[ts["battery_id"] == bid_ex].sort_values("cycle")
fig, ax = plt.subplots(figsize=(6.6, 4.2))
ax.plot(g["cycle"], g["SOH"], lw=1.3, color="#34495e", label="SOH 实测")
ax.plot(g["cycle"], g["soh_t"], lw=1.1, ls="--", color="#c0392b", label="退化趋势 $soh_t$")
ph1 = g[g["phase_label"] == 1]; ph2 = g[g["phase_label"] == 2]; ph3 = g[g["phase_label"] == 3]
ax.axvspan(ph1["cycle"].min(), ph1["cycle"].max(), alpha=0.10, color="green", label="阶段Ⅰ 初始陡降")
ax.axvspan(ph2["cycle"].min(), ph2["cycle"].max(), alpha=0.10, color="#2980b9", label="阶段Ⅱ 近似线性")
ax.axvspan(ph3["cycle"].min(), ph3["cycle"].max(), alpha=0.14, color="orange", label="阶段Ⅲ 加速失效")
ax.axhline(0.70, ls="--", c="red", lw=1)
ax.set_xlabel("循环次数 n"); ax.set_ylabel("SOH")
ax.set_title(f"三阶段划分示例（{bid_ex}）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "q1_phase.png"), dpi=160); plt.close(fig)

# 3.2 拐点统计 (每电池 knee_cycle: 趋势 soh_t 首次跌破该电池 knee_soh 的循环)
knee = ts.groupby("battery_id")["knee_cycle"].last()
results["q1_knee"] = {
    "knee_soh_window": [0.82, 0.85],
    "knee_soh_mean": round(float(meta["knee_soh"].mean()), 3),
    "knee_cycle_mean": round(float(knee.mean()), 1),
    "knee_cycle_median": int(knee.median()),
}

# 3.3 三阶段记录占比 (接口标准 stage: SOH阈值法)
stage_pct = ts["stage"].value_counts(normalize=True)
results["q1_stage_pct"] = {k: round(float(v * 100), 1) for k, v in stage_pct.items()}


# =====================================================================
# §4 影响因子量化模型 —— 表 tab:factor_quant (多方法交叉验证)
# =====================================================================
# 响应: 每循环容量损失率 r = Q_loss_pct / n_cycles
agg = ts.groupby("battery_id").agg(
    n_cycles=("cycle", "max"),
    Q_loss_pct=("SOH", lambda s: (1 - s.min()) * 100),
    T=("T", "first"), C=("c_rate", "first"), DoD=("dod", "first"),
).reset_index()
agg["r"] = agg["Q_loss_pct"] / agg["n_cycles"]
X = agg[["T", "C", "DoD"]].values
y = agg["r"].values

# 4.1 随机森林特征重要性 (树数300) —— fig:q1_importance
rf = RandomForestRegressor(n_estimators=300, random_state=1).fit(X, y)
imp = rf.feature_importances_
fig, ax = plt.subplots(figsize=(6.6, 3.6))
labels = ["温度 T", "倍率 C", "放电深度 DoD"]
bars = ax.bar(labels, imp, color=["#c0392b", "#e67e22", "#2980b9"])
for b, v in zip(bars, imp):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.2f}", ha="center", fontsize=9)
ax.set_ylabel("随机森林特征重要性"); ax.set_ylim(0, imp.max() * 1.2)
ax.set_title("影响因子重要性（每循环容量损失率）")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "q1_importance.png"), dpi=160); plt.close(fig)

# 4.2 相关性分析 (Pearson / Spearman)
pearson = [round(pearsonr(X[:, i], y)[0], 2) for i in range(3)]
spearman = [round(spearmanr(X[:, i], y)[0], 2) for i in range(3)]

# 4.3 灰色关联度 (rho=0.5, 各序列 min-max 归一)
def grey_relational(X, y, rho=0.5):
    t = (y - y.min()) / (y.max() - y.min() + 1e-12)
    g = []
    for j in range(X.shape[1]):
        x = (X[:, j] - X[:, j].min()) / (X[:, j].max() - X[:, j].min() + 1e-12)
        delta = np.abs(x - t)
        rel = (delta.min() + rho * delta.max()) / (delta + rho * delta.max())
        g.append(rel.mean())
    return np.array(g)

grey = grey_relational(X, y)

# 4.4 熵权法 (各列 min-max 归一后按信息熵确定客观权重)
def entropy_weight(X):
    W = []
    for j in range(X.shape[1]):
        x = (X[:, j] - X[:, j].min()) / (X[:, j].max() - X[:, j].min() + 1e-12)
        p = x / x.sum(); p = p + 1e-12
        e = -(p * np.log(p)).sum() / np.log(len(x))
        W.append(1 - e)
    W = np.array(W)
    return W / W.sum()

entropy = entropy_weight(X)

# 4.5 组合权重 w = alpha*w_grey + (1-alpha)*w_entropy, 再归一 (alpha=0.5)
alpha = 0.5
comb_raw = alpha * grey + (1 - alpha) * entropy
comb = comb_raw / comb_raw.sum()

factor_names = ["T", "C", "DoD"]
results["q1_factor_quant"] = {
    "rf":  {k: round(float(v), 2) for k, v in zip(factor_names, imp)},
    "pearson":  {k: v for k, v in zip(factor_names, pearson)},
    "spearman": {k: v for k, v in zip(factor_names, spearman)},
    "grey":     {k: round(float(v), 2) for k, v in zip(factor_names, grey)},
    "entropy":  {k: round(float(v), 2) for k, v in zip(factor_names, entropy)},
    "comb":     {k: round(float(v), 2) for k, v in zip(factor_names, comb)},
}


# =====================================================================
# §5 多因子综合退化模型 —— eq:loss_rate 参数标定 (与 generate_sim.py 一致)
# =====================================================================
# 说明: 综合退化模型在数据生成阶段即按本节公式实现 (data/dataset/generate_sim.py),
#       此处复述并输出标定参数, 供论文表 tab:params 取值核对。
model_params = {
    "r_base_pct_per_cyc": 0.035,                       # 基准每循环损失率
    "f_T": {10: 0.55, 23: 1.0, 35: 1.9, 45: 3.0},      # Arrhenius 10°C 翻倍律
    "f_C": "0.45 + 0.55*C^1.1",                        # 倍率指数增长
    "f_D": "(DoD/0.8)^2.2",                            # Wöhler 疲劳
    "m_phase": {1: 1.8, 2: 1.0, 3: 2.2},               # 阶段乘子
    "knee_soh": "0.82-0.85",                           # 加速拐点窗口
    "eol": 0.70,                                       # 失效阈值
}
results["q1_model_params"] = model_params


# =====================================================================
# §6 仿真数据合理性验证
# =====================================================================
# 6.1 温度—寿命关系 (表 tab:temp_life) + 温度与寿命 Pearson 相关
tl = meta.groupby("temperature_C")["eol_cycle"].mean()
tl_ratios = tl.values[1:] / tl.values[:-1]
temp_life_pearson = round(float(np.corrcoef(meta["temperature_C"], meta["eol_cycle"])[0, 1]), 2)
results["q1_temp_life"] = {
    "life": {int(k): round(float(v)) for k, v in tl.items()},
    "adjacent_ratio": [round(float(r), 2) for r in tl_ratios],
    "pearson_T_life": temp_life_pearson,
}

# 6.2 倍率/放电深度边际寿命 (表 tab:factor_life, NCM 全因子子集)
ncm = meta[meta["chemistry"] == "NCM"]
cc = ncm.groupby("charge_rate_C")["eol_cycle"].mean()
dd = ncm.groupby("dod_pct")["eol_cycle"].mean()
results["q1_factor_life"] = {
    "C":   {str(k): round(float(v)) for k, v in cc.items()},
    "C_ratio":  [round(float(a / b), 2) for a, b in zip(cc.values[1:], cc.values[:-1])],
    "DoD": {str(k): round(float(v)) for k, v in dd.items()},
    "DoD_ratio": [round(float(a / b), 2) for a, b in zip(dd.values[1:], dd.values[:-1])],
}

# 6.3 容量再生统计 (单循环回升样本占比: SOH 较上一循环回升)
prev = ts.groupby("battery_id")["SOH"].shift(1)
regen_pct = float((ts["SOH"] > prev).mean() * 100)
results["q1_regen"] = {"rebound_pct": round(regen_pct, 1)}

# 6.4 数据集规模 (表 tab:dataset)
results["q1_dataset"] = {
    "n_battery": int(len(meta)),
    "n_rows": int(len(ts)),
    "chem_count": {k: int(v) for k, v in meta["chemistry"].value_counts().items()},
}


# =====================================================================
# 输出
# =====================================================================
with open(os.path.join(DATA, "q1_results.json"), "w", encoding="utf-8") as fp:
    json.dump(results, fp, ensure_ascii=False, indent=2)

print("=== 问题1 关键结果 ===")
print("特征示例:", results["q1_feature_example"])
print("内阻增幅:", results["q1_resistance"])
print("拐点统计:", results["q1_knee"])
print("三阶段占比:", results["q1_stage_pct"])
print("因子量化:")
print("  RF 重要性:", results["q1_factor_quant"]["rf"])
print("  Pearson :", results["q1_factor_quant"]["pearson"])
print("  Spearman:", results["q1_factor_quant"]["spearman"])
print("  灰色关联:", results["q1_factor_quant"]["grey"])
print("  熵权    :", results["q1_factor_quant"]["entropy"])
print("  组合权重:", results["q1_factor_quant"]["comb"])
print("温度-寿命:", results["q1_temp_life"])
print("倍率/DoD边际寿命:", results["q1_factor_life"])
print("容量再生回升占比:", results["q1_regen"])
print("=== 图已生成:", [f for f in os.listdir(FIG) if f.startswith("q1_")])
print("=== 结果已保存: 支撑材料/数据/q1_results.json")
