# -*- coding: utf-8 -*-
"""
A题 数据预处理 & 退化特征 补充图表脚本
=====================================
生成:
  支撑材料/图表/q0_preprocess.png  原始SOH(含AR(1)噪声+容量再生尖刺) vs 平滑趋势 soh_t 对比
  支撑材料/图表/q1_resistance.png  内阻随循环增长曲线(按温度着色, 双对数下近似线性)
运行: python 支撑材料/程序代码/preprocess_figs.py
"""
import os, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in font_manager.fontManager.ttflist:
    if f.name == "Microsoft YaHei":
        plt.rcParams["font.family"] = f.name
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG  = os.path.join(ROOT, "图表")
DATA = os.path.join(ROOT, "数据")
os.makedirs(FIG, exist_ok=True)

ts = pd.read_csv(os.path.join(DATA, "battery_timeseries.csv"), encoding="utf-8-sig",
                 usecols=["battery_id", "cycle", "SOH", "soh_t", "resistance", "T"])

# =====================================================================
# 1) 数据预处理: 原始观测(噪声+容量再生) 与 平滑趋势 对比
# =====================================================================
# 选取一条寿命适中的 NCM 电池, 能清晰展示尖刺与噪声
g = ts[ts["battery_id"].str.contains("NCM")].groupby("battery_id")["cycle"].max()
bid = g[(g > 600) & (g < 1200)].sort_values().index[0]
s = ts[ts["battery_id"] == bid].sort_values("cycle")

# 滑动平均(窗口 25)作为平滑基准, 与趋势真值 soh_t 对照
soh_sm = s["SOH"].rolling(25, center=True, min_periods=1).mean()

fig, ax = plt.subplots(figsize=(6.8, 4.0))
ax.plot(s["cycle"], s["soh_t"], lw=1.6, color="#c0392b", label="退化趋势真值 $soh_t$")
ax.plot(s["cycle"], s["SOH"], lw=0.9, alpha=0.45, color="#7f8c8d", label="原始观测 SOH（含噪声/容量再生）")
ax.plot(s["cycle"], soh_sm, lw=1.3, ls="--", color="#2980b9", label="滑动平均平滑（窗口 25）")
ax.axhline(0.70, ls=":", c="red", lw=1, label="EOL 阈值")
ax.set_xlabel("循环次数 $n$"); ax.set_ylabel("SOH")
ax.set_title(f"数据预处理：原始观测与平滑趋势对比（{bid}）")
ax.legend(fontsize=8, loc="upper right")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "q0_preprocess.png"), dpi=160); plt.close(fig)

# =====================================================================
# 2) 退化特征: 内阻随循环增长(按温度着色)
# =====================================================================
meta = pd.read_csv(os.path.join(DATA, "battery_meta.csv"), encoding="utf-8-sig")
sel = meta[meta["chemistry"] == "NCM"].groupby("temperature_C").head(1)["battery_id"].tolist()
sample = ts[ts["battery_id"].isin(sel)]
fig, ax = plt.subplots(figsize=(6.6, 4.2))
for bid_, gg in sample.groupby("battery_id"):
    T = gg["T"].iloc[0]
    ax.plot(gg["cycle"], gg["resistance"], lw=1.4, label=f"T={int(T)}°C")
ax.set_xlabel("循环次数 $n$"); ax.set_ylabel("内阻 $R$ (Ω)")
ax.set_title("内阻随循环增长曲线（NCM 体系，不同温度）")
ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG, "q1_resistance.png"), dpi=160); plt.close(fig)

print("已生成:", [f for f in os.listdir(FIG) if f in ("q0_preprocess.png", "q1_resistance.png")])
