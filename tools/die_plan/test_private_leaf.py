"""HEAD-SERDES-1115 11-15: clock.private_leaf = [{like, re}] -> OT_PRIVATE_LEAF_LIKE/RE + private_leaf.tcl post-CTS kit step."""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402
from test_g2 import PAIR  # noqa: E402

TCLSH = shutil.which("tclsh")
ROW = {"like": "u_phy.u_link.u_dec.u_chn",
       "re": r"(?:^|[.])u_phy\.u_link\.u_dec\.u_syn\.g_bm\[[0-2]\]\.u_bm\.done\[0\]"}


def _plan(row):
    p = copy.deepcopy(PAIR)
    if row is not None:
        p["partition_types"]["fa"].setdefault("clock", {})["private_leaf"] = row
    return p


def test_key_declared_and_on_disk_schema_in_sync():
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk == json.loads(json.dumps(schema.SCHEMA))
    assert '"private_leaf"' in json.dumps(schema.SCHEMA)


def test_plan_with_row_validates_and_bad_rows_are_refused():
    assert not [e for e in schema.validate(_plan([ROW])) if "private_leaf" in e]
    assert [e for e in schema.validate(_plan([{"re": "xyz"}])) if "private_leaf" in e]            # like required
    assert [e for e in schema.validate(_plan([dict(ROW), dict(ROW)])) if "private_leaf" in e]     # one row per type
    assert [e for e in schema.validate(_plan([dict(ROW, bogus=1)])) if "private_leaf" in e]


def test_exports():
    assert gen_phys.private_leaf_exports({}) == []
    assert gen_phys.private_leaf_exports({"clock": {}}) == []
    out = gen_phys.private_leaf_exports({"clock": {"private_leaf": [ROW]}})
    assert out == [f"export OT_PRIVATE_LEAF_LIKE = {ROW['like']}", f"export OT_PRIVATE_LEAF_RE = {ROW['re']}"]


@pytest.mark.parametrize("bad", [{"like": "a b", "re": "xyz"}, {"like": "a", "re": "x$"}, {"like": "a", "re": "x y"},
                                 {"like": "a#", "re": "xyz"}, {"like": "", "re": "xyz"}, {"like": "a", "re": "(["}])
def test_exports_refuse_unsafe_or_bad_regex(bad):
    with pytest.raises(Exception):
        gen_phys.private_leaf_exports({"clock": {"private_leaf": [bad]}})


def _kit(tmp, row):
    gen_phys.write_type_kit(schema.Plan(_plan(row)), "fa", str(tmp), [])
    return Path(tmp) / "fa"


def test_kit_without_row_is_unchanged(tmp_path):
    k = _kit(tmp_path, None)
    assert not (k / "private_leaf.tcl").exists()
    assert "OT_PRIVATE_LEAF" not in (k / "config.mk").read_text()


def test_kit_with_row_gets_step_file_and_config(tmp_path):
    k = _kit(tmp_path, [ROW])
    assert (k / "private_leaf.tcl").read_text() == (HERE / "private_leaf.tcl").read_text()
    cfg = (k / "config.mk").read_text()
    assert f"export OT_PRIVATE_LEAF_LIKE = {ROW['like']}" in cfg and f"export OT_PRIVATE_LEAF_RE = {ROW['re']}" in cfg


def test_run_kit_step_is_file_gated_fail_open_and_before_tt_repair():
    t = gen_phys.RUN_KIT
    i = t.index("/work/private_leaf.tcl")
    assert t.index("$M cts SKIP_CTS_REPAIR_TIMING=1") < i < t.index("tt_setup_repair.on") < t.index("hold_gate.tcl")
    assert "OT_PRIVATE_LEAF FALLBACK step rc" in t and "4_cts.odb unchanged" in t


def test_tcl_moves_clock_pins_only_of_an_anchor_leaf_clone_and_fails_open():
    t = (HERE / "private_leaf.tcl").read_text()
    for need in ("OT_PRIVATE_LEAF_LIKE", "OT_PRIVATE_LEAF_RE", "dbInst_create", "detailed_placement", "check_placement",
                 "OT_PRIVATE_LEAF FALLBACK", "OT_PRIVATE_LEAF_AT", "setDoNotTouch 1", "$it disconnect; $it connect $newnet"):
        assert need in t, need
    assert "write_db" in t and t.index("check_placement") < t.index("write_db")                  # nothing written when illegal
    assert "repair_timing" not in t and "set_clock_latency" not in t


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_tcl_is_complete():
    code = f"set f [open {HERE / 'private_leaf.tcl'}]; set t [read $f]; close $f; puts [info complete $t]"
    assert subprocess.run([TCLSH], input=code, text=True, capture_output=True).stdout.strip() == "1"
