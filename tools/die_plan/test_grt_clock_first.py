"""FLOW-CLKGRT-1121: OT_GRT_CLOCK_FIRST=1 (gen env) -> config.mk line + grt_clock_first.tcl staged + hook appended last to grt_pre.tcl;
unset -> kit byte-equal.  The Tcl wraps only the first full global_route and passes incremental calls through."""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402


def test_cfg_off_by_default(monkeypatch):
    monkeypatch.delenv("OT_GRT_CLOCK_FIRST", raising=False)
    assert gen_phys.grt_clock_first_cfg() == []
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST", "0")
    assert gen_phys.grt_clock_first_cfg() == []


def test_cfg_on_and_reserve(monkeypatch):
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST", "1")
    monkeypatch.delenv("OT_GRT_CLOCK_FIRST_RESERVE", raising=False)
    assert "export OT_GRT_CLOCK_FIRST = 1" in gen_phys.grt_clock_first_cfg()
    monkeypatch.setenv("OT_GRT_CLOCK_FIRST_RESERVE", "0")
    assert gen_phys.grt_clock_first_cfg()[-1] == "export OT_GRT_CLOCK_FIRST_RESERVE = 0"
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
