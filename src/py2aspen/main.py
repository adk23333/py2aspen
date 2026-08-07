import time
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import cast

from comtypes import CoClass, client
from comtypes.automation import IDispatch
from comtypes.GUID import GUID

from py2aspen.aspen_type import APP, IHNode
from py2aspen.flowsheet import Action
from py2aspen.log import logger
from py2aspen.properties import ComponentManager


class AspenVersionCode(StrEnum):
    V14 = "40.0"


class ExportType(IntEnum):
    """Aspen Plus export file types (``HAPEXPType``)."""
    BACKUP              =  1  # Backup file (.bkp)
    REPORT              =  2  # Report file (.rep)
    SUMMARY             =  3  # Summary file (.sum)
    INPUT               =  4  # Input file (.inp)
    INPUT_GRAPHICS      =  5  # Input + graphics data file
    RUN_MSG             =  6  # Run messages file (.msg)
    REPORT_INPUT        =  7  # Report + input file
    REPORT_SUMMARY      =  8  # Report + summary file
    FLOW_DYN            =  9  # Flow-driven dynamic simulation file
    PRESSURE_DYN        = 10  # Pressure-driven dynamic simulation file
    INPUT_WITH_GRAPHICS = 18  # Input file with graphics


class UnitAspen(object):
    def __init__(self, progid: str | type[CoClass] | GUID, machine: str | None = None):
        self.progid = progid
        self.machine = machine
        self.app: APP = client.CreateObject(progid, machine=machine)
        self.current_file: Path | None = None
        self._components: ComponentManager | None = None
        logger.success("Connected to Aspen Plus on machine {} with progid {}", self.machine, self.progid)

    def _set_current_file(self, path: str | Path) -> None:
        """Record the currently opened file's absolute path."""
        self.current_file = Path(path).resolve()
        logger.info("Tracked current file: {}", self.current_file)

    def _clear_current_file(self) -> None:
        """Reset the current file path to None."""
        if self.current_file is not None:
            logger.info("Untracked current file: {}", self.current_file)
        self.current_file = None

    def lazybind(self):
        """Enable late binding for the COM object.
    
        Replaces ``self.app`` with a ``comtypes.client.lazybind.Dispatch``
        wrapper, allowing dynamic method calls without pre-generated type library
        code. Called automatically by ``__enter__``.
        """
        disp = self.app.QueryInterface(IDispatch)
        type_info = disp.GetTypeInfo(0)
        self.app = cast(APP, client.lazybind.Dispatch(disp, type_info))

    def exit(self):
        """Quit Aspen Plus and release COM resources.
    
        Called automatically by ``__exit__`` when the context manager exits.
        """
        self.app.Close()
        self._clear_current_file()
        logger.success("Closed Aspen Plus application")

    def __enter__(self) -> "UnitAspen":
        self.lazybind()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    @property
    def version(self) -> str:
        """It will be return Aspen Plus version"""
        version_name: str = self.app.Name
        code = version_name.split(" ")[2]
        return AspenVersionCode(code).name

    def create_simulation(self, **kwargs) -> None:
        self.app.InitNew(**kwargs)

    def open_bkp(self, path: str | Path, **kwargs) -> None:
        """Open an Aspen Plus backup file (``.bkp``) via ``InitFromArchive2``.

        Args:
            path: Path to the backup file.
            **kwargs: Forwarded to ``InitFromArchive2``.
        """
        self._set_current_file(path)
        self.app.InitFromArchive2(str(self.current_file), **kwargs)
        logger.success("Opened Aspen Plus file: {}", self.current_file)

    def open_apw(self, path: str | Path, **kwargs) -> None:
        self._set_current_file(path)
        self.app.InitFromFile(str(self.current_file), **kwargs)

    def restore_bkp(self, path: str | Path) -> None:
        """Restore/merge an archive file into the current case."""
        self._set_current_file(path)
        self.app.Restore2(str(self.current_file))
        logger.success("Restored backup from: {}", self.current_file)

    def save(self) -> None:
        """Save the current file as an Aspen Plus document (``.apw``)."""
        self.app.Save()
        logger.success("Saved current file")

    def save_as(self, path: str | Path, overwrite: bool = False, **kwargs) -> None:
        """Save the current file as an Aspen Plus document (``.apw``) under a new name.

        Args:
            path: Destination path for the saved file.
            overwrite: Whether to overwrite an existing file.
            **kwargs: Additional keyword arguments forwarded to the COM
                ``SaveAs`` method.
        """
        self._set_current_file(path)
        self.app.SaveAs(str(self.current_file), overwrite, **kwargs)
        logger.success("Saved current file as: {}", self.current_file)

    def save_bkp(self, path: str | Path, save_children: bool = True) -> None:
        """Export the current file as an Aspen Plus backup archive (``.bkp``).

        Args:
            path: Destination path for the backup archive.
            save_children: Whether to save child objects (``WriteArchive2``
                ``savechildren`` argument).
        """
        self._set_current_file(path)
        self.app.WriteArchive2(str(self.current_file), save_children)
        logger.success("Saved backup archive to: {}", self.current_file)

    def export(self, path: str | Path, export_type: ExportType = ExportType.BACKUP) -> None:
        """Export an Aspen Plus file.
    
        Args:
            export_type: Export type, see :class:`ExportType`.
            path: Destination path for the exported file.
            **kwargs: Additional keyword arguments forwarded to the COM
                ``Export`` method.
        """
        self._set_current_file(path)
        self.app.Export(export_type.value, str(self.current_file))
        logger.success("Exported {} to: {}", export_type.name, self.current_file)

    def set_visible(self, visible: bool):
        """Set the visibility of the Aspen Plus application window.

        Args:
            visible: ``True`` to show the window, ``False`` to hide it.
            Setting ``False`` can be useful for running simulations in the
            background.
        """
        self.app.Visible = visible
        logger.info("Set Aspen Plus visibility to: {}", visible)

    def engine_run(self) -> None:
        """Run the simulation, equivalent to pressing the play button (``Run2``)."""
        self.app.Run2()
        logger.success("Started simulation")

    def engine_stop(self) -> None:
        """Stop the simulation, equivalent to pressing the stop button (``Engine.Stop``)."""
        self.app.Engine.Stop()
        logger.info("Stopped simulation")

    def engine_reinit(self) -> None:
        """Reinitialize the entire simulation, equivalent to pressing the reset button (``Reinit``)."""
        self.app.Reinit()
        logger.info("Reinitialized simulation")

    def engine_dummy_run(self) -> None:
        """Run the engine as a dummy run via ``Engine.Run2``, timing the execution."""
        start = time.time()
        self.app.Engine.Run2()
        logger.success("Dummy run completed in {:.2f}s", time.time() - start)

    def suppress_dialogs(self, suppress: bool = True) -> None:
        """Suppress or re-enable Aspen Plus popup dialogs (``SuppressDialogs``).

        Args:
            suppress: ``True`` to suppress dialogs, ``False`` to re-enable them.
        """
        self.app.SuppressDialogs = suppress
        logger.info("Set dialog suppression to: {}", suppress)

    def exec(self, action: Action) -> None:
        """Inject node references and execute all recorded operations in *action*.

        Args:
            action: An :class:`Action` instance with recorded operations.
        """
        blocks_node = self.app.Tree.Elements("Data").Elements("Blocks")
        streams_node = self.app.Tree.Elements("Data").Elements("Streams")
        action._inject_nodes(blocks_node, streams_node)
        action._execute()
        logger.success("Executed action with {} operation(s)", len(action._operations))

    def components(self) -> ComponentManager:
        """Return a :class:`ComponentManager` bound to the current components node."""
        if self._components is None:
            components_node: IHNode = self.app.Tree.Elements("Data").Elements("Components")
            self._components = ComponentManager(components_node)
        return self._components


if __name__ == "__main__":
    with UnitAspen("{CF916C06-D17A-4A07-8548-787F4B0F99CB}", machine="192.168.88.129") as aspen:
        aspen.create_simulation()
        aspen.set_visible(True)