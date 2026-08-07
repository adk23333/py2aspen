English | [简体中文](README.zh-CN.md)

# py2aspen

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