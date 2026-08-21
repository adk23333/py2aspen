<h1 align="center">py2aspen</h1>

<h4 align="center">基于 comtypes 的 Aspen Plus Python 封装库 ✨</h4>

<p align="center">
  <a href="https://pypi.org/project/py2aspen/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/py2aspen?style=flat&logo=pypi&logoColor=white"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue?style=flat&logo=python&logoColor=white">
  <a href="https://pypi.org/project/py2aspen/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/py2aspen?style=flat"></a>
  <a href="https://github.com/adk23333/py2aspen"><img alt="Stars" src="https://img.shields.io/github/stars/adk23333/py2aspen?style=flat&logo=github"></a>
  <a href="https://github.com/adk23333/py2aspen/issues"><img alt="Issues" src="https://img.shields.io/github/issues/adk23333/py2aspen?style=flat"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/adk23333/py2aspen?style=flat"></a>
</p>

<p align="center">
  <img alt="comtypes" src="https://img.shields.io/badge/comtypes-1.4+-blue?style=flat&logo=python">
  <img alt="uv" src="https://img.shields.io/badge/uv-dependency%20management-4c1?style=flat&logo=astral">
  <img alt="ty" src="https://img.shields.io/badge/ty-type%20checker-7b3?style=flat">
  <img alt="ruff" src="https://img.shields.io/badge/ruff-code%20style-4a1?style=flat&logo=ruff">
  <img alt="QQ交流群" src="https://img.shields.io/badge/QQ%E4%BA%A4%E6%B5%81%E7%BE%A4-562721026-12b7f5?style=flat&logo=qq&logoColor=white">
</p>

[English](./README.md) | 简体中文

基于 [comtypes](https://github.com/enthought/comtypes) 的 Aspen Plus Python 封装库，把 COM 自动化调用包装为面向对象的 Python API：连接应用、打开 `.bkp`、在流程图上放置/连接模块与物流、读写物性、运行模拟、导出报告。支持本机 COM，也可通过 DCOM 连接远程机器。

### 安装

使用 `uv`（推荐）或 `pip` 安装：

```bash
uv add py2aspen
# 或
pip install py2aspen
```

### 最小示例

```python
from py2aspen import UnitAspen, bind, MaterialStream, MaterialStreamInput

# Aspen Plus 的 ProgID
PROGID = "AspenPlus.Document"
BKP_PATH = r"C:\path\to\solid1.bkp" # Aspen自带的示例文件，自行找一下可用路径

with UnitAspen(PROGID) as aspen:
    aspen.suppress_dialogs(True)
    aspen.open_bkp(BKP_PATH)
    aspen.set_visible(True)

    stream = MaterialStream(name="WET-COAL")
    aspen.exec(bind(stream))

    stream.set_input(MaterialStreamInput(temperature=100))
    aspen.engine_run()
```

> `with` 会自动调用 `lazy_bind()` 启用 late binding，并在退出时关闭 Aspen Plus。若希望脚本结束后保留应用窗口（如调试），可以不使用 `with`，但是需要手动调用 `lazy_bind()`。

## 开发流程（uv + ty + ruff）

项目使用 [src 布局](src/py2aspen)，构建后端为 `uv_build`，依赖管理通过 [`uv`](https://docs.astral.sh/uv/) 完成，类型检查使用 [`ty`](https://docs.astral.sh/ty/)，代码规范使用 [`ruff`](https://docs.astral.sh/ruff/)。

### 生成 comtypes 类型模块

`py2aspen` 依赖 `comtypes.gen.Happ`（Aspen Plus 类型库）。仓库已在 [`tlb/v14/happ.tlb`](tlb/v14/happ.tlb) 提供 `.tlb`，安装后需在目标 Python 环境中生成一次（结果写入 `<env>/Lib/site-packages/comtypes/gen/`）：

```powershell
.venv\Scripts\python.exe -c "import comtypes.client as cc; cc.GetModule(r'tlb\v14\happ.tlb')"
```

> 重新创建虚拟环境或删除了 `comtypes/gen/` 目录后需要重新执行此命令。

### 环境与依赖

```powershell
# 克隆后初始化环境（按 pyproject.toml 安装运行依赖与 dev 组）
uv sync
```

### 类型检查（ty）

```powershell
uvx ty check            # 检查全仓
uvx ty check src/       # 仅检查某个路径
```

### 代码规范（ruff）

```powershell
uvx ruff check          # 静态检查
uvx ruff check --fix    # 自动修复
uvx ruff format         # 格式化
```

### 测试

```powershell
uv run pytest -v        # 或在 VS Code 中运行 pytest 任务
```

## 项目状态

![Project Status](https://repobeats.axiom.co/api/embed/2ddd5c3f0817babc318877f3254563c0318c4a91.svg)

## 贡献者

感谢所有为 py2aspen 做出贡献的人！

![Contributors]([![contributors](https://contrib.rocks/image?repo=adk23333/py2aspen)](https://github.com/adk23333/py2aspen/graphs/contributors))

同时感谢以下群聊内群友的帮助：

QQ：562721026

TG：暂无

感谢以下同类项目提供的参考：

[AspenPlus-Python-Interface](https://github.com/YouMayCallMeJesus/AspenPlus-Python-Interface) - Python interface which acts as an API to automate the design synthsis. It includes all variables for RADFRAC, DSTWU, Flash2, RYield, RPlug, RCSTR, Heater, Mixer, Splitter. It includes a optimization library implementation from scipy

欢迎任何形式的贡献：提交 [Issue](https://github.com/adk23333/py2aspen/issues) 报告问题、提出建议，或发起 [Pull Request](https://github.com/adk23333/py2aspen/pulls) 改进代码。
