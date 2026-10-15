#!/usr/bin/env python3
"""Q-LINK 2026-10-15: compiler pass for the static Qwen D2D link (rtl/qwen_sys/d2d_static_20261015).

Input: one cross-die message list per calendar run (one decode layer) with each message's compiled SEND cycle relative to
the sending die's cal_start, its producer port, kind and beat; the fixed latencies of the implemented RTL (TXL: tx_slot
to PHY pin, PHY: FDI-to-far-FDI, OFS: receiver cal_start minus sender cal_start). Output: the four calendar images
(compute TX/RX, KV TX/RX; 32-b entries {dt14, last1, port3, kind4, beat5, 0}) and the expected event table.

Hard checks (fail closed): one TX frame per cycle per end; one RX arrival per cycle per end; per-end write-capture
cycles (send + TXD[port]) unique; dt in 1..16383; entries <= NE; every message has a receiver port.
No runtime arbitration exists to absorb a conflict: a conflicting program is rejected here.

Segments (RTL ot_qwen_d2d_cal start_seg): every message carries seg 0 (decode-layer run, one image replayed by each of
the 36 layer cal_starts) or seg 1 (token run: terminal RESULT C->S, then the embedding row S->C). Each image is segment 0
followed by segment 1; the segment-1 base is written at cfg_addr[5] = 1 (files cal_<end>_<dir>_seg1.memh). Entries are
bursts {dt14, last1, port3, kind4, beat5, rep5}: consecutive-cycle beats of one port/kind are one entry (NE 32).

--profile program: the full 36-layer decode-token program. Layer-relative send cycles come from the priced token path
(results/arch/token_path_20261009/qwen_rom.json, the KV-die variant: q / new K/V / attention output cross the link) --
CMD + 32 Q at the end of rmsnorm1 + qkv + qknorm_rope, 4 KVN after Q (codec 2 edges), the kind-15 status one cycle
after the last KVN capture; the 32 RESULT
beats + STATUS sent by the KV die so that the last arrives (codec out) by the end of attn_kv (softmax_norm 0). The
token run: kind-15 terminal RESULT at token-run cycle 2, the 64-word embedding row (kinds 6/7) sent so the last word is
out of the compute end by the priced embed window. The absolute table replays segment 0 at each priced layer start.
"""
import argparse, json, sys

NE = 32


def entry(dt, last, port, kind, beat, rep=0):
    assert 1 <= dt < (1 << 14), dt
    assert 0 <= port < 8 and 0 <= kind < 16 and 0 <= beat < 32 and 0 <= rep < 32 and beat + rep < 32
    return (dt << 18) | (last << 17) | (port << 14) | (kind << 10) | (beat << 5) | rep


def bursts(events):
    """merge consecutive-cycle events of one port/kind with beat + 1 into one entry (rep = extra events)"""
    out = []
    for c, p, k, b in events:
        if out:
            c0, p0, k0, b0, r0 = out[-1]
            if p == p0 and k == k0 and c == c0 + r0 + 1 and b == b0 + r0 + 1 and r0 < 31:
                out[-1] = (c0, p0, k0, b0, r0 + 1)
                continue
        out.append((c, p, k, b, 0))
    return out


def image(events):
    """events: sorted list of (cycle, port, kind, beat), cycle >= 1 relative to cal_start."""
    out, prev = [], 0
    bs = bursts(events)
    for i, (c, p, k, b, r) in enumerate(bs):
        out.append(entry(c - prev, int(i == len(bs) - 1), p, k, b, r))
        prev = c + r
    if len(out) > NE:
        raise SystemExit(f"calendar has {len(out)} entries > NE {NE}")
    return out


def bench_layer():
    """Bench layer profile (native typed548, LINK.md section 3 counts): C->S CMD + 32 Q beats + 1 kind-15 status;
    S->C 32 RESULT beats + 1 STATUS."""
    m = []
    m.append(dict(src="C", cyc=2, tx_port=0, rx_port=0, kind=1, beat=0))
    for b in range(32):
        m.append(dict(src="C", cyc=3 + b, tx_port=0, rx_port=0, kind=2, beat=b))
    m.append(dict(src="C", cyc=40, tx_port=2, rx_port=2, kind=15, beat=0))
    for b in range(32):
        m.append(dict(src="K", cyc=50 + b, tx_port=0, rx_port=0, kind=3, beat=b))
    m.append(dict(src="K", cyc=83, tx_port=0, rx_port=0, kind=4, beat=0))
    return m


def dies_layer():
    """Die-wrapper profile: bench layer + 4 KVN words (port 3, kind 5, codec 2 edges) per layer."""
    m = bench_layer()
    for i in range(4):
        m.append(dict(src="C", cyc=42 + i, tx_port=3, rx_port=3, kind=5, beat=i))
    return m


def token_run():
    """Segment 1: terminal RESULT (kind 15) C->S at cycle 2 (it carries the token id to the HOST / embedding provider),
    then the 64-word embedding row S->C: kind 6 beats 0..31 = row words 0..31, kind 7 beats 0..31 = words 32..63."""
    m = [dict(seg=1, src="C", cyc=2, tx_port=2, rx_port=2, kind=15, beat=0)]
    for w in range(64):
        m.append(dict(seg=1, src="K", cyc=EMB_SEND + w, tx_port=2, rx_port=2, kind=6 + w // 32, beat=w % 32))
    return m


EMB_SEND = 20   # bench token run: provider row staged (one ready per buffer block at the HBM boundary) by cycle 19


def layer_msgs(seg, base, w, txl, phy):
    """one decode layer's link messages at layer offset base; w = op windows (rmsnorm1, qkv, qknorm_rope, attn_kv)"""
    q0 = base + int(sum(w[:3]))
    a_end = q0 + int(w[3])
    m = [dict(seg=seg, src="C", cyc=q0, tx_port=0, rx_port=0, kind=1, beat=0)]
    m += [dict(seg=seg, src="C", cyc=q0 + 1 + b, tx_port=0, rx_port=0, kind=2, beat=b) for b in range(32)]
    m += [dict(seg=seg, src="C", cyc=q0 + 33 + i, tx_port=3, rx_port=3, kind=5, beat=i) for i in range(4)]
    m.append(dict(seg=seg, src="C", cyc=q0 + 38, tx_port=2, rx_port=2, kind=15, beat=0))
    # RESULT: the last beat (STATUS) out of the compute end (arrive + 2 + codec 1) at a_end
    r_last = a_end - (txl + phy + 3)
    r0 = r_last - 33
    m += [dict(seg=seg, src="K", cyc=r0 + b, tx_port=0, rx_port=0, kind=3, beat=b) for b in range(32)]
    m.append(dict(seg=seg, src="K", cyc=r_last, tx_port=0, rx_port=0, kind=4, beat=0))
    return m, dict(q_send=q0, attn_end=a_end, result_send=[r0, r_last])


def program_profile(txl, phy, tp_path, emb_window=None, host_stages=None):
    """Full 36-layer decode-token program from the priced token path (layer-relative op windows).
    Segment 0 = L1..L35 (identical windows: the KV fill of layer n+1 is hidden behind layer n); segment 1 = the token
    run = terminal RESULT + embedding row + L0 (its KV fill is exposed: attn_kv 2,038 vs 1,816 cycles)."""
    if host_stages is not None and (type(host_stages) is not int or host_stages < 0):
        raise ValueError("host_stages must be a measured nonnegative integer or None (pending)")
    d = json.load(open(tp_path))
    nodes = {n["id"]: n for n in d["nodes"]}
    groups = [g for g in d["groups"] if g["kind"] == "layer"]
    lay = [g["id"] for g in groups]
    assert len(lay) == 36, len(lay)
    ops = ("rmsnorm1", "qkv", "qknorm_rope", "attn_kv")
    win = {L: [nodes[f"{L}.{o}"]["cycles"] for o in ops] for L in lay}
    if not all(win[L] == win[lay[1]] for L in lay[2:]):
        raise SystemExit("L1..L35 op windows differ: one replayed segment-0 image cannot serve them")
    m0, l1 = layer_msgs(0, 0, win[lay[1]], txl, phy)
    emb = int(nodes["embed"]["cycles"]) if emb_window is None else emb_window
    l0_start = int(groups[0]["start"])
    e_last = emb - (txl + phy + 2)
    m1 = [dict(seg=1, src="C", cyc=2, tx_port=2, rx_port=2, kind=15, beat=0)]
    m1 += [dict(seg=1, src="K", cyc=e_last - 63 + w, tx_port=2, rx_port=2, kind=6 + w // 32, beat=w % 32) for w in range(64)]
    ml0, l0 = layer_msgs(1, l0_start, win[lay[0]], txl, phy)
    layout = dict(source=tp_path, layers=[dict(id=g["id"], start=int(g["start"]), cycles=int(g["cycles"])) for g in groups],
                  embed=dict(start=0, cycles=emb), windows=dict(L0=dict(zip(ops, map(int, win[lay[0]]))),
                  L1_35=dict(zip(ops, map(int, win[lay[1]])))), layer=l1, token_run_L0=l0,
                  emb_send=[e_last - 63, e_last],
                  host_relay_stages=dict(value=host_stages, status="measured (KV die lead)" if host_stages is not None else
                      "PENDING: KV die lead re-measure after the HOST core moves next to the D2D end (coordinator: the "
                      "54-57-stage HOST<->D2D relay figure is a floorplan defect, not a calendar input); compiled with 0"),
                  hbm_embedding_budget=dict(result_at_kv_host=2 + 1 + txl + phy + 2 + 1 + (host_stages or 0),
                      first_emb_send=e_last - 63,
                      note="the KV-die embedding provider must hold the staged row (one ready per buffer block at the HBM "
                           "boundary) by first_emb_send; a late row is a schedule fault, never a stretched timeline"))
    return m0 + m1 + ml0, layout


def compile_cal(msgs, txl, phy, ofs, txd):
    """txd: {'C': [..], 'K': [..]} per-end producer codec latency; txl = slot-to-pin latency at codec latency 1."""
    segs = sorted({m.get("seg", 0) for m in msgs})
    assert set(segs) <= {0, 1}, segs
    out_imgs, out_tab, base = {}, [], {}
    for sg in (0, 1):
        sm = [m for m in msgs if m.get("seg", 0) == sg]
        if not sm:
            continue
        imgs, tab = compile_seg(sm, txl, phy, ofs, txd)
        for k, v in imgs.items():
            if sg == 1:
                base[k] = len(out_imgs.get(k, []))
            out_imgs[k] = out_imgs.get(k, []) + v
            if len(out_imgs[k]) > NE:
                raise SystemExit(f"{k}: {len(out_imgs[k])} entries > NE {NE}")
        out_tab += [dict(t, seg=sg) for t in tab]
    if 1 in segs and set(base) != set(out_imgs):
        raise SystemExit(f"segment 1 must reserve every calendar (an empty segment cannot start): {sorted(base)}")
    return out_imgs, out_tab, base


def compile_seg(msgs, txl, phy, ofs, txd):
    ends = {"C": dict(tx=[], rx=[]), "K": dict(tx=[], rx=[])}
    table = []
    for m in msgs:
        s, r = m["src"], "K" if m["src"] == "C" else "C"
        # receiver-relative arrival cycle at the PHY pins; receiver cal_start is OFS later on the K die (OFS<0: earlier)
        arr = m["cyc"] + txd[s][m["tx_port"]] - 1 + txl + phy - (ofs if r == "K" else -ofs)
        if arr < 1:
            raise SystemExit(f"arrival before receiver start: {m}")
        ends[s]["tx"].append((m["cyc"], m["tx_port"], m["kind"], m["beat"]))
        ends[r]["rx"].append((arr, m["rx_port"], m["kind"], m["beat"]))
        table.append(dict(m, arrive=arr, rx_out=arr + 2, wr=m["cyc"] + txd[s][m["tx_port"]]))
    for e, d in ends.items():
        for k in ("tx", "rx"):
            d[k].sort()
            cyc = [x[0] for x in d[k]]
            if len(set(cyc)) != len(cyc):
                raise SystemExit(f"{e} {k}: two frames in one cycle")
        wr = sorted(t["wr"] for t in table if t["src"] == e)
        if len(set(wr)) != len(wr):
            raise SystemExit(f"{e}: two write captures in one cycle (TXD collision)")
    imgs = {f"{e}_{k}": image(d[k]) for e, d in ends.items() for k in ("tx", "rx") if d[k]}
    return imgs, table


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--txl", type=int, required=True)
    ap.add_argument("--phy", type=int, default=5)
    ap.add_argument("--ofs", type=int, default=0)
    ap.add_argument("--txd-c", default="1,1,1,1", help="compute end codec latency per TX port")
    ap.add_argument("--txd-k", default="1,1,1,1", help="KV end codec latency per TX port")
    ap.add_argument("--spec", help="message list JSON (default: bench layer profile)")
    ap.add_argument("--profile", default="bench", choices=["bench", "dies", "dies_token", "program"])
    ap.add_argument("--token-path", default="results/arch/token_path_20261009/qwen_rom.json")
    ap.add_argument("--host-stages", type=int, default=None,
                    help="KV die HOST core <-> qkd_d2d_static relay stages (each way), from the KV die lead's measured "
                         "die plan; added to the KV HOST-record TX codec latency (port 1) and the token-id budget")
    a = ap.parse_args()
    txd = {"C": [int(x) for x in a.txd_c.split(",")], "K": [int(x) for x in a.txd_k.split(",")]}
    layout = None
    if a.spec:
        msgs = json.load(open(a.spec))
    elif a.profile == "program":
        msgs, layout = program_profile(a.txl, a.phy, a.token_path, host_stages=a.host_stages)
        if a.host_stages:
            txd["K"][1] += a.host_stages   # HOST record words reach the end's capture edge host_stages later
    elif a.profile == "dies_token":
        msgs = dies_layer() + token_run()
    else:
        msgs = dies_layer() if a.profile == "dies" else bench_layer()
    imgs, table, base = compile_cal(msgs, a.txl, a.phy, a.ofs, txd)
    import os
    os.makedirs(a.out, exist_ok=True)
    for k, v in imgs.items():
        with open(f"{a.out}/cal_{k}.memh", "w") as f:
            f.write("\n".join(f"{x:08x}" for x in v + [0] * (NE - len(v))) + "\n")
        with open(f"{a.out}/cal_{k}_seg1.memh", "w") as f:
            f.write(f"{base.get(k, 0):08x}\n")
    spans = {sg: max(max(t["rx_out"], t["cyc"]) for t in table if t["seg"] == sg) for sg in {t["seg"] for t in table}}
    rec = dict(txl=a.txl, phy=a.phy, ofs=a.ofs, txd=txd, entries={k: len(v) for k, v in imgs.items()},
               seg1_base=base, span=spans.get(0, 0), spans=spans, messages=table)
    if layout:
        # absolute program: segment 0 replayed at every priced layer start, segment 1 at token start (cycle 0)
        L = layout["layers"]
        over = [l["id"] for l in L if spans[0] >= l["cycles"]]
        if over:
            raise SystemExit(f"layer run longer than its layer window: {over}")
        # a calendar is busy until its last event (TX slot / RX expectation), then a new cal_start is legal
        busy = {sg: max(max(t["arrive"], t["cyc"]) for t in table if t["seg"] == sg) for sg in spans}
        if busy[1] >= L[1]["start"] or busy[0] >= min(l["cycles"] for l in L[1:]):
            raise SystemExit(f"run overlap: token run (embed + L0) busy to {busy[1]} vs L1 start {L[1]['start']}, layer run busy {busy[0]}")
        layout["cal_busy"] = busy
        frames = {"C": 0, "K": 0}
        for t in table:
            frames[t["src"]] += 35 if t["seg"] == 0 else 1
        tok_cyc = L[-1]["start"] + L[-1]["cycles"]
        layout.update(token_frames=frames, layer_run_span=spans[0], token_run_span=spans[1],
                      cal_starts=[dict(seg=1, cycle=0, run="token: RESULT + embedding + L0")] +
                                 [dict(seg=0, cycle=l["start"], layer=l["id"]) for l in L[1:]],
                      link_occupancy={e: round(n / tok_cyc, 5) for e, n in frames.items()}, token_cycles_through_L35=tok_cyc)
        rec["program"] = layout
    json.dump(rec, open(f"{a.out}/calendar.json", "w"), indent=1)
    print(json.dumps(dict(entries=rec["entries"], seg1_base=base, spans=spans,
                          **({"program": {k: layout[k] for k in ("layer", "token_run_L0", "emb_send", "hbm_embedding_budget", "token_frames", "link_occupancy", "cal_busy")}} if layout else {}))))


if __name__ == "__main__":
    sys.exit(main())
