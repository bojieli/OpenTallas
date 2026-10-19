#!/usr/bin/env python3
"""VEH-FMT-COLL2 (10-19): payloads for the remaining COLL record kinds of the d4g SW-quadrant slice (GEN2 RTL):
COLL.GROUP_REDUCE_MCAST, COLL.TOPK_MERGE, COLL.ROW_GATHER.  Companion of coll_images.py (COLL.ALL_GATHER).

What the SW slice can execute of each kind (d4g placement classes, tools/hgi_sim/d4g_quadrant_1017.py):
  GROUP_REDUCE_MCAST (C1, o-group tree reduce of 8 contributors + multicast; O = every sub-group's result, 12,288
      BF16 values held one per VM word): each quadrant COLL engine writes ONLY its own 8 banks, so after the cross-die
      reduce lands quadrant q's quarter, the on-die ALL-GATHER on the COLL ring (gq master + ring A/B, GATHER kind 3)
      replicates the quarters.  That ON-DIE phase is emitted here with coll_images.gather_record on the fixture O
      (bit-exact ds_native output, rank 0; the o-group result is identical on every die of the group), i.e. the same
      gq row + calendar_SW window + far-end ring flits + landed-sector checks as ALL_GATHER.
      The CROSS-DIE reduce (hb_coll_SW link RX of the 7 peer partials, FP32 adds in the golden tree order, TX) is NOT
      emitted: (a) the record is needs_tp192_programme (the golden tree is the TP-96 8-contributor o-group; no
      TP-192 DS programme fixes the d4g contributor set / tree), (b) the fixture holds rank 0's partial A only, (c) the
      hb_coll_SW programme is the 1536-b uop ISA (static_uop_layout_v4.json, ot_hgi_coll_issuer_m) and the only row
      compilers (tools/hbm_coll_static/row_gather_rows.py, argmax_rows.py) target host_v4 timing, not hard_v8x.
  TOPK_MERGE (C4, 96 x 512 index merge -> 512 ascending U32 ids, consumed by ROW_GATHER I in the owning quadrant):
      no on-die ring phase (lands in the consumer's quadrant).  The SW-slice part is hb_coll_SW link RX -> qslots ->
      tkm_SW (ot_hgi_coll_tkm_m_tp192 via tkx_*; uop fields tkm_start / tkm_del_slot / tkm_cfg_*), plus the own list
      via SU inject.  Not emitted: needs_tp192_programme, peer lists absent from the rank-0 fixture, no v8x row
      compiler, far-end link frames (612-b registered frame with sequence / epoch / CRC) need a frame generator.
  ROW_GATHER (C3; L2/L14 selected compressed-KV rows, L14 engram.gather): rows go to the token-owning quadrant's
      endpoint, no ring phase.  Not emitted: A / O are HBM operands (fixture carries sha256 only), owner rows come from
      peer dies over ep_S0/S1, same compiler / frame gaps as TOPK_MERGE.

    PYTHONPATH=tools python3 -m hbm_next.vehicle.coll_ops_images --fixtures results/rtl/hbm_ds_layer_tput_1018/fixtures/L00
        --boundary slice/boundary.json --out OUT [--pre-events DIR] [--nev 6309]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
from hbm_next.vehicle import coll_images as CI  # noqa: E402

OPS = {"COLL.GROUP_REDUCE_MCAST": "grm", "COLL.TOPK_MERGE": "tkm", "COLL.ROW_GATHER": "rg"}
OPEN = {
    "COLL.GROUP_REDUCE_MCAST": [
        "cross-die reduce phase not emitted: needs_tp192_programme (golden tree = TP-96 o-group of 8; d4g contributor "
        "set / tree order undefined until a TP-192 DS programme exists)",
        "peer partials A of the 7 other contributors absent (fixture ranks [0]; all-rank capture launched: "
        "dsfix/fix_allr on ot-epyc5)",
        "hb_coll_SW programme = 1536-b uop rows (static_uop_layout_v4.json): no hard_v8x row compiler for the reduce "
        "(row_gather_rows.py / argmax_rows.py are host_v4-timed mechanism compilers)"],
    "COLL.TOPK_MERGE": [
        "no on-die ring phase (d4g class C4: lands in the consumer quadrant); SW-slice part = ep_S0/S1 RX -> qslots -> "
        "tkm_SW (tkm_start / tkm_del_slot / tkm_cfg_* uop fields) + own list via SU inject",
        "needs_tp192_programme (TP-96 golden merges G=96 lists; tkm_SW is TP-192)",
        "peer (value, id) lists absent (fixture ranks [0]; all-rank capture launched: dsfix/fix_allr on ot-epyc5)",
        "no hard_v8x uop row compiler; far-end 612-b link frames (seq / epoch / CRC) need a frame generator"],
    "COLL.ROW_GATHER": [
        "no on-die ring phase (d4g class C3: rows go to the token-owning quadrant's endpoint)",
        "A / O are HBM operands: the fixture carries (addr, bytes, sha256) only, no row values",
        "owner rows arrive from peer dies over ep_S0/S1: same uop-compiler / link-frame gaps as TOPK_MERGE"],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--R", type=int, default=2, choices=(1, 2))
    ap.add_argument("--t-start", type=int, default=40)
    ap.add_argument("--nev", type=int, default=6309)
    ap.add_argument("--rank", default="0")
    ap.add_argument("--pre-events", type=Path)
    a = ap.parse_args()
    meta, z, recs = CI.load_fixture_records(a.fixtures, a.rank)
    L = int(meta["layer"]) if str(meta["layer"]).isdigit() else meta["layer"]
    prefix = f"ds_l{L}" if isinstance(L, int) else f"ds_{L}"
    bnd = json.loads(a.boundary.read_text())
    ins = {e["name"] for e in bnd["inputs"]}
    outs = {e["name"] for e in bnd["outputs"]}
    a.out.mkdir(parents=True, exist_ok=True)
    man = []
    for x in recs:
        if x["op"] not in OPS:
            continue
        pr = x.get("priced") or []
        i_rec = int(pr[0]["i"]) if pr else None
        ent = dict(k_layer=x["k"], tag=x["tag"], i=i_rec, op=x["op"], d4g_placement=x.get("d4g_placement"),
                   priced_cycles=round(pr[0]["end"] - pr[0]["start"], 2) if pr else None, open=OPEN[x["op"]])
        if i_rec is None:
            ent.update(status="unpriced", reasons=["record not in the priced layer (no i): not replayed"])
            man.append(ent)
            continue
        if x["op"] != "COLL.GROUP_REDUCE_MCAST":
            ent.update(status="cross_die_only", reasons=OPEN[x["op"]])
            man.append(ent)
            continue
        O = np.asarray(z[x["outputs"]["O"]["array"]], np.uint32)
        g = CI.gather_record(O, i_rec, R=a.R, t_start=a.t_start)
        if g["status"] != "emitted":
            ent.update(g)
            man.append(ent)
            continue
        parts = []
        for suf, evs in CI.replays(g, a.nev):
            name = f"{prefix}_grm_r{i_rec:03d}{suf}"
            for e in evs:
                if e["k"] == "D":
                    assert e["port"] in ins, e["port"]
                elif e["k"] == "C" and not e["port"].startswith("vm:"):
                    assert e["port"] in outs, e["port"]
            evs = sorted(evs, key=lambda e: (e["dom"], e["cyc"], e["k"]))
            rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top", "sw"), design="ds",
                       layer=str(L), record=i_rec, tag=x["tag"], op=x["op"], lane="VEH-FMT-COLL2",
                       assumptions=["on-die multicast phase only: the cross-die o-group reduce has landed quadrant q's "
                                    "quarter of O in its own banks (VM preload); quadrant q holds contiguous quarter q",
                                    "O = BF16 results one per VM word (fixture u32 words), moved bit-exact",
                                    "calendar_SW = COLL-only window grant (sole VM owner in this replay)"],
                       events=evs)
            txt = json.dumps(rep) + "\n"
            (a.out / f"{name}.json").write_text(txt)
            if a.pre_events:
                a.pre_events.mkdir(parents=True, exist_ok=True)
                (a.pre_events / f"{name}.events.txt").write_text(CI.pre_events(evs))
            parts.append(dict(name=name, events=sum(1 for e in evs if e["k"] != "M"),
                              vm_preload=sum(1 for e in evs if e["k"] == "M"), cycles=g["check_cyc"] + 64,
                              checks=sum(1 for e in evs if e["k"] == "C"),
                              replay_sha256=hashlib.sha256(txt.encode()).hexdigest()))
        ent.update({k: v for k, v in g.items() if k not in ("events", "chk_vm", "chk_ring", "chk_misc")})
        ent.update(status="emitted_on_die_phase", replays=parts)
        man.append(ent)
    doc = dict(schema="opentallas.hbm_coll_ops_images.v1", lane="VEH-FMT-COLL2", fixtures=str(a.fixtures), layer=L,
               R=a.R, t_start=a.t_start, nev=a.nev, records=man,
               counts={s: sum(1 for m in man if m["status"] == s) for s in sorted({m["status"] for m in man})})
    (a.out / f"{prefix}_coll_ops_manifest.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(dict(layer=L, counts=doc["counts"],
                          replays=[p["name"] for m in man for p in m.get("replays", [])])))


if __name__ == "__main__":
    main()
