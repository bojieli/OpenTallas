#!/usr/bin/env python3
"""TOKEN-XDIE-S81: golden data + compiler static calendar for tb_xdie_s81 (S81 p4l TP4 cross-die collectives).

    python3 tools/xdie_s81/gen_golden.py --out DIR [--lat S=..,N=..] [--per S=..,N=..] [--fold F] [--reps 2]

Writes DIR/stim.hex (one line per beat: {deadline 32, issue 32, dp 8, beat 1104}, sorted by issue cycle), DIR/NS
(the beat count, passed as +NS=) and DIR/golden.json (collectives, instances, beats per peer, start cycles, payload
sha256 per (instance, src die), the all-reduce golden folds).

Collectives = the DS ROM decode's cross-die operations (token DAG results/arch/token_path_20261009/ds_rom.json, TP4,
payload_B as dsrom_1m_allmeasured links_coll.json: all-gather payload = the gathered total, all-reduce payload = the
per-rank vector):
  argmax_merge (head)        AG      32 B   -> 8 B a rank   -> 1 beat a peer
  router_allgather (dispatch)AG   1,536 B   -> 384 B         -> 3
  a_allgather                AG   3,648 B   -> 912 B         -> 8
  eng_rows_allgather         AG   6,336 B   -> 1,584 B       -> 13
  idx_topk_merge             AG  16,384 B   -> 4,096 B       -> 32
  cand_merge                 AG  65,536 B   -> 16,384 B      -> 128
  rows_allgather             AG  67,584 B   -> 16,896 B      -> 132
  out/combine_allreduce      AR  20,480 B = reduce-scatter (5,120 B quarter to its owner, 40 beats) + owner fold
                                 ((p0 + p1) + (p2 + p3)) in fp32 (die-internal, golden here) + all-gather (40 beats)
  stage_hop (h, 40,976 B)    P2P die d -> die d+1 (one port, 321 beats)
A beat carries 128 B (the line beat payload, 1,024 b: the XQ / RD payload width of ot_s81sl_rstop / ot_s81sl_xr).
Calendar: every sender port issues one beat a cycle from the instance's start cycle (the line rate; the lep TX landing
SRAM absorbs bursts <= 2,170 beats, off-die rate <= lane rate is a compiler rule the bursts here respect).
Deadlines (static-schedule check): deadline(k) = max(start + LAT[class] + ceil(k * PER[class]), the same port's previous
beat deadline + ceil(PER)) (a port drains in order at PER: a burst issued before the previous one drained queues) with class S (s_0S / s_7S
ports: UCIe lane 0 + SerDes lane 1) or N (s_0N / s_7N: 2 x SerDes); 0 = no deadline (calibration run).  The AR
all-gather phase starts at the RS phase's last deadline + 1 + FOLD (static: issued whatever the link did).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ND, NP = 4, 4
BEAT_B = 128
WARM = 12000          # cycles before the first instance (links trained; the calendar starts after link-up)
GAP = 4000            # cycles between instances (no overlap of instances: E is measured in isolation)

COLLS = [  # name, kind, payload_B (AG: gathered total; AR: per-rank vector; P2P: message)
    ("argmax_merge", "AG", 32),
    ("router_allgather", "AG", 1536),
    ("a_allgather", "AG", 3648),
    ("eng_rows_allgather", "AG", 6336),
    ("idx_topk_merge", "AG", 16384),
    ("cand_merge", "AG", 65536),
    ("rows_allgather", "AG", 67584),
    ("allreduce_20480", "AR", 20480),
    ("stage_hop", "P2P", 40976),
]
# port ids: 0 = WS (s_0S), 1 = ES (s_7S), 2 = WN (s_0N), 3 = EN (s_7N); circuits: d.ES <-> (d+1).WS, d.EN <-> (d+2).WN
PORT_TO = {1: +1, 0: -1, 3: +2}       # sender port -> peer offset (each die reaches its 3 peers in one crossing)
CLASS = {0: "S", 1: "S", 2: "N", 3: "N"}


def beat_word(payload: bytes, inst: int, seq: int, src: int) -> int:
    assert len(payload) <= BEAT_B
    w = 1                                  # valid
    w |= 0 << 1                            # kind CTL (slice mask 0: no slice acts; forwarding is kind-blind)
    w |= 3 << 4                            # hops 3: out of the sender end slice, across, inward out of the peer end
    w |= (src & 0xF) << 9
    w |= int.from_bytes(payload.ljust(BEAT_B, b"\0"), "little") << 64
    w |= (inst & 0xFF) << 1088
    w |= (seq & 0xFF) << 1096
    return w


def chunks(b: bytes):
    return [b[i:i + BEAT_B] for i in range(0, len(b), BEAT_B)] or [b""]


def parse_cls(s, default):
    out = dict(default)
    if s:
        for kv in s.split(","):
            k, v = kv.split("=")
            out[k] = float(v)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--lat", default="", help="first-beat latency per class, e.g. S=560,N=560 (empty: no deadlines)")
    ap.add_argument("--per", default="", help="cycles per beat drain per class, e.g. S=1.4,N=1.4")
    ap.add_argument("--fold", type=int, default=0, help="owner fold cycles between the AR phases (die-internal)")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--only", default="", help="comma list of collective names (default all)")
    ap.add_argument("--gap", type=int, default=GAP, help="cycles from an instance's last issue to the next start")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    lat = parse_cls(a.lat, {}); per = parse_cls(a.per, {})
    gate = bool(lat) and bool(per)
    only = set(a.only.split(",")) if a.only else None

    port_busy = {}   # sender port -> last compiled landing deadline (the port drains its queue in order at PER)

    def deadline(start, k, cls, dp=None):
        if not gate:
            return 0
        d = start + int(lat[cls]) + math.ceil(k * per[cls])
        if dp is not None and dp in port_busy:          # queued behind the previous burst on the same port
            d = max(d, port_busy[dp] + math.ceil(per[cls]))
        if dp is not None:
            port_busy[dp] = d
        return d

    lines = []      # (issue, dp, beat, deadline)
    insts = []
    t = WARM
    inst = 0
    for rep in range(a.reps):
        for name, kind, pb in COLLS:
            if only and name not in only:
                continue
            rec = dict(inst=inst, name=name, kind=kind, payload_B=pb, rep=rep, start=t, src_sha={})
            rng = np.random.default_rng(1000 * inst + 17)
            if kind == "AG":
                per_rank = pb // ND
                rec.update(per_rank_B=per_rank, beats_per_peer=len(chunks(bytes(per_rank))))
                for d in range(ND):
                    data = rng.integers(0, 256, per_rank, dtype=np.uint8).tobytes()
                    rec["src_sha"][d] = hashlib.sha256(data).hexdigest()
                    for p in PORT_TO:
                        for k, c in enumerate(chunks(data)):
                            lines.append((t + k, d * NP + p, beat_word(c, inst, k, d * NP + p), deadline(t, k, CLASS[p], d * NP + p)))
                end = t + rec["beats_per_peer"]
            elif kind == "AR":
                n = pb // 4
                q = n // ND
                parts = [rng.standard_normal(n).astype(np.float32) for _ in range(ND)]
                fold = (parts[0] + parts[1]) + (parts[2] + parts[3])          # golden tree order, fp32
                rec.update(quarter_B=q * 4, beats_per_peer=len(chunks(bytes(q * 4))),
                           fold_order="((p0 + p1) + (p2 + p3)) fp32 (np.float32 adds, round-to-nearest-even)",
                           fold_sha=hashlib.sha256(fold.tobytes()).hexdigest())
                # phase 1 reduce-scatter: die d sends quarter o of its partial to owner o (o != d)
                rs_dead = 0
                for d in range(ND):
                    rec["src_sha"][d] = hashlib.sha256(parts[d].tobytes()).hexdigest()
                    for p, off in PORT_TO.items():
                        o = (d + off) % ND
                        data = parts[d][o * q:(o + 1) * q].tobytes()
                        cs = chunks(data)
                        for k, c in enumerate(cs):
                            dl = deadline(t, k, CLASS[p], d * NP + p)
                            rs_dead = max(rs_dead, dl)
                            lines.append((t + k, d * NP + p, beat_word(c, inst, k, d * NP + p), dl))
                # phase 2 all-gather of the folded quarter (owner o = d) at its compiled cycle
                t2 = (rs_dead + 1 + a.fold) if gate else t + 1500 + a.fold
                rec["ag_start"] = t2
                for d in range(ND):
                    data = fold[d * q:(d + 1) * q].tobytes()
                    for p in PORT_TO:
                        for k, c in enumerate(chunks(data)):
                            lines.append((t2 + k, d * NP + p, beat_word(c, inst + 1, k, d * NP + p), deadline(t2, k, CLASS[p], d * NP + p)))
                rec["inst_ag"] = inst + 1
                inst += 1
                end = t2 + rec["beats_per_peer"]
            else:  # P2P stage hop: die d -> d+1 over its ES port
                rec.update(beats=len(chunks(bytes(pb))), port="ES")
                for d in range(ND):
                    data = rng.integers(0, 256, pb, dtype=np.uint8).tobytes()
                    rec["src_sha"][d] = hashlib.sha256(data).hexdigest()
                    for k, c in enumerate(chunks(data)):
                        lines.append((t + k, d * NP + 1, beat_word(c, inst, k, d * NP + 1), deadline(t, k, "S", d * NP + 1)))
                end = t + rec["beats"]
            insts.append(rec)
            inst += 1
            t = end + a.gap
    lines.sort(key=lambda x: (x[0], x[1]))
    seen = set()
    for iss, dp, _, _ in lines:
        assert (iss, dp) not in seen, "two beats on one port in one cycle"
        seen.add((iss, dp))
    with open(out / "stim.hex", "w") as f:
        for iss, dp, w, dl in lines:
            f.write(f"{dl:08x}{iss:08x}{dp:02x}{w:0276x}\n")
    (out / "NS").write_text(f"{len(lines)}\n")
    g = dict(schema="opentallas.xdie_s81.golden.v1", beats=len(lines), beat_B=BEAT_B, warm=WARM, gap=a.gap, reps=a.reps,
             gate=gate, lat=lat, per=per, fold=a.fold, instances=insts, port_to=PORT_TO, cls=CLASS,
             last_issue=max(x[0] for x in lines))
    (out / "golden.json").write_text(json.dumps(g, indent=1))
    print(f"beats {len(lines)} instances {len(insts)} last issue {g['last_issue']} gate {gate}")


if __name__ == "__main__":
    main()
