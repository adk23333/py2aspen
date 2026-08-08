<h1 align="center">py2aspen</h1>

<h4 align="center">A Python wrapper for Aspen Plus built on comtypes ✨</h4>

<p align="center">
  <a href="https://pypi.org/project/py2aspen/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/py2aspen?style=for-the-badge&logo=pypi&logoColor=white"></a>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white">
  <a href="https://pypi.org/project/py2aspen/"><img alt="Downloads" src="https://img.shields.io/pypi/dm/py2aspen?style=for-the-badge"></a>
  <a href="https://github.com/adk23333/py2aspen"><img alt="Stars" src="https://img.shields.io/github/stars/adk23333/py2aspen?style=for-the-badge&logo=github"></a>
  <a href="https://github.com/adk23333/py2aspen/issues"><img alt="Issues" src="https://img.shields.io/github/issues/adk23333/py2aspen?style=for-the-badge"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/github/license/adk23333/py2aspen?style=for-the-badge"></a>
</p>

<p align="center">
  <img alt="comtypes" src="https://img.shields.io/badge/comtypes-1.4+-blue?style=for-the-badge&logo=python">
  <img alt="uv" src="https://img.shields.io/badge/uv-dependency%20management-4c1?style=for-the-badge&logo=astral">
  <img alt="ty" src="https://img.shields.io/badge/ty-type%20checker-7b3?style=for-the-badge">
  <img alt="ruff" src="https://img.shields.io/badge/ruff-code%20style-4a1?style=for-the-badge&logo=ruff">
</p>

English | [简体中文](README.zh-CN.md)

A Python wrapper for Aspen Plus built on [comtypes](https://github.com/enthought/comtypes), packaging COM automation calls into an object-oriented Python API: connect to the application, open `.bkp` files, place/connect blocks and streams on the flowsheet, read/write properties, run simulations, and export reports. It supports local COM as well as remote connections over DCOM.

### Installation

Install with `uv` (recommended) or `pip`:

```bash
uv add py2aspen
# or
pip install py2aspen
```

### Minimal example

```python
from py2aspen import UnitAspen, bind, MaterialStream, MaterialStreamInput

# ProgID for Aspen Plus
PROGID = "AspenPlus.Document"
BKP_PATH = r"C:\path\to\solid1.bkp" # Example file shipped with Aspen; pick a valid path on your machine

with UnitAspen(PROGID) as aspen:
    aspen.suppress_dialogs(True)
    aspen.open_bkp(BKP_PATH)
    aspen.set_visible(True)

    stream = MaterialStream(name="WET-COAL")
    aspen.exec(bind(stream))

    stream.set_input(MaterialStreamInput(temperature=100))
    aspen.engine_run()
```

> The `with` block automatically calls `lazy_bind()` to enable late binding and closes Aspen Plus on exit. To keep the application window open after the script finishes (e.g. for debugging), skip `with` and call `lazy_bind()` manually instead.

## Development workflow (uv + ty + ruff)

The project uses the [src layout](src/py2aspen) with `uv_build` as the build backend. Dependency management is handled by [`uv`](https://docs.astral.sh/uv/), type checking by [`ty`](https://docs.astral.sh/ty/), and code style by [`ruff`](https://docs.astral.sh/ruff/).

### Generate the comtypes type module

`py2aspen` depends on `comtypes.gen.Happ` (the Aspen Plus type library). The repo ships the `.tlb` at [`tlb/v14/happ.tlb`](tlb/v14/happ.tlb); after installing, generate it once in the target Python environment (the output is written to `<env>/Lib/site-packages/comtypes/gen/`):

```powershell
.venv\Scripts\python.exe -c "import comtypes.client as cc; cc.GetModule(r'tlb\v14\happ.tlb')"
```

> Re-run this command after recreating the virtual environment or deleting the `comtypes/gen/` directory.

### Environment and dependencies

```powershell
# Initialize the environment after cloning (installs runtime deps and the dev group from pyproject.toml)
uv sync
```

### Type checking (ty)

```powershell
uvx ty check            # Check the whole repo
uvx ty check src/       # Check a specific path
```

### Code style (ruff)

```powershell
uvx ruff check          # Static checks
uvx ruff check --fix    # Auto-fix
uvx ruff format         # Format
```

### Tests

```powershell
uv run pytest -v        # Or run the pytest task in VS Code
```

## Project Status

![Project Status](https://repobeats.axiom.co/api/embed/2ddd5c3f0817babc318877f3254563c0318c4a91.svg)

## Contributors

Thanks to everyone who contributes to py2aspen!

![Contributors]([![contributors](https://contrib.rocks/image?repo=adk23333/py2aspen)](https://github.com/adk23333/py2aspen/graphs/contributors))

Contributions of any kind are welcome: open an [Issue](https://github.com/adk23333/py2aspen/issues) to report problems or suggest features, or submit a [Pull Request](https://github.com/adk23333/py2aspen/pulls) to improve the code.