#!/usr/bin/env python3
"""TOKEN-XDIE-QWEN 2026-10-18: compiler pass for the Qwen compute <-> KV/system D2D exchange co-sim
(rtl/test/qwen_split/tb_xdie_qwen_exchange.sv).

It is d2d_link_calendar.py's decode-layer (segment 0, L1..L35) image, compiled with the REAL producer / consumer
latencies of the two die masters the vehicle instantiates instead of the component-bench codecs:

  compute TX port 0 (CMD + 32 Q): d2d slot pin -> CS_TXS die stages -> qfd_native59_dv_service (pin register +
      record codec = 2 edges) -> SC_TX die stages -> d2d pin flop          raw TXD = CS_TXS + 2 + SC_TX   (bench codec: 1)
  compute TX port 3 (4 KVN):      slot pin -> CS_X3S -> native59 pin register + KVN transport (2) -> SC_X3 -> d2d pin
      flop -> kvn_tx in the master (1)                                   raw TXD = CS_X3S + 3 + SC_X3   (bench: 2)
  KV TX port 0 (32 RESULT + STATUS): att_tx_slot pin -> KS_TXS -> qkd_native_attention_programme codec (1) -> SK_TXP
      -> d2d pin flop                                                    raw TXD = KS_TXS + 1 + SK_TXP  (bench: 1)
The KV attention programme (kvs14c qkd_kvs_attn: qkd_attn_cal_gen STRETCH=1, RX_CMD 2, SERVICE_END 1777) has FIXED ages:
the CMD must reach its rx pins at programme age RX_CMD and its first RESULT slot is age TX_FIRST = RX_CMD + 2 +
SERVICE_END - 31.  With att_rx_v at the d2d pins at arrival + 2 and KS_RXV stages to the programme, the link slot r0 of
RESULT beat 0 must satisfy  r0 + KS_TXS = (arr_cmd + 2 + KS_RXV) + (TX_FIRST - RX_CMD).  The priced token path fixes r0
from the end of the attn_kv window; the extension X (edges added to attn_kv) that makes the two compiled calendars agree
is therefore computed here (the compiler's job: every added stage is accounted, no runtime alignment):
  X = r0_needed - r0_priced.  X > 0 is exposed latency against the priced token path; it is reported, never hidden.
Outputs (OUT/): cal_{C,K}_{tx,rx}.memh (32 entries), calendar.json (d2d_link_calendar record + 'xdie' block),
xdie_params.svh (bench constants), and the compute-local sys_face slot table the bench drives (declared stimulus).
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import d2d_link_calendar as L   # noqa: E402

RX_CMD, SERVICE_END = 2, 1777            # kvs14c qkd_kvs_attn u_attn_cal parameters (qkd_kvs_tiles_hroot_ff_k.sv @ f05f9338f)
TX_FIRST = RX_CMD + 2 + SERVICE_END - 31  # qkd_attn_cal_gen STRETCH=1: constant
N59_TX = L.N59_TX   # qfd_native59_dv_service: tx_slot pin -> native_tx_v (pin register + qkd_native_attention_record register)
N59_X3 = L.N59_X3   # kv_x3_slot pin -> x3 (pin register + qfd_kvn_static_transport register)
N59_RX_DR = 4   # native_rx pins -> dr_o (pin register, codec register, vm_write register, dr_o register)
N59_LAND = 8    # qfd_native59_dv_service LAND_EDGES default (dr_o -> slice VM write commit, compiler constant)
KV_CODEC = L.KV_CODEC   # qkd_native_attention_static_ctl codec: age-slot event -> tx_valid register


def layer_msgs_gap(w, txl, phy, st_ofs, gap):
    """d2d_link_calendar.layer_msgs (segment 0, base 0) with `gap` idle slots between CMD and Q beat 0; KVN and the
    kind-15 status move by the same gap (one TX frame per cycle per end).  gap 0 == layer_msgs exactly."""
    q0 = int(sum(w[:3]))
    a_end = q0 + int(w[3])
    m = [dict(seg=0, src='C', cyc=q0, tx_port=0, rx_port=0, kind=1, beat=0)]
    m += [dict(seg=0, src='C', cyc=q0 + 1 + gap + b, tx_port=0, rx_port=0, kind=2, beat=b) for b in range(32)]
    m += [dict(seg=0, src='C', cyc=q0 + 33 + gap + i, tx_port=3, rx_port=3, kind=5, beat=i) for i in range(4)]
    m.append(dict(seg=0, src='C', cyc=q0 + st_ofs + gap, tx_port=2, rx_port=2, kind=15, beat=0))
    r_last = a_end - (txl + phy + 3)
    r0 = r_last - 33
    m += [dict(seg=0, src='K', cyc=r0 + b, tx_port=0, rx_port=0, kind=3, beat=b) for b in range(32)]
    m.append(dict(seg=0, src='K', cyc=r_last, tx_port=0, rx_port=0, kind=4, beat=0))
    if gap == 0 and st_ofs == 40:
        assert m == L.layer_msgs(0, 0, w, txl, phy, st_ofs)[0]
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--txl', type=int, default=6)
    ap.add_argument('--phy', type=int, default=5)
    ap.add_argument('--token-path', default='results/arch/token_path_20261009/qwen_rom.json')
    ap.add_argument('--link-handoff', default='results/arch/qwen_split_compute_1014/res_train_decision_1015/decision.json')
    ap.add_argument('--stages', default='2,2,2,2,2,2/11,11,9,9,9,11,11',
                    help='CS_TXS,CS_RXV,CS_RXP,CS_X3S,SC_TX,SC_X3 / KS_RXV,KS_RXP,KS_TXS,KS_TXK,KS_TXB,SK_TXV,SK_TXP')
    ap.add_argument('--txd-override', default=None, help='MUTANT: compile with these raw TXD C ports 0..3 (e.g. 1,1,1,2)')
    ap.add_argument('--no-extend', action='store_true', help='MUTANT: compile the priced attn_kv window (X = 0)')
    ap.add_argument('--layer', default='L1_35', choices=('L1_35', 'L0'),
                    help='decode-layer windows (L1..L35) or the token-run L0 windows (QXF-LINK F7: priced attn_kv 2,038 '
                         'carries 222 edges of per-token KV adders no RTL element implements; the compiled window is the '
                         'implemented KV service, X < 0)')
    ap.add_argument('--masters-txdp', default=None,
                    help='MUTANT: TXDP the die masters are built with, C0..3/K0..3 (default: the compiled TXDP; '
                         'e.g. the r4..r9 hard-wired 3,3,1,4/3,4,3,3)')
    ap.add_argument('--c-real', type=int, default=1, help='1: qfd_native59_dv_service is the compute producer/consumer')
    ap.add_argument('--kv-codec', type=int, default=1, choices=(1, 2),
                    help='KV attention programme codec edges of the vehicle: 1 = LAND 0 (as-built), 2 = LAND 1 (OT_KV_ATTN_LAND)')
    ap.add_argument('--k-real', type=int, default=1, help='1/2: the kvs_attn programme is the KV producer/consumer')
    ap.add_argument('--qgap', type=int, default=0,
                    help='idle link slots between CMD and Q beat 0: 0 = the compiler law (d2d_link_calendar layer_msgs, Q beat b '
                         'at q0 + 1 + b; native59 opens its Q window on the request edge since QXF-LINK F1); 1 = the pre-fix '
                         'native59 requirement (negative witness only)')
    a = ap.parse_args()
    cs, ks = a.stages.split('/')
    CS_TXS, CS_RXV, CS_RXP, CS_X3S, SC_TX, SC_X3 = map(int, cs.split(','))
    KS_RXV, KS_RXP, KS_TXS, KS_TXK, KS_TXB, SK_TXV, SK_TXP = map(int, ks.split(','))
    if not a.c_real:
        CS_TXS = CS_RXV = CS_RXP = CS_X3S = SC_TX = SC_X3 = 0
    if not a.k_real:
        KS_RXV = KS_RXP = KS_TXS = KS_TXK = KS_TXB = SK_TXV = SK_TXP = 0
    # producer TXD from the die stages: the compiler law (d2d_link_calendar.producer_txd, QXF-LINK F4); the component
    # codec at an unreal end has raw 1 (KVN 2) and no seam
    S = dict(CS_TXS=CS_TXS, CS_RXV=CS_RXV, CS_RXP=CS_RXP, CS_X3S=CS_X3S, SC_TX=SC_TX, SC_X3=SC_X3, KS_RXV=KS_RXV,
             KS_RXP=KS_RXP, KS_TXS=KS_TXS, KS_TXK=KS_TXK, KS_TXB=KS_TXB, SK_TXV=SK_TXV, SK_TXP=SK_TXP)
    law = L.producer_txd(S, kv_codec=a.kv_codec)
    raw_c = law['C'] if a.c_real else [1, 1, 1, 2]
    raw_k = law['K']
    if a.txd_override:
        raw_c = [int(x) for x in a.txd_override.split(',')]
    ext = L.PINREG_EXT                                       # --pinreg (die masters PR = 1)
    txd = {'C': [x + e for x, e in zip(raw_c, ext['C'])], 'K': [x + e for x, e in zip(raw_k, ext['K'])]}
    if a.masters_txdp:
        mc, mk = a.masters_txdp.split('/')
        mtx = {'C': [int(x) for x in mc.split(',')], 'K': [int(x) for x in mk.split(',')]}
    else:
        mtx = txd
    txl_p, phy_p, phy_c = a.txl + 2, a.phy + 2, a.phy + 2
    # priced windows (the same pass d2d_link_calendar --profile program runs)
    _, lay = L.program_profile(txl_p, phy_p, a.token_path, host_stages=0, st_ofs=40, handoff=a.link_handoff)
    w = [lay['windows'][a.layer][k] for k in ('rmsnorm1', 'qkv', 'qknorm_rope', 'attn_kv')]
    period = next(l['cycles'] for l in lay['layers'] if l['id'] == ('L1' if a.layer == 'L1_35' else 'L0'))
    q0 = sum(w[:3])
    arr_cmd = q0 + txd['C'][0] - 1 + a.txl + phy_c          # compile_seg arrival (ofs 0)
    t_cmd_prog = arr_cmd + 2 + KS_RXV                       # CMD at the programme rx pins = programme age RX_CMD
    r0_need = t_cmd_prog + (TX_FIRST - RX_CMD) - KS_TXS
    r0_priced = q0 + w[3] - (txl_p + phy_p + 3) - 33
    X = 0 if a.no_extend else r0_need - r0_priced
    w2 = list(w)
    w2[3] += X
    # status (kind 15) placement: the first offset >= 40 whose write capture is unique (compiler search, fail closed)
    for st_ofs in range(40, 49):
        msgs = layer_msgs_gap(w2, txl_p, phy_p, st_ofs, a.qgap)
        try:
            imgs, table, _ = L.compile_cal(msgs, a.txl, phy_c, 0, txd)
            break
        except SystemExit as e:
            last = e
    else:
        raise last
    os.makedirs(a.out, exist_ok=True)
    for k, v in imgs.items():
        with open(f'{a.out}/cal_{k}.memh', 'w') as f:
            f.write('\n'.join(f'{x:08x}' for x in v + [0] * (L.NE - len(v))) + '\n')
    span = max(max(t['rx_out'], t['cyc']) for t in table)
    if span + 64 >= period + X:
        raise SystemExit(f'layer run span {span} does not fit the layer period {period + X}')
    q = [t for t in table if t['src'] == 'C' and t['tx_port'] == 0]
    r = [t for t in table if t['src'] == 'K' and t['tx_port'] == 0]
    kv = [t for t in table if t['src'] == 'C' and t['tx_port'] == 3]
    st = [t for t in table if t['src'] == 'C' and t['tx_port'] == 2]
    assert len(q) == 33 and len(r) == 33 and len(kv) == 4 and len(st) == 1
    assert r[0]['cyc'] == r0_need or a.no_extend, (r[0]['cyc'], r0_need)
    # programme (KV) run cycle: age 0 is the cycle after the run edge, so run is asserted in cycle t_cmd_prog - RX_CMD - 1
    kv_run = t_cmd_prog - RX_CMD - 1
    # compute-local sys_face slots (declared compiled stimulus of qfd_sys_face at the native59 pins)
    n59_cmd = q0 + CS_TXS - 1                                # native_cmd one edge before the CMD slot reaches native59
    n59_ctx = n59_cmd - 117                                  # begin (layer_context_v); K/V dd from +4, Q dd from +39
    n59_kvw = [kv[i]['cyc'] + CS_X3S - 3 for i in range(4)]  # kv_word_slot three edges before each x3 slot
    t31 = r[31]['arrive'] + 2 + CS_RXV                       # result beat 31 at the native59 rx pins
    n59_vis = t31 + N59_RX_DR + N59_LAND + 2
    n59_cmp = n59_vis + 2
    P = dict(P_PERIOD=period + X, P_QS=q0, P_RS=r[0]['cyc'], P_RE=r[32]['cyc'], P_SS=st[0]['cyc'], P_KS=kv[0]['cyc'],
             P_ARR_Q0=q[0]['arrive'], P_ARR_R0=r[0]['arrive'], P_ARR_K0=kv[0]['arrive'], P_ARR_S=st[0]['arrive'],
             P_KV_RUN=kv_run, P_TX_FIRST=TX_FIRST, P_RX_CMD=RX_CMD,
             P_N59_CTX=n59_ctx, P_N59_CMD=n59_cmd, P_N59_KVW=n59_kvw[0], P_N59_VIS=n59_vis, P_N59_CMP=n59_cmp,
             P_X=X, P_TXL=a.txl, P_PHY=a.phy, P_QGAP=a.qgap,
             CS_TXS=CS_TXS, CS_RXV=CS_RXV, CS_RXP=CS_RXP, CS_X3S=CS_X3S, SC_TX=SC_TX, SC_X3=SC_X3,
             KS_RXV=KS_RXV, KS_RXP=KS_RXP, KS_TXS=KS_TXS, KS_TXK=KS_TXK, KS_TXB=KS_TXB, SK_TXV=SK_TXV, SK_TXP=SK_TXP)
    for k, v in P.items():
        if v < 0 and k != 'P_X':      # X < 0: the priced window is longer than the implemented service (L0, F7)
            raise SystemExit(f'{k} = {v} < 0')
    with open(f'{a.out}/xdie_params.svh', 'w') as f:
        f.write(''.join(f'localparam integer {k} = {v};\n' for k, v in P.items()))
        # the die masters' TXDP (compiler output; a mutant may build the masters with another vector)
        f.write(f"localparam [31:0] P_TXDP_C = 32'h{L.txdp_word(mtx['C']):08x};\n"
                f"localparam [31:0] P_TXDP_K = 32'h{L.txdp_word(mtx['K']):08x};\n")
    with open(f'{a.out}/txdp.svh', 'w') as f:
        f.write(L.txdp_svh(txd, f'xdie_exchange_cal.py stages {a.stages} c_real {a.c_real} k_real {a.k_real}'))
    rec = dict(schema='opentallas.xdie_qwen_exchange_cal.v1', layer=a.layer, masters_txdp=mtx, c_real=a.c_real, k_real=a.k_real, qgap=a.qgap, txl=a.txl, phy=a.phy, phy_compiled=phy_c, pinreg=True, ofs=0,
               txd=txd, raw_txd=dict(C=raw_c, K=raw_k), stages=a.stages, entries={k: len(v) for k, v in imgs.items()},
               windows_priced=dict(zip(('rmsnorm1', 'qkv', 'qknorm_rope', 'attn_kv'), w)), attn_extend_X=X,
               layer_period=period, layer_period_compiled=period + X, span=span, messages=table,
               kv_programme=dict(RX_CMD=RX_CMD, SERVICE_END=SERVICE_END, TX_FIRST=TX_FIRST, run_cycle=kv_run,
                                 cmd_at_programme=t_cmd_prog, r0_needed=r0_need, r0_priced=r0_priced),
               params=P, token_path=a.token_path, link_handoff=a.link_handoff,
               overlap_note='L1..L35 layer: rmsnorm1 -> qkv -> qknorm_rope -> [Q/CMD over D2D -> KV attention -> RESULT over '
                            'D2D] -> o_proj ...: the compiler schedules no independent compute-die op inside attn_kv '
                            '(windows are serial in the token path), so O_meas = 0 for the CMD/Q and RESULT exchanges; '
                            'the 4 KVN words (new K/V of this token) are consumed by the NEXT token attention, '
                            'O_meas = layer period - KVN latency (fully hidden).')
    json.dump(rec, open(f'{a.out}/calendar.json', 'w'), indent=1)
    print(json.dumps(dict(X=X, txd=txd, q0=q0, r0=r[0]['cyc'], kv_run=kv_run, period=period + X, entries=rec['entries'])))


if __name__ == '__main__':
    main()
