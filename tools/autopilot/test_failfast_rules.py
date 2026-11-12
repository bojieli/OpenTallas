"""FAILFAST-1 (2026-11-11): progress-based stop rules (physical/common_flow/failfast_rules.py), the autopilot classes they reach,
and the duplicate-attempt report of the dry-run scanner.  Local, no Docker/OpenROAD.
    python3 -m pytest -q tools/autopilot/test_failfast_rules.py"""
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "physical/common_flow"))
sys.path.insert(0, str(HERE))
import failfast_rules as R  # noqa: E402
import failfast_scan as FS  # noqa: E402
import failfast_hostscan as HS  # noqa: E402

C = R.config_values({}, "")


def rep(total, h=None, layer="-"):
    """congestion report text with `total` overflow: h to the horizontal entry, the rest vertical"""
    h = total // 2 if h is None else h
    s = ""
    for kind, c in (("Horizontal", h), ("Vertical", total - h)):
        if c:
            s += ("violation type: %s congestion\n\tsrcs: net:a net:b\n\tcomment: capacity:20 usage:%d congestion:%d\n"
                  "\tbbox = (1.0, 2.0) - (1.5, 2.5) on Layer %s\n" % (kind, 20 + c, c, layer))
    return s


def log_iters(*rounds):
    """GRT-0102 lines for rounds [len, len, ...]; NDR relaxation between rounds"""
    out = ["[INFO GRT-0101] Running extra iterations to remove congestion."]
    for k, n in enumerate(rounds):
        out += ["[INFO GRT-0102] Start extra iteration %d/30" % i for i in range(1, n + 1)]
        if k < len(rounds) - 1:
            out.append("[WARNING GRT-0273] Disabled NDR (to reduce congestion) for net: clk_t2")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------------------------------- parsing
def test_report_and_iteration_parsing():
    r = R.parse_report(rep(1500, h=1000, layer="M5"))
    assert (r["total"], r["H"], r["V"], r["layers"]) == (1500, 1000, 500, {"M5": 1500})
    assert R.parse_report(rep(7))["layers"] == {}                      # mid-route reports name no layer
    s = R.scan_lines(log_iters(15, 15, 7).splitlines())
    assert R.iteration_state(s["iters"]) == (37, 7, 15, 2) and s["ndr"] == 2
    assert R.iteration_state([]) == (0, 0, 0, 0)


def test_config_precedence():
    assert R.config_values({}, "export OT_FF_GRT_MAX = 500\n")["OT_FF_GRT_MAX"] == 500
    assert R.config_values({"OT_FF_GRT_MAX": "700"}, "export OT_FF_GRT_MAX = 500\n")["OT_FF_GRT_MAX"] == 700
    assert R.config_values({"OT_FF_GRT_MAX": "x"}, "")["OT_FF_GRT_MAX"] == 1000                     # malformed: default
    assert C["OT_FF_GRT_MAX"] == 1000 and C["OT_FF_DRT_ITER"] == 20 and C["OT_FF_HOLD_CAPS"] == 0


# ---------------------------------------------------------------------------------------------------- (a) GRT
def entry(cum, total, n=5):
    return {"cum": cum, "n": n, "total": total, "H": total // 2, "V": total - total // 2, "layers": {}, "mtime": float(cum)}


def test_grt_stops_when_high_and_flat_after_two_rounds():
    ser = [entry(30, 9000, 30), entry(60, 8800, 30)]                   # 2.2 % over the last round, 8,800 > 1,000
    d = R.grt_decide(ser, 60, C)
    assert d and d["rule"] == "GRT_NO_PROGRESS" and d["fall_pct"] == 2.2
    line = R.grt_line(dict(d, last=dict(ser[-1], layers={"M5": 5000, "M6": 3800})), rounds=2, ndr=4, stamp=False)
    assert line.startswith("OT_GRT_NO_PROGRESS stage=grt class=GRT_NO_PROGRESS")
    assert "M5=5000 M6=3800" in line and "H 4400 / V 4400" in line and "after 60 extra iterations in 2 rounds" in line


def test_grt_rising_overflow_stops():
    assert R.grt_decide([entry(30, 5000, 30), entry(65, 8000, 5)], 65, C)


def test_grt_converging_run_is_not_stopped():
    """overflow falling > 10 % per round and ending at 0: no step of the run is stopped"""
    cum, vals = 0, [60000, 40000, 30000, 25000, 20000, 15000, 9000, 6000, 3000, 1200, 400, 0]
    ser = []
    for v in vals:
        cum += 30
        ser.append(entry(cum, v, 30))
        assert R.grt_decide(ser, cum, C) is None, (cum, v)


def test_grt_slow_but_10_percent_is_not_stopped():
    assert R.grt_decide([entry(30, 10000, 30), entry(60, 8900, 30)], 60, C) is None               # 11 %
    assert R.grt_decide([entry(30, 10000, 30), entry(60, 9000, 30)], 60, C) is None               # exactly 10 %: keep going
    assert R.grt_decide([entry(30, 10000, 30), entry(60, 9100, 30)], 60, C)                       # 9 %: stop


def test_grt_not_before_two_rounds_nor_at_or_below_the_ceiling():
    assert R.grt_decide([entry(10, 9000), entry(40, 9000)], 40, C) is None                         # 40 < 60 iterations
    assert R.grt_decide([entry(30, 900, 30), entry(60, 900, 30)], 60, C) is None                   # 900 <= 1,000: DRT decides
    assert R.grt_decide([entry(60, 9000, 30)], 60, C) is None                                      # no history one round back
    assert R.grt_decide([], 60, C) is None
    assert R.grt_decide([entry(30, 0, 30), entry(60, 0, 30)], 60, C) is None


def test_grt_config_keys():
    flat = [entry(30, 9000, 30), entry(60, 9000, 30)]
    assert R.grt_decide(flat, 60, R.config_values({"OT_FF_GRT": "0"}))is None
    assert R.grt_decide(flat, 60, R.config_values({"OT_FF_GRT_MAX": "20000"})) is None
    assert R.grt_decide(flat, 60, R.config_values({"OT_FF_GRT_MIN_DROP_PCT": "0"})) is None
    assert R.grt_decide(flat, 59, R.config_values({"OT_FF_GRT_ROUNDS": "3"})) is None


def write_run(k, log, reports, t=None):
    lg = k / "run/logs/asap7/t/base"
    rp = k / "run/reports/asap7/t/base"
    lg.mkdir(parents=True, exist_ok=True)
    rp.mkdir(parents=True, exist_ok=True)
    (lg / "5_1_grt.tmp.log").write_text(log)
    for n, txt in reports.items():
        (rp / ("congestion-%d.rpt" % n)).write_text(txt)
        if t:
            os.utime(rp / ("congestion-%d.rpt" % n), (t, t))
    return lg, rp


def test_judge_records_history_and_stops_a_flat_run(tmp_path):
    k, st = tmp_path / "w", tmp_path / "state.json"
    t0 = time.time() - 1000
    write_run(k, log_iters(30), {n: rep(9000, layer="M5") for n in (5, 10, 15, 20, 25, 30)}, t0 + 100)
    assert R.judge(str(k), t0, str(st), env={}, settle_s=0) == []                  # one round: history only
    write_run(k, log_iters(30, 30), {n: rep(8700, layer="M5") for n in (5, 10, 15, 20, 25, 30)}, t0 + 500)
    out = R.judge(str(k), t0, str(st), env={}, settle_s=0)
    assert len(out) == 1 and out[0].startswith("OT_GRT_NO_PROGRESS stage=grt") and "M5=8700" in out[0]


def test_judge_converging_run_never_stops(tmp_path):
    k, st = tmp_path / "w", tmp_path / "state.json"
    t0 = time.time() - 10000
    rounds = [30]
    for r, v in enumerate([60000, 40000, 25000, 12000, 5000, 1500, 400, 0]):
        write_run(k, log_iters(*rounds), {n: rep(v) for n in (5, 10, 15, 20, 25, 30)} if v else {n: "" for n in (5, 10, 15, 20, 25, 30)},
                  t0 + 100 + 500 * r)
        assert R.judge(str(k), t0, str(st), env={}, settle_s=0) == [], (r, v)
        rounds.append(30)


def test_judge_ignores_reports_of_an_earlier_run_and_opt_out(tmp_path):
    k, st = tmp_path / "w", tmp_path / "state.json"
    now = time.time()
    write_run(k, log_iters(30, 30), {n: rep(9000) for n in (5, 10, 15, 20, 25, 30)}, now - 5000)       # before t0
    assert R.judge(str(k), now - 100, str(st), env={}, settle_s=0) == []
    write_run(k, log_iters(30), {n: rep(9000) for n in (5, 10, 15, 20, 25, 30)}, now - 50)
    write_run(k, log_iters(30, 30), {n: rep(9000) for n in (5, 10, 15, 20, 25, 30)}, now - 10)
    assert R.judge(str(k), now - 100, str(st), env={"OT_FAILFAST": "0"}, settle_s=0) == []


# ---------------------------------------------------------------------------------------------------- (b) DRT
def drt(vals):
    return [("%d" % i, v) for i, v in enumerate(vals)]


def test_drt_flat_above_10000_at_iteration_20_stops():
    s = drt([50000] * 16 + [30000, 29950, 29900, 29800])            # 20 iterations, the last 3 fell 0.7 % in all
    d = R.drt_decide(s, C)
    assert d and d["rule"] == "DRT_NO_PROGRESS" and d["iteration"] == 20 and d["violations"] == 29800
    assert R.drt_line(d, stamp=False).startswith("OT_DRT_NO_PROGRESS stage=route class=DRT_NO_PROGRESS: iteration 20 has 29800")


def test_drt_falling_5_percent_per_iteration_is_not_stopped():
    v = [100000 * 0.93 ** i for i in range(40)]                     # 7 % per iteration, > 10,000 for a long time
    for i in range(1, 41):
        assert R.drt_decide(drt([int(x) for x in v[:i]]), C) is None, i


def test_drt_guards():
    assert R.drt_decide(drt([50000] * 19), C) is None                               # before iteration 20
    assert R.drt_decide(drt([9000] * 30), C) is None                                # <= 10,000: flat is fine
    assert R.drt_decide(drt([50000] * 30), R.config_values({"OT_FF_DRT": "0"})) is None
    assert R.drt_decide(drt([50000] * 30), R.config_values({"OT_FF_DRT_ITER": "40"})) is None
    assert R.drt_decide(drt([50000] * 20 + [0, 0, 0]), C) is None                   # clean: zero before = no division


def test_drt_log_parse_and_judge(tmp_path):
    lines = []
    for i in range(25):
        lines += ["[INFO DRT-0195] Start %dth optimization iteration." % i, "    Completing 10%% with 40000 violations.",
                  "[INFO DRT-0199]   Number of violations = 40000."]
    lines += ["[INFO DRT-0195] Start 3rd stubborn tiles iteration.", "[INFO DRT-0199]   Number of violations = 39000."]
    s = R.scan_lines(lines)
    assert len(s["drt"]) == 26 and s["drt"][-1] == ("S3", 39000)
    k = tmp_path / "w"
    lg = k / "run/logs/asap7/t/base"
    lg.mkdir(parents=True)
    (lg / "5_2_route.tmp.log").write_text("\n".join(lines) + "\n")
    out = R.judge(str(k), 0, None, env={})
    assert len(out) == 1 and out[0].startswith("OT_DRT_NO_PROGRESS stage=route")


# ---------------------------------------------------------------------------------------------------- (c) hold
CAP = "OT_HOLD_GUARD chunk %d: buffer cap 4000 reached (RSZ-0060), continuing"
STALL = "OT_HOLD_STALL NEEDS_RTL (hold repair over 3 h): R2R=6544@-101 -> /x/ot_hold_stall_grt.rpt"


def test_hold_two_caps_or_stall():
    s = R.scan_lines([CAP % 1, "[ERROR RSZ-0060] Max buffer count reached", "x", CAP % 2])
    assert s["caps"] == 2                                                       # the caught tool error itself is not a second hit
    assert R.hold_decide(9, None, C) is None                                    # cap clause off by default (COORD 11-11)
    C2 = R.config_values({"OT_FF_HOLD_CAPS": "2"})
    assert R.hold_decide(1, None, C2) is None
    d = R.hold_decide(2, None, C2)
    assert d["rule"] == "HOLD_STRUCTURAL" and "2 times" in d["why"]
    assert R.hold_decide(0, R.scan_lines([STALL])["stall"], C)["why"].startswith("OT_HOLD_STALL")
    assert R.hold_line(d, "cts", stamp=False).startswith("OT_HOLD_STRUCTURAL stage=cts failfast class=HOLD_STRUCTURAL")


def test_hold_exemptions():
    assert R.hold_decide(5, STALL, R.config_values({"OT_FF_HOLD": "0"})) is None
    assert R.hold_decide(5, STALL, C, "export OT_HOLD_STRUCTURAL_ADVISORY = 1\n") is None
    assert R.hold_decide(1, None, R.config_values({"OT_FF_HOLD_CAPS": "1"}))


def test_judge_hold_counts_cts_and_grt_of_this_run_only(tmp_path):
    k = tmp_path / "w"
    lg = k / "run/logs/asap7/t/base"
    lg.mkdir(parents=True)
    (lg / "4_1_cts.log").write_text(CAP % 1 + "\n")
    (lg / "5_1_grt.tmp.log").write_text("x\n" + CAP % 1 + "\n")
    assert R.judge(str(k), 0, None, env={}) == []                                # default: cap clause off
    out = R.judge(str(k), 0, None, env={"OT_FF_HOLD_CAPS": "2"})
    assert len(out) == 1 and out[0].startswith("OT_HOLD_STRUCTURAL stage=grt failfast")
    os.utime(lg / "4_1_cts.log", (100, 100))                                 # the CTS log belongs to an earlier run
    assert R.judge(str(k), time.time() - 5, None, env={"OT_FF_HOLD_CAPS": "2"}) == []


# ---------------------------------------------------------------------------------------------------- autopilot / kit-wave class
def test_autopilot_and_wave_classes():
    import autopilot as AP
    import kit_wave as KW
    grt = "OT_GRT_NO_PROGRESS stage=grt class=GRT_NO_PROGRESS: after 60 extra iterations total overflow 8700"
    drt_l = "OT_DRT_NO_PROGRESS stage=route class=DRT_NO_PROGRESS: iteration 20 has 29800 violations"
    hold = "OT_HOLD_STRUCTURAL stage=cts failfast class=HOLD_STRUCTURAL: hold repair hit the buffer cap (RSZ-0060) 2 times (limit 2)"
    assert AP.classify({"grt_no_progress": grt}, {"exit": 21}) == ("STRUCTURAL", "grt-no-progress", grt)
    assert AP.classify({"drt_no_progress": drt_l}, {"exit": 21}) == ("STRUCTURAL", "drt-no-progress", drt_l)
    assert AP.classify({"hold_structural": hold}, {"exit": 21})[1] == "hold-structural"
    src = AP.PROBE_CLASSIFY
    i = src.index("pat = {")
    j = src.index("}", src.index('"orfs_error"', i)) + 1
    pat = eval(src[i + len("pat = "):j], {})
    import re
    assert re.search(pat["grt_no_progress"], "x\n" + grt + "\n").group(0) == grt
    assert re.search(pat["drt_no_progress"], "x\n" + drt_l + "\n").group(0) == drt_l
    assert re.search(pat["hold_structural"], "x\n" + hold + "\n").group(0) == hold
    for kind, why, cls in (("grt-no-progress", grt, "ROUTING"), ("drt-no-progress", drt_l, "ROUTING"), ("hold-structural", hold, "TIMING")):
        stage, st, c, msg = KW.queue_class({"status": "DONE-STRUCTURAL", "kind": kind, "reasons": why, "signoff": None})
        assert (st, c) == ("FAIL", cls), (kind, c)
        assert why[:40] in msg and msg.startswith(kind)


# ---------------------------------------------------------------------------------------------------- (d) duplicates
def row(host, pid, key, sha, age, kit, att=1):
    return {"pid": pid, "key": key, "plan_sha": sha, "age_h": age, "kit": kit, "attempt": att, "verdicts": []}


def test_duplicate_attempts_reported_older_first():
    w = "wave:s81/ev/ot_s81sl_leaf__t9"
    res = [{"host": "epyc4", "rows": [row("epyc4", 1333254, w, "", 47.0, "/a/attempt_3/gen/x", 3),
                                      row("epyc4", 2111492, w, "", 23.0, "/a/attempt_5/gen/x", 5),
                                      row("epyc4", 7, "wave:s81/ev/other", "", 5.0, "/b")]},
           {"host": "epyc2", "rows": [row("epyc2", 9, "name:lone", "ab12cd34", 3.0, "/c")]}]
    d = FS.duplicates(res)
    assert len(d) == 1 and d[0]["key"] == w and d[0]["older"] == "epyc4:1333254" and d[0]["reaper"] is True
    res[1]["rows"].append(row("epyc2", 10, "name:lone", "ab12cd34", 2.0, "/c2"))
    d = {x["key"]: x for x in FS.duplicates(res)}
    assert d["name:lone"]["reaper"] is False                                    # not a wave row: report only
    res[1]["rows"] = [row("epyc2", 9, "name:lone", "ab12cd34", 3.0, "/c"), row("epyc2", 10, "name:lone", "ff", 2.0, "/c2")]
    assert "name:lone" not in {x["key"] for x in FS.duplicates(res)}            # other plan sha: a variant, not a duplicate


def test_item_key():
    k = HS.item_key("/s/kw/runs/s81/kit-wave/s81/e9/items/ot_s81sl_leaf__t9/attempt_18/gen/x/", "dpkit-ot_s81sl_leaf__t9-1333254")
    assert k == ("wave:s81/e9/ot_s81sl_leaf__t9", "", True, 18)
    k = HS.item_key("/s/ot-jobs/x/work", "dpkit-sle_hc1__cl22c1ff36-138058")
    assert k == ("name:sle_hc1__cl22c1ff36", "22c1ff36", False, 0)


def test_payload_runs_standalone(tmp_path):
    """the ssh payload (rules module + host scan) compiles and executes without docker (an empty job list)"""
    import subprocess
    p = FS.payload()
    r = subprocess.run([sys.executable, "-I", "-c", p], capture_output=True, text=True, timeout=120, cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    assert '"rows"' in r.stdout
