# VS Code + LaTeX Workshop 统一配置指南（全队通用）

> **用途**：让全队成员在 5 分钟内统一 VS Code 的 LaTeX 编译环境，确保：
> 1. **编译不出现 `[?]` 文献乱码**（核心问题）
> 2. **Ctrl+F1 能正常"源码 ↔ PDF"同步定位**
> 3. 所有成员编译出的 PDF 行为一致
>
> **本文件既可手动照做，也可把文末"给 AI 的提示词"整段复制给 AI 让它帮你配置。**
>
> **整理时间**：2026年8月

---

## 目录

1. [第 0 步：确认前置环境（必做）](#第-0-步确认前置环境必做)
2. [第 1 步：配置编译流程 settings.json](#第-1-步配置编译流程-settingsjson)
3. [第 2 步：配置快捷键 keybindings.json](#第-2-步配置快捷键-keybindingsjson)
4. [第 3 步：验证是否配置成功](#第-3-步验证是否配置成功)
5. [日常使用：快捷键速查表](#日常使用快捷键速查表)
6. [常见问题排查（FAQ）](#常见问题排查faq)
7. [附：给 AI 的配置提示词（可整段复制）](#附给-ai-的配置提示词可整段复制)

---

## 第 0 步：确认前置环境（必做）

| 项目 | 要求 | 检查方式 |
|------|------|---------|
| **TeX 发行版** | MiKTeX 或 TeX Live（必须带 **XeLaTeX**） | 命令行输入 `xelatex --version` 有输出即通过 |
| **编辑器** | **VS Code**（注意：不是 Cursor / Trae，LaTeX 扩展装在哪个编辑器就在哪个用） | 看窗口左上角标题栏 |
| **扩展** | **LaTeX Workshop**（作者 james-yu） | 左侧扩展栏搜索 "LaTeX Workshop" 已安装且未禁用 |

> ⚠️ **最容易踩的坑**：如果装了多个编辑器（VS Code / Cursor / Trae），**LaTeX Workshop 扩展必须装在你要用的那个编辑器里**。扩展装在 VS Code，却在 Cursor 里打开 .tex 文件 → 快捷键全部失效、没有编译按钮。**确认你打开 .tex 用的就是装好扩展的那个编辑器。**

---

## 第 1 步：配置编译流程 settings.json

> **为什么必须这么配**：默认的 latexmk 单命令在"残留旧编译文件"时会**不自动跑 bibtex**，导致正文文献引用显示 `[?]`。
> 改成 **显式四步序列** 后，每次保存都必定执行 bibtex，`[?]` 永不出现。

### 手动操作方式

1. VS Code 按 `Ctrl+Shift+P`，输入 `Preferences: Open User Settings (JSON)` 回车；
2. 在打开的 `settings.json` 中，**找到（或新增）** 以下两个配置项：

```json
{
    "latex-workshop.latex.recipes": [
        {
            "name": "xelatex -> bibtex -> xelatex x2",
            "tools": [ "xelatex", "bibtex", "xelatex", "xelatex" ]
        }
    ],
    "latex-workshop.latex.tools": [
        {
            "name": "xelatex",
            "command": "xelatex",
            "args": [
                "-synctex=1",
                "-interaction=nonstopmode",
                "-file-line-error",
                "%DOC%"
            ]
        },
        {
            "name": "bibtex",
            "command": "bibtex",
            "args": [ "%DOC%" ]
        }
    ]
}
```

3. 同时确认（可选）以下两项：

```json
{
    "latex-workshop.view.pdf.viewer": "tab",
    "latex-workshop.latex.autoBuild.run": "onSave"
}
```

> **说明**：
> - 如果 `settings.json` 里已有 `latex-workshop.latex.recipes` / `latex-workshop.latex.tools`，**整段替换**即可；
> - 文件里可以包含 `// 注释` 和尾随空格，VS Code 支持（这是 JSONC 格式）；
> - 改完后 `Ctrl+Shift+P` → `Developer: Reload Window` 重启生效。

---

## 第 2 步：配置快捷键 keybindings.json

> 绑定 `Ctrl+F1` 为"光标 → PDF"正向同步定位（LaTeX Workshop 的 `synctex` 命令）。

### 手动操作方式

1. `Ctrl+Shift+P`，输入 `Preferences: Open Keyboard Shortcuts (JSON)` 回车；
2. 在 `keybindings.json` 数组里**新增**一个对象：

```json
[
    {
        "key": "ctrl+f1",
        "command": "latex-workshop.synctex",
        "when": "editorTextFocus && !config.latex-workshop.bind.altKeymap.enabled && editorLangId =~ /^latex$|^latex-expl3$|^doctex$/"
    }
]
```

> 如果文件里已有其他键位，直接追加这个对象即可（数组用逗号分隔）。
> 扩展自带的同步键还有 `Ctrl+Alt+J`（无需配置即可用），可作备用。

---

## 第 3 步：验证是否配置成功

### 验证编译（防止 `[?]`）

1. 打开论文主文件 `main.tex`；
2. 按 `Ctrl+S` 触发自动编译（左下角出现 LaTeX 状态栏转圈）；
3. 编译完成后，**确认两个结果**：
   - 正文中的 `\cite{...}` 显示为 `[1]`、`[2]` 等编号，**不是 `[?]`**；
   - 文末**参考文献列表**已渲染（如 `[1] WILLIARD N, et al. ...`）。

### 验证同步定位（Ctrl+F1）

**正确操作顺序（重点！）**：
1. 先在 `main.tex` 里按 `Ctrl+Alt+V` **打开 PDF**；
2. 把光标点回 .tex 编辑器，放在某一行；
3. 按 `Ctrl+F1` → PDF 应跳转到对应位置。

若 PDF 是双击文件管理器打开的（不在 VS Code 里），同步定位**不会工作**——必须先由 VS Code 打开 PDF。

---

## 日常使用：快捷键速查表

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `Ctrl+Alt+V` | 打开 / 预览 PDF | 在 VS Code 内标签页打开编译结果 |
| `Ctrl+F1` | 源码 → PDF 同步定位 | 光标处跳到 PDF 对应位置（需先开 PDF） |
| `Ctrl+Alt+J` | 源码 → PDF 同步定位 | 扩展默认键，备用 |
| `Ctrl+Alt+B` | 手动编译 | 触发当前 recipe |
| `Ctrl+Alt+C` | 清理编译产物 | 删除 aux/log/out 等 |
| `Ctrl+Alt+X` | 打开 LaTeX 侧边栏 | 查看构建日志、错误定位 |
| `Ctrl+S` | 保存并自动编译 | 已配置 onSave 自动构建 |

> **PDF 反向定位**（PDF → 源码）：在 VS Code 打开的 PDF 中 `Ctrl+点击` 某处，跳回 .tex 对应行。

---

## 常见问题排查（FAQ）

### Q1：编译后正文出现 `[?]`（文献显示为问号）

**原因**：缺少 `main.bbl`，或编译流程没跑 bibtex（latexmk 不稳定的典型症状）。

**解决**：
1. 确认 settings.json 已按**第 1 步**改成四步序列；
2. 重新加载窗口（`Ctrl+Shift+P` → `Developer: Reload Window`）；
3. 再按 `Ctrl+S` 编译一次；
4. 若仍不行，手动删掉 main 的编译产物后重编：
   ```
   rm -f main.aux main.bbl main.blg main.log main.out main.synctex.gz
   ```
   然后重新 `Ctrl+S`。

### Q2：Ctrl+F1 没反应

按顺序检查：
1. **PDF 是否先打开了**？必须先 `Ctrl+Alt+V` 打开 PDF，再点回 .tex 按 Ctrl+F1；
2. **光标焦点**是否在 .tex 编辑器上（不是 PDF 标签页）？
3. **右下角语言模式**是否为 "LaTeX"？（显示 "Plain Text" 则快捷键不触发，点它改成 LaTeX）
4. keybindings.json 是否保存并已 Reload Window？
5. 确认用的是**装了 LaTeX Workshop 的那个编辑器**（见第 0 步）。

### Q3：编译报错 "file not found: main.aux / main.bbl"

**原因**：编译工作目录不在 `paper/` 下，或文件名不匹配。

**解决**：确保 .tex 文件与 `ref.bib`、`cumcmthesis.cls` 在同一目录（即 `paper/`），在 VS Code 里打开的是 `main.tex` 本身。

### Q4：中文显示成方块 / 字体警告

模板已配置 `ctex` 与 `fonts/` 字体。若出现字体缺失，确保在 **`paper/` 目录内**用 XeLaTeX 编译（VS Code 的 recipe 已用 xelatex，默认无此问题）。

### Q5：保存后编译结果没更新

检查状态栏是否显示 LaTeX 构建中（转圈）；或手动 `Ctrl+Alt+B` 强制编译一次。

---

## 附：给 AI 的配置提示词（可整段复制）

> 把下面这段话复制给 AI（如 Claude Code / ChatGPT），它会帮你自动完成全部配置。**运行前先确认：你打开的 .tex 所在的编辑器，就是装了 LaTeX Workshop 扩展的那个。**

```
请帮我配置 VS Code 的 LaTeX Workshop 环境，要求如下：

1. 【settings.json】在 VS Code 的用户设置中，把 LaTeX 编译 recipe 改为显式四步
   "xelatex -> bibtex -> xelatex x2"，tools 分别为：
   - xelatex: args = ["-synctex=1","-interaction=nonstopmode","-file-line-error","%DOC%"]
   - bibtex:  args = ["%DOC%"]
   并确保 latex-workshop.view.pdf.viewer 为 "tab"、
   latex-workshop.latex.autoBuild.run 为 "onSave"。
   注意：这是为了强制每次编译都跑 bibtex，避免文献显示 [?]。

2. 【keybindings.json】新增一个键位：Ctrl+F1 绑定 latex-workshop.synctex，
   when 条件为 editorTextFocus && !config.latex-workshop.bind.altKeymap.enabled
   && editorLangId =~ /^latex$|^latex-expl3$|^doctex$/。
   用途：源码到 PDF 的正向同步定位。

3. 改完后提示我：需要 Ctrl+Shift+P -> Developer: Reload Window 重启生效；
   并告诉我验证步骤（先 Ctrl+Alt+V 打开 PDF，再点回 tex 按 Ctrl+F1 测试定位）。

4. 修改前先备份原 settings.json 和 keybindings.json。
```

---

*本指南由队员整理，供全队统一 LaTeX 协作环境使用。配置项均已在真实环境中验证。*
