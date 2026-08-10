# -*- coding: utf-8 -*-
"""
A题 数据分析脚本 —— 基于共享数据集计算问题1~4量化结果并生成论文图表
数据集: data/dataset/  (battery_meta / battery_timeseries / battery_final_states)
输出:   paper/figures/*.png   paper/code/results.json
运行:   python paper/code/analyze.py
"""
import os, json, numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---- 中文字体 ----
for f in font_manager.fontManager.ttflist:
    if f.name == "Microsoft YaHei":
        plt.rcParams["font.family"] = f.name
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("MM_ROOT", os.path.dirname(HERE))  # paper/ (可用环境变量覆盖)
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)
DATA = os.path.join(ROOT, "..", "data", "dataset")

meta = pd.read_csv(os.path.join(DATA, "battery_meta.csv"), encoding="utf-8-sig")
fin  = pd.read_csv(os.path.join(DATA, "battery_final_states.csv"), encoding="utf-8-sig")
ts = pd.read_csv(os.path.join(DATA, "battery_timeseries.csv"), encoding="utf-8-sig",
                 usecols=["cycle","SOH","resistance","T","c_rate","dod","battery_id",
                          "soh_t","ccct_min","cvct_min","ce","phase_label","knee_cycle","rul_cycles","chemistry"])

rng = np.random.default_rng(42)
results = {}

# =====================================================================
# 问题1: 退化特征分析与影响因子辨识
# =====================================================================
# 1) 容量衰减曲线(按温度分色) 图
sel = meta.groupby(["temperature_C"]).head(1)["battery_id"].tolist()[:6]
sample = ts[ts["battery_id"].isin(sel)]
fig, ax = plt.subplots(figsize=(6.6, 4.2))
for bid, g in sample.groupby("battery_id"):
    T = g["T"].iloc[0]
    ax.plot(g["cycle"], g["SOH"], lw=1.4, label=f"T={int(T)}°C")
ax.axhline(0.70, ls="--", c="red", lw=1.2, label="EOL (SOH=70%)")
ax.set_xlabel("循环次数 n"); ax.set_ylabel("SOH")
ax.set_title("容量衰减曲线（不同环境温度）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q1_decay.png"), dpi=160); plt.close(fig)

# 2) 三阶段划分(单电池) 图
bid = fin["battery_id"].iloc[0]
g = ts[ts["battery_id"] == bid].sort_values("cycle")
kn = int(g["rul_cycles"].iloc[0])
fig, ax = plt.subplots(figsize=(6.6, 4.2))
ax.plot(g["cycle"], g["SOH"], lw=1.3, label="SOH 实测")
seg = g["cycle"].values
ax.axvspan(seg.min(), kn, alpha=0.12, color="green", label="阶段Ⅰ 正常退化")
ax.axvspan(kn, seg.max(), alpha=0.15, color="orange", label="阶段Ⅱ/Ⅲ 加速–失效")
ax.axhline(0.70, ls="--", c="red", lw=1)
ax.set_xlabel("循环次数 n"); ax.set_ylabel("SOH")
ax.set_title(f"三阶段划分示例（{bid}）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q1_phase.png"), dpi=160); plt.close(fig)

# 3) 因子重要性: 每循环容量损失率为目标做随机森林
agg = ts.groupby("battery_id").agg(
    n_cycles=("cycle","max"),
    Q_loss_pct=("SOH", lambda s: (1-s.min())*100),
    T=("T","first"), C=("c_rate","first"), DoD=("dod","first"),
).reset_index()
agg["loss_per_cyc"] = agg["Q_loss_pct"] / agg["n_cycles"]
X = agg[["T","C","DoD"]].values; y = agg["loss_per_cyc"].values
from sklearn.ensemble import RandomForestRegressor
rf = RandomForestRegressor(n_estimators=300, random_state=1).fit(X, y)
imp = rf.feature_importances_
fig, ax = plt.subplots(figsize=(6.6, 3.6))
labels = ["温度 T", "倍率 C", "放电深度 DoD"]
ax.bar(labels, imp, color=["#c0392b","#e67e22","#2980b9"])
for i, v in enumerate(imp):
    ax.text(i, v+0.005, f"{v:.2f}", ha="center", fontsize=9)
ax.set_ylabel("随机森林特征重要性"); ax.set_ylim(0, imp.max()*1.2)
ax.set_title("影响因子重要性（每循环容量损失率）")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q1_importance.png"), dpi=160); plt.close(fig)
results["q1_importance"] = {"T": float(imp[0]), "C": float(imp[1]), "DoD": float(imp[2])}
results["q1_corr"] = {"T_corr": float(np.corrcoef(X[:,0], y)[0,1]),
                      "C_corr": float(np.corrcoef(X[:,1], y)[0,1]),
                      "DoD_corr": float(np.corrcoef(X[:,2], y)[0,1])}
tmp = agg.groupby("T")["n_cycles"].mean()
results["q1_temp_life"] = {int(k): float(v) for k, v in tmp.items()}
results["q1_knee_mean"] = float(agg["n_cycles"].mean())
results["q1_n_battery"] = int(len(meta))

# =====================================================================
# 问题2: SOH 评估与 RUL 预测
# =====================================================================
s = ts[ts["battery_id"] == bid].sort_values("cycle").reset_index(drop=True)
soh = s["SOH"].values; n = s["cycle"].values
win = 25
soh_sm = pd.Series(soh).rolling(win, center=True, min_periods=1).mean().values
resid = soh - soh_sm
sigma = np.nanstd(resid)
fig, ax = plt.subplots(figsize=(6.6, 4.2))
ax.plot(n, soh, alpha=0.35, lw=0.8, label="SOH 实测")
ax.plot(n, soh_sm, lw=1.5, label="滑动平均")
ax.fill_between(n, soh_sm-1.96*sigma, soh_sm+1.96*sigma, alpha=0.18, label="95% 置信带")
ax.axhline(0.70, ls="--", c="red", lw=1, label="EOL 阈值")
ax.set_xlabel("循环次数 n"); ax.set_ylabel("SOH")
ax.set_title(f"SOH 辨识与置信区间（{bid}）"); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q2_soh.png"), dpi=160); plt.close(fig)

from scipy.optimize import curve_fit
train = s[s["SOH"] >= 0.80]                      # 自退役判定点(SOH=0.80)起预测 RUL
nt, yt = train["cycle"].values, train["SOH"].values
test = s[s["SOH"] < 0.80]
ne, ye = test["cycle"].values, test["SOH"].values
EOL = 0.70
def predict_and_rmse(model):
    if model == "linear":
        k, b = np.polyfit(nt, yt, 1)
        yp = k*ne + b
    elif model == "poly2":
        c = np.polyfit(nt, yt, 2)
        yp = np.polyval(c, ne)
    elif model == "exp":
        def f(x, a, b, c): return a*np.exp(-b*x)+c
        p, _ = curve_fit(f, nt, yt, p0=[0.3, 0.0005, 0.7], maxfev=100000)
        a, b, c = p
        yp = f(ne, *p)
    elif model == "rf":
        m = RandomForestRegressor(n_estimators=300, random_state=1).fit(nt.reshape(-1,1), yt)
        yp = m.predict(ne.reshape(-1,1))
    rmse = float(np.sqrt(np.mean((yp-ye)**2)))
    if model == "linear":
        rul_pred = (EOL-b)/k - n.max()
    elif model == "poly2":
        roots = np.roots([c[0], c[1], c[2]-EOL])
        root = roots[(roots.imag==0) & (roots.real>n.max())]
        rul_pred = float(root.real.min() - n.max()) if len(root) else np.nan
    elif model == "exp":
        rul_pred = float(-np.log((EOL-c)/a)/b - n.max()) if c < EOL else np.nan
    else:
        rul_pred = np.nan
    return rmse, rul_pred

models = ["linear","poly2","exp","rf"]
rows = []
for m in models:
    rmse, rp = predict_and_rmse(m)
    rows.append({"model": m, "rmse": rmse, "rul_pred": rp})
mc = pd.DataFrame(rows)
true_rul = s["rul_cycles"].iloc[0]
mc["rul_err"] = np.abs(mc["rul_pred"] - true_rul)
results["q2_model_cmp"] = mc.to_dict("records")
results["q2_true_rul"] = float(true_rul)

fig, ax = plt.subplots(figsize=(6.6, 3.6))
names = {"linear":"线性外推","poly2":"二阶多项式","exp":"指数拟合","rf":"随机森林"}
bars = ax.bar([names[m] for m in models], mc["rmse"], color=["#7f8c8d","#2980b9","#c0392b","#27ae60"])
for b, v in zip(bars, mc["rmse"]):
    ax.text(b.get_x()+b.get_width()/2, v+0.001, f"{v:.3f}", ha="center", fontsize=9)
ax.set_ylabel("RMSE"); ax.set_title(f"RUL 预测模型对比（{bid}）")
fig.tight_layout(); fig.savefig(os.path.join(FIG,"q2_model.png"), dpi=160); plt.close(fig)

with open(os.path.join(HERE, "results.json"), "w", encoding="utf-8") as fp:
    json.dump(results, fp, ensure_ascii=False, indent=2)
print("=== 关键结果 ===")
print("Q1 因子重要性:", results["q1_importance"], "相关性:", results["q1_corr"])
print("Q1 温度-寿命:", results["q1_temp_life"])
print("Q2 模型对比:", json.dumps(results["q2_model_cmp"], ensure_ascii=False))
print("=== 图已生成:", sorted(os.listdir(FIG)))
