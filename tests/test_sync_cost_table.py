"""The synchronisation-cost record reproduces from its inputs, and the link tiers keep their validated order."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sync_cost_table as S  # noqa: E402


def test_record_reproduces():
    rec, tech = S.build()
    committed = json.loads(S.OUT.read_text())
    assert committed["inputs"] == rec["inputs"], "sync_cost_table.json is stale: rerun tools/sync_cost_table.py"
    assert committed["rows"] == json.loads(json.dumps(rec["rows"]))


def test_cable_tier_is_never_faster_than_the_on_module_link():
    L = json.loads(S.TECH.read_text())["links"]
    board = L["rom_board_serdes"]["hop_latency_s"]        # the full RS(544,514) KP4 package hop on this base
    cable = L["rom_rack_cable_serdes"]["hop_latency_s"]
    assert cable["value"] >= board["value"] > S.LIGHT_FEC_HOP_S
    assert L["rom_package_ucie"]["hop_latency_s"]["value"] < S.LIGHT_FEC_HOP_S


def test_light_fec_hop_is_the_v41_baseline():
    import arch_budget_v41 as V
    assert V.BASELINE["board_hop_s"] == S.LIGHT_FEC_HOP_S


def test_stage_hops_ride_the_cable_tier():
    import decode_critical_path as D
    tech = json.loads(S.TECH.read_text())
    links = D.link_consts(tech)
    light = dict(links, rom_board_serdes=dict(links["rom_board_serdes"], hop=S.LIGHT_FEC_HOP_S))
    fab = D.ArrayFabric(light, 2, "ring", 4, "best")
    assert fab.alpha_board == S.LIGHT_FEC_HOP_S
    assert fab.alpha_stage == tech["links"]["rom_rack_cable_serdes"]["hop_latency_s"]["value"]


def test_power_record_reproduces_and_keeps_the_scenarios_apart():
    tech = json.loads(S.TECH.read_text())
    prec = S.power_record(tech)
    committed = json.loads(S.OUT_P.read_text())
    assert committed["inputs"] == prec["inputs"], "power_assumptions.json is stale: rerun tools/sync_cost_table.py"
    assert committed["rows"] == json.loads(json.dumps(prec["rows"]))
    assert {r["scenario"][0] for r in prec["scenarios"]} >= {"A", "B"}
    keller = next(r for r in prec["rows"] if r["refs"] == ["r-keller"])
    assert "INTEGER" in keller["cls"] and "FP4" not in keller["quantity"]


def test_every_cited_reference_exists():
    rec = json.loads(S.OUT.read_text())
    used = {r for row in rec["rows"] for r in row["gpu"]["refs"] + row["ot"]["refs"]}
    used |= {r for v in rec["values_checked"] for r in v["refs"]}
    used |= {r for p in json.loads(S.OUT_P.read_text())["rows"] for r in p["refs"]}
    assert used <= set(rec["references"])
