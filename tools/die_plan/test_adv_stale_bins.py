"""ADV-STALE-BINS (QC-CB-SPREAD-R2 11-24): sink bins vs placed regs (> 5 %) and placed tap fanout (> 1,000), report-only."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_stale_bins as A  # noqa: E402
import plan_advisory as PA  # noqa: E402


def _plan(tmp, types):
    pr = tmp / "physical" / "die_plan" / "x" / "plan_of_record"
    pr.mkdir(parents=True)
    raw = {"partition_types": {}, "partitions": []}
    for tn, nb in types.items():
        f = f"physical/die_plan/x/plan_of_record/sink_bins/{tn}.json"
        (tmp / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp / f).write_text(json.dumps({"bin_um": 10, "n": nb, "bins": [[5, 5, nb]]}))
        raw["partition_types"][tn] = {"clock": {"tap_mode": "density", "sink_bins_file": f}}
        raw["partitions"].append({"type": tn})
    raw["partition_types"]["nobins"] = {"clock": {"tap_mode": "grid"}}
    p = pr / "plan.json"
    p.write_text(json.dumps(raw))
    return raw, p


CACHE = {"made": "t", "placed_bins": {"stale": {"n_regs": 74284, "ts": 1}, "fresh": {"n_regs": 1020, "ts": 1},
                                      "pile__cl1234567": {"n_regs": 1000, "ts": 2}},
         "placed": {"stale": {"n_regs": 74284, "max_load": 4670, "max_tap": "clk_t92", "ts": 1},
                    "fresh": {"n_regs": 1020, "max_load": 900, "max_tap": "clk_t1", "ts": 1},
                    "pile__cl1234567": {"n_regs": 1000, "max_load": 1500, "max_tap": "clk_t3", "ts": 2}}}


def test_flags_stale_and_fanout(tmp_path):
    raw, p = _plan(tmp_path, {"stale": 58858, "fresh": 1000, "pile": 1000})
    out = A.findings(raw, str(p), None, flops_cache=CACHE)
    s = [x for x in out if "ADV-STALE-BINS stale:" in x]
    assert len(s) == 1 and "x1.26" in s[0] and "4,670" in s[0] and "clk_t92" in s[0]
    assert not any("ADV-STALE-BINS fresh:" in x for x in out)            # 2 % off, fanout 900: quiet
    pile = [x for x in out if "ADV-STALE-BINS pile:" in x]                 # base-type kit: bins match, fanout 1,500 > 1,000
    assert len(pile) == 1 and "fanout 1,500" in pile[0] and "x1.00" not in pile[0]
    assert out[-1].startswith("WARN ADV-STALE-BINS summary: 1 of 3 types") and "2 with a placed tap fanout" in out[-1]
    assert all(x.startswith("WARN ") for x in out)
    assert out.index(s[0]) < out.index(pile[0])                            # worst first


def test_no_cache_and_missing_file(tmp_path):
    raw, p = _plan(tmp_path, {"stale": 100})
    assert A.findings(raw, str(p), None, flops_cache={})[0].startswith("WARN ADV-STALE-BINS not checked")
    raw["partition_types"]["stale"]["clock"]["sink_bins_file"] = "nope/x.json"
    out = A.findings(raw, str(p), None, flops_cache=CACHE)
    assert any("not found" in x for x in out) and "1 bins files missing" in out[-1]


def test_registered_in_plan_advisory():
    assert ("STALE-BINS", "adv_stale_bins") in PA.CHECKS
