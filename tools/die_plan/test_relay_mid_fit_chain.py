"""relay_mid.tcl FIT CHAIN (FAM-S81-COL-R3 11-21, opt-in OT_RELAY_MID_FIT_CHAIN=1): the previous leg of a FIT stage is
measured from the previous chain stage's actual seat.  gen_phys exports the env only when the plan or GEN env asks for it,
so kits without the key are byte-identical.   python3 -m pytest -q tools/die_plan/test_relay_mid_fit_chain.py"""
import re
from pathlib import Path

import gen_phys

HERE = Path(__file__).resolve().parent


def test_fit_chain_opt_in(monkeypatch):
    monkeypatch.delenv("OT_RELAY_MID_FIT_CHAIN", raising=False)
    assert not gen_phys._relay_mid_fit_chain({}, "col_h10_r0_p1__t1__cl574cc59d")
    assert gen_phys._relay_mid_fit_chain({"relay_mid_fit_chain": True}, "x__t1")
    assert gen_phys._relay_mid_fit_chain({"relay_mid_fit_chain_types": ["col_h10_r0_p1"]}, "col_h10_r0_p1__t1__cl574cc59d")
    assert not gen_phys._relay_mid_fit_chain({"relay_mid_fit_chain_types": ["col_h9_r1"]}, "col_h10_r0_p1__t1__cl574cc59d")
    monkeypatch.setenv("OT_RELAY_MID_FIT_CHAIN", "1")
    assert gen_phys._relay_mid_fit_chain({}, "anything__t1")


def test_tcl_chain_guarded():
    s = (HERE / "relay_mid.tcl").read_text()
    assert re.search(r'set rm_fit_chain \[expr \{\[info exists ::env\(OT_RELAY_MID_FIT_CHAIN\)\] && \$::env\(OT_RELAY_MID_FIT_CHAIN\) eq "1"\}\]', s)
    # the actual previous seat replaces the nominal one only in chain mode, and seats are recorded only in chain mode
    assert "if {$rm_fit_chain && [dict exists $rm_prev $g] && [dict exists $rm_seat [dict get $rm_prev $g]]}" in s
    assert "if {$rm_fit_chain} { dict set rm_seat $g" in s
    # predecessor of each straight-line chain stage
    assert "dict set rm_prev $c $rm_pc" in s
