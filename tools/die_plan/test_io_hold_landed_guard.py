"""DIE-QC-97 11-10: IO-HOLD option A never re-delays a LANDED input.  Landed (clock-landing ring / landed ft) ports are
timed on their forwarded clock; `set_input_delay -min -clock vclk` without -add_delay (constraint.sdc per-port lines,
io_hold.tcl ot_io_hold_apply) would replace their fclk_in_* delays, so input_hold_min leaves them on the ring contract."""
import copy
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _plan(landed=()):
    raw = copy.deepcopy(PAIR)
    raw.setdefault("clock", {})["io_hold"] = "sender_min"
    if landed:
        ck = raw["partition_types"]["fb"].setdefault("clock", {})
        ck["landing_contract"] = {"bands": {b: {"instance": f"u_cland_{b}"} for b in landed}}
    return schema.Plan(raw)


def test_landed_port_excluded_unlanded_kept():
    base = gen_phys.input_hold_min(_plan(), "fb")
    assert set(base) == {"z_i", "x_i"}
    P = _plan(landed=("x_i",))
    m = gen_phys.input_hold_min(P, "fb")
    assert set(m) == {"z_i"}                                  # x_i stays on its ring contract
    tcl = gen_phys.io_hold_tcl(P, "fb")
    assert "x_i[*]" not in tcl and "z_i[*]" in tcl
    # constraint.sdc per-port lines come from the same input_hold_min (gen_phys.sdc)


def test_all_landed_means_no_overlay():
    P = _plan(landed=("x_i", "z_i"))
    assert gen_phys.input_hold_min(P, "fb") == {} and gen_phys.io_hold_tcl(P, "fb") is None


def test_qc_slw_fw_v3_rings_not_redelayed():
    """optional on a host with a QC plan (OT_QC_PLAN): none of slw_fw_v3's landed ring / ft inputs take option A"""
    f = os.environ.get("OT_QC_PLAN")
    if not f:
        return
    raw = json.load(open(f))
    raw["clock"]["io_hold"] = "sender_min"
    P = schema.Plan(raw, path=f)
    m = gen_phys.input_hold_min(P, "slw_fw_v3")
    ring = {"cmd_wi", "rd_wi", "dr_wi", "st_wi", "cws0_i", "rsf_i", "rsn_i", "x_ctl_i", "x_st_a_fe_i"}
    assert not ring & set(m), sorted(ring & set(m))
    assert {"x_fe_i", "x_fe_p1_i", "x_stm_i"} <= set(m)


if __name__ == "__main__":
    for n, fn in sorted(globals().items()):
        if n.startswith("test_"):
            fn(); print("PASS", n)
