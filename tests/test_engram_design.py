import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import engram_design as ED  # noqa: E402
import rtl_dsrom_engram_lookup_campaign as C  # noqa: E402


def test_design_record_is_current():
    assert ED.OUT.read_text() == json.dumps(ED.run(), indent=1, sort_keys=False) + "\n"


def test_tables_and_split():
    rec = json.loads(ED.OUT.read_text())
    tb = rec["tables"]
    assert tb["bytes_total"] == 768_022_850 * 264
    # every rank region of both layers fits 2 shipping stacks with KV headroom; the split is balanced to 0.01 %
    regions = [x for li in tb["bytes_per_rank_region"] for x in li]
    assert max(regions) < 2 * 22.5e9 * 0.9 and (max(regions) - min(regions)) / max(regions) < 1e-4
    assert rec["access"]["consumers"]["L1"]["home_stage_1792"] == 3
    assert rec["access"]["consumers"]["L14"]["home_stage_1792"] == 42


def test_engram_branch_is_off_the_critical_path():
    rec = json.loads(ED.OUT.read_text())
    for k, v in rec["timeline_cycles"].items():
        assert v["slack_cycles"] > 0 and not v["on_critical_path"], k
    assert rec["reprice_item"]["on_path_cycles_ar"] == 0


def test_token_path_carries_the_engram_nodes():
    d = json.loads((ROOT / "results/arch/token_path_20261009/ds_rom.json").read_text())
    ids = {n["id"]: n for n in d["nodes"]}
    for L in (1, 14):
        for k in ("lead_flit", "hash", "hbm_read", "rows_allgather", "wkv", "knorm"):
            n = ids[f"E{L}.{k}"]
            assert not n["critical"] and n["src"]["grade"] == "modelled" and n["slack"] > 0
    m = json.loads((ROOT / "results/arch/token_path_20261009/ds_rom_mtp.json").read_text())
    assert any(n["id"] == "accept.engram_rewind" for n in m["nodes"])


def test_official_window_rule_with_rewinds():
    # user 0: a b c d, rewind 2, e  -> e's window is (e, b, a, pad); DEAD blocks everything behind it
    ev = [(0, 0, 1, 0, 10), (0, 0, 0, 0, 11), (0, 0, 0, 0, 12), (0, 0, 0, 0, 13), (1, 0, 0, 0, 2), (0, 0, 0, 0, 14),
          (0, 0, 0, 1, 15), (0, 0, 0, 0, 16)]
    w = C.official_windows(ev)
    assert w[0] == [10, 2, 2, 2] and w[3] == [13, 12, 11, 10]
    assert w[4] == [14, 11, 10, 2]
    assert w[5] == [2, 2, 2, 2] and w[6] == [16, 2, 2, 2]


def test_campaign_record_passes():
    rec = json.loads((ROOT / "results/rtl/dsrom_engram_lookup_campaign.json").read_text())
    assert rec["status"] == "pass"
    assert all(m["caught"] != bool(m.get("control")) for m in rec["mutations"])
    assert rec["mtp_rewinds"] > 0 and rec["modes"]["crc_injection_stressed"]["poisoned_as_injected"]
