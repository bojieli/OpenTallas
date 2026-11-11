"""DIE-QC-97 11-11 ISLAND-VIEW: qc_island_view_event binds the vmr / crh_rp1 plan instances to the signed FT view."""
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import core_ft_physical as CF  # noqa: E402
import kit_core_clocks as K  # noqa: E402
import qc_island_view_event as E  # noqa: E402

PLAN_DIR = ROOT / E.PLAN_DIR


def _pv():
    spec = importlib.util.spec_from_file_location("_pv_iv", ROOT / "tools/autopilot/prov_view.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def core(inst, module):
    return {"inst": inst, "module": module, "origin_um": [25.92, 51.84], "outline_um": [250.56, 216.0], "orient": "R0",
            "track_offset_um": [0.012, 0.012], "pins_file": f"cores/su/signed/{module}_pins.json", "note": "K2b"}


def plan():
    hc = [core("u_suvm_u_vm8q_u_va", "qfd_dv_s8x_vmr"), core("u_suvm_u_vm8q_u_cl", "qfd_dv_s8_crh_rp1"),
          {"inst": "u_suvm_u_su8", "module": "qfd_dv_s5_su8_rst3", "pins_file": "x.json", "note": "rst3"}]
    return {"die": {"name": "qwen_compute"}, "partition_types": {"sle_su_c": {"hard_cores": hc, "clock": {"taps": []}},
                                                                 "sle_ctl": {"hard_cores": [], "clock": {}}}}


def test_binds_both_masters_and_nothing_else():
    P = plan()
    Q, ch = E.apply(P, ROOT)
    assert ch == {"sle_su_c": ["u_suvm_u_vm8q_u_va", "u_suvm_u_vm8q_u_cl"]}
    assert E.diff_keys(P, Q) == ["partition_types.sle_su_c"]
    a, b = P["partition_types"]["sle_su_c"]["hard_cores"], Q["partition_types"]["sle_su_c"]["hard_cores"]
    assert a[2] == b[2]                                          # rst3 neighbour (no FT pins) unchanged
    for old, new in zip(a[:2], b[:2]):
        assert {k for k in set(old) | set(new) if old.get(k) != new.get(k)} == {"note", "physical_ft", "native_port_adapter"}
        assert new["native_port_adapter"] == {"merge": {}, "cycles": 0, "tie": {"ft_ck_i": "1'b0", "ft_rst_i": "1'b0"}}
        assert new["physical_ft"]["unconsumed_outputs"] == ["ft_ck_o", "ft_rst_o"]
        assert not Path(new["physical_ft"]["proof"]).is_absolute()
        d = ROOT / Path(new["physical_ft"]["proof"]).parent
        m = new["module"]
        k = CF.load(new, m, d / f"{m}.lef", d / f"{m}_tt.lib", d / f"{m}_ff.lib", root=ROOT, plan_dir=PLAN_DIR)
        assert sorted(p["name"] for p in k["ports"]) == ["ft_ck_i", "ft_ck_o", "ft_rst_i", "ft_rst_o"]
    R, ch2 = E.apply(Q, ROOT)                                    # idempotent
    assert R == Q and ch2 == {}


def test_wrong_pins_or_conflicting_adapter_fail_closed():
    P = plan()
    P["partition_types"]["sle_su_c"]["hard_cores"][0]["pins_file"] = "cores/su/signed/qfd_dv_s8x_prog_pins.json"
    with pytest.raises(ValueError, match="not the signed core pins"):
        E.apply(P, ROOT)
    P = plan()
    P["partition_types"]["sle_su_c"]["hard_cores"][1]["native_port_adapter"] = {"merge": {}, "cycles": 1, "tie": {}}
    with pytest.raises(ValueError, match="different native_port_adapter"):
        E.apply(P, ROOT)


def test_kit_tie_then_gen_contract_accepts_the_parent_form():
    Q, _ = E.apply(plan(), ROOT)
    cores = Q["partition_types"]["sle_su_c"]["hard_cores"][:2]
    bound = "module p(input clk);\n" + "".join(
        f"  {c['module']} u_{c['inst']} (\n    .clk(clk)\n  );\n" for c in cores) + "endmodule\n"
    staged, rec = K.adapt_core_ports(bound, cores)
    assert [r["ports"] for r in rec] == [["ft_ck_i", "ft_rst_i"]] * 2
    macros = []
    for c in cores:
        d = ROOT / Path(c["physical_ft"]["proof"]).parent
        macros.append((None, c["module"], d / f"{c['module']}.lef", d / f"{c['module']}_tt.lib"))
    out = CF.contracts(cores, macros, staged, ROOT, PLAN_DIR)
    assert sorted(out) == sorted(E.CORES)
    bad = staged.replace("ft_rst_i(1'b0)", "ft_rst_i(clk)", 1)
    with pytest.raises(ValueError, match="input tie not emitted"):
        CF.contracts(cores, macros, bad, ROOT, PLAN_DIR)


def test_prov_view_resolves_relative_proof_against_src(tmp_path):
    PV = _pv()
    Q, _ = E.apply(plan(), ROOT)
    c = Q["partition_types"]["sle_su_c"]["hard_cores"][0]
    d = ROOT / Path(c["physical_ft"]["proof"]).parent
    here = os.getcwd()
    os.chdir(tmp_path)                                           # the remote kit_wave shell cwd is not the repo
    try:
        assert PV.check_routed(str(d), c["module"], c, PV.plan_pins(c, str(PLAN_DIR)), None, str(ROOT)) == (True, "ok")
    finally:
        os.chdir(here)


def test_serialization_style_kept():
    P = plan()
    text = json.dumps(P, separators=(",", ":")) + "\n"
    Q, _ = E.apply(copy.deepcopy(P), ROOT)
    out = E.dumps_like(Q, text)
    assert out.endswith("}\n") and ", " not in out.split('"note"')[0]
