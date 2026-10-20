#!/usr/bin/env python3
"""TOKSIM-S81B/LEG (10-19): static calendar + expected beats for tb_leg_s81 (rtl/test/toksim_s81b_leg).
Windows (one flow at a time, beats every cycle = the ring line rate, 1,104 b = 4 x 276-b lanes a cycle):
  terms : the production payload of every cross-die term at the FARTHEST slice (7 ring links, the priced case), per
          tier and flow: beats a peer as tb_xdie_s81_2 / gen_golden.py COLLS (128 B a beat).
  sweep : every source / owning column (1..7 links), 16 beats each, per tier and flow.
Beat = gen_golden.beat_word form: valid, kind CTL (forwarding is kind-blind), hops [8:4], src sid [12:9], payload
128 B at [1087:64], inst [1095:1088], seq [1103:1096]; bench tag [40:33] = {tier, flow}, [32:13] = beat index.
Payload bytes: SHA-256 stream of (term, tier, flow, beat) -- deterministic, full-entropy production-size data."""
import argparse, hashlib, json
from pathlib import Path

BEAT_B = 128
TERMS = [("argmax_merge", 1), ("router_allgather", 3), ("a_allgather", 8), ("eng_rows_allgather", 13),
         ("idx_topk_merge", 32), ("allreduce_20480", 40), ("cand_merge", 128), ("rows_allgather", 132),
         ("stage_hop", 321)]          # beats a peer per crossing (results/rtl/xdie_s81_1019/record.json collectives.*.beats_per_peer)
FLOWS = {0: "out_W (src -> W end stop 0)", 1: "out_E (src -> E end stop 7)",
         2: "in_E (W end stop 0 -> owner, E-bound)", 3: "in_W (E end stop 7 -> owner, W-bound)"}


def payload(tag: str) -> int:
    b = b""
    i = 0
    while len(b) < BEAT_B:
        b += hashlib.sha256(f"{tag}/{i}".encode()).digest(); i += 1
    return int.from_bytes(b[:BEAT_B], "little")


def beat(hops, src, pl, inst, seq, tier, flow, idx):
    w = 1 | (0 << 1) | ((hops & 0x1F) << 4) | ((src & 0xF) << 9)
    w |= (idx & 0xFFFFF) << 13
    w |= ((tier & 1) << 40) | ((flow & 3) << 38)
    w |= pl << 64
    w |= (inst & 0xFF) << 1088
    w |= (seq & 0xFF) << 1096
    return w


def sethops(w, h):
    return (w & ~(0x1F << 4)) | ((h & 0x1F) << 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sweep-beats", type=int, default=16)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ent = []; wins = []
    t0 = 64; idx = 0; inst = 0

    def window(name, tier, flow, col, nb):
        nonlocal t0, idx, inst
        if flow == 0:   src, dst, h_in, h_exp = col, 0, col + 2, 3
        elif flow == 1: src, dst, h_in, h_exp = col, 7, 9 - col, 3
        elif flow == 2: src, dst, h_in, h_exp = 0, col, col + 1, 1
        else:           src, dst, h_in, h_exp = 7, col, 8 - col, 1
        sid = 2 * src + tier
        links = abs(dst - src)
        wins.append(dict(name=name, tier="SN"[tier], flow=flow, flow_desc=FLOWS[flow], src_col=src, dst_col=dst,
                         links=links, beats=nb, start=t0, inst=inst))
        for k in range(nb):
            pl = payload(f"{name}/{tier}/{flow}/{col}/{k}")
            b = beat(h_in, sid, pl, inst, k, tier, flow, idx)
            ent.append((t0 + k, flow, tier, src if flow < 2 else (0 if flow == 2 else 7), dst if flow >= 2 else (0 if flow == 0 else 7),
                        b, sethops(b, h_exp)))
            idx += 1
        t0 += nb + 300; inst = (inst + 1) & 0xFF

    for tier in (0, 1):
        for flow in (0, 1, 2, 3):
            far = {0: 7, 1: 0, 2: 7, 3: 0}[flow]
            for name, nb in TERMS:
                window(name, tier, flow, far, nb)
            cols = range(1, 8) if flow in (0, 2) else range(0, 7)
            for c in cols:
                window(f"sweep_c{c}", tier, flow, c, a.sweep_beats)
    with open(out / "stim.hex", "w") as f:
        for (c, fl, t, s, d, b, e) in ent:
            v = (c << 2232) | (fl << 2224) | (t << 2216) | (s << 2212) | (d << 2208) | (b << 1104) | e
            f.write(f"{v:0566x}\n")
    (out / "NS").write_text(str(len(ent)))
    json.dump(dict(windows=wins, n_beats=len(ent), beat_B=BEAT_B, terms=TERMS), open(out / "windows.json", "w"), indent=1)
    print("NS", len(ent), "windows", len(wins), "last", t0)


if __name__ == "__main__":
    main()
