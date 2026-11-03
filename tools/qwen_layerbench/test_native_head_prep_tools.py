"""Smoke test: the native HEAD preparation tools (headlease-candidate-2145) compile and import without side effects."""
import importlib.util
import py_compile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = [
    "head_stage_loader_fixture.py",
    "native_fw_command_frame.py",
    "native_head_partial_gold.py",
    "prepare_bound_head_producer_cut.py",
    "prepare_native_head_prefix_capture.py",
    "prepare_native_l6_node_component.py",
    "prepare_native_start_cone.py",
    "prepare_native_tail_control.py",
]


@pytest.mark.parametrize("name", TOOLS)
def test_tool_compiles(name):
    py_compile.compile(str(HERE / name), doraise=True)


@pytest.mark.parametrize("name", ["native_fw_command_frame.py"])
def test_library_tools_import(name):
    spec = importlib.util.spec_from_file_location(name[:-3], HERE / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
