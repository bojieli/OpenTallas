"""KW-FIX-44 11-10 GRT-EARLY (COORD, owner fail-fast): grt183_make.sh stops the 5_1_grt stage INSIDE the full global route
when a congestion-<N>.rpt of this run meets the FLOW-TIME-1 rule (default 15:10000,20:1000).  Local, no Docker/OpenROAD.
    python3 -m pytest -q tools/die_plan/test_grt_early_stop_kit.py"""
import os
import time

from test_grt183_kit import calls, fake, kit, run

FAST = {"OT_GRT_STALL_POLL": "1", "OT_GRT_STALL_KILL_WAIT": "1", "OT_GRT_EARLY_SETTLE_S": "1"}
LOG = "global_route -congestion_report_iter_step 5 -verbose -allow_congestion\n[INFO GRT-0101] Running extra iterations\n"


def report(entries):
    """congestion report text: entries [(kind H|V, congestion, x, y, top instance)]"""
    s = ""
    for kind, c, x, y, inst in entries:
        s += (f"violation type: {'Horizontal' if kind == 'H' else 'Vertical'} congestion\n"
              f"\tsrcs: net:{inst}/_001_ net:{inst}/_002_ net:other/_9_\n"
              f"\tcomment: capacity:21 usage:{21 + c} congestion:{c}\n"
              f"\tbbox = ({x:.4f}, {y:.4f}) - ({x + 0.57:.4f}, {y + 0.57:.4f}) on Layer -\n")
    return s


HOT = [("H", 6000, 1265.0, 45.0, "u_bound.u_cland_dn"), ("H", 5000, 1270.0, 50.0, "u_bound.u_cland_dn"),
       ("V", 1535, 300.0, 300.0, "u_ring")]                                    # 12,535 in all, 11,000 in one tile


def body(rpts, then="sleep 60; exit 0"):
    """write the log, then each (iteration, text) report into the stage's reports dir, then `then`"""
    s = "D=$K/run/reports/asap7/t/base; mkdir -p $D\ncat > $L/5_1_grt.tmp.log <<'EOF'\n" + LOG + "EOF\n"
    for n, txt in rpts:
        s += f"cat > $D/congestion-{n}.rpt <<'EOF'\n{txt}EOF\n"
    return s + then + "\n"


def test_iteration_15_over_10000_stops_inside_the_route(tmp_path):
    k, r, l, s = kit(tmp_path)
    t = time.time()
    p = run(k, s, fake(tmp_path, body([(5, report(HOT)), (10, report(HOT)), (15, report(HOT))])), "grt", env=FAST)
    assert p.returncode == 21, p.stdout + p.stderr
    assert time.time() - t < 40
    line = next(x for x in p.stdout.splitlines() if x.startswith("OT_GRT_CONGESTED_FAIL"))
    assert "stage=grt early: congestion-15 overflow 12535 >= 10000 (rule 15:10000,20:1000)" in line
    assert "H 11000 / V 1535" in line and "hotspot (1260,40)-(1280,60) overflow 11000 of 12535" in line
    assert "top u_bound.u_cland_dn" in line and "KW-FIX-44 GRT-EARLY" in line
    assert "OT_GRT_STOP congested" in p.stdout and len(calls(k)) == 1          # no fresh-process re-run


def test_iteration_20_floor_1000(tmp_path):
    k, r, l, s = kit(tmp_path)
    small = [("V", 600, 10.0, 10.0, "u_a"), ("H", 500, 30.0, 10.0, "u_b")]  # 1,100: under 10,000 at 15, over 1,000 at 20
    p = run(k, s, fake(tmp_path, body([(15, report(small)), (20, report(small))])), "grt", env=FAST)
    assert p.returncode == 21 and "congestion-20 overflow 1100 >= 1000" in p.stdout


def test_below_rule_and_other_iterations_run_on(tmp_path):
    k, r, l, s = kit(tmp_path)
    low = [("H", 900, 10.0, 10.0, "u_a")]
    p = run(k, s, fake(tmp_path, body([(10, report(HOT)), (15, report(low)), (20, report(low)), (25, report(HOT))],
                                      then="sleep 5; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_CONGESTED_FAIL" not in p.stdout and "OT_GRT_STOP" not in p.stdout


def test_report_of_an_earlier_run_is_ignored(tmp_path):
    k, r, l, s = kit(tmp_path)
    d = k / "run/reports/asap7/t/base"; d.mkdir(parents=True)
    (d / "congestion-15.rpt").write_text(report(HOT))
    os.utime(d / "congestion-15.rpt", (1000, 1000))
    p = run(k, s, fake(tmp_path, body([], then="sleep 5; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout


def test_config_rule_and_opt_out(tmp_path):
    k, r, l, s = kit(tmp_path / "rule", "export OT_GRT_EARLY_STOP = 10:500\n")
    p = run(k, s, fake(tmp_path / "rule", body([(10, report([("H", 600, 10.0, 10.0, "u_a")]))])), "grt", env=FAST)
    assert p.returncode == 21 and "congestion-10 overflow 600 >= 500 (rule 10:500)" in p.stdout
    k, r, l, s = kit(tmp_path / "off", "export OT_GRT_EARLY_STOP = off\n")
    p = run(k, s, fake(tmp_path / "off", body([(15, report(HOT))], then="sleep 5; exit 0")), "grt", env=FAST)
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout
    k, r, l, s = kit(tmp_path / "env", "")
    p = run(k, s, fake(tmp_path / "env", body([(15, report(HOT))], then="sleep 5; exit 0")), "grt",
            env=dict(FAST, OT_GRT_EARLY_STOP="0"))
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout


def test_malformed_rule_never_stops(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, body([(15, report(HOT))], then="sleep 5; exit 0")), "grt",
            env=dict(FAST, OT_GRT_EARLY_STOP="fifteen"))
    assert p.returncode == 0 and "OT_GRT_STOP" not in p.stdout
