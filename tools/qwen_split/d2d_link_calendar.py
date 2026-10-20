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


def layer_msgs(seg, base, w, txl, phy, st_ofs=38, status_delay=0):
    """one decode layer's link messages at layer offset base; w = op windows (rmsnorm1, qkv, qknorm_rope, attn_kv)"""
    if type(status_delay) is not int or status_delay < 0:
        raise ValueError("status_delay must be a nonnegative static edge count")
    q0 = base + int(sum(w[:3]))
    a_end = q0 + int(w[3])
    m = [dict(seg=seg, src="C", cyc=q0, tx_port=0, rx_port=0, kind=1, beat=0)]
    m += [dict(seg=seg, src="C", cyc=q0 + 1 + b, tx_port=0, rx_port=0, kind=2, beat=b) for b in range(32)]
    m += [dict(seg=seg, src="C", cyc=q0 + 33 + i, tx_port=3, rx_port=3, kind=5, beat=i) for i in range(4)]
    m.append(dict(seg=seg, src="C", cyc=q0 + st_ofs, tx_port=2, rx_port=2, kind=15, beat=0))
    # RESULT: the last beat (STATUS) out of the compute end (arrive + 2 + codec 1) at a_end
    r_last = a_end - (txl + phy + 3)
    r0 = r_last - 33
    m += [dict(seg=seg, src="K", cyc=r0 + b, tx_port=0, rx_port=0, kind=3, beat=b) for b in range(32)]
    m.append(dict(seg=seg, src="K", cyc=r_last + status_delay, tx_port=0, rx_port=0, kind=4, beat=0))
    return m, dict(q_send=q0, attn_end=a_end + status_delay, result_send=[r0, r_last + status_delay],
                  retirement_status_delay=status_delay)


def handoff_windows(path):
    """Q-ATTN result-serializer decision (results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json):
    per token-path op, the measured end-beat landing of its LAST result burst on the VM result face, in edges after the
    op's ME go edge. A link message that reads the op's result is legal only from the edge after that landing (VM write
    visibility +1); the compiler places Q/KVN no earlier. Returns {token_path_op: (last_landing+1, pc)}."""
    d = json.load(open(path))
    ops = d["link_handoff"]["ops"]
    out = {}
    for p in d["per_op"]:
        op, pc = p.get("token_path_op"), p["pc"]
        if op and pc in ops:
            out[op] = (int(max(ops[pc]["end_beat_landing_after_go"])) + 1, pc)
    return out


PREC_K0 = 3   # first S->C program-record slot of the token / admission run (run cycle)
ADM_REPLAY = 1056   # admission: AUTH accepted -> 1,032-word replay + ledger commit (~1,045, Q-NETLIST) + margin


def context_slot(txl, phy, host_stages, host_req):
    """KV-DCAL2 10-19 (KV-EMB2 d9631325d): the token-run kind-12 CONTEXT slot carries step n+1's owner/token; for a
    generated token that token IS RESULT(n), so the slot is legal only once the KV HOST holds the step n+1 request:
    RESULT(n) at the KV HOST (send 2 + codec 1 + txl + phy + rx 2 + 1 + host stages) + host_req (the HOST's measured
    RESULT -> context-record latency).  Prompt tokens are ready earlier; one static slot serves both.  host_req None =
    the pre-EMB2 slot PREC_K0 (images unchanged)."""
    if host_req is None:
        return PREC_K0, None
    if type(host_req) is not int or host_req < 0:
        raise ValueError("host_req must be a measured nonnegative integer")
    r_host = 2 + 1 + txl + phy + 2 + 1 + (host_stages or 0)
    return max(PREC_K0, r_host + host_req), r_host


def program_profile(txl, phy, tp_path, emb_window=None, host_stages=None, st_ofs=38, handoff=None, mu=False,
                    host_req=None, emb_fill=None, status_delay=0):
    """Full 36-layer decode-token program from the priced token path (layer-relative op windows).
    Segment 0 = L1..L35 (identical windows: the KV fill of layer n+1 is hidden behind layer n); segment 1 = the token
    run = terminal RESULT + embedding row + L0 (its KV fill is exposed: attn_kv 2,038 vs 1,816 cycles).
    handoff (--link-handoff): the qkv window becomes max(priced, measured last result landing + 1) so Q/KVN are sent only
    after the actual producer's last qkv row is visible in the VM (no ready/credit: a late row is a schedule fault)."""
    if host_stages is not None and (type(host_stages) is not int or host_stages < 0):
        raise ValueError("host_stages must be a measured nonnegative integer or None (pending)")
    d = json.load(open(tp_path))
    nodes = {n["id"]: n for n in d["nodes"]}
    groups = [g for g in d["groups"] if g["kind"] == "layer"]
    lay = [g["id"] for g in groups]
    assert len(lay) == 36, len(lay)
    ops = ("rmsnorm1", "qkv", "qknorm_rope", "attn_kv")
    win = {L: [nodes[f"{L}.{o}"]["cycles"] for o in ops] for L in lay}
    hw = handoff_windows(handoff) if handoff else {}
    priced_qkv = {L: win[L][1] for L in lay}
    if "qkv" in hw:
        for L in lay:
            win[L][1] = max(win[L][1], hw["qkv"][0])
    if not all(win[L] == win[lay[1]] for L in lay[2:]):
        raise SystemExit("L1..L35 op windows differ: one replayed segment-0 image cannot serve them")
    m0, l1 = layer_msgs(0, 0, win[lay[1]], txl, phy, st_ofs, status_delay)
    emb = int(nodes["embed"]["cycles"]) if emb_window is None else emb_window
    l0_start = int(groups[0]["start"])
    e_last = emb - (txl + phy + 2)
    m1 = [dict(seg=1, src="C", cyc=2, tx_port=2, rx_port=2, kind=15, beat=0)]
    # kind-8 row header (Q-NETLIST qfd_sys_face record layout, 2026-10-16) one edge before word 0: 65 port-2 records
    m1.append(dict(seg=1, src="K", cyc=e_last - 64, tx_port=2, rx_port=2, kind=8, beat=0))
    m1 += [dict(seg=1, src="K", cyc=e_last - 63 + w, tx_port=2, rx_port=2, kind=6 + w // 32, beat=w % 32) for w in range(64)]
    # program-record slots (port 1, every token run; a slot without a HOST / face record carries observed = 0):
    # S->C kind 13 beat 1 BEGIN, kind 13 beat 2 AUTH, kind 12 CONTEXT; C->S kind 14 WITNESS after the context is out
    # of the compute RX (arrival + 2) plus 2 face edges, with slack for the pin registers
    # token run: S->C kind 12 CONTEXT (token / position for the face) and C->S kind 14 beat 0 per-token WITNESS
    # (ready / digest or not-ready: always a record)
    ctx_k, r_host = context_slot(txl, phy, host_stages, host_req)
    hdr = e_last - 64
    ctx_budget = hdr - ctx_k     # edges from the CONTEXT slot to the row-header slot (EMB2 fill: fork + 2 + join last + 1)
    if emb_fill is not None and ctx_budget < emb_fill:
        raise SystemExit(f"embedding fill budget {ctx_budget} edges (CONTEXT slot {ctx_k} -> header slot {hdr}) < required "
                         f"{emb_fill} (fork + 2 + join last + 1): lengthen the embed window by {emb_fill - ctx_budget}")
    m1.append(dict(seg=1, src="K", cyc=ctx_k, tx_port=1, rx_port=1, kind=12, beat=0))
    if mu:
        # MU-KV-CTX 10-19 (coordinator 0kg, --mu; Qwen ROM 4 users): the MU CONTEXT slot, S->C kind 12 beat 1 ONE cycle
        # before the existing kind-12 slot.  The KV host record port (qkd_host_record_port_mu MU 1) fills it with one
        # filler's initial context (or a user-0 copy); the compute face's own kind-12 RX accepts it and the existing slot
        # one edge later restores user 0's context; qfd_mu_ctx_rx loads users 1..3 into the ctlm boot-context loader.
        # Field spec: results/rtl/mu_qwen_1018/kvctx/README.md section 2.  (= mu-die-qw2 05a8c8fe3; KV-LINKCFG-MU 10-19)
        m1.append(dict(seg=1, src="K", cyc=ctx_k - 1, tx_port=1, rx_port=1, kind=12, beat=1))
    prec_w = ctx_k + txl + phy + 12
    m1.append(dict(seg=1, src="C", cyc=prec_w, tx_port=1, rx_port=1, kind=14, beat=0))
    # ADMISSION run (segment 2; once per epoch, before the first token; Q-NETLIST 2026-10-16): S->C kind 13 beat 1
    # BEGIN, beat 2 AUTH; the compute face replays the 1,032-word program from one edge after AUTH and commits its
    # ledgers ~1,040 edges later, so the C->S kind 14 beat 1 admission WITNESS leaves AUTH arrival + ADM_REPLAY edges
    m2 = [dict(seg=2, src="K", cyc=PREC_K0 + i, tx_port=1, rx_port=1, kind=13, beat=1 + i) for i in range(2)]
    adm_w = PREC_K0 + 1 + txl + phy + 4 + ADM_REPLAY
    m2.append(dict(seg=2, src="C", cyc=adm_w, tx_port=1, rx_port=1, kind=14, beat=1))
    ml0, l0 = layer_msgs(1, l0_start, win[lay[0]], txl, phy, st_ofs, status_delay)
    layout = dict(source=tp_path, layers=[dict(id=g["id"], start=int(g["start"]) + i * status_delay, cycles=int(g["cycles"]) + status_delay) for i, g in enumerate(groups)],
                  embed=dict(start=0, cycles=emb), windows=dict(L0=dict(zip(ops, [int(n) + (status_delay if i == 3 else 0) for i, n in enumerate(win[lay[0]])])),
                  L1_35=dict(zip(ops, [int(n) + (status_delay if i == 3 else 0) for i, n in enumerate(win[lay[1]])]))), layer=l1, token_run_L0=l0,
                  emb_send=[e_last - 63, e_last], emb_header_send=e_last - 64,
                  program_records=dict(k_send=[ctx_k, ctx_k], kinds="token run: 12 CONTEXT S->C, 14/0 WITNESS C->S",
                                       witness_send=prec_w,
                                       context_after_result=(None if host_req is None else dict(
                                           result_at_kv_host=r_host, host_req=host_req, context_send=ctx_k,
                                           moved_by=ctx_k - PREC_K0, header_send=hdr, fill_budget_edges=ctx_budget,
                                           fill_required_edges=emb_fill,
                                           note="KV-EMB2: kvs_emb starts the row fill from this record (fork + 2 edges); "
                                                "the budget must cover join last + 1, else the embed window grows"))),
                  admission=dict(k_send=[PREC_K0, PREC_K0 + 1], kinds="13/1 BEGIN, 13/2 AUTH S->C; 14/1 WITNESS C->S",
                                 witness_send=adm_w, replay_edges=ADM_REPLAY),
                  token_period=int(d["totals"]["cycles"]) + 36 * status_delay,
                  retirement=dict(status_delay=status_delay, token_added_edges=36 * status_delay,
                                  qualification="UNQUALIFIED: requires full source deadline/path/reset proof"),
                  result_handoff=(dict(source=handoff, op="qkv", pc=hw["qkv"][1], visible_after_go=hw["qkv"][0],
                                       priced_qkv=int(priced_qkv[lay[1]]), qkv_window=int(win[lay[1]][1]),
                                       q_send_shift=int(win[lay[1]][1] - priced_qkv[lay[1]]),
                                       note="the shift is the VM result-face cost (Q-ATTN ledger), not a link cost")
                                  if "qkv" in hw else None),
                  host_relay_stages=dict(value=host_stages, status="measured (KV die lead)" if host_stages is not None else
                      "PENDING: KV die lead re-measure after the HOST core moves next to the D2D end (coordinator: the "
                      "54-57-stage HOST<->D2D relay figure is a floorplan defect, not a calendar input); compiled with 0"),
                  hbm_embedding_budget=dict(result_at_kv_host=2 + 1 + txl + phy + 2 + 1 + (host_stages or 0),
                      first_emb_send=e_last - 63,
                      note="the KV-die embedding provider must hold the staged row (one ready per buffer block at the HBM "
                           "boundary) by first_emb_send; a late row is a schedule fault, never a stretched timeline"))
    return m0 + m1 + ml0 + m2, layout


# ---------------------------------------------------------------------------------------------------------------------
# QXF-LINK 2026-10-18 (TOKEN-XDIE-QWEN F4): the die masters' TXDP parameter is a COMPILER output.  Producer capture latency
# per TX port = the producer's own codec edges + the die seam stages between the master and the producer (slot out and
# record back) + the PR = 1 pin flops (PINREG_EXT).  Producers (current die RTL):
#   C0 native59 CMD/Q: CS_TXS + N59_TX + SC_TX | C1 program record witness: 1 | C2 STATUS (inside the core): 1
#   C3 KVN: CS_X3S + N59_X3 + kvn_tx 1 + SC_X3 | K0 attention programme RESULT/STATUS: KS_TXS + KV_CODEC + SK_TXP
#   K1 HOST record port: 2 (+ host stages) | K2 embedding provider: 1 | K3 (unused): 1
# STAGE_NAMES: the seam bundles' compiled ages (every member of a bundle lands on one age; F5 / F6).
STAGE_NAMES = ('CS_TXS', 'CS_RXV', 'CS_RXP', 'CS_X3S', 'SC_TX', 'SC_X3', 'KS_RXV', 'KS_RXP', 'KS_TXS', 'KS_TXK', 'KS_TXB',
               'SK_TXV', 'SK_TXP')
N59_TX, N59_X3, KV_CODEC = 2, 2, 1
PINREG_EXT = {"C": [2, 2, 0, 2], "K": [2, 2, 2, 2]}


def parse_stages(s):
    """'CS_TXS,CS_RXV,CS_RXP,CS_X3S,SC_TX,SC_X3/KS_RXV,KS_RXP,KS_TXS,KS_TXK,KS_TXB,SK_TXV,SK_TXP' -> dict"""
    cs, ks = s.split("/")
    v = [int(x) for x in cs.split(",")] + [int(x) for x in ks.split(",")]
    if len(v) != len(STAGE_NAMES) or min(v) < 0:
        raise SystemExit(f"--die-stages needs {len(STAGE_NAMES)} nonnegative stage counts: {s}")
    return dict(zip(STAGE_NAMES, v))


def producer_txd_c(S):
    """Compute-die producer edges, independent of the KV die's codec."""
    return [S["CS_TXS"] + N59_TX + S["SC_TX"], 1, 1,
            S["CS_X3S"] + N59_X3 + 1 + S["SC_X3"]]


def producer_txd(S, host_stages=0, kv_codec=None):
    """raw producer latency per TX port (before the PR pin flops) from the die seam stages S.  kv_codec = the attention
    programme's codec edges as instantiated (HKV-DIE 10-19: OT_KV_ATTN_LAND / .LAND(1) -> 2); never silently 1."""
    if kv_codec is None:
        raise SystemExit("producer_txd: kv_codec required (layer_compile.kv_codec_edges of the KV die's qkd_kvs_attn)")
    return {"C": producer_txd_c(S),
            "K": [S["KS_TXS"] + kv_codec + S["SK_TXP"], 2 + host_stages, 1, 1]}


def txdp_word(v):
    """per-port list (port 0 first) -> the 32-b TXDP parameter (byte p = port p)"""
    assert len(v) == 4 and all(1 <= x < 256 for x in v), v
    return sum(x << (8 * p) for p, x in enumerate(v))


def txdp_svh(txd, note):
    return (f"// GENERATED by tools/qwen_split/d2d_link_calendar.py ({note}): D2D die-master TXDP parameter (byte p = port p)\n"
            f"localparam [31:0] QFD_D2D_TXDP = 32'h{txdp_word(txd['C']):08x};   // compute {txd['C']}\n"
            f"localparam [31:0] QKD_D2D_TXDP = 32'h{txdp_word(txd['K']):08x};   // KV {txd['K']}\n")


def compile_cal(msgs, txl, phy, ofs, txd):
    """txd: {'C': [..], 'K': [..]} per-end producer codec latency; txl = slot-to-pin latency at codec latency 1."""
    segs = sorted({m.get("seg", 0) for m in msgs})
    assert set(segs) <= {0, 1, 2}, segs
    out_imgs, out_tab, base, base2 = {}, [], {}, {}
    for sg in (0, 1, 2):
        sm = [m for m in msgs if m.get("seg", 0) == sg]
        if not sm:
            continue
        imgs, tab = compile_seg(sm, txl, phy, ofs, txd)
        for k, v in imgs.items():
            if sg == 1:
                base[k] = len(out_imgs.get(k, []))
            if sg == 2:
                base2[k] = len(out_imgs.get(k, []))
            out_imgs[k] = out_imgs.get(k, []) + v
            if len(out_imgs[k]) > NE:
                raise SystemExit(f"{k}: {len(out_imgs[k])} entries > NE {NE}")
        out_tab += [dict(t, seg=sg) for t in tab]
    if 1 in segs and set(base) != set(out_imgs):
        raise SystemExit(f"segment 1 must reserve every calendar (an empty segment cannot start): {sorted(base)}")
    if 2 in segs and set(base2) != set(out_imgs):
        raise SystemExit(f"the admission segment must reserve every calendar: {sorted(base2)}")
    return out_imgs, out_tab, (base, base2)


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
    ap.add_argument("--pinreg", action="store_true",
                    help="pin-registered die masters (PR=1, d2d_pinreg_gen.py): PHY hop +2 (TX + far RX pin flops), producer "
                         "capture +2 (slot out + payload in), consumer outputs +1; production default for the r4 masters")
    ap.add_argument("--link-handoff", default=None,
                    help="Q-ATTN result-serializer decision.json (link_handoff + per_op): Q/KVN sends wait for the measured last "
                         "qkv result landing (+1 visibility) instead of the priced qkv window")
    ap.add_argument("--period-align", type=int, default=768,
                    help="program profile: pad the token period up to a multiple of this many core edges (default 768, "
                         "coordinator 10-17 KVJ-E2: 768 core edges = 625 HBM beats, so every token run starts at one HBM-beat "
                         "phase and the KV die's compiled core->HBM phase launches hold for every token); 1 = no padding")
    ap.add_argument("--kv-codec", type=int, default=None,
                    help="with --die-stages: KV attention codec edges as instantiated (1 as-built, 2 with .LAND(1)); required")
    ap.add_argument("--die-stages", default=None,
                    help="die seam stages " + ",".join(STAGE_NAMES[:6]) + "/" + ",".join(STAGE_NAMES[6:]) + ": the producer "
                         "TXD per port is derived from them (overrides --txd-c / --txd-k; QXF-LINK F4)")
    ap.add_argument("--allow-unmeasured-host", action="store_true",
                    help="diagnostic program images only: retain PENDING HOST stages and compile with zero; never production-qualified")
    ap.add_argument("--ctx-host-req", type=int, default=None,
                    help="KV-DCAL2/KV-EMB2 10-19: place the token-run kind-12 CONTEXT slot after RESULT(n) reaches the KV HOST "
                         "plus this measured HOST request latency (edges); default off = the PREC_K0 slot (images unchanged)")
    ap.add_argument("--emb-fill-edges", type=int, default=None,
                    help="with --ctx-host-req: required CONTEXT->header edges (die fork ages + 2 + join4_cal last + 1); "
                         "fail closed when the slot leaves less")
    ap.add_argument("--mu", action="store_true",
                    help="MU-KV-CTX 10-19 (Qwen ROM 4 users): add the token run's MU context slot (S->C kind 12 beat 1, one "
                         "cycle before the existing kind-12 slot); default off = the single-user images, unchanged")
    ap.add_argument("--status-delay", type=int, default=0, help="opt-in static STATUS-only tail per layer; priced in every layer/token window; requires retirement proof")
    a = ap.parse_args()
    if a.status_delay < 0 or (a.status_delay and a.profile != "program"):
        ap.error("--status-delay requires program profile and nonnegative edges")
    if a.profile == "program" and a.host_stages is None and not a.allow_unmeasured_host:
        ap.error("program calendar requires --host-stages from the measured KV die plan; use --allow-unmeasured-host only for diagnostics")
    txd = {"C": [int(x) for x in a.txd_c.split(",")], "K": [int(x) for x in a.txd_k.split(",")]}
    stages = parse_stages(a.die_stages) if a.die_stages else None
    if stages:
        txd = producer_txd(stages, kv_codec=a.kv_codec)    # host stages are added below, as for --txd-k
    phy_c, txl_p, phy_p = a.phy, a.txl, a.phy
    if a.pinreg:
        # +2 on ports whose codec is OUTSIDE the die master (slot pin flop + payload pin flop); the compute STATUS
        # codec (port 2) sits inside qfd_d2d_static_core and keeps its latency
        ext = {"C": [2, 2, 0, 2], "K": [2, 2, 2, 2]}
        txd = {k: [x + e for x, e in zip(v, ext[k])] for k, v in txd.items()}
        phy_c = a.phy + 2                      # compiled pin-to-pin: TX pin flop + far RX pin flop
        txl_p, phy_p = a.txl + 2, a.phy + 2    # message placement: slot->codec-out budget grows by 4 (see docstring)
    layout = None
    if a.spec:
        msgs = json.load(open(a.spec))
    elif a.profile == "program":
        msgs, layout = program_profile(txl_p, phy_p, a.token_path, host_stages=a.host_stages,
                                        st_ofs=40 if a.pinreg else 38, handoff=a.link_handoff, mu=a.mu,
                                        host_req=a.ctx_host_req, emb_fill=a.emb_fill_edges,
                                        status_delay=a.status_delay)   # STATUS capture after the (+2) KVN captures
        if a.host_stages:
            txd["K"][1] += a.host_stages   # HOST record words reach the end's capture edge host_stages later
    elif a.profile == "dies_token":
        msgs = dies_layer() + token_run()
    else:
        msgs = dies_layer() if a.profile == "dies" else bench_layer()
    imgs, table, (base, base2) = compile_cal(msgs, a.txl, phy_c, a.ofs, txd)
    import os
    os.makedirs(a.out, exist_ok=True)
    for k, v in imgs.items():
        with open(f"{a.out}/cal_{k}.memh", "w") as f:
            f.write("\n".join(f"{x:08x}" for x in v + [0] * (NE - len(v))) + "\n")
        with open(f"{a.out}/cal_{k}_seg1.memh", "w") as f:
            f.write(f"{base.get(k, 0):08x}\n")
        if base2:
            with open(f"{a.out}/cal_{k}_seg2.memh", "w") as f:
                f.write(f"{base2.get(k, 0):08x}\n")
    spans = {sg: max(max(t["rx_out"], t["cyc"]) for t in table if t["seg"] == sg) for sg in {t["seg"] for t in table}}
    rec = dict(txl=a.txl, phy=a.phy, phy_compiled=phy_c, pinreg=a.pinreg, ofs=a.ofs, txd=txd, entries={k: len(v) for k, v in imgs.items()},
               seg1_base=base, seg2_base=base2, span=spans.get(0, 0), spans=spans, messages=table)
    if layout:
        # absolute program: segment 0 replayed at every priced layer start, segment 1 at token start (cycle 0)
        L = layout["layers"]
        if a.period_align < 1:
            raise SystemExit("--period-align must be >= 1")
        raw = layout["token_period"]
        layout["token_period"] = -(-raw // a.period_align) * a.period_align
        layout["token_period_pad"] = dict(unpadded=raw, align=a.period_align, pad_edges=layout["token_period"] - raw,
                                          why="core 625 u x 768 = HBM 768 u x 625: a token period that is a multiple of 768 "
                                              "core edges starts every token run at one HBM-beat phase (KV phase launches)")
        over = [l["id"] for l in L if spans[0] >= l["cycles"]]
        if over:
            raise SystemExit(f"layer run longer than its layer window: {over}")
        # a calendar is busy until its last event (TX slot / RX expectation), then a new cal_start is legal
        busy = {sg: max(max(t["arrive"], t["cyc"]) for t in table if t["seg"] == sg) for sg in spans}
        if busy[1] >= L[1]["start"] or busy[0] >= min(l["cycles"] for l in L[1:]):
            raise SystemExit(f"run overlap: token run (embed + L0) busy to {busy[1]} vs L1 start {L[1]['start']}, layer run busy {busy[0]}")
        layout["cal_busy"] = busy
        if 2 in busy:
            # admission run: every calendar idle (incl. the last RX expectation's 2-edge checked output) + settle edges
            adm_len = max(max(t["rx_out"], t["cyc"]) for t in table if t["seg"] == 2) + 4
            adm_ofs = 2 * NE + 8                 # after a sequencer (re)load (2 NE + 2) on the same epoch strobe
            layout["admission"].update(len=adm_len, ofs=adm_ofs, first_token_ofs=adm_ofs + adm_len + 4)
        frames = {"C": 0, "K": 0}
        for t in table:
            frames[t["src"]] += 35 if t["seg"] == 0 else 1
        tok_cyc = L[-1]["start"] + L[-1]["cycles"]
        layout.update(token_frames=frames, layer_run_span=spans[0], token_run_span=spans[1],
                      cal_starts=[dict(seg=1, cycle=0, run="token: RESULT + embedding + L0")] +
                                 [dict(seg=0, cycle=l["start"], layer=l["id"]) for l in L[1:]],
                      link_occupancy={e: round(n / tok_cyc, 5) for e, n in frames.items()}, token_cycles_through_L35=tok_cyc)
        rec["program"] = layout
    rec["die_stages"] = stages
    rec["txdp"] = {e: dict(ports=txd[e], word=f"32'h{txdp_word(txd[e]):08x}") for e in ("C", "K")}
    with open(f"{a.out}/txdp.svh", "w") as f:
        f.write(txdp_svh(txd, f"pinreg={int(a.pinreg)} die_stages={a.die_stages or 'none (component-bench codecs)'}"))
    json.dump(rec, open(f"{a.out}/calendar.json", "w"), indent=1)
    print(json.dumps(dict(entries=rec["entries"], seg1_base=base, spans=spans,
                          **({"program": {k: layout[k] for k in ("layer", "token_run_L0", "emb_send", "hbm_embedding_budget", "token_frames", "link_occupancy", "cal_busy")}} if layout else {}))))


if __name__ == "__main__":
    sys.exit(main())
