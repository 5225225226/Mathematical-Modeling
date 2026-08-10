# -*- coding: utf-8 -*-
"""
统一数据流转生成器 —— 依据 数据格式规范1.1.md
================================================================
输入(成员A): battery_timeseries.csv / battery_final_states.csv / battery_meta.csv
输出:
  battery_health_indicators.csv   (成员B接口: 含 cond_id/condition/SOH/resistance/RUL/T/c_rate/dod)
  selected_batteries.csv          (成员C接口: 在健康指标表基础上增加 selected/cluster/grade)
说明:
  RUL = 自退役判定点(SOH=0.80)至EOL(0.70)的循环数(演示值, 成员B建模后可替换)
  cluster = K-means(SOH+内阻, k=3); grade = 双指标规则分级(SOH+内阻)
运行: python data/dataset/generate_data.py
"""
import os, json, numpy as np, pandas as pd
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
FIG = os.path.join(os.path.dirname(os.path.dirname(HERE)), "paper", "figures")  # paper/figures
os.makedirs(FIG, exist_ok=True)

# 统一接口标准(数据格式规范1.1.md §2.1/§2.4)
def get_stage(soh):
    if soh >= 0.90: return "正常运行"
    if soh >= 0.80: return "性能劣化"
    return "失效临界"

def get_grade(soh):
    # 规范 §2.4 统一代码: 单指标 SOH 分级(接口标准, 全队统一)
    if soh >= 0.85: return "一级梯次"
    if soh >= 0.75: return "二级梯次"
    return "建议回收"

# ---------------- 读取 ----------------
ts  = pd.read_csv(os.path.join(HERE, "battery_timeseries.csv"), encoding="utf-8-sig")
fin = pd.read_csv(os.path.join(HERE, "battery_final_states.csv"), encoding="utf-8-sig")
meta = pd.read_csv(os.path.join(HERE, "battery_meta.csv"), encoding="utf-8-sig")

# ---------------- 成员B: 健康指标表 ----------------
# 退役状态 = knee 拐点(健康状态中最有信息量, 对应 SOH 82~85%) 时刻的 SOH/内阻
knee = ts[ts["cycle"] == ts["knee_cycle"]][["battery_id","SOH","resistance","rul_cycles"]].copy()
# RUL: 规范中 RUL 单位为"循环数"。以 knee→EOL 的剩余循环作为演示估计(可用经验模型替换)
knee["RUL"] = knee["rul_cycles"]
# 对齐成员A原始工况信息(来自 final_states 首行, 每块电池工况唯一)
info = fin.groupby("battery_id").first()[["cond_id","condition","T","c_rate","dod"]].reset_index()
health = knee.merge(info, on="battery_id").drop(columns=["rul_cycles"])
# 规范字段顺序
health = health[["cond_id","condition","SOH","resistance","RUL","T","c_rate","dod","battery_id"]]
health.to_csv(os.path.join(HERE, "battery_health_indicators.csv"), index=False, encoding="utf-8-sig")

# ---------------- 成员C: 分级 + 选中表 ----------------
# 贪心选择: 内阻排序滑动窗口 (目标: 平均SOH高 + 内阻std小 + 最低SOH高; 约束: 6~14块/极差≤range_max)
def greedy(S, R, range_max=0.04, min_soh=0.80):
    order = np.argsort(R); Ss, Rs = S[order], R[order]
    bst = None
    for i in range(len(order)):
        for j in range(i+5, min(i+14, len(order))):
            if Ss[i:j+1].min() < min_soh or Rs[i:j+1].max()-Rs[i:j+1].min() > range_max: continue
            sc = -(2.2*Ss[i:j+1].mean() - 3.8*Rs[i:j+1].std() + 1.5*Ss[i:j+1].min())
            if bst is None or sc < bst[0]: bst = (sc, i, j)
    if bst is None:  # 极差约束过严时降级: 放宽到 6~14 块中内阻最接近者
        for i in range(len(order)):
            for j in range(i+5, min(i+14, len(order))):
                if Ss[i:j+1].min() < min_soh: continue
                sc = -(2.2*Ss[i:j+1].mean() - 3.8*Rs[i:j+1].std() + 1.5*Ss[i:j+1].min())
                if bst is None or sc < bst[0]: bst = (sc, i, j)
    if bst is None:  # 仍无可行解: 取内阻最接近的 8 块
        i0, j0 = len(order)//2-4, len(order)//2+3
        bst = (0.0, i0, j0)
    m = np.zeros(len(S), dtype=bool); m[order[bst[1]:bst[2]+1]] = True
    return m

sel = health.copy()
sel["grade"] = [get_grade(s) for s in sel["SOH"]]   # 规范 §2.4 单指标分级
# K-means 聚类
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
Xs = StandardScaler().fit_transform(sel[["SOH","resistance"]].values)
sel["cluster"] = KMeans(n_clusters=3, n_init=10, random_state=1).fit(Xs).labels_
# 贪心优化选中
S, R = sel["SOH"].values, sel["resistance"].values
mb = greedy(S, R)
sel["selected"] = mb.astype(int)
sel = sel[["cond_id","condition","SOH","resistance","RUL","T","c_rate","dod","selected","cluster","grade","battery_id"]]
sel.to_csv(os.path.join(HERE, "selected_batteries.csv"), index=False, encoding="utf-8-sig")

# ---------------- 关键图 ----------------
# 图1: 退役电池分级散点 (K-means 颜色 + 选中框)
fig, ax = plt.subplots(figsize=(6.6, 4.2))
colors = ["#27ae60","#2980b9","#c0392b"]
for ci in range(3):
    sub = sel[sel["cluster"]==ci]
    ax.scatter(sub["resistance"], sub["SOH"], s=26, c=colors[ci], alpha=0.85, label=f"簇{ci}(n={len(sub)})")
ax.scatter(sel.loc[sel["selected"]==1,"resistance"], sel.loc[sel["selected"]==1,"SOH"],
           s=120, facecolors="none", edgecolors="black", lw=1.2, label="选中编组")
ax.set_xlabel("内阻 (Ω)"); ax.set_ylabel("SOH")
ax.set_title(f"退役电池分级与编组选中（n={len(sel)}）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q3_grade.png"), dpi=160); plt.close(fig)

# 图2: 高温/大倍率鲁棒性
fig, ax = plt.subplots(figsize=(6.6, 3.8))
SOHh, Rh = S*0.94, R*1.20
mb = greedy(S, R); mh = greedy(SOHh, Rh, range_max=0.05, min_soh=0.75)
cats = ["基准", "高温(×0.94)", "大倍率(×1.20)"]
vals = [int(mb.sum()), int(mh.sum()), int(mh.sum())]
bars = ax.bar(cats, vals, color=["#2ecc71","#e74c3c","#e67e22"])
for b, v in zip(bars, vals): ax.text(b.get_x()+b.get_width()/2, v+0.4, str(v), ha="center", fontsize=10)
ax.set_ylabel("编组块数"); ax.set_title(f"鲁棒性：选中集与基准重合 {int((mb&mh).sum())}/{int(mb.sum())} 块")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q4_sens.png"), dpi=160); plt.close(fig)

# ---------------- 摘要 ----------------
print("=== battery_health_indicators.csv ===")
print(health.head(3).to_string())
print("RUL: min", health["RUL"].min(), "max", health["RUL"].max())
print("\n=== selected_batteries.csv ===")
print("分级:", sel["grade"].value_counts().to_dict())
print("选中:", int(sel["selected"].sum()), "块 | 平均SOH", round(sel.loc[sel.selected==1,'SOH'].mean(),4),
      "| 内阻std", round(sel.loc[sel.selected==1,'resistance'].std(),5))
print("K-means 簇均值:", sel.groupby('cluster')[['SOH','resistance','RUL']].mean().round(3).to_dict('records'))
