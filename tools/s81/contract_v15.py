#!/usr/bin/env python3
"""S81 hierarchy contract v14 -> v15 (one-shot, idempotent).  Folds the 2026-10-13 04:50 slot requests (el1011-s81die.log,
[s81-slots]): A1 xport outline, A2 fadd16 outline + position + orientation (faces MEASURED on the closed LEFs), A3 sp_p2
parent = container, B the 0 x 0 'rep/*' descriptor rows -> per-master rows (outline + placed count from the c5 census);
records the decisions on the SU slot change, the Engram home cluster and the M6 pin-only proposals.

Usage: contract_v15.py [--check]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"
CEN = ROOT / "results/physical/die_iter_1012/s81/real_view_census_20261013/c5_census.json"
# per-master rows replacing the group descriptors: (old row, master, w, h, count in c5 floorplan_placed.def, note)
REP = [("rep/bf", "dsfd_bf", 1002.888, 198.696, 512, "BF frame master"),
       ("rep/q_elem", "ot_v41_rom_elem_q_qxpq_w10", 510.84, 221.4, 1280, "Q element (10-way)"),
       ("rep/q_elem", "dsfd_qbank_N", 60.456, 6.456, 1280, "q-bank relay row N of each q element"),
       ("rep/q_elem", "dsfd_qbank_S", 60.456, 6.456, 1280, "q-bank relay row S of each q element"),
       ("rep/pqc", "dsfd_sp_pq", 1672.248, 449.256, 1, "PQ service parent (children below; closed ot_pqc_t_* M5 tiles are its sub_layout)"),
       ("rep/pqc", "dsfd_pq_root", 132.168, 211.656, 128, "PQ root, one per column"),
       ("rep/pqc", "dsfd_rstg_pq66", 132.168, 8.616, 128, "PQ return stage 66 b"),
       ("rep/pqc", "dsfd_rstg_pq68", 132.168, 8.616, 128, "PQ return stage 68 b")]
M6_PROPOSALS = ["dsfd_mtp_seq", "dsfd_mtp_seq_rtt", "dsfd_cap_mtp_ep", "dsfd_coll_mtp_lane", "ot_p2h_fadd16", "dsfd_engram_sink"]


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    c = json.loads(CON.read_text())
    if c["version"] >= 15:
        print("already v15"); return 0
    assert c["version"] == 14, c["version"]
    cen = {m["master"]: m for m in json.loads(CEN.read_text())["masters"]}
    by = {s["name"]: s for s in c["slots"]}
    # A1
    x = by["sp_p2/xport"]; assert (x["outline"]["w"], x["outline"]["h"]) == (403.2, 228.96)
    x["outline"]["h"] = 211.68; x["version"] = 15
    x["view_status"] = "closed mtp-p2h-xp-7a43b0b52-tc-pk45 (TT +8.17 / FF +3.33 / DRC 0), LEF 403.2 x 211.68; no _tt.lib in the view dir (export-sdc stream)"
    # A2: closed LEF 216 x 58.32; f_ab[1024:0] + ck on N (x 9.7..206.3, M5), t_y[559:0] on S (x 54.3..161.6, M5).
    # head (432 x 172.8 at 446.4, 0): t_ab on N at x 15.8..300.6, f_y on N at x 31.9..296.8.
    # => orient MX (f_ab faces the head), f_ab centre on head t_ab centre (604.6): x0 = 496.608; 21.6-um channel kept.
    f = by["sp_p2/fadd16"]; f["outline"] = {"w": 216.0, "h": 58.32}
    f["origin"] = {"x": 496.608, "y": 194.4, "orient": "MX"}; f["version"] = 15
    f["notes"] = ("v15: closed LEF 216 x 58.32 (mtp-p2h-fa-50b05596a-tc-a/-b, TT +98.70 / FF +2.43 / DRC 0). MEASURED faces of the "
                  "closed view: f_ab 1025 + ck on N (x 9.7..206.3, M5), t_y 560 on S (x 54.3..161.6): the v13 note (f_ab on S) was the "
                  "kit plan, not the view. Slot orient MX so f_ab faces head t_ab across the 21.6-um channel, centred on it (lateral "
                  "<= 44 um, est. crossing 159 b / 831 tracks = 0.19); t_y leaves on the far (north) face and returns over the tile "
                  "to head f_y (N face, x 478..743): <= ~250 um, registered both ends. x 496.608..712.608 inside sp_p2, top 252.72 < 270; "
                  "no overlap with head (y <= 172.8) or xport (x <= 403.2).")
    # A3
    p = by["sp_p2"]; p["kind"] = "container"; p["master"] = None; p["version"] = 15
    p["notes"] += " v15: container only (no master, no view: the closed 560 x 460 ot_mtp_p2_prefix_path is the pre-v13 monolith, absorbed by xport + head + fadd16); not a census instance."
    # B
    out, done = [], set()
    for s in c["slots"]:
        if s["name"] in ("rep/q_elem", "rep/bf", "rep/pqc"):
            for old, m, w, h, n, note in REP:
                if old != s["name"]:
                    continue
                cm = cen.get(m, {})
                n_c = cm.get("instances")
                r = {k: v for k, v in s.items() if k not in ("notes",)}
                r.update(name=f"{old}/{m}", cell=m, kind="element", outline={"w": w, "h": h}, version=15,
                         replicated={"count": n, "count_census_c5": n_c, "placement": "die plan floorplan.def (generator); no single origin"},
                         notes=f"v15 per-master row ({note}); replaces the 0 x 0 descriptor row {old}; outline = die case c5 master")
                if m.startswith("dsfd_pq_root") or m.startswith("dsfd_rstg"):
                    r["parent_master"] = "dsfd_sp_pq"
                out.append(r)
            done.add(s["name"])
        elif s["name"] == "rep/engram_c":
            r = dict(s); r.update(name="rep/engram_c/dsfd_engram_c", cell="dsfd_engram_c", outline={"w": 1188.0, "h": 432.0}, version=15,
                                  assembly="cluster", die_variant="layer1e only (Engram home die, instance eng_SE); absent on layer1",
                                  notes="v15: one hardened cluster, 8 hard instances + wires, no register in the cluster top; N face M5 "
                                        "(f_ai, t_ag, f_win, t_vm, f_vm, c_*), W face M4 (t_hq, f_hr); origin = generator eng_SE. View to "
                                        "be delivered at physical/s81_ph_views/closed/dsfd_engram_c (el1013-s81-engram).")
            out.append(r); done.add(s["name"])
        else:
            out.append(s)
    assert done == {"rep/q_elem", "rep/bf", "rep/pqc", "rep/engram_c"}, done
    c["slots"] = out
    zero = [s["name"] for s in c["slots"] if not s["outline"]["w"] or not s["outline"]["h"]]
    assert not zero, zero
    c["m6_pin_grants"] = {"rule": "tools/hier_contract/M6_PIN_GRANT.md: exact master, source commit, physical-spec digest, exact bits / face / span; "
                                  "signals and PG stay <= M5", "granted": [],
                          "approved_in_principle_pending_exact_audit": M6_PROPOSALS,
                          "note": "the 10-12 18:18-20:48 proposals carry pins/um only: no bit list, span, source commit or spec digest, so no "
                                  "grant can be signed yet. The die lead signs each grant when the owner posts the m6_pin_grant block of the "
                                  "M5 kit (m6_pin_grant.py); the closed M6 / M7 views stand meanwhile (owner 10-12 19:00)."}
    c["open_items"] = list(c.get("open_items", [])) + [
        "v15 SU slot change (s81su 03:40): kv0/kv1 -> kvt x4 (36.72 x 453.6) + kvq x16 (259.2 sq) + kve/kvp/kvr; qb0-3 -> qbt (572.4 x 453.6) + qbe; "
        "sw0-7 -> swt (572.4 x 453.6) + swe: ACCEPTED as the target, NOT folded as slots: the four tiles are not closed, qbt/swt insertion "
        "614-740 ps fails the 300 ps clock rule (half-tap split likely), and no sub-layout origins were posted. Fold with the verdicts.",
        "v15 fadd16: closed view routes signals on M7 above its cap M6 (view_status INVALID stands); t_y on the far face (MX slot).",
        "v15 layer1e die case (Engram home) missing from the real-view census.",
        "v15 no closed slot-shaped view by name for dsfd_bf, ot_v41_rom_elem_q_qxpq_w10, dsfd_pq_root, dsfd_sp_pq (unowned per [s81-slots])."]
    c["version"] = 15; c["updated"] = "2026-10-13 PT"
    c["changelog"].append({"version": 15, "when": "2026-10-13 PT", "change":
        "s81-die: (A1) sp_p2/xport 403.2 x 228.96 -> 403.2 x 211.68 (closed view). (A2) sp_p2/fadd16 150 x 66.15 @ (587.4, 194.4) R0 -> "
        "216 x 58.32 @ (496.608, 194.4) MX (closed view; faces measured on the LEF, f_ab centred on head t_ab). (A3) sp_p2 = container. "
        "(B) rep/q_elem, rep/bf, rep/pqc descriptor rows (0 x 0) -> 8 per-master rows with outline and placed count; rep/engram_c -> "
        "dsfd_engram_c 1188 x 432 cluster on layer1e only. m6_pin_grants: none signed, 6 pending the exact audit. SU kv/qb/sw slot change "
        "accepted as target, carried open. No price changed; no closed tile re-shaped."})
    if a.check:
        print("ok (check only)"); return 0
    CON.write_text(json.dumps(c, indent=1) + "\n"); print("v15 written", len(c["slots"]), "slots"); return 0


if __name__ == "__main__":
    sys.exit(main())
