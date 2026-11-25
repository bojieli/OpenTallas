"""ADV-STALE-BINS (QC-CB-SPREAD-R2 11-24, recalibrated): sink bins vs the kit's CLOCK-NET sinks (> 5 %) and the kit's largest tap
after the cap pass (> 1,000, only when the kit is newer than the bins file); report-only."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "precheck"))
import adv_stale_bins as A  # noqa: E402
import kit_sinks as KS  # noqa: E402
import plan_advisory as PA  # noqa: E402


def _plan(tmp, types, bins_mtime=1000.0):
    pr = tmp / "physical" / "die_plan" / "x" / "plan_of_record"
    pr.mkdir(parents=True)
    raw = {"partition_types": {}, "partitions": []}
    for tn, nb in types.items():
        f = f"physical/die_plan/x/plan_of_record/sink_bins/{tn}.json"
        (tmp / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp / f).write_text(json.dumps({"bin_um": 10, "n": nb, "bins": [[5, 5, nb]]}))
        os.utime(tmp / f, (bins_mtime, bins_mtime))
        raw["partition_types"][tn] = {"clock": {"tap_mode": "density", "sink_bins_file": f}}
        raw["partitions"].append({"type": tn})
    raw["partition_types"]["nobins"] = {"clock": {"tap_mode": "grid"}}
    p = pr / "plan.json"
    p.write_text(json.dumps(raw))
    return raw, p


KS_MAP = {"stale": {"sinks": 74284, "taps": 122, "max_tap": "clk_t92", "max_sinks": 4074, "mtime": 2000.0},
          "fresh": {"sinks": 1020, "taps": 3, "max_tap": "clk_t1", "max_sinks": 900, "mtime": 2000.0},
          "pile__cl1234567": {"sinks": 1000, "taps": 2, "max_tap": "clk_t3", "max_sinks": 1500, "mtime": 2000.0},
          "rebinned": {"sinks": 5000, "taps": 4, "max_tap": "clk_t2", "max_sinks": 3000, "mtime": 500.0}}


def test_flags_stale_and_fanout(tmp_path):
    raw, p = _plan(tmp_path, {"stale": 58858, "fresh": 1000, "pile": 1000, "rebinned": 5000, "nokit": 10})
    out = A.findings(raw, str(p), None, kit_sinks=KS_MAP)
    s = [x for x in out if "ADV-STALE-BINS stale:" in x]
    assert len(s) == 1 and "x1.26" in s[0] and "clock-net" in s[0] and "4,074" in s[0] and "clk_t92" in s[0]
    assert not any("ADV-STALE-BINS fresh:" in x for x in out)            # 2 % off, tap 900: quiet
    pile = [x for x in out if "ADV-STALE-BINS pile:" in x]                 # base-type kit: count matches, tap 1,500 > 1,000
    assert len(pile) == 1 and "1,500" in pile[0] and "off by" not in pile[0]
    assert not any("ADV-STALE-BINS rebinned:" in x for x in out)         # kit older than the re-binned file: fanout not listed
    summ = out[-1]
    assert summ.startswith("WARN ADV-STALE-BINS summary: 1 of 4 types") and "2 with a kit tap" in summ
    assert "1 more on kits older than their bins" in summ and "1 without a kit clock-sink count" in summ
    assert all(x.startswith("WARN ") for x in out)
    assert out.index(s[0]) < out.index(pile[0])                            # worst first


def test_no_map_and_missing_file(tmp_path):
    raw, p = _plan(tmp_path, {"stale": 100})
    assert A.findings(raw, str(p), None, kit_sinks={})[0].startswith("WARN ADV-STALE-BINS not checked")
    assert A.findings(raw, str(p), None, kit_sinks=str(tmp_path / "none.json"))[0].startswith("WARN ADV-STALE-BINS not checked")
    raw["partition_types"]["stale"]["clock"]["sink_bins_file"] = "nope/x.json"
    out = A.findings(raw, str(p), None, kit_sinks=KS_MAP)
    assert any("not found" in x for x in out) and "1 bins files missing" in out[-1]


def test_kit_sinks_kitwave_scan(tmp_path):
    log = tmp_path / "w/runs/qc/kit-wave/qc/V4/private/L/cbf_q01_1124/gen/cbf_q01/run/logs/asap7/dp_cbf_q01/base/4_1_cts.log"
    log.parent.mkdir(parents=True)
    log.write_text("x\nOT_CLOCK_TAPS 3 taps, 3200 sinks moved off clk: clk 100 clk_t1 3000 clk_t2 100\n"
                   "OT_CLOCK_TAPS cap 1000 sinks/tap: 2000 sinks re-assigned; per tap: clk 1000, clk_t1 1000, clk_t2 1000, clk_t3 200\n"
                   "OT_CLOCK_TAPS cap recheck after hop latches: 0 sinks re-assigned in 5 launch units + single sinks; over cap now: clk_t1 1190\n")
    pat = str(tmp_path / "w/runs/*/kit-wave/*/*/{,private/*/}*/gen/*/run/logs/asap7/*/base/4_1_cts.log")
    r = KS.scan_kitwave(pat, max_age_h=1e9)
    assert r["cbf_q01"]["sinks"] == 3200 and r["cbf_q01"]["taps"] == 3
    assert (r["cbf_q01"]["max_tap"], r["cbf_q01"]["max_sinks"]) == ("clk_t1", 1190)
    assert KS.kit_type("/a/gen/x__cl1/run/logs/b") == "x__cl1" and KS.kit_type("/a/b") is None


def test_registered_in_plan_advisory():
    assert ("STALE-BINS", "adv_stale_bins") in PA.CHECKS
