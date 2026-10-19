#!/usr/bin/env python3
"""VEH-FMT-COLL: fast local checks of coll_images.py (no simulator).

  PYTHONPATH=tools python3 tools/hbm_next/vehicle/test_coll_images.py [--boundary slice_sw/boundary.json]
1. flit layout = ot_hgi_coll_ring_ag_lane.sv inject concatenation {1, 2'd3, qid, qid, ttl, tag, 1'b0, 11'b0, data};
2. gq descriptor row = the ot_hgi_coll_gq.sv field map (tb_hgi_coll_gq frame_cfg), F20 header c7a1 / row;
3. calendar window word = universal calendar layout with rslot 3 / wslot 2 on all 8 banks (compile_schedule);
4. DS L0 / L14 fixtures: every gather replay drives only slice inputs (when --boundary), checks only slice outputs / VM;
   arrivals per (port, edge) unique; sources = PREV^h / NEXT^h; landed (word, bank) set and edges = the
   collq_gather_1018.schedule() rule (+ the registered kq share); every checked VM word reconstructs the fixture's O;
   every replay fits NEV 6309 (L14 eg_kv splits in two).
The RTL pre-check of the same events (one real quadrant: gq + ring A + ring B + shares) is tb_coll_replay.sv.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parents[1]))
from hbm_next.vehicle import coll_images as CI  # noqa: E402

FIX = ROOT / "results/rtl/hbm_ds_layer_tput_1018/fixtures"


def t_flit():
    rtl = (ROOT / "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_ring_ag_lane.sv").read_text()
    assert "{1'b1,2'd3,qid,qid,tx_ttl[d*2+:2],tx_tag,1'b0,11'b0,tx_q}" in rtl
    d = (1 << 256) - 12345
    f = CI.flit(2, 3, 13, d)
    assert f >> 279 == 1 and (f >> 277) & 3 == 3 and (f >> 275) & 3 == 2 and (f >> 273) & 3 == 2
    assert (f >> 271) & 3 == 3 and (f >> 268) & 7 == 13 % 8 and (f >> 256) & 0xfff == 0 and f & ((1 << 256) - 1) == d
    print("flit layout OK")


def t_row():
    p = CI.gq_row(72, 2, 40, CI.sec16(0, 0x100), CI.sec16(0, 0x100), 72, 41)
    get = lambda lo, w: (p >> lo) & ((1 << w) - 1)
    assert get(0, 1) == 0 and get(1, 1) == 1 and get(2, 1) == 0 and get(3, 16) == 40 and get(19, 10) == 72
    assert get(29, 8) == 0 and get(37, 16) == 0x100 and get(53, 16) == 0x100 and get(69, 16) == 72 and get(85, 16) == 41
    w = CI.f20_word(0, p)
    assert w >> 240 == 0xc7a1 and (w >> 224) & 0xfff == 0
    gq = (ROOT / "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_gq.sv")
    if gq.exists():
        t = gq.read_text()
        for frag in ("[18:3] t_start", "[28:19] F", "[52:37] src sector", "[68:53] dst sector", "[84:69] stride",
                     "[100:85] period"):
            assert frag in t, frag
    print("gq row OK")


def t_calendar():
    prog, word = CI.calendar_window(500)
    assert prog["start"] == dict(base=0, limit=1, loops=500) and len(prog["configuration_writes"]) == 1
    spec = prog["layout"]
    v = int(prog["configuration_writes"][0]["data"], 16)
    f = {x["name"]: (v >> x["lo"]) & ((1 << x["bits"]) - 1) for x in spec["fields"]}
    assert f["rslot_v"] == 0xff and f["wslot_v"] == 0xff
    assert all((f["rslot"] >> (3 * b)) & 7 == 3 for b in range(8)) and all((f["wslot"] >> (3 * b)) & 7 == 2 for b in range(8))
    assert v >> 240 == 0xc7a1
    print("calendar window OK")


def t_layer(fdir, bnd, expect_split=False):
    import hgi_sim.collq_gather_1018 as CQ
    meta, z, recs = CI.load_fixture_records(fdir)
    ins = outs = None
    if bnd:
        b = json.loads(Path(bnd).read_text())
        ins, outs = {e["name"] for e in b["inputs"]}, {e["name"] for e in b["outputs"]}
    n_rep = split = 0
    for x in recs:
        if x["op"] != "COLL.ALL_GATHER" or not x.get("priced"):
            continue
        i = int(x["priced"][0]["i"])
        O = np.asarray(z[x["outputs"]["O"]["array"]], np.uint32)
        g = CI.gather_record(O, i)
        assert g["status"] == "emitted", (x["tag"], g)
        F, R, stride, FE = g["F"], g["R"], g["stride"], g["fire"]
        # arrivals: unique per (port, edge), sources = ring tables
        seen = set()
        for e in g["events"]:
            if e["k"] == "D" and e["src"].startswith("farend") and e["val"] != "0":
                key = (e["port"], e["cyc"])
                assert key not in seen
                seen.add(key)
                v = int(e["val"], 16)
                src, ttl = (v >> 275) & 3, (v >> 271) & 3
                h = 4 - ttl
                d = 0 if e["port"].endswith("cw_o") and "ccw" not in e["port"] else 1
                assert src == CI.src_of(0, d, h), (e["port"], src, h)
        # landed sectors (VM checks) vs collq schedule(): same (bank, word) set, same edge offsets (+ kq share)
        _, writes = CQ.schedule(0, F, R, False, 0, g["src_sector"] & 0x1fff, g["dst_sector"] & 0x1fff, stride)
        cq_k = getattr(CQ, "KQ_SHARE_EDGES", 0)
        cw = {(w[2], w[0] + (CI.KQ_SHARE - cq_k)) for w in writes}
        mine = set()
        for ii in range(F):
            k = ii // R
            for h in (1, 2, 3):
                s = CI.src_of(0, k & 1, h)
                mine.add(((g["dst_sector"] & 0x1fff) + s * stride + ii, CI.issue_rel(k) + CI.PUBLISH_WRITE + 2 * h))
        assert mine == cw, (x["tag"], len(mine ^ cw))
        assert g["last_write"] - FE == CI.span(F, R)
        # VM checks reconstruct O
        got = {}
        for c in g["chk_vm"]:
            got[int(c["port"][3:], 16)] = int(c["val"], 16)
        rec = np.zeros(len(O), np.uint32)
        sw = len(O) // 4
        for s in range(4):
            for j in range(F):
                v = got[g["dst_sector"] + s * stride + j]
                for b in range(8):
                    rec[s * sw + 8 * j + b] = (v >> (32 * b)) & 0xffffffff
        assert np.array_equal(rec, O), x["tag"]
        parts = CI.replays(g, 6309)
        split += len(parts) > 1
        for _, evs in parts:
            n_rep += 1
            assert sum(1 for e in evs if e["k"] != "M") <= 6308
            if ins is not None:
                for e in evs:
                    if e["k"] == "D":
                        assert e["port"] in ins, e["port"]
                    elif e["k"] == "C" and not e["port"].startswith("vm:"):
                        assert e["port"] in outs, e["port"]
    assert bool(split) == expect_split, split
    print(f"{fdir.name}: {n_rep} gather replays OK (split records {split})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boundary")
    a = ap.parse_args()
    t_flit()
    t_row()
    t_calendar()
    t_layer(FIX / "L00", a.boundary)
    t_layer(FIX / "L14", a.boundary, expect_split=True)
    print("TEST_COLL_IMAGES PASS")


if __name__ == "__main__":
    main()
