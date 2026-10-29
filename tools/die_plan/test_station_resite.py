"""DIE-HBM-14 station_resite: FF homes inside a core body+halo are re-sited with the same count; legal plans are no-ops."""
import json

import station_resite as SR


def _plan(regs):
    t = {"outline_um": [1200.0, 600.0],
         "hard_cores": [{"inst": "u_c", "origin_um": [380.16, 103.68], "outline_um": [172.8, 393.12]}],
         "internal_stations": [{"conn": "u_a.x|u_b", "from_um": [8.64, 302.4], "to_um": [1105.92, 302.4],
                                "bits": 8, "regs_um": regs}]}
    return {"partition_types": {"hub": t}}


def _run(tmp_path, regs):
    d = tmp_path / "in"; d.mkdir(); (d / "die_plan.json").write_text(json.dumps(_plan(regs)))
    rep = SR.run(d, tmp_path / "out", log=lambda *a: None)
    return rep["types"]["hub"], json.loads((tmp_path / "out" / "die_plan.json").read_text())


def test_in_body_regs_resited_same_count(tmp_path):
    r, p = _run(tmp_path, [[302.4, 302.4], [466.56, 302.4], [699.84, 302.4]])  # middle reg inside u_c
    assert r["regs_in_body_halo_before"] == 1 and r["regs_in_body_halo_after"] == 0
    assert r["cycles_added_total"] == 0 and not r["failed"]
    s = p["partition_types"]["hub"]["internal_stations"][0]
    assert len(s["regs_um"]) == 3 and SR.max_hop(s) <= 405 + 1e-6
    rects = SR.core_rects(p["partition_types"]["hub"])
    assert not any(SR.blocked(rects, q) for q in s["regs_um"])


def test_legal_plan_unchanged(tmp_path):
    regs = [[302.4, 302.4], [604.8, 302.4], [907.2, 302.4]]
    r, p = _run(tmp_path, regs)
    assert r["chains_resited"] == 0
    assert p["partition_types"]["hub"]["internal_stations"][0]["regs_um"] == regs


def test_infeasible_count_reports_added_cycle(tmp_path):
    r, _ = _run(tmp_path, [[466.56, 302.4]])  # 1 reg cannot span 1097 um at 405 reach -> +N reported, never silent
    assert r["cycles_added_total"] >= 1 and r["chains_added_cycles"]
