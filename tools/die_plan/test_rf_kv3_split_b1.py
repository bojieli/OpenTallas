"""B1 PCC commit export (default-off) in rf_kv3_split.py: connect_b1_commit must handle the generated single-line
instance call and the multi-line form; the flag-off CLI/main behaviour stays the stock one."""
import importlib.util
import inspect
import sys
from pathlib import Path

import pytest

HARDEN = Path(__file__).resolve().parents[2] / "physical/die_plan/qwen_kvsys/cores/harden"
sys.path.insert(0, str(HARDEN))
_spec = importlib.util.spec_from_file_location("rf_kv3_split_under_test", HARDEN / "rf_kv3_split.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

CHILD = "qkd_kvs_pc__core_sc"
INST = "u_pc"

SINGLE = (
    "module qkd_kvs_pc__leaf (input ck);\n"
    "  wire a;\n"
    f"  {CHILD} {INST} (.ck(ck), .native_commit_valid(nv), .native_commit_identity(nid), .native_commit_address(nad));\n"
    "endmodule\n"
)
MULTI = (
    "module qkd_kvs_pc__leaf (input ck);\n"
    "  wire a;\n"
    f"  {CHILD} {INST} (\n"
    "      .ck(ck),\n"
    "      .native_commit_valid(nv),\n"
    "      .native_commit_identity(nid),\n"
    "      .native_commit_address(nad)\n"
    "  );\n"
    "endmodule\n"
)
UNCONNECTED = (
    "module qkd_kvs_pc__leaf (input ck);\n"
    f"  {CHILD} {INST} (.ck(ck));\n"
    "endmodule\n"
)


@pytest.mark.parametrize("form", [SINGLE, MULTI])
def test_connected_ports_alias_to_raw_bus(form):
    out = mod.connect_b1_commit(form, CHILD, INST)
    assert "assign pcc_b1_raw[90] = nv;" in out
    assert "assign pcc_b1_raw[89:29] = nid;" in out
    assert "assign pcc_b1_raw[28:0] = nad;" in out
    # connected ports stay as they were; the raw bus is an alias of the existing nets
    assert ".native_commit_valid(nv)" in out and ".native_commit_identity(nid)" in out and ".native_commit_address(nad)" in out
    assert out.count("module qkd_kvs_pc__leaf") == 1 and out.rstrip().endswith("endmodule")


def test_single_and_multi_line_forms_agree():
    a = mod.connect_b1_commit(SINGLE, CHILD, INST)
    b = mod.connect_b1_commit(MULTI, CHILD, INST)
    assert sorted(x for x in a.splitlines() if "assign" in x) == sorted(x for x in b.splitlines() if "assign" in x)


@pytest.mark.parametrize("form", [SINGLE, MULTI])
def test_unconnected_ports_are_added(form):
    src = UNCONNECTED if form is SINGLE else UNCONNECTED.replace("(.ck(ck));", "(\n      .ck(ck)\n  );")
    out = mod.connect_b1_commit(src, CHILD, INST)
    for p, idx in (("native_commit_valid", "[90]"), ("native_commit_identity", "[89:29]"), ("native_commit_address", "[28:0]")):
        assert f".{p}(pcc_b1_raw{idx})" in out


def test_missing_instance_asserts():
    with pytest.raises(AssertionError):
        mod.connect_b1_commit(SINGLE, "no_such_child", INST)


def test_default_off_signature_and_scope():
    sig = inspect.signature(mod.main)
    assert sig.parameters["b1_commit_export"].default is False
    with pytest.raises(ValueError):
        mod.main("k", "a", "b", "qkd_kvs_pc_h_head_p", b1_commit_export=True)
    src = (HARDEN / "rf_kv3_split.py").read_text()
    assert "b1_regs = \"\"" in src   # flag-off appends nothing to the PCC top
