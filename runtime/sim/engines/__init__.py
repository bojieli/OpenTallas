"""Engine implementations for the ABI 3.0 functional device.

Importing this package registers every available engine with
``runtime.sim.engine``.  Registration is explicit rather than implicit so that
an unimplemented operation fails closed at issue time with a capability trap,
which is the required behaviour: no simulator, firmware or framework fallback
may substitute for a missing engine operation.
"""

from __future__ import annotations

import importlib
from typing import Iterable

#: Engine modules, in load order.  Each registers its own (family, subopcode)
#: handlers via the ``runtime.sim.engine.register`` decorator.
ENGINE_MODULES = (
    "runtime.sim.engines.dma",
    "runtime.sim.engines.tensor",
    "runtime.sim.engines.vector",
    "runtime.sim.engines.attention",
    "runtime.sim.engines.route",
    "runtime.sim.engines.reduction",
    "runtime.sim.engines.selection",
    "runtime.sim.engines.link",
    "runtime.sim.engines.deepseek_vector",
)


def load_engines(modules: Iterable[str] | None = None) -> dict[str, object]:
    """Import the engine modules and report registration coverage.

    Returns a dict with ``loaded``, ``unavailable`` and the coverage report
    from :func:`runtime.sim.engine.coverage_report`.  A module that is not yet
    present is reported rather than silently ignored, so a partially built
    device is always visible as such.
    """
    from runtime.sim.engine import coverage_report

    loaded: list[str] = []
    unavailable: dict[str, str] = {}
    for name in modules if modules is not None else ENGINE_MODULES:
        try:
            importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name == name or (exc.name or "").startswith(name):
                unavailable[name] = "module not present"
            else:
                unavailable[name] = f"missing dependency {exc.name}"
        except Exception as exc:  # a real error in an engine must be visible
            unavailable[name] = f"{type(exc).__name__}: {exc}"
        else:
            loaded.append(name)
    report = coverage_report()
    return {
        "loaded": loaded,
        "unavailable": unavailable,
        "implemented": report["implemented"],
        "missing": report["missing"],
        "sequencer_executed": report["sequencer_executed"],
        "implemented_count": len(report["implemented"]),
        "missing_count": len(report["missing"]),
        "sequencer_count": len(report["sequencer_executed"]),
    }
