[English](README.md) | 简体中文

# py2aspen

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
