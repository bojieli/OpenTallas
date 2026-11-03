"""FLOW-INFRA-2 10-25: GRT-RC tap pre-pass (tapbal_grt.tcl) between CTS and the FF GRT hold repair."""
import tempfile
import subprocess

import pytest

from test_flow_hold_basis import HERE, _plan, gen_phys


def _cfg(monkeypatch, env=None, type_clock=None):
    if env is None:
        monkeypatch.delenv("OT_GEN_TAP_GRT_PRE", raising=False)
    else:
        monkeypatch.setenv("OT_GEN_TAP_GRT_PRE", env)
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(_plan(type_clock=type_clock), "src", d, [],
                                     hold_ff_margin=gen_phys.HOLD_FF_MARGIN_DEFAULT)
        assert (kd / "tapbal_grt.tcl").is_file()
        return (kd / "config.mk").read_text()


def test_default_off_env_and_plan_on(monkeypatch):
    assert gen_phys.TAP_GRT_PRE_DEFAULT is False
    assert "OT_TAP_GRT_PRE" not in _cfg(monkeypatch)
    assert "export OT_TAP_GRT_PRE = 1" in _cfg(monkeypatch, env="1")
    assert "export OT_PINREG_PAD = 1" in _cfg(monkeypatch, env="1")
    assert "OT_TAP_GRT_PRE" not in _cfg(monkeypatch, env="0")
    assert "export OT_TAP_GRT_PRE = 1" in _cfg(monkeypatch, type_clock=dict(tap_grt_pre=True))
    assert "OT_TAP_GRT_PRE" not in _cfg(monkeypatch, env="1", type_clock=dict(tap_grt_pre=False))


def test_run_kit_runs_prepass_after_cts_before_hold_gate_and_ff_grt():
    rk = gen_phys.RUN_KIT
    i_cts = rk.index("\\$M cts SKIP_CTS_REPAIR_TIMING=1")
    i_pre = rk.index("RUN_SCRIPT=/work/tapbal_grt.tcl")
    i_hg = rk.index("/work/hold_gate.tcl")
    i_grt = rk.index("OT_VCLK_CORNER=ff \\$MF grt")  # macro_ff_repair.mk form (MF = M [+ DESIGN_CONFIG])
    assert i_cts < i_pre < i_hg < i_grt
    assert "grep -Eq '^export OT_(TAP_GRT_PRE|PINREG_PAD) = 1' /work/config.mk" in rk
    assert "CORNER=TC CORNERS=tc" in rk[i_pre - 200:i_pre + 200]


def test_prepass_script_routes_balances_on_grt_and_rewrites_cts_odb():
    s = (HERE / "tapbal_grt.tcl").read_text()
    order = ["load_design 4_cts.odb 4_cts.sdc", "\nglobal_route {*}$tg_args", "\nestimate_parasitics -global_routing",
             "set ::env(OT_TAP_EST) grt", "source [file join $tg_dir tap_balance.tcl]", "file copy -force", "write_db $::env(RESULTS_DIR)/4_cts.odb"]
    pos = [s.index(o) for o in order]
    assert pos == sorted(pos)
    assert "set ::env(OT_TAP_REPORT_ONLY) 0" in s


def test_pinreg_pad_uses_gate_set_and_fresh_measure():
    s = (HERE / "pinreg_pad.tcl").read_text()
    g = (HERE / "postcts_gate.tcl").read_text()
    for frag in ("ot_pinreg_set", "ot_pinreg_arr", "pinreg_measure.tcl"):
        assert frag in s and frag in g, frag
    m = s[s.index("proc pp_measure"):]
    assert m.index("set_propagated_clock [all_clocks]") < m.index("estimate_parasitics -global_routing")
    assert "sta::sta_to_db_pin" in s and "global_route -start_incremental" in s and "global_route -end_incremental" in s
    t = (HERE / "tapbal_grt.tcl").read_text()
    assert t.index("tap_balance.tcl]") < t.index("pinreg_pad.tcl") < t.index("write_db")


def test_gate_and_pad_share_one_pinreg_measure():
    # FLOW-CANARY 10-25: pad and gate must measure the same set + quantity (one proc), in the same GRT context
    m = (HERE / "pinreg_measure.tcl").read_text()
    for frag in ("proc ot_pinreg_set", "proc ot_pinreg_arr", "get_fanout -from $din", "get_fanin -to [all_outputs]",
                 "ot_cf_wire"):
        assert frag in m, frag
    g = (HERE / "postcts_gate.tcl").read_text()
    s = (HERE / "pinreg_pad.tcl").read_text()
    for x in (g, s):
        assert "pinreg_measure.tcl" in x and "ot_pinreg_set" in x and "ot_pinreg_arr" in x
        assert "all_registers -clock_pins" not in x and "get_fanout -from" not in x
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(_plan(), "src", d, [], hold_ff_margin=gen_phys.HOLD_FF_MARGIN_DEFAULT)
        assert (kd / "pinreg_measure.tcl").is_file()


def test_prepass_grt_edits_are_resistance_aware_as_orfs():
    # ORFS global_route.tcl routes (and re-routes incrementally) with -resistance_aware (asap7 ENABLE_RESISTANCE_AWARE=1);
    # without it the pre-pass read the s81 t12 pin-register mean 245.94 vs 226.32 with it (gate on 5_1_grt: 226.54)
    t = (HERE / "tapbal_grt.tcl").read_text()
    assert "append_env_var ::ot_grt_res_aware ENABLE_RESISTANCE_AWARE -resistance_aware 0" in t
    assert t.index("ot_grt_res_aware") < t.index("\nglobal_route {*}$tg_args")
    for f in ("tap_balance.tcl", "pinreg_pad.tcl"):
        s = (HERE / f).read_text()
        for ln in s.splitlines():
            if "global_route -end_incremental" in ln and not ln.lstrip().startswith("#"):
                assert "ot_grt_res_aware" in ln, (f, ln)


@pytest.mark.parametrize("config,enabled", [("export OT_PINREG_PAD = 1\n", True), ("export OT_TAP_GRT_PRE = 1\n", True), ("export OT_PINREG_PAD = 0\n", False), ("", False)])
def test_runner_prepass_predicate_honors_standalone_pinreg_pad(config, enabled):
    import re
    predicate = re.search(r"grep -Eq '([^']+)' /work/config.mk", gen_phys.RUN_KIT)[1]
    result = subprocess.run(["grep", "-Eq", predicate], input=config, text=True)
    assert (result.returncode == 0) == enabled


def test_plan_schema_accepts_tap_grt_pre():
    """DIE-HEAD-55 11-02: gen_phys reads type/plan clock.tap_grt_pre, so validate_structure must accept it (it refused
    the key as unknown, which made the knob unusable from a plan)."""
    import copy
    import schema
    from test_flow_hold_basis import TINY
    raw = copy.deepcopy(TINY)
    raw["partition_types"]["src"]["clock"]["tap_grt_pre"] = True
    raw["clock"]["tap_grt_pre"] = False
    assert not [e for e in schema.validate_structure(raw) if "tap_grt_pre" in e]
    raw["partition_types"]["src"]["clock"]["tap_grt_pre"] = "yes"
    assert [e for e in schema.validate_structure(raw) if "tap_grt_pre" in e]


# KW-FIX-4 11-03 (COORD 12:01 ruling (1)): HEAD l48h0 hd_st_str@3 / hd_st_n3_transit@4 (jobs 06a0a80ba547, d5e999faca7b)
# lost the kit to an OpenROAD SIGABRT inside the pre-pass (4_2_tapbal_grt.log: "Assertion '__n < this->size()' failed.
# Signal 6 received", frame sta::RequiredCmp::requiredSet, right after the tap_balance GRT it0 DPL).  A crash kills the
# whole process, so the runner (not a Tcl catch) restores 4_cts.odb and takes the plain GRT path.
CRASH_LOG = ("OT_TAP_BALANCE GRT it0 target 450: clk=424\nPlacement Analysis\n"
             "/usr/include/c++/11/bits/stl_vector.h:1045: ... Assertion '__n < this->size()' failed.\n"
             "Signal 6 received\nStack trace:\n 6# sta::RequiredCmp::requiredSet(unsigned long, sta::Delay&) in openroad\n")


def _prepass_segment():
    rk = gen_phys.RUN_KIT
    i = rk.index("    if [ \\$rc = 0 ] && grep -Eq '^export OT_(TAP_GRT_PRE|PINREG_PAD) = 1'")
    j = rk.index("rc=6; fi; fi; \\\n", i) + len("rc=6; fi; fi; \\\n")
    # the segment sits inside run_kit.sh's  bash -lc "..."  string: undo that quoting level
    return rk[i:j].replace("\\\n", "").replace("\\$", "$").replace('\\"', '"')


def _run_prepass(tmp_path, log, make_rc, config="export OT_TAP_GRT_PRE = 1\n", write_partial=True):
    work = tmp_path / "work"
    base = work / "run/results/asap7/dp_x/base"
    logs = work / "run/logs/asap7/dp_x/base"
    base.mkdir(parents=True)
    logs.mkdir(parents=True)
    (base / "4_cts.odb").write_text("CTS")
    (work / "config.mk").write_text(config)
    make = tmp_path / "make.sh"
    make.write_text("#!/bin/bash\n"
                    + (f"printf 'PARTIAL' > {base}/4_cts.odb\n" if write_partial else "")
                    + f"cat > {logs}/4_2_tapbal_grt.log <<'L'\n{log}L\nexit {make_rc}\n")
    make.chmod(0o755)
    seg = _prepass_segment().replace("/work", str(work))
    script = f"M={make}; rc=0; {seg}\necho RC=$rc\n"
    r = subprocess.run(["bash", "-c", script], text=True, capture_output=True)
    return r, work, base


def test_prepass_crash_falls_back_to_plain_grt(tmp_path):
    r, work, base = _run_prepass(tmp_path, CRASH_LOG, 250)
    assert "RC=0" in r.stdout, r.stdout + r.stderr
    assert (base / "4_cts.odb").read_text() == "CTS"  # the CTS database, not the half-written pre-pass one
    assert not (work / "FAIL_POSTCTS").exists() and not (work / "4_cts_pretapbal.odb").exists()
    fb = (work / "tapbal_fallback.log").read_text()
    assert fb.startswith("OT_TAPBAL_FALLBACK tapbal_grt.tcl tool crash (rc 250: Signal 6 received; sta::RequiredCmp::requiredSet)")
    assert "OT_TAPBAL_FALLBACK" in r.stdout
    # the crash log leaves the step-log set (autopilot crash patterns / canary step scans) but is kept as evidence
    assert "Signal 6 received" in (work / "4_2_tapbal_grt_crash.log").read_text()
    assert not list((work / "run/logs").rglob("4_2_tapbal_grt.log"))


@pytest.mark.parametrize("log,config", [
    ("[ERROR GRT-0118] routing congestion too high\n", "export OT_TAP_GRT_PRE = 1\n"),   # a non-crash failure
    (CRASH_LOG, "export OT_TAP_GRT_PRE = 1\nexport OT_TAPBAL_FALLBACK = 0\n"),         # fallback switched off
])
def test_prepass_noncrash_or_disabled_still_stops(tmp_path, log, config):
    r, work, _ = _run_prepass(tmp_path, log, 2, config)
    assert "RC=6" in r.stdout, r.stdout + r.stderr
    assert (work / "FAIL_POSTCTS").read_text() == "FAIL_POSTCTS GRT-RC tap pre-pass (tapbal_grt.tcl)\n"
    assert not (work / "tapbal_fallback.log").exists() and not (work / "4_cts_pretapbal.odb").exists()


def test_prepass_success_keeps_rewritten_odb(tmp_path):
    r, work, base = _run_prepass(tmp_path, "OT_TAP_GRT_PRE done\n", 0)
    assert "RC=0" in r.stdout and (base / "4_cts.odb").read_text() == "PARTIAL"
    assert not (work / "tapbal_fallback.log").exists() and not (work / "4_cts_pretapbal.odb").exists()


def test_generated_run_kit_parses():
    assert subprocess.run(["bash", "-n"], input=gen_phys.RUN_KIT, text=True).returncode == 0
