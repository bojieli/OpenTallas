"""C-GPL-POSTTD-TAIL-SPARSE (HEAD-EAST-R4 11-27): plan gpl_td.post_td_exit, default OFF.  The timing-driven GPL call ends at the exit
overflow, so the post-TD Nesterov tail that spread a sparse kit's free cells into empty strips (hd_lep0N C1d +53 % HPWL) is cut; the TD
pass stays at least 5 points above the exit and is kept (not virtual)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gpl_td as GT
import test_gpl_guard as TG
from test_gpl_td import CALL, MOCK, GP

HERE = Path(__file__).resolve().parent
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
BASE = {"top_overflow_trigger": 1, "firm_small_clusters": 1, "cell_growth_gate": 2}
# the measured hd_lep0N C1d call (3_3_place_gp.log line 235, before the wrapper's own edits)
REAL = ("-density 0.5 -pad_left 0 -pad_right 0 -routability_driven -timing_driven -keep_resize_below_overflow 0 "
        "-force_center_initial_place -min_phi_coef 0.95 -max_phi_coef 1.05")


def _kit(tmp_path, name):
    kd = tmp_path / name
    kd.mkdir()
    for n in ("face_flops.tcl", "face_flops_release.tcl", "config.mk"):
        (kd / n).write_text("orig\n")
    return kd


def test_off_is_the_old_spec_and_kit(tmp_path):
    for d in (dict(BASE), dict(BASE, post_td_exit=0), dict(BASE, post_td_exit=False)):
        assert GT.spec({"gpl_td": d}, "T") == {"top": 0.25, "firm_small": 20, "growth": 2}
    a, b = _kit(tmp_path, "a"), _kit(tmp_path, "b")
    GT.apply(a, {"gpl_td": dict(BASE)}, "T")
    GT.apply(b, {"gpl_td": dict(BASE, post_td_exit=0)}, "T")
    assert {p.name: p.read_bytes() for p in a.iterdir()} == {p.name: p.read_bytes() for p in b.iterdir()}
    assert "OT_GPL_TD_EXIT" not in (a / "config.mk").read_text()


@pytest.mark.parametrize("top,v,want", [(1, 1, 0.20), (1, True, 0.20), (1, 0.15, 0.15), (0.3, 0.18, 0.18), (0.35, 1, 0.20)])
def test_spec_and_config_line(top, v, want):
    raw = {"gpl_td": dict(BASE, top_overflow_trigger=top, post_td_exit=v)}
    assert GT.spec(raw, "T")["exit"] == want
    assert f"export OT_GPL_TD_EXIT = {want:g}" in GT.cfg_lines(raw, "T")


@pytest.mark.parametrize("v", [1.0001, -0.1, 1.5, "x", "0.2", "report", [0.2], None])
def test_bad_exit_fails_closed(v):
    with pytest.raises(ValueError, match="gpl_td"):
        GT.spec({"gpl_td": dict(BASE, post_td_exit=v)}, "T")


def test_bad_exit_fails_even_outside_the_type_scope():
    with pytest.raises(ValueError, match="post_td_exit"):
        GT.spec({"gpl_td": dict(BASE, post_td_exit=1.5, types="^hd_lep0N$")}, "hd_spn")


def test_exit_needs_the_settle_trigger_with_a_five_point_margin():
    with pytest.raises(ValueError, match="needs top_overflow_trigger"):
        GT.spec({"gpl_td": {"post_td_exit": 1}}, "T")
    for top, ex in ((1, 0.21), (0.25, 0.24), (0.3, 0.3), (0.2, 1)):
        with pytest.raises(ValueError, match="at least 0.05 under"):
            GT.spec({"gpl_td": {"top_overflow_trigger": top, "post_td_exit": ex}}, "T")
    with pytest.raises(ValueError, match="at most 0.2"):                  # settle 0.35 / exit 0.30 would raise the stock keep 0.25
        GT.spec({"gpl_td": {"top_overflow_trigger": 0.35, "post_td_exit": 0.3}}, "T")


def test_exit_with_trigger_installs_the_hook(tmp_path):
    kd = _kit(tmp_path, "k")
    assert GT.apply(kd, {"gpl_td": {"top_overflow_trigger": 1, "post_td_exit": 1}}, "T") is True
    mk = (kd / "config.mk").read_text()
    assert "export OT_GPL_TD_EXIT = 0.2" in mk and "export OT_GPL_TD_TOP = 0.25" in mk
    assert (kd / "face_flops.tcl").read_text().endswith("source /work/gpl_td.tcl\n")


def test_exit_follows_the_type_scope():
    raw = {"gpl_td": dict(BASE, post_td_exit=1, types="^hd_lep0N$")}
    assert GT.spec(raw, "hd_lep0N")["exit"] == 0.20 and GT.spec(raw, "hd_spn") == {}


def test_schema_carries_the_key():
    sch = json.loads((HERE / "die_plan.schema.json").read_text())
    hits = []

    def walk(o):
        if isinstance(o, dict):
            if "post_td_exit" in o.get("properties", {}) and "top_overflow_trigger" in o["properties"]:
                hits.append(o["properties"]["post_td_exit"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(sch)
    assert hits and all(set(h["type"]) == {"integer", "number", "boolean"} for h in hits)


def _calls(tmp_path, call, env):
    pre = MOCK % dict(CELLS="A B", RES=str(tmp_path), ENV=env)
    out = subprocess.run(["tclsh"], input=pre + GP + f"global_placement {call}\nforeach c $::calls {{ puts \"C: $c\" }}\n",
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout, re.findall(r"^C: (.*)$", out.stdout, re.M)


TE = "set ::env(OT_GPL_TD_TOP) 0.25; set ::env(OT_GPL_TD_EXIT) 0.2"


@needs_tcl
def test_exit_sets_the_overflow_and_the_td_pass_still_runs_first(tmp_path):
    out, c = _calls(tmp_path, CALL, TE)
    assert c == [CALL + " -overflow 0.2 -timing_driven_net_reweight_overflow 25"], c      # TD pass at 0.25, exit at 0.20
    assert "OT_GPL_TD_EXIT timing-driven GPL ends at overflow 0.2" in out


@needs_tcl
def test_the_measured_c1d_call_shape(tmp_path):
    out, c = _calls(tmp_path, REAL, TE)
    assert c == [REAL + " -overflow 0.2 -timing_driven_net_reweight_overflow 25"], c      # keep 0 = no keep bound: untouched
    assert "keep_resize_below_overflow" not in out.split("OT_GPL_TD_EXIT", 1)[1].split("\n")[0]


@needs_tcl
def test_exit_only_env_still_places_the_pass_above_the_exit(tmp_path):
    out, c = _calls(tmp_path, CALL, "set ::env(OT_GPL_TD_EXIT) 0.2")
    assert c == [CALL + " -overflow 0.2 -timing_driven_net_reweight_overflow 25"], c
    assert "no settle overflow" in out


@needs_tcl
def test_named_thresholds_at_or_under_the_exit_floor_are_dropped(tmp_path):
    _, c = _calls(tmp_path, CALL + " -timing_driven_net_reweight_overflow {79 64 49 29 21 15}", TE)
    assert c == [CALL + " -timing_driven_net_reweight_overflow 25 -overflow 0.2"], c


@needs_tcl
def test_threshold_window_is_floor_to_settle(tmp_path):
    _, c = _calls(tmp_path, CALL.replace("0.25", "0.4") + " -timing_driven_net_reweight_overflow {79 64 49 29 21 15}",
                  "set ::env(OT_GPL_TD_TOP) 0.35; set ::env(OT_GPL_TD_EXIT) 0.2")
    assert c == [CALL.replace("0.25", "0.4") + " -timing_driven_net_reweight_overflow 29 -overflow 0.2"], c


@needs_tcl
def test_keep_under_the_floor_is_raised_so_the_pass_is_kept(tmp_path):
    out, c = _calls(tmp_path, CALL, "set ::env(OT_GPL_TD_TOP) 0.25; set ::env(OT_GPL_TD_EXIT) 0.3")
    assert c == [CALL.replace("-keep_resize_below_overflow 0.25", "-keep_resize_below_overflow 0.4")
                 + " -overflow 0.3 -timing_driven_net_reweight_overflow 35"], c
    assert "raised to 0.4" in out


@needs_tcl
def test_a_higher_own_exit_is_kept_and_unset_env_is_untouched(tmp_path):
    call = CALL.replace("0.25", "0.5") + " -overflow 0.3"
    _, c = _calls(tmp_path, call, TE)
    assert c == [call + " -timing_driven_net_reweight_overflow 35"], c
    _, c = _calls(tmp_path, CALL, "set ::env(OT_GPL_TD_TOP) 0.25")
    assert c == [CALL + " -timing_driven_net_reweight_overflow 25"], c                    # flag off: the 11-26 call


@needs_tcl
def test_exit_only_touches_timing_driven_calls(tmp_path):
    plain = "-density 0.5 -pad_left 0"
    _, c = _calls(tmp_path, plain, "set ::env(OT_GPL_TD_EXIT) 0.2")
    assert c == [plain]


@needs_tcl
def test_bad_exit_env_errors(tmp_path):
    pre = MOCK % dict(CELLS="A", RES=str(tmp_path), ENV="set ::env(OT_GPL_TD_EXIT) 0.95")
    body = f"if {{[catch {{global_placement {CALL}}} e]}} {{ puts \"ERR: $e\" }}\nputs \"N=[llength $::calls]\"\n"
    out = subprocess.run(["tclsh"], input=pre + GP + body, capture_output=True, text=True)
    assert "ERR: OT_GPL_TD_EXIT must be" in out.stdout and "N=0" in out.stdout, out.stdout + out.stderr   # fails before the call


def _guard(gpl, env):
    body = TG.MOCK % dict(INSTS=" ".join("{" + " ".join(map(str, i)) + "}" for i in TG.SPARSE), ENV=env, GPL=gpl)
    tail = f'\nset rc [catch {{global_placement {TG.ARGS}}} res]\nputs "RC=$rc"\n'
    out = subprocess.run(["tclsh"], input=body + TG.GUARD + GP + tail, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout, re.findall(r"^CALL \d+: (.*)$", out.stdout, re.M)


@needs_tcl
def test_through_the_gpl_guard_sparse_and_plain_retry(tmp_path):
    out, c = _guard("ok", TE)
    assert len(c) == 1 and "-routability_driven" not in c[0] and "-timing_driven" in c[0], out
    assert "-overflow 0.2" in c[0] and "-timing_driven_net_reweight_overflow 25" in c[0], c
    out, c = _guard("diverge_modal", TE)
    assert len(c) == 2 and "-timing_driven" not in c[1] and "-overflow 0.2" in c[1], out          # plain retry inherits the exit
    out, c = _guard("ok", "set ::env(OT_GPL_TD_TOP) 0.25")
    assert "-overflow" not in c[0], c                                                              # flag off: no exit edit
