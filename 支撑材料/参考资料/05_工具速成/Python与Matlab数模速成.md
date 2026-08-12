# Python 与 Matlab 数模速成要点

> 资料来源：B站课程讲义《4 1小时零基础拿下数模MATLAB》（PPTX 59页）与《10 1小时零基础拿下数模Python》（5 个 Jupyter Notebook + 26 页 PDF）。本文件提炼两门语言在数学建模中的核心用法与标准流程，供备赛时快速上手、应急查语法。
> 讲义位置：`D:/ycy111/数模/数学建模统一资料/B站课程讲义：2026国赛速成课配套讲义课件等！/4 1小时零基础拿下数模MATLAB/` 与 `/10 1小时零基础拿下数模Python/`

---

## 目录

- [一、Python 数模三剑客核心用法](#一python-数模三剑客核心用法)
- [二、Python 扩展库：scipy / sklearn / statsmodels](#二python-扩展库scipy--sklearn--statsmodels)
- [三、Matlab 常用建模函数](#三matlab-常用建模函数)
- [四、标准流程：读取数据-预处理-建模-绘图](#四标准流程读取数据-预处理-建模-绘图)
- [五、Python / Matlab 对照速查表](#五python--matlab-对照速查表)

---

## 一、Python 数模三剑客核心用法

### 1.1 Numpy —— 数组与数值计算

**创建数组**（`numpy.ipynb`）：

```python
import numpy as np
np.array([1,2,3,4,5])          # 列表转数组（手动初始化小规模系数）
np.zeros((3,2))                # 全 0 矩阵（初始化状态空间/距离矩阵）
np.ones((4,2))                 # 全 1 矩阵（权重基数）
np.arange(3,7)                 # 等差序列（左闭右开，生成时间步/迭代步数）
np.linspace(0,1,5)             # 等距采样点（绘图 x 轴、微分方程求解、网格寻优）★
np.random.rand(2,4)            # [0,1) 均匀随机矩阵（蒙特卡洛、GA/PSO 初始种群）
np.eye(4)                      # 单位矩阵（马尔可夫状态转移、矩阵求逆基准）
```

**运算**：

```python
a * 5          # 广播：标量自动扩展
np.dot(a,b)    # 向量内积 → 综合得分 = Σ w_i·x_i
a @ b          # 矩阵乘法（AHP/TOPSIS 一致性检验、综合权重）
np.log(a)      # 自然对数 ln（注意不是 lg）
np.power(a,2)  # 批量幂运算
a.min()/a.max()/a.argmin()/a.argmax()   # 最值与索引（找最优目标值位置）
a.sum()        # 全元素求和
a.mean()/np.median(a)  # 均值（受异常值影响）/中位数（抗异常）
a.var()/a.std()         # 方差/标准差（方案稳定性、波动程度）
```

**axis 方向（数模核心考点）**：`axis=0` 按列统计（压缩行，算每列/每科均值），`axis=1` 按行统计（算每个样本/学生总分）。

**索引与清洗**：

```python
a[0,1]              # 二维定位：a[行, 列]
a[0, 0:2]           # 切片 [start:stop:step] 左闭右开
a[::2]              # 步长隔项提取
a[(a>3)&(a%2==0)]   # 复合条件筛选：& 且 / | 或，条件必须用括号括起来
b = a.copy()        # 深拷贝（直接 b=a 是软链接，改 b 会连带改 a！）
np.int32 转类型      # 网格坐标做矩阵索引前必须转 int
```

### 1.2 Pandas —— 数据读取与清洗

**读取与感知**（`pandas.ipynb`）：

```python
import pandas as pd
df = pd.read_csv('data.csv')   # 读取 CSV（xlsx 用 pd.read_excel）
df.head()/df.tail(3)           # 首/尾几行
df.shape                       # (行数, 列数)
df.columns                     # 列名列表
df.info()                      # 非空计数 + 数据类型
df.describe()                  # 数值列均值/标准差/最值统计摘要
```

**清洗**：

```python
df.isnull()                    # 缺失值位置检测
df.dropna()                    # 删除含缺失值的行
df['col'].fillna(df['col'].mean())   # 均值填补（也可中位数/插值/模型填补）
df.duplicated(subset=['name','salary'])  # 检测重复行
df.drop_duplicates()           # 去重
```

**选择/筛选/统计**：

```python
df.iloc[0:2, 0:3]      # iloc 按位置（左闭右开）
df.loc[df['age']>30]   # loc 按标签/条件
df.query("age > 30 and salary > 50000")   # 高可读性查询，强烈推荐
df['category'].value_counts()   # 类别频次统计
df.sort_values(by="salary", ascending=False)   # 排序
df['new'] = df['value'].apply(lambda x: x*10+5)  # 逐元素映射（归一化/无量纲化）
```

**分组/透视/合并/重塑**：

```python
df.groupby("category")['value'].mean()        # 分组聚合
df.pivot_table(values="value", index="category", aggfunc="sum")  # 数据透视表
pd.concat([df1,df2]) / pd.merge(df1,df2,on='key')  # 拼接/关联
pd.melt(wide_df, id_vars=['id'])              # 宽表→长表（时间序列分析常用）
```

### 1.3 Matplotlib —— 绘图

**中文字体（必设，否则中文变方块）**（`matplotlab.ipynb`）：

```python
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
```

**常用图**：

```python
plt.plot(x, y, marker='o', label='模型A')    # 折线图（算法收敛对比/时序）
plt.scatter(x, y)                             # 散点图（聚类结果/特征关系）
plt.bar(categories, scores)                   # 柱状图（方案得分排序）
plt.hist(data, bins=30)                       # 直方图（频数分布）
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10,4))  # 子图拼版（省空间）
ax2 = ax1.twinx()                             # 双 y 轴（不同量纲两指标）
```

**出图规范**：`title` / `xlabel` / `ylabel` / `legend` / `grid` 齐全，`figsize` 控制比例，`savefig('xxx.png', dpi=300)` 导出高清图。

### 1.4 完整小案例流程

`small_case_csv_to_plot.ipynb` 演示了标准链路：

```python
df = pd.read_csv('rich_simulation.csv')
clean_df = df.dropna(subset=['year','category','value'])      # 清洗
summary = clean_df.groupby(['category','year'])['value'].mean()\
                 .reset_index().sort_values(['category','year'])  # 分组汇总
for category, group in summary.groupby('category'):
    ax.plot(group['year'], group['value'], marker='o', label=category)  # 趋势图
```

### 1.5 Python 语法速记（`examples.ipynb`）

- 动态类型：直接赋值即可；读 TXT 的数字默认字符串，须 `float()`/`int()` 转换。
- 容器：列表 `[]`（收集迭代损失）、元组 `()`（不可变常量，如网格形状）、字典 `{}`（管理超参数/方案得分）、集合 `{}`（去重/交集）。
- 列表/字典/集合**解析式**：一行批量生成数据或做标签→数字映射。
- 文件读写：用 `with open('f.txt','w') as f:`（自动 close，防数据丢失）；大文件逐行 `for line in f:` 防内存爆炸。
- `dir(module)`：断网自救，查模块里有哪些函数。

---

## 二、Python 扩展库：scipy / sklearn / statsmodels

> 速成课未展开但数模必用，配合「算法源代码库索引.md」中的代码使用。

### 2.1 scipy —— 科学计算

```python
from scipy.optimize import minimize, linprog, curve_fit, differential_evolution
from scipy.integrate import solve_ivp, odeint
from scipy.interpolate import interp1d, griddata
from scipy import stats

# 非线性规划
res = minimize(fun, x0, bounds=bounds, constraints=cons)
# 线性规划
res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds)
# 常微分方程数值解（A 题机理建模核心）
sol = solve_ivp(ode_fun, [t0, tf], y0, t_eval=t)
# 曲线拟合（参数反演）
popt, pcov = curve_fit(func, xdata, ydata, p0=[1,1])
```

### 2.2 sklearn —— 机器学习

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, mean_squared_error, r2_score
from sklearn.svm import SVR, SVC

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
X_scaled = StandardScaler().fit_transform(X)   # 距离类算法必须先标准化
kmeans = KMeans(n_clusters=3, n_init=10).fit(X)  # n_init 消除初始随机影响
```

### 2.3 statsmodels —— 统计检验与时间序列

```python
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller, acf, pacf
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox

adf = adfuller(series)          # ADF 平稳性检验（p<0.05 平稳）
model = ARIMA(series, order=(p,d,q)).fit()   # ARIMA 建模
ljung = acorr_ljungbox(model.resid)          # 残差白噪声检验
```

---

## 三、Matlab 常用建模函数

讲义《2-1：Matlab基础入门及编程讲解.pptx》共四部分：**界面使用 → 矩阵基础 → 逻辑结构 → 画图**。

### 3.1 矩阵基础（核心）

```matlab
A = [1 2 3; 4 5 6]      % 直接输入法（; 分行，空格/逗号分列）
zeros(3,2); ones(4,2); eye(4)      % 全0/全1/单位矩阵
rand(2,4); randi(10,2,3); randn(2,4)   % 均匀随机/随机整数/正态随机
A(2,3) = 9              % 修改元素；A(2,:)=[] 删除整行
[A, B]; [A; B]; cat(2,A,B)   % 横向/纵向拼接
reshape(A, m, n); sort(A, dim)   % 重排/排序
A'                      % 转置
A*B   % 矩阵乘法；A.*B 对应元素乘；./ 对应元素除
x = A\b                 % 左除解线性方程组（数模高频：最小二乘 A\b）
```

**读数据**：`readmatrix`/`xlsread`/`csvread` 读 txt/csv/xlsx。

### 3.2 逻辑与结构

```matlab
if ... elseif ... else ... end        % 条件（if 与 end 不能省略）
switch ... case ... otherwise ... end % 可被 if 代替
for i = 1:n ... end                    % 已知次数循环
while cond ... end                     % 未知次数循环（Ctrl+C 中断）
break; continue                        % 循环控制
all(A,dim); any(A,dim); find(A>3)      % 逻辑判断/找索引（高频）
& / &&  | / ||                         % 逐元素与 / 短路与（&& 只能对标量）
```

### 3.3 画图

```matlab
plot(x, y, '--or')       % 折线：'--'线型 + 'o'标记 + 'r'颜色
fplot(fun, [xmin,xmax])  % 函数绘图（fun 用函数句柄 @(x)）
bar(); scatter(); area(); histogram()   % 统计图
title(); xlabel(); ylabel(); legend(); text(x,y,'说明')   % 标注
plot3(x,y,z); fplot3(funx,funy,funz,tlims)   % 三维曲线
[X,Y]=meshgrid(x,y); mesh(X,Y,Z); surf(X,Y,Z)  % 三维曲面（网格 + 曲面）
```

### 3.4 常用建模函数（补充，配合算法库）

```matlab
% 优化
linprog(f,A,b,Aeq,beq,lb,ub)          % 线性规划
intlinprog(f,intcon,A,b)              % 整数/0-1 规划
fmincon(fun,x0,A,b,Aeq,beq,lb,ub)     % 非线性约束优化
ga(@fitness,nvars,A,b); particleswarm(@fit,nvars); simulannealbnd(@fit,x0,lb,ub)  % 智能算法
% 微分方程（A 题机理）
ode45(@odefun,[t0 tf],y0); ode15s(...) % 刚性用 ode15s
% 拟合/插值
polyfit(x,y,n); lsqcurvefit(fun,p0,x,y); interp1(x,y,xi,'spline')
% 统计
zscore(x); corrcoef(x); [coeff,score,latent]=pca(X)
```

---

## 四、标准流程：读取数据-预处理-建模-绘图

> 数模通用解题链路，无论 Python 还是 Matlab 都按此走（对应讲义中的"完整小案例"）。

### 4.1 流程总览

```
① 读取数据 → ② 数据清洗 → ③ 特征工程 → ④ 建模求解 → ⑤ 绘图可视化 → ⑥ 导出结果
```

### 4.2 Python 标准模板

```python
# ① 读取
import pandas as pd, numpy as np
df = pd.read_excel('附件.xlsx', sheet_name='Sheet1')

# ② 清洗
df = df.dropna(subset=['关键列'])
df = df.drop_duplicates()
df['数值列'] = pd.to_numeric(df['数值列'], errors='coerce')

# ③ 特征工程/预处理
from sklearn.preprocessing import StandardScaler
X = df[['特征1','特征2']].values
X = StandardScaler().fit_transform(X)   # 距离类/机器学习必做

# ④ 建模（示例：K-means）
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=3, n_init=10, random_state=42).fit(X)
df['簇'] = kmeans.labels_

# ⑤ 绘图
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']; plt.rcParams['axes.unicode_minus']=False
plt.scatter(X[:,0], X[:,1], c=df['簇'], cmap='viridis'); plt.xlabel('特征1'); plt.ylabel('特征2')
plt.title('聚类结果'); plt.savefig('聚类结果.png', dpi=300)

# ⑥ 导出
df.to_excel('结果.xlsx', index=False)
```

### 4.3 Matlab 标准模板

```matlab
%% ① 读取
data = readmatrix('data.csv');   % 或 xlsread('data.xlsx')
X = data(:, 1:end-1); y = data(:, end);

%% ② 清洗（异常值 3σ）
mu = mean(X); sig = std(X);
X(abs(X-mu) > 3*sig) = NaN;   % 或按 IQR
X = fillmissing(X, 'linear');  % 缺失值插值填补

%% ③ 标准化
X = zscore(X);

%% ④ 建模（示例：K-means）
[idx, C] = kmeans(X, 3);
gscatter(X(:,1), X(:,2), idx);   % 按簇着色散点

%% ⑤ 标注与导出
xlabel('特征1'); ylabel('特征2'); title('聚类结果'); legend('簇1','簇2','簇3');
saveas(gcf, '聚类结果.png');
```

---

## 五、Python / Matlab 对照速查表

| 操作 | Python | Matlab |
|------|--------|--------|
| 全 0 矩阵 | `np.zeros((m,n))` | `zeros(m,n)` |
| 等差序列 | `np.arange(a,b)` / `np.linspace(a,b,n)` | `a:b` / `linspace(a,b,n)` |
| 矩阵乘法 | `a @ b` | `A*B` |
| 逐元素乘 | `a * b` | `A.*B` |
| 解方程组 | `np.linalg.solve(A,b)` | `A\b` |
| 均值/方差 | `a.mean()`, `a.std()` | `mean(A)`, `std(A)` |
| 数据读取 | `pd.read_csv/excel` | `readmatrix/xlsread` |
| 线性规划 | `scipy.optimize.linprog` | `linprog` |
| 非线性规划 | `scipy.optimize.minimize` | `fmincon` |
| 微分方程 | `scipy.integrate.solve_ivp` | `ode45` |
| K-means | `sklearn.cluster.KMeans` | `kmeans` |
| PCA | `sklearn.decomposition.PCA` | `pca` |
| 折线图 | `plt.plot(x,y)` | `plot(x,y)` |
| 三维曲面 | `ax.plot_surface` | `meshgrid`+`surf` |

---

*文档生成日期：2026-08-10。内容提炼自 B 站速成课讲义，补充 scipy/sklearn/statsmodels 与标准流程要点。*
