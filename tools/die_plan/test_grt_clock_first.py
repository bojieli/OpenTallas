"""FLOW-CLKGRT-1121: OT_GRT_CLOCK_FIRST=1 (gen env) -> config.mk line + grt_clock_first.tcl staged + hook appended last to grt_pre.tcl;
unset -> on (default, FLOW-CLKGRT-R2); OT_GRT_CLOCK_FIRST=0 -> no line, no hook.  The Tcl wraps only the first full global_route and passes incremental calls through."""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402


def test_cfg_on_by_default_opt_out(monkeypatch):
    for k in ("OT_GRT_CLOCK_FIRST", "OT_GRT_CLOCK_FIRST_RESERVE", "OT_GRT_CLOCK_FIRST_RES_AWARE"):
        monkeypatch.delenv(k, raising=False)
    assert "export OT_GRT_CLOCK_FIRST = 1" in gen_phys.grt_clock_first_cfg()
    assert not any("RES_AWARE" in l for l in gen_phys.grt_clock_first_cfg())   # resistance-aware stays opt-in
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST", "0")
    assert gen_phys.grt_clock_first_cfg() == []
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST", "2")
    with pytest.raises(SystemExit):
        gen_phys.grt_clock_first_cfg()


def test_cfg_on_and_reserve(monkeypatch):
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST", "1")
    monkeypatch.delenv("OT_GRT_CLOCK_FIRST_RESERVE", raising=False)
    assert "export OT_GRT_CLOCK_FIRST = 1" in gen_phys.grt_clock_first_cfg()
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST_RESERVE", "0")
    assert gen_phys.grt_clock_first_cfg()[-1] == "export OT_GRT_CLOCK_FIRST_RESERVE = 0"
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST_RES_AWARE", "1")
    assert gen_phys.grt_clock_first_cfg()[-1] == "export OT_GRT_CLOCK_FIRST_RES_AWARE = 1"
    monkeypatch.delenv("OT_GRT_CLOCK_FIRST_RES_AWARE")
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST_RESERVE", "x")
    with pytest.raises(SystemExit):
        gen_phys.grt_clock_first_cfg()


def test_install_from_final_config(tmp_path):
    (tmp_path / "grt_pre.tcl").write_text("# pre\nif {1} { source pg_pair_cap.tcl; ot_pgcap_add }\n")
    (tmp_path / "config.mk").write_text("export OT_PGCAP = 1\n")
    assert gen_phys.grt_clock_first_install(tmp_path) is False
    assert not (tmp_path / "grt_clock_first.tcl").exists()
    (tmp_path / "config.mk").write_text("export OT_GRT_CLOCK_FIRST = 1\n")
    assert gen_phys.grt_clock_first_install(tmp_path) is True
    assert gen_phys.grt_clock_first_install(tmp_path) is True        # idempotent
    g = (tmp_path / "grt_pre.tcl").read_text()
    assert g.count("grt_clock_first.tcl") == 1 and g.index("ot_pgcap_add") < g.index("grt_clock_first.tcl")
    assert (tmp_path / "grt_clock_first.tcl").read_bytes() == (HERE / "grt_clock_first.tcl").read_bytes()


def test_tcl_wraps_first_full_route_only():
    t = (HERE / "grt_clock_first.tcl").read_text()
    assert "rename ::global_route ::ot_gcf_gr_orig" in t
    assert re.search(r"-start_incremental\]\s*>=\s*0\s*\|\|\s*\[lsearch -exact \$args -end_incremental\]\s*>=\s*0", t)
    assert "grt::add_net_to_route" in t and len(re.findall(r"^\s*grt::read_segments", t, re.M)) == 2
    assert 'OT_GRT_CLOCK_FIRST) eq "1"' in t and "OT_GRT_CLOCK_FIRST_RESERVE" in t
    # the merge read_segments resets the router: allow-congestion is re-armed after it (else the next incremental route GRT-0116)
    tail = t[t.rindex("grt::read_segments $dir/5_1_grt.clock_first_all.seg"):]
    assert "::grt::set_allow_congestion 1" in tail
    assert re.search(r"OT_GRT_CLOCK_FIRST_RES_AWARE\) eq \"1\".*\n\s*lappend args -resistance_aware -res_aware_nets_percentage 0", t)


def test_tcl_reports_clock_phase_ndr_loss():
    # GRT-0273 in the clock-only phase = pin/root escape capacity (pc_v3 1122043653: 4 M7 clock tap ports): captured with
    # utl::teeStringBegin/End around phase 1 only, written to 5_1_grt.clock_ndr_loss.tsv, never a stop
    t = (HERE / "grt_clock_first.tcl").read_text()
    ph1 = t[t.index("::utl::teeStringBegin }"):t.index("grt::write_segments $dir/5_1_grt.clock_first.seg")]
    assert "::utl::teeStringEnd" in ph1 and "ndr_loss $log1 $dir/5_1_grt.clock_ndr_loss.tsv" in ph1
    assert "return -options $opts1 $res1" in ph1
    proc = t[t.index("proc ndr_loss"):t.index("proc route")]
    assert "GRT-0273" in proc and "getNonDefaultRule" in proc and "utl::error" not in proc
