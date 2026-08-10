# 数学建模竞赛 A题 —— 锂电池剩余寿命预测与梯次利用筛选优化

> **共享仓库**：本仓库用于全队同步 A 题进度、数据、解答与论文。
> 数据接口严格执行 [`data/数据格式规范1.1.md`](data/数据格式规范1.1.md)，全队字段、命名、分级/阶段代码统一。
> 最新论文草稿：[`paper/main.pdf`](paper/main.pdf)（16 页，xelatex 编译）。

---

## 目录结构

```
Mathematical-Modeling/
├── README.md                     ← 本文件（导航）
├── solution_A/                   ★ A题解答（分问题 Markdown + 可视化）
│   ├── 问题1_退化特征分析与影响因子辨识.md
│   ├── 问题2_SOH评估与RUL预测建模.md
│   ├── Q3_梯次筛选与编组多目标优化.md      （成员C，按早期口径）
│   ├── Q4_多工况仿真与鲁棒性分析.md        （成员C，按早期口径）
│   ├── Q2_成员B版本.md
│   └── visualizations/           A题交互可视化 HTML
├── data/                         ★ 所有数据（统一接口标准）
│   ├── 数据格式规范1.1.md          ← 全队数据接口唯一标准（★核心）
│   ├── 00_数据汇总说明.md  / 01_数据来源清单.md
│   ├── 02_统一数据集格式_可直接入模.md / 03_数据资产现状清单.md
│   ├── dataset/                   ← 数据文件
│   │   ├── battery_timeseries.csv       成员A：完整时序（153 块电池）
│   │   ├── battery_final_states.csv     成员A：每块电池最终状态
│   │   ├── battery_health_indicators.csv 成员B接口：含 RUL（已生成）
│   │   ├── selected_batteries.csv       成员C接口：分级 + 编组选中（已生成）
│   │   ├── battery_meta.csv / eis_spectrum.csv
│   │   ├── generate_sim.py / generate_data.py / convert_to_spec.py
│   │   └── ...
│   └── PDF文件/                  本地 PDF 归档
├── references/                   ★ 资料库（竞赛试题/规则/论文精读/建模知识/工具速成）
│   ├── README_资料索引.md          ← 资料导航入口
│   ├── 01_竞赛试题 ~ 07_论文pdf原件资料
├── paper/                        ★ 论文（LaTeX + PDF）
│   ├── main.tex                   论文主文件（xelatex + bibtex 编译）
│   ├── main.pdf                   编译产物（最新草稿）
│   ├── figures/                  数据可视化图（Q1-Q4）
│   ├── code/analyze.py           Q1/Q2 分析脚本
│   ├── cumcmthesis.cls / ref.bib / gbt7714-numerical.bst
│   └── fonts/                    模板字体（Source Han Serif / YaHei Consolas）
```

---

## 数据流转（对应 `数据格式规范1.1.md` §5）

```
成员A ──生成──▶ battery_timeseries.csv / battery_final_states.csv
                     │
                     ▼
成员B ──读取+建模──▶ battery_health_indicators.csv（含 RUL）
                     │
                     ▼
成员C ──分级+优化──▶ selected_batteries.csv（selected/cluster/grade）
```

- `data/dataset/generate_sim.py`：成员A 仿真数据生成器（多因子衰减模型，参数含文献来源）。
- `data/dataset/generate_data.py`：生成成员B/C 接口表，可直接运行复现。

---

## 论文编译

```bash
cd paper
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

要求：MiKTeX/TeXLive + XeLaTeX；字体位于 `paper/fonts/`，编译需在 `paper/` 目录内进行。

---

## 当前进度

| 项目 | 状态 | 说明 |
|------|------|------|
| 数据规范 v1.1 | ✅ | 全队统一接口标准 |
| 时序/最终状态数据 | ✅ | 153 块电池，多工况 |
| 健康指标表 | ✅ | 已生成演示 RUL（可替换） |
| 选中结果表 | ✅ | 分级 + 编组选中 |
| 问题1 解答 | ✅ | 退化特征 + 因子量化 |
| 问题2 解答 | ✅ | SOH + RUL 建模思路 |
| 问题3/4 解答 | ✅ | 分级 + 优化 + 鲁棒性 |
| 论文草稿 | ✅ | 16 页 PDF 草稿 |
