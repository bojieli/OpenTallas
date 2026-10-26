#!/usr/bin/env python3
"""MU-D2D-OVL 2026-10-19 (coordinator 0ki): overlapping request / response segments on the static compute <-> KV D2D link.

Finding (MU-DQ-TOK, mu_d2d_overlap.py): ot_qwen_d2d_cal plays one segment per calendar per start, and one cal_start
starts BOTH calendars of an end (TX + RX), so a layer exchange holds the link from the CMD to the last RESULT
(1,816 cycles).  968 of the 1,655 adjacent user exchanges of the 4-user frame of record overlap -> 9,834 tok/s (-28 %).

Fix (static, no credits / backpressure):
  RTL  ot_qwen_d2d_static_end OVL = 1: the RX calendar has its own start (cal_start_rx / cal_seg_rx), and each start
       carries the USER whose segment it plays (cal_user_tx / cal_user_rx); the end tags every TX slot and every RX
       event with that user (tx_user / rx_user).  Each direction is still ONE playhead: a start while that direction's
       segment runs is the calendar's sticky fault (collision = fault).  ot_qwen_d2d_ovl_seq plays the compiled
       per-direction start lists (ROM, {dt, seg, user, wrap}) from the common epoch anchor, after the unchanged image
       load / admission of ot_qwen_d2d_cal_seq.
  Compiler (this file): the layer exchange is split into a REQUEST segment (C->K: CMD, 32 Q, 4 KVN, STATUS) and a
       RESPONSE segment (K->C: 32 RESULT + STATUS, on the as-built KV programme's fixed RESULT age), the token run into
       a token-head TX (STATUS + programme witness) and token-head RX (context record, embedding header + 64 row
       words) segment; each segment's image is rebased so it starts LEAD edges before its first event.  Every
       segment's playhead occupancy [start, last event] at all four calendars (d2d.ctx, d2d.crx, d2d.ktx, d2d.krx) is
       a resource of the frame compiler (mu_calendar att_windows / seg_windows), so mu_opcal.compile_frame places the
       users' segments in free link slots and refuses any collision; the start lists are emitted from that schedule.

    python3 -m qwen_static_schedule.mu_d2d_ovl --out DIR [--stages ...] [--frame 16] [--mut collide|slot|user]
"""
from __future__ import annotations

import argparse
import gzip,hashlib
import json
import sys
from pathlib import Path

from .calendar import ScheduleError
from . import mu_calendar as M
from . import mu_opcal as O

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qwen_split"))
import d2d_link_calendar as L  # noqa: E402

# netlisted seam of the MU release dies (MU-DQ-TOK record_bundle_audit on dv2f18mu + kvs14r-bce531645-mu, XQ_PLAN):
# compute C.tx_slot 2 / C.rx_record 2 / x3_slot E2 -> 3 / C.tx_record 2 / C.x3_record 2; KV K.rx_record 11, tx_slot 9,
# tx_record 9 -> TXDP C [8, 3, 1, 10], K [21, 4, 3, 3] (coordinator 0ki)
STAGES = "2,2,2,3,2,2/11,11,9,9,9,9,9"
TXL, PHY = 6, 5                    # slot-to-pin latency at codec 1; UCIe FDI-to-FDI 5 (both + 2 with the PR pin flops)
RX_CMD, SERVICE_END = 2, 1777      # as-built KV attention programme (kvs14c qkd_kvs_attn u_attn_cal, STRETCH 1)
TX_FIRST = RX_CMD + 2 + SERVICE_END - 31
ATT_BUSY = 1784                    # KV attention programme busy [run, run + 1784] (MU-KV-PROG audit; end = TX_FIRST + 34)
LEAD = 1                           # a segment's start is LEAD edges before its first event (calendar dt >= 1)
DT_W = 20                          # start-list entry dt width
MIN_DT = 4                         # ot_qwen_d2d_list_play prefetch: entries at least 4 edges apart
CALS = ("C_tx", "C_rx", "K_tx", "K_rx")
RES = {"C_tx": "d2d.ctx", "C_rx": "d2d.crx", "K_tx": "d2d.ktx", "K_rx": "d2d.krx"}


SH = 64                            # compile_seg needs cycles >= 1: segments are compiled SH edges after their reference


def _cseg(msgs, txd):
    _, tab = L.compile_seg([dict(m, cyc=m["cyc"] + SH) for m in msgs], TXL, PHY + 2, 0, txd)
    return [dict(t, cyc=t["cyc"] - SH, arrive=t["arrive"] - SH, wr=t["wr"] - SH) for t in tab]


def txd_of(stages, kv_codec=1):
    S = L.parse_stages(stages)
    raw = L.producer_txd(S, kv_codec=kv_codec)
    return S, {e: [x + d for x, d in zip(raw[e], L.PINREG_EXT[e])] for e in ("C", "K")}


def seg_msgs(S, txd, attn=1816, kv_codec=1):
    """the four link segments as message lists (cycles relative to the segment reference: the CMD send edge for the
    layer exchange, the token-head reference for the token head), plus the KV-programme law of the layer exchange"""
    txl_p, phy_p, phy_c = TXL + 2, PHY + 2, PHY + 2
    req = [dict(src="C", cyc=0, tx_port=0, rx_port=0, kind=1, beat=0)]
    req += [dict(src="C", cyc=1 + b, tx_port=0, rx_port=0, kind=2, beat=b) for b in range(32)]
    req += [dict(src="C", cyc=33 + i, tx_port=3, rx_port=3, kind=5, beat=i) for i in range(4)]
    # STATUS (kind 15): the first offset >= 40 whose write capture is unique (the d2d_link_calendar search)
    for st in range(40, 49):
        m = req + [dict(src="C", cyc=st, tx_port=2, rx_port=2, kind=15, beat=0)]
        try:
            _cseg(m, txd)
            req = m
            break
        except SystemExit:
            continue
    else:
        raise ScheduleError("no STATUS offset with a unique write capture")
    # RESPONSE on the as-built programme's fixed RESULT age (xdie_exchange_cal.py law)
    arr_cmd = txd["C"][0] - 1 + TXL + phy_c
    t_prog = arr_cmd + 2 + S["KS_RXV"]
    r0 = t_prog + (TX_FIRST - RX_CMD) - S["KS_TXS"]
    r0_priced = attn - (txl_p + phy_p + 3) - 33 - (kv_codec - 1)
    rsp = [dict(src="K", cyc=r0 + b, tx_port=0, rx_port=0, kind=3, beat=b) for b in range(32)]
    rsp.append(dict(src="K", cyc=r0 + 33, tx_port=0, rx_port=0, kind=4, beat=0))
    # token head (the single-user token run without its L0 exchange: d2d_link_calendar --profile program seg 1)
    tkt = [dict(src="C", cyc=2, tx_port=2, rx_port=2, kind=15, beat=0),
           dict(src="C", cyc=30, tx_port=1, rx_port=1, kind=14, beat=0)]
    tkr = [dict(src="K", cyc=3, tx_port=1, rx_port=1, kind=12, beat=0),
           dict(src="K", cyc=191, tx_port=2, rx_port=2, kind=8, beat=0)]
    tkr += [dict(src="K", cyc=192 + b, tx_port=2, rx_port=2, kind=6, beat=b) for b in range(32)]
    tkr += [dict(src="K", cyc=224 + b, tx_port=2, rx_port=2, kind=7, beat=b) for b in range(32)]
    law = dict(arr_cmd=arr_cmd, cmd_at_programme=t_prog, run=t_prog - RX_CMD - 1, r0=r0, r0_priced=r0_priced,
               X=r0 - r0_priced)
    return dict(req=req, rsp=rsp, tok_tx=tkt, tok_rx=tkr), law


def seg_images(segs, txd):
    """per segment: per calendar {start offset s (from the segment reference), image words, occupancy [s, last + 1)}"""
    out = {}
    for name, msgs in segs.items():
        tab = _cseg(msgs, txd)
        ev = {c: [] for c in CALS}
        for t in tab:
            s, r = t["src"], "K" if t["src"] == "C" else "C"
            ev[f"{s}_tx"].append((t["cyc"], t["tx_port"], t["kind"], t["beat"]))
            ev[f"{r}_rx"].append((t["arrive"], t["rx_port"], t["kind"], t["beat"]))
        d = {}
        for c, e in ev.items():
            if not e:
                continue
            e.sort()
            s0 = e[0][0] - LEAD
            d[c] = dict(start=s0, img=L.image([(x - s0, p, k, b) for x, p, k, b in e]), occ=(s0, e[-1][0] + 1),
                        events=len(e))
        out[name] = d
    return out


def build(stages=STAGES, frame=16, kv_prog=False, starts=None, kv_codec=1, pair_calendar=None, token_path=None):
    S, txd = txd_of(stages, kv_codec=kv_codec)
    segs, law = seg_msgs(S, txd, kv_codec=kv_codec)
    pair=None
    pair_price={}
    if pair_calendar:
        pair=json.loads(Path(pair_calendar).read_text())
        if pair['txd']!=txd:raise ScheduleError('pair calendar and OVL seam differ')
        ms=pair['messages'];cmd=next(m['cyc'] for m in ms if m['seg']==0 and m['src']=='C' and m['kind']==1)
        clean=lambda m,ref:dict(src=m['src'],cyc=m['cyc']-ref,tx_port=m['tx_port'],rx_port=m['rx_port'],kind=m['kind'],beat=m['beat'])
        segs=dict(req=[clean(m,cmd) for m in ms if m['seg']==0 and m['src']=='C'],
                  rsp=[clean(m,cmd) for m in ms if m['seg']==0 and m['src']=='K'],
                  tok_tx=[clean(m,0) for m in ms if m['seg']==1 and m['src']=='C' and m['kind'] in (12,14,15) and m['cyc']<pair['program']['token_run_L0']['q_send']],
                  tok_rx=[clean(m,0) for m in ms if m['seg']==1 and m['src']=='K' and m['kind'] in (6,7,8,12)])
        actual=pair['program'];w=actual['windows']['L1_35']
        raw=Path(token_path).read_bytes();tp=json.loads(gzip.decompress(raw) if str(token_path).endswith('.gz') else raw)
        byop={n['op']:int(n['cycles']) for n in tp['nodes'] if n['id'].startswith('L1.')}
        byop.update(w);byop['attention']=w['attn_kv']
        M.LAYER_WINDOWS=tuple((op,unit,byop.get(op,n),busy) for op,unit,n,busy in M.LAYER_WINDOWS)
        floor=max(8012,max(int(g['cycles']) for g in actual['layers']))
        period=actual['token_period']
        head=period-actual['embed']['cycles']-sum(int(g['cycles']) for g in actual['layers'])-O.EMB_T
        if head<0:raise ScheduleError('pair period cannot contain actual head/embedding')
        pair_price=dict(layer_period=floor,l0_extra=0,embed_cycles=actual['embed']['cycles'],head_cycles=head,
                        kv_service=2003,head_tok_ofs=O.EMB_T)
        kv_prog=True
        law.update(source='actual canonical pair calendar',kernel_busy=2003,
                   r0=segs['rsp'][0]['cyc'],run=law['run'],X=max(0,w['attn_kv']-1816))
    im = seg_images(segs, txd)
    X = max(0, law["X"])
    att = {}
    for sg in ("req", "rsp"):
        for c, d in im[sg].items():
            att.setdefault(RES[c], []).append(d["occ"])
    if kv_prog:                                    # optional: the as-built KV attention programme is one resource
        att["kv.prog"] = [(law["run"], law["run"] + (2003 if pair else ATT_BUSY + 1))]
    o = O.EMB_T                                    # head block: the token-head reference = the EMB edge (head_tok_ofs)
    head = {}
    for sg in ("tok_tx", "tok_rx"):
        for c, d in im[sg].items():
            head.setdefault(RES[c], []).append((o + d["occ"][0], o + d["occ"][1]))
    if pair:
        head.setdefault("kv.prog",[]).append((o,o+pair["program"]["embed"]["cycles"]))
        head.setdefault("emb.row",[]).append((o,o+pair["program"]["embed"]["cycles"]))
    p = dict(attn_extra=X, att_windows=att, seg_windows={"head": head}, **pair_price)
    # layer_block reserves att_windows at the actual attention offset; do not add them twice.
    cal = O.compile_frame(frame, p=p, starts=starts)
    return dict(S=S, txd=txd, segs=segs, law=law, im=im, X=X, p=p, cal=cal, head_ref=o)


def start_lists(b):
    """per calendar: [(frame time, seg, user)] over one frame (mod H)"""
    cal, im, H = b["cal"], b["im"], b["cal"]["H"]
    lists = {c: [] for c in CALS}
    for u, seq in cal["schedule"].items():
        for n, t0, blk in seq:
            w = blk["windows"]
            if "d2d_q" in w:                                  # a layer exchange: reference = the CMD send edge
                ref = t0 + w["d2d_q"][0][0]
                for sg, seg in (("req", 0), ("rsp", 0)):
                    for c, d in im[sg].items():
                        lists[c].append(((ref + d["start"]) % H, seg, u))
            if n == "head":
                ref = t0 + b["head_ref"]
                for sg in ("tok_tx", "tok_rx"):
                    for c, d in im[sg].items():
                        lists[c].append(((ref + d["start"]) % H, 1, u))
    for c in CALS:
        lists[c].sort()
    return lists


def encode(lists, H, mut=None):
    """ROM words per calendar: [31:12] dt, [11] go, [10] seg, [9:8] user, [7] wrap.  All four lists share one origin
    (the anchor): frame time 0 is D0 edges after the anchor go, D0 = in the largest circular gap of all starts."""
    allt = sorted({t for c in CALS for t, _, _ in lists[c]})
    gaps = [(allt[(i + 1) % len(allt)] - allt[i]) % H for i in range(len(allt))]
    i = max(range(len(gaps)), key=lambda k: gaps[k])
    mid = (allt[i] + gaps[i] // 2) % H                          # new frame origin (anchor + D0 = first frame start)
    D0 = 16
    words, meta = {}, {}
    for c in CALS:
        L_ = sorted((((t - mid) % H), s, u) for t, s, u in lists[c])
        L_ = [(t + D0, s, u) for t, s, u in L_]                 # times from the anchor go edge
        if mut and mut[0] == c:
            L_ = mut[1](L_)
        w, prev = [], 0
        for t, s, u in L_:
            dt = t - prev
            while dt >= (1 << DT_W):                            # NOP entries for long gaps
                w.append(((1 << DT_W) - 1) << 12)
                dt -= (1 << DT_W) - 1
            if dt < MIN_DT:
                raise ScheduleError(f"{c}: starts {dt} edges apart < {MIN_DT} (list player prefetch)")
            w.append((dt << 12) | (1 << 11) | (s << 10) | (u << 8))
            prev = t
        end = H                                                 # wrap NOP: entry 0 (dt from here) lands at its time + H
        dt = end - prev
        if dt < MIN_DT:
            raise ScheduleError(f"{c}: wrap {dt} < {MIN_DT}")
        while dt >= (1 << DT_W):
            w.append(((1 << DT_W) - 1) << 12)
            dt -= (1 << DT_W) - 1
        w.append((dt << 12) | (1 << 7))
        words[c] = w
        meta[c] = dict(starts=len(L_), words=len(w), first=L_[0][0], last=L_[-1][0])
    return words, dict(origin=mid, D0=D0, period=H, lists=meta)


def occupancy_check(lists, im, H):
    """independent check: per calendar, consecutive segments of the played list never overlap (start > previous last)"""
    seg_occ = {}
    for sg, d in im.items():
        for c, x in d.items():
            seg_occ.setdefault(c, {})[0 if sg in ("req", "rsp") else 1] = x["occ"][1] - x["occ"][0]
    bad = []
    for c in CALS:
        L_ = lists[c]
        for (t, s, u), (t2, s2, u2) in zip(L_, L_[1:] + [(L_[0][0] + H, L_[0][1], L_[0][2])]):
            if t + seg_occ[c][s] > t2:
                bad.append((c, t, s, u, t2, s2, u2))
    return bad


def mutate(kind, lists, im, H):
    """negative witnesses: collide = a C_rx response start inside the previous response; slot = one K_tx start one edge
    late; user = one K_rx start tagged with another user"""
    if kind == "collide":
        L_ = lists["C_rx"]
        i = next(k for k in range(1, len(L_)) if L_[k][1] == 0 and L_[k - 1][1] == 0)
        occ = im["rsp"]["C_rx"]["occ"]
        return ("C_rx", lambda X, i=i, d=(occ[1] - occ[0]) // 2: [x if j != i else (X[i - 1][0] + d, x[1], x[2])
                                                                    for j, x in enumerate(X)]), i
    if kind == "slot":
        return ("K_tx", lambda X: [x if j != 7 else (x[0] + 1, x[1], x[2]) for j, x in enumerate(X)]), 7
    if kind == "user":
        return ("K_rx", lambda X: [x if j != 9 else (x[0], x[1], (x[2] + 1) % 4) for j, x in enumerate(X)]), 9
    raise SystemExit(f"unknown mutant {kind}")


def single_playhead_rate(frame=16):
    """the as-built one-playhead reference (mu_d2d_overlap): the whole attention op exclusive on one link resource"""
    p = M._need(dict(M.SOURCED, users=O.NU, occupancy="measured", head_chunks=8))
    att = M.layer_block(p)["ops"]["attention"]
    return O.compile_frame(frame, p={"seg_windows": {"layer": {"d2dcal": [tuple(att)]}}})["aggregate_tok_s"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pair-calendar",type=Path,help="authoritative sole pairedcalendar; no legacy191/1777 guesses")
    ap.add_argument("--token-path",type=Path,default=Path(__file__).resolve().parents[2]/"results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/token_path_compiled.json.gz")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stages", default=STAGES)
    ap.add_argument("--frame", type=int, default=16)
    ap.add_argument("--kv-codec", type=int, choices=(1, 2), default=1, help="ATTN_LAND registered TX launch uses 2")
    ap.add_argument("--mut", choices=("collide", "slot", "user"))
    ap.add_argument("--kv-prog", action="store_true", help="also reserve the as-built KV programme busy window")
    a = ap.parse_args()
    b = build(a.stages, a.frame, kv_prog=a.kv_prog, kv_codec=a.kv_codec, pair_calendar=a.pair_calendar,token_path=a.token_path)
    cal, im, H = b["cal"], b["im"], b["cal"]["H"]
    lists = start_lists(b)
    bad = occupancy_check(lists, im, H)
    if bad:
        raise ScheduleError(f"link playhead collision in the compiled frame: {bad[:3]}")
    mut, mi = (mutate(a.mut, lists, im, H) if a.mut else (None, None))
    words, enc = encode(lists, H, mut)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    NE = L.NE
    imgs, bases = {}, {}
    for c in CALS:
        s0 = im["req" if c in ("C_tx", "K_rx") else "rsp"][c]["img"]
        s1 = im["tok_tx" if c in ("C_tx", "K_rx") else "tok_rx"][c]["img"]
        imgs[c], bases[c] = s0 + s1, len(s0)
        if len(imgs[c]) > NE:
            raise ScheduleError(f"{c}: {len(imgs[c])} entries > NE {NE}")
        (out / f"cal_{c}.memh").write_text("\n".join(f"{x:08x}" for x in imgs[c] + [0] * (NE - len(imgs[c]))) + "\n")
        (out / f"list_{c}.memh").write_text("\n".join(f"{x:08x}" for x in words[c]) + "\n")
    ex = {u: sum(1 for n, _, bb in seq if "d2d_q" in bb["windows"]) for u, seq in cal["schedule"].items()}
    tok = {u: sum(1 for n, _, _ in seq if n == "head") for u, seq in cal["schedule"].items()}
    P = dict(P_H=H, P_D0=enc["D0"], P_TXD_C=L.txdp_word(b["txd"]["C"]), P_TXD_K=L.txdp_word(b["txd"]["K"]),
             P_PHY=PHY + 2, P_NW_CTX=len(words["C_tx"]), P_NW_CRX=len(words["C_rx"]), P_NW_KTX=len(words["K_tx"]),
             P_NW_KRX=len(words["K_rx"]), P_SEG1_CTX=bases["C_tx"], P_SEG1_CRX=bases["C_rx"], P_SEG1_KTX=bases["K_tx"],
             P_SEG1_KRX=bases["K_rx"], P_EX0=ex[0], P_EX1=ex[1], P_EX2=ex[2], P_EX3=ex[3], P_TOK0=tok[0],
             P_TOK1=tok[1], P_TOK2=tok[2], P_TOK3=tok[3])
    with open(out / "ovl_img.svh", "w") as f:            # the sequencers' constant images (ot_qwen_d2d_ovl_seq)
        for c in CALS:
            v = imgs[c] + [0] * (NE - len(imgs[c]))
            f.write(f"localparam [32*{NE}-1:0] IMG_{c.upper()} = {32 * NE}'h" + "".join(f"{x:08x}" for x in reversed(v))
                    + ";\n")
            f.write(f"localparam [31:0] SEG1_{c.upper()} = 32'h{bases[c]:08x};\n")
    with open(out / "ovl_params.svh", "w") as f:
        for k, v in P.items():
            f.write(f"localparam integer {k} = {v};\n" if not k.startswith("P_TXD") else
                    f"localparam [31:0] {k} = 32'h{v:08x};\n")
    rec = dict(schema="opentallas.qwen.mu_d2d_ovl.v1", stages=a.stages, kv_codec=a.kv_codec, txd=b["txd"], frame_tokens=a.frame, H=H,
               mutant=a.mut, mutant_index=mi, kv_prog=a.kv_prog or bool(a.pair_calendar), pair_calendar=str(a.pair_calendar),pair_sha256=hashlib.sha256(a.pair_calendar.read_bytes()).hexdigest() if a.pair_calendar else None, kv_law=b["law"], attn_extra_X=b["X"],
               segments={sg: {c: dict(start=d["start"], occ=d["occ"], events=d["events"], entries=len(d["img"]))
                              for c, d in v.items()} for sg, v in im.items()},
               images={c: dict(entries=len(imgs[c]), seg1_base=bases[c]) for c in CALS}, encode=enc,
               exchanges_per_frame=ex, tokens_per_frame=tok,
               rate=dict(aggregate_tok_s=round(cal["aggregate_tok_s"], 1),
                         per_user=[round(u["tok_s"], 1) for u in cal["users"]],
                         single_playhead_tok_s=None if a.pair_calendar else round(single_playhead_rate(a.frame), 1)))
    (out / "frame_schedule.json").write_text(json.dumps(cal,indent=1)+"\n")
    (out / "ovl.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(H=H, X=b["X"], rate=rec["rate"], images=rec["images"], lists=enc["lists"],
                          tokens=tok, mutant=a.mut)))


if __name__ == "__main__":
    main()
