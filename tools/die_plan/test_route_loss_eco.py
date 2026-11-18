"""ROUTE-LOSS 11-18 (FABLE-FIX-ROUTE-LOSS): sign-off endpoint tables + sign-off priced static plan of the single-mode late hold ECO."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eco_loop  # noqa: E402
import hold_eco_internal_run as HR  # noqa: E402
import signoff  # noqa: E402


def test_signoff_sessions_write_endpoint_tables():
    ff = signoff.session_tcl("ff", [], "/base/6_final.spef")
    tt = signoff.session_tcl("tt", [], "/base/6_final.spef")
    ss = signoff.session_tcl("ss", ["/ml0/m_ss.lib"], spef="/x/6_final.spef")
    assert ff.count("/out/ep_ff.tsv") == 1 and "/out/ep_tt.tsv" not in ff
    assert tt.count("/out/ep_tt.tsv") == 1 and "/out/ep_ff.tsv" not in tt
    assert "ep_ff.tsv" not in ss and "ep_tt.tsv" not in ss
    for t, name in ((ff, "ep_ff"), (tt, "ep_tt")):
        assert t.count(signoff.EP_MARK) == 1 and t.index("/out/%s.tsv" % name) < t.index(signoff.EP_MARK)
        assert t.index("so_timing STD") < t.index("/out/%s.tsv" % name)          # after the STD frame is bound
        assert "so EP_DUMP error" in t                                             # a dump failure never stops the session
    assert "-slack_max %d " % signoff.EP_TT_SLACK_MAX_PS in tt and "@EP_TT_MAX@" not in tt
    assert signoff.EP_TT_SLACK_MAX_PS >= 4 * 132.8 + 42                            # above it an end pays the 4-cell cap anyway


def test_signoff_endpoint_tables_opt_out(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_EP_DUMP", "0")
    assert "ep_ff.tsv" not in signoff.session_tcl("ff", [], "/base/6_final.spef")


def test_patch_session_is_idempotent_on_native_session():
    ff = signoff.session_tcl("ff", [], "/base/6_final.spef")
    assert HR.patch_session(ff, "ff") == ff
    tt = signoff.session_tcl("tt", [], "/base/6_final.spef")
    assert HR.patch_session(tt, "tt") == tt


def _signoff(tmp, ff_rows, tt_rows, logs=True):
    so = tmp / "signoff"
    (so / "ff").mkdir(parents=True)
    (so / "tt").mkdir(parents=True)
    (so / "ff" / "ep_ff.tsv").write_text("endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\n" + "".join(ff_rows))
    (so / "tt" / "ep_tt.tsv").write_text("endpoint\ttt_setup_slack_ps\n" + "".join(tt_rows))
    if logs:
        (so / "ff" / "sta.log").write_text("SO EP_DUMP ff %d\n" % len(ff_rows))
        (so / "tt" / "sta.log").write_text("SO EP_DUMP tt %d slack_max_ps 600\n" % len(tt_rows))
    (so / "signoff.json").write_text("{}")
    return so


def test_native_tables_need_both_files_and_session_lines(tmp_path):
    so = _signoff(tmp_path, ["u/a/D\tu/b/QN\treg\treg\t-8e12\n"], ["u/a/D\t300e12\n"])
    assert HR.native_tables(so)
    (so / "tt" / "sta.log").write_text("no dump line\n")
    assert not HR.native_tables(so)
    (so / "tt" / "ep_tt.tsv").unlink()
    assert not HR.native_tables(so)


def test_static_hold_plan_prices_tt_room_from_signoff(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "config.mk").write_text("export DESIGN_NAME = x\n")          # single-mode kit (no OT_HOLD_MM)
    so = _signoff(tmp_path,
                  ["u/a/D\tu/b/QN\treg\treg\t-8e12\n",                  # internal, TT room for one cell
                   "u/c/D\tu/d/QN\treg\treg\t-6e12\n",                  # internal, TT-critical: must not be padded
                   "u/e/D\tin[0]\tport\treg\t-50e12\n"],                # port start: the parent's
                  ["u/a/D\t300e12\n", "u/c/D\t20e12\n"])
    hp = eco_loop.static_hold_plan(kit, so / "signoff.json", tmp_path / "plan")
    assert hp and hp["rows"] == 1 and hp["endpoints"] == 3
    rows = [ln.split("\t") for ln in Path(hp["plan"]).read_text().splitlines() if ln and not ln.startswith("#")]
    assert [r[0] for r in rows] == ["u/a/D"] and int(rows[0][1]) == 1
    text = Path(hp["plan"]).read_text()
    assert "u/c/D" in text and "u/e/D" not in [r[0] for r in rows]      # the TT-critical end is listed as skipped, never padded


def test_static_hold_plan_falls_back(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "config.mk").write_text("export OT_HOLD_MM = 1\n")
    so = _signoff(tmp_path, ["u/a/D\tu/b/QN\treg\treg\t-8e12\n"], ["u/a/D\t300e12\n"])
    assert eco_loop.static_hold_plan(kit, so / "signoff.json", tmp_path / "p1") is None      # two-mode: priced in session
    (kit / "config.mk").write_text("export DESIGN_NAME = x\n")
    (so / "tt" / "ep_tt.tsv").unlink()
    assert eco_loop.static_hold_plan(kit, so / "signoff.json", tmp_path / "p2") is None      # older sign-off: no tables
    assert eco_loop.static_hold_plan(kit, None, tmp_path / "p3") is None


def test_iterate_hands_the_static_plan_to_the_b_pass():
    src = (HERE / "eco_loop.py").read_text()
    assert 'env["OT_PRD_HOLD_PLAN"] = hp["plan"]' in src and "_BASE_SIGNOFF.set(str(base_signoff))" in src
    hook = (HERE / "post_route_drv" / "prd_hook.tcl").read_text()
    assert hook.index("OT_PRD_HOLD_PLAN)] && $::env(OT_PRD_HOLD_PLAN) ne") < hook.index("OT_PRD_HOLD_TARGETED)] && $::env(OT_PRD_HOLD_TARGETED) eq")
    mk = (HERE / "post_route_drv" / "prd_mk.sh").read_text()
    assert "OT_PRD_HOLD_PLAN=/work/hold_plan.tsv" in mk


def test_hold_repair_signal_table_opt_out():
    t = (HERE / "hold_sdc_guard.tcl").read_text()
    i = t.index("proc ::ot_hsg_signal_ff")
    body = t[i:t.index("\n}\n", i)]
    assert 'OT_RC_SIGNAL_HOLD) eq "0"' in body and body.index("OT_RC_SIGNAL_HOLD") < body.index("::ot_rc_signal_table")


def _seed_block():
    """prd_mk.sh from the OT_PRD_FROM default to the seed-exists test, verbatim"""
    mk = (HERE / "post_route_drv" / "prd_mk.sh").read_text().splitlines()
    i = mk.index("FROM=${OT_PRD_FROM:-grt}")
    j = next(k for k, ln in enumerate(mk) if ln.startswith('test -f $RS/$SRC -a -f "$SPEF"'))
    assert i < j
    return "\n".join(mk[i:j + 1]) + '\necho "SEED $FROM $SRC"\n'


def _seed(tmp_path, files, frm):
    rs = tmp_path / "base"
    rs.mkdir(exist_ok=True)
    for f in files:
        (rs / f).write_text("x")
    env = {"PATH": "/usr/bin:/bin", "RS": str(rs), "SPEF": str(rs / "6_final.spef"), "OT_PRD_FROM": frm}
    return subprocess.run(["bash", "-euo", "pipefail", "-c", _seed_block()], env=env, capture_output=True, text=True)


def test_late_eco_stages_on_a_stage_capped_kit(tmp_path):
    """the automatic post-route repair must stage on what a capped kit holds (LATE-ECO 8f3d167975 fallback): measured on the capped
    private copy of QC sle_hc0__cl38badc56, prd_mk.sh b10 -> OT_PRD_FROM=final, pass dir ready"""
    p = _seed(tmp_path, ["6_final.odb", "6_final.spef", "5_1_grt.odb"], "route")
    assert p.returncode == 0 and "SEED final 6_final.odb" in p.stdout, p.stdout + p.stderr
    q = _seed(tmp_path, ["5_2_route.odb"], "route")
    assert q.returncode == 0 and "SEED route 5_2_route.odb" in q.stdout, q.stdout + q.stderr
