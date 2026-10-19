#!/usr/bin/env python3
"""QXF-PAIR 2026-10-18: record for the PAIRED Qwen compute <-> KV D2D co-sim (tb_xdie_qwen_exchange.sv C_REAL=1 K_REAL=3,
run by rtl/test/qwen_split/run_xdie_exchange.sh RUN pair ...).

Reads RUN/<config>/{run.log, cal/calendar.json} and writes RUN/record.json:
  - per config: expectation, verdict, XQ_E / XQ_CFG / layer-1 XQ_MEAS;
  - landing check: every measured pin event minus its compiled calendar cycle (calendar.json messages, the same
    compiler pass) is the compiler's fixed pin offset (d2d_link_calendar N59_TX / N59_X3 / KV_CODEC, xdie_exchange_cal
    N59_RX_DR, stage counts) or, where the compiler does not name the RTL-internal pin offset, IDENTICAL in every PASS
    config (L1..35 / L0, PHY 5 / 9, T 256 / 8192): landings move exactly with the compiled calendar;
  - mutants: fail regex must match the committed witness and must not match any PASS log;
  - exchanges: E_meas per exchange, O_meas from the calendar's overlap rule, exposed = max(0, E - O), split by grade;
  - token_compose block (results/arch/token_path_1018/README.md override format) for qwen_rom
    L0.xdie.d2d_attention / Lc.xdie.d2d_attention.
Fails (exit 1) when any check fails.
"""
import argparse, json, re, sys
from pathlib import Path

N59_TX, N59_X3, KV_CODEC, N59_RX_DR = 2, 2, 1, 4      # d2d_link_calendar.py / xdie_exchange_cal.py constants

PASS_CFGS = ('pair', 'pair_t8192', 'pair_phy9', 'pair_l0', 'pair_l0_phy9')
MUTANTS = {
    'pair_mut_txdp_c_off1': ('compute die master built with TXDP C port 0 one edge over the compiled value (CMD/Q port)',
                             r'^XQ_CAUSE d2d: compute fault 1 abort 0 end_fault 1'),
    'pair_mut_kseam_rx_torn': ('KV seam K.rx_record torn: att_rx_v 10 stages vs rx_payload 11',
                               r'^XQ_CAUSE kvs_attn\+pvfin .*record 1 \(codec cause 1010\)'),
    'pair_mut_kseam_tx_torn': ('KV seam K.tx_record torn: tx_v 10 stages vs tx_payload 11',
                               r'^XQ_CAUSE d2d: .*\| KV fault 1 abort 0 end_fault 1'),
    'pair_mut_status_done': ('STATUS done bit (data bit 3) cleared at the KV producer pins, layer 4',
                             r'^XQ_ERR .*STATUS word at the compute consumer != namespace'),
    'pair_mut_result_bit': ('RESULT beat 7 data bit 0 flipped at the KV producer pins, layer 5',
                            r'^XQ_ERR .*RESULT beat != golden at the compute consumer'),
    'pair_mut_phy_bit': ('one PHY bit flipped in a compute->KV frame, layer 3 (CRC abort)',
                         r'^XQ_CAUSE d2d: .*KV fault 0 abort 1 end_fault 0 cause 00000001'),
}


def kv(line):
    return {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)}


def parse(cdir):
    log = (cdir / 'run.log').read_text()
    lines = log.splitlines()
    e = next((kv(l) for l in lines if l.startswith('XQ_E ')), {})
    cfg = next((l for l in lines if l.startswith('XQ_CFG')), '')
    meas = [kv(l) for l in lines if l.startswith('XQ_MEAS')]
    return dict(log=log, lines=lines, E=e, cfg=cfg, meas=meas, passed=any(l.startswith('XQ_PASS') for l in lines),
                cal=json.loads((cdir / 'cal' / 'calendar.json').read_text()))


def landing_offsets(r):
    """measured pin cycle (layer 1, layer-relative) minus the compiled calendar cycle of the same frame."""
    c, m = r['cal'], r['meas'][0]
    P = c['params']
    msg = c['messages']
    q = [t for t in msg if t['src'] == 'C' and t['tx_port'] == 0]
    rr = [t for t in msg if t['src'] == 'K' and t['tx_port'] == 0]
    kvn = [t for t in msg if t['src'] == 'C' and t['tx_port'] == 3]
    off = {
        # producer issue at the producer pins vs the compiled TX slot (compiler: slot + seam + producer pin/codec)
        'cmd_issue-C.slot[CMD]': (m['cmd_issue'] - q[0]['cyc'], P['CS_TXS'] + N59_TX),
        'q0_issue-C.slot[Q0]': (m['q0_issue'] - q[1]['cyc'], P['CS_TXS'] + N59_TX),
        'q31_issue-C.slot[Q31]': (m['q31_issue'] - q[32]['cyc'], P['CS_TXS'] + N59_TX),
        'kvn0_issue-C.slot[KVN0]': (m['kvn0_issue'] - kvn[0]['cyc'], P['CS_X3S'] + N59_X3),
        'kvn3_issue-C.slot[KVN3]': (m['kvn3_issue'] - kvn[3]['cyc'], P['CS_X3S'] + N59_X3),
        'r0_issue-K.slot[R0]': (m['r0_issue'] - rr[0]['cyc'], P['KS_TXS'] + KV_CODEC),
        'r31_issue-K.slot[R31]': (m['r31_issue'] - rr[31]['cyc'], P['KS_TXS'] + KV_CODEC),
        'status_issue-K.slot[STATUS]': (m['status_issue'] - rr[32]['cyc'], P['KS_TXS'] + KV_CODEC),
        # consumer land at the consumer pins vs the compiled arrival at the far D2D end (+2 = rx_out)
        'r0_land(dr_o)-arrive[R0]': (m['r0_land'] - rr[0]['arrive'], 2 + P['CS_RXV'] + N59_RX_DR),
        'r31_land(dr_o)-arrive[R31]': (m['r31_land'] - rr[31]['arrive'], 2 + P['CS_RXV'] + N59_RX_DR),
        'status_land(n59 rx)-arrive[STATUS]': (m['status_land'] - rr[32]['arrive'], 2 + P['CS_RXV']),
        # KV programme pins: compiler fixes the AGE (RX_CMD) of the CMD at the programme rx pins; request / q_valid
        # are registered programme outputs -> offsets named by the RTL, required identical in every config
        'cmd_land(request_valid)-arrive[CMD]': (m['cmd_land'] - q[0]['arrive'], None),
        'q0_land(q_valid)-arrive[Q0]': (m['q0_land'] - q[1]['arrive'], None),
        'q31_land(q_valid)-arrive[Q31]': (m['q31_land'] - q[32]['arrive'], None),
        'kvn0_land(kvn word)-arrive[KVN0]': (m['kvn0_land'] - kvn[0]['arrive'], None),
        'kvn3_land(kvn word)-arrive[KVN3]': (m['kvn3_land'] - kvn[3]['arrive'], None),
        # the programme's age 0 is the cycle after the compiled run edge: CMD at age RX_CMD + the request register
        'cmd_land-(P_KV_RUN+1+RX_CMD)': (m['cmd_land'] - (P['P_KV_RUN'] + 1 + P['P_RX_CMD']), None),
        'r0_issue-(P_KV_RUN+1+TX_FIRST)': (m['r0_issue'] - (P['P_KV_RUN'] + 1 + P['P_TX_FIRST']), KV_CODEC),
    }
    return off


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run', help='run dir (configs as subdirs)')
    ap.add_argument('--rel', default='results/rtl/xdie_qwen_1018/pair_r1', help='repo path of the committed run dir')
    ap.add_argument('--branch', default='')
    # Q-XDIE-GEN 10-18: a re-run on the NETLISTED seam of named die GENs (run_xdie_exchange.sh XQ_PLAN)
    ap.add_argument('--seam', default=None, help='seam provenance note (default: the fixed-GEN plan text of pair_r1)')
    ap.add_argument('--lane', default='QXF-PAIR (Q-XDIE-FIX, TOKEN-XDIE-QWEN paired run)')
    a = ap.parse_args()
    R = Path(a.run)
    bad = []
    cfgs = {}
    for name in PASS_CFGS + tuple(MUTANTS):
        cdir = R / name
        if not (cdir / 'run.log').exists():
            bad.append(f'{name}: no run.log')
            continue
        cfgs[name] = parse(cdir)
    # ---- PASS configs: verdict, 35 layers, static, landings
    land = {}
    for n in PASS_CFGS:
        r = cfgs.get(n)
        if not r:
            continue
        if not r['passed']:
            bad.append(f'{n}: not XQ_PASS')
        if len(r['meas']) != 35 or any(m != r['meas'][0] | {'layer': m['layer']} for m in r['meas']):
            bad.append(f'{n}: per-layer measurements not identical over 35 layers')
        land[n] = landing_offsets(r)
    keys = list(next(iter(land.values())).keys()) if land else []
    landing = {}
    for k in keys:
        vals = {n: land[n][k][0] for n in land}
        want = next(iter(land.values()))[k][1]
        ok = len(set(vals.values())) == 1 and (want is None or all(v == want for v in vals.values()))
        landing[k] = dict(measured=vals, compiler=want, ok=ok)
        if not ok:
            bad.append(f'landing {k}: {vals} (compiler {want})')
    # ---- mutants: FAIL, regex on the witness, regex absent from every PASS log
    mut = {}
    for n, (what, rx) in MUTANTS.items():
        r = cfgs.get(n)
        if not r:
            continue
        hit = [l for l in r['lines'] if re.search(rx, l)]
        clean = all(not re.search(rx, l) for p in PASS_CFGS if p in cfgs for l in cfgs[p]['lines'])
        ok = (not r['passed']) and any(l.startswith('XQ_FAIL') for l in r['lines']) and bool(hit) and clean
        mut[n] = dict(what=what, fail_regex=rx + '|^XQ_FAIL', expect='FAIL', got='PASS' if r['passed'] else 'FAIL',
                      first_match=hit[0] if hit else None, regex_absent_from_pass_logs=clean,
                      witness=f'{a.rel}/{n}/run.log', ok=ok)
        if not ok:
            bad.append(f'mutant {n}: {mut[n]}')
    # ---- exchanges (E from the PASS runs; O from the calendar overlap rule of the same compiler pass)
    def exch(n):
        r = cfgs[n]
        E, P = r['E'], r['cal']['params']
        phy = P['P_PHY']
        c2k_seam = P['SC_TX'] + P['KS_RXV']
        k2c_seam = P['SK_TXP'] + P['CS_RXV']
        c2k, k2c, kvn = E['C2K_q31_issue_to_land'], E['K2C_r31_issue_to_land'], E['KVN_k3_issue_to_land']
        period = r['cal']['layer_period_compiled']
        return dict(
            C2K=dict(E=c2k, what='CMD + 32 Q: native59 Q31 issue (native_tx_v) -> kvs_attn programme q_valid beat 31',
                     parts=dict(rtl=c2k - phy - c2k_seam, seam=c2k_seam, phy=phy), O=0, exposed=max(0, c2k)),
            K2C=dict(E=k2c, what='32 RESULT (+STATUS): kvs_attn programme R31 issue (tx_valid) -> native59 dr_o beat 31',
                     parts=dict(rtl=k2c - phy - k2c_seam, seam=k2c_seam, phy=phy), O=0, exposed=max(0, k2c)),
            KVN=dict(E=kvn, what='4 KVN words: native59 x3 word 3 -> KV d2d kvn word 3', O=period - kvn, exposed=0,
                     O_rule='consumed by the NEXT token attention: O = layer period - E (calendar overlap_note)'),
            STATUS=dict(E=E['K2C_status_issue_to_land'], what='STATUS issue -> native59 rx pins (one slot after R31; '
                        'lands before R31 reaches dr_o, inside the native59 RX/land pipe)', O=None, exposed=0),
            per_layer_exposed=max(0, c2k) + max(0, k2c),
            roundtrip_cmd_issue_to_r31_land=E['roundtrip_cmd_issue_to_r31_land'],
            # like-for-like with the TOKEN-XDIE-QWEN record layer_attention_segment (q0 = compiled CMD slot P_QS; priced
            # 1814 = the d2d_link_calendar image with zero-latency component codecs)
            attn_segment_q0slot_to_r31_land=r['meas'][0]['r31_land'] - P['P_QS'],
            attn_segment_vs_priced_1814=r['meas'][0]['r31_land'] - P['P_QS'] - 1814,
            kv_service_cmd_land_to_r31_issue=E['kv_service_cmd_land_to_r31_issue'],
            attn_window_extension_X=r['cal']['attn_extend_X'], layer_period_compiled=period,
            layer_period_priced=r['cal']['layer_period'], windows_priced=r['cal']['windows_priced'],
            O_source=r['cal']['overlap_note'])
    ex = {n: exch(n) for n in PASS_CFGS if n in cfgs}
    # Q-XDIE-GEN: the die masters with the TXDP the GENs BIND (pair_gen_txdp, optional): recorded with its verdict
    gen_txdp = None
    if (R / 'pair_gen_txdp' / 'run.log').exists():
        g = parse(R / 'pair_gen_txdp')
        gen_txdp = dict(passed=g['passed'], cfg=g['cfg'], log=f'{a.rel}/pair_gen_txdp/run.log',
                        first_cause=next((l for l in g['lines'] if l.startswith('XQ_CAUSE')), None),
                        masters_txdp=g['cal'].get('masters_txdp'), compiled_txd=g['cal'].get('txd'))
    if bad:
        print('\n'.join('PAIR_RECORD BAD ' + b for b in bad))
    L1, L0 = ex.get('pair'), ex.get('pair_l0')

    def tc_term(slot, e, note):
        rtl = e['C2K']['parts']['rtl'] + e['K2C']['parts']['rtl']
        seam = e['C2K']['parts']['seam'] + e['K2C']['parts']['seam']
        phy = e['C2K']['parts']['phy'] + e['K2C']['parts']['phy']
        return dict(design='qwen_rom', workload='ar', slot=slot,
                    E=[dict(grade='measured-current-RTL', E=float(rtl),
                            note='die masters qfd_d2d_static / qkd_d2d_static (PR=1, compiled TXDP) + native59 + kvs_attn '
                                 'programme pins, measured on the paired co-sim'),
                       dict(grade='measured-current-RTL', E=float(seam),
                            note=a.seam or ('die seam relays at the fixed-GEN bundle depth (compute C.tx_record 0 / C.rx_record 2, '
                                 'KV K.rx_record 11 / K.tx_record 11; QXF-SEAMC / QXF-SEAMK), register chains in the vehicle')),
                       dict(grade='modelled-PHY', E=float(phy),
                            note='UCIe PHY pair ot_qkvd_ucie_x64_phy_model LAT 5 FDI cycles each way (3.5 ns, JSSC 2026 '
                                 'doi:10.1109/JSSC.2026.3651425)')],
                    O=0.0, O_source='xdie_exchange_cal.py calendar (same compiler pass): attn_kv is serial in the token path '
                    '(rmsnorm1 -> qkv -> qknorm_rope -> attn_kv -> o_proj), no independent compute-die op inside it -> O 0; '
                    'KVN hidden (next token)', pointer=note)
    tcomp = None
    if L1 and L0:
        tcomp = dict(terms=[tc_term('Lc.xdie.d2d_attention', L1, 'exchanges.pair (C2K + K2C, PHY 5)'),
                            tc_term('L0.xdie.d2d_attention', L0, 'exchanges.pair_l0 (C2K + K2C, PHY 5)')])
    rec = dict(
        schema='opentallas.xdie_qwen_pair.v1', lane=a.lane, date='2026-10-18',
        branch=a.branch, verdict='PASS' if not bad else 'FAIL', problems=bad,
        vehicle=dict(
            bench='rtl/test/qwen_split/tb_xdie_qwen_exchange.sv C_REAL=1 K_REAL=3, run_xdie_exchange.sh (Verilator 5.050, fleet)',
            real_rtl=['compute die master qfd_d2d_static (d2d_rom of dv2f14bn; PR=1, TXDP C [6,3,1,9] compiled; slot link, '
                      'CRC, LLR, calendars ot_qwen_d2d_cal_seq loaded from the compiler image)',
                      'KV die master qkd_d2d_static (d2d_kv of kvs14c; TXDP K [23,4,3,3] compiled; KVN word path)',
                      'compute producer/consumer qfd_native59_dv_service (Q seat bank + Q export from the request edge (F1), '
                      'FP8 K/V formatter, KVN transport, static service, record endpoint, dr_o return)',
                      'KV as-built qkd_kvs_attn (vendored kvs14c): qkd_native_attention_programme (static_ctl, STATUS encoder '
                      'qkd_native_status_word (F2)), qkd_attn_cal_gen STRETCH=1, qkd_attn_service_root, qkd_attn_result_face_s '
                      '(max(P0,P1,R) law, F3)',
                      'KV final join qkd_pv_fin_s (REAL fp32 add/mul: RESULT = (P0 + P1) * rz, 32-sum buffer, R join, F3)'],
            modelled=['UCIe PHY pair ot_qkvd_ucie_x64_phy_model LAT 5 (sensitivity 9)',
                      a.seam or ('die seam relays / landings as register chains of the fixed-GEN bundle depth (compute 2,2,2,2,0,2; '
                      'KV 11,11,9,9,9,11,11) -- the GENs that adopt QXF-SEAMC / QXF-SEAMK have not run'),
                      'outer-pin stimuli only: native59 slice Q/K/V dd_i words, compute sys_face slots (q_slot, kv_word_slot, '
                      'visibility, complete), HOST context, KV layer-programme authority (go/issue/run, i_ctl)',
                      'the KV attention ARITHMETIC upstream of the final join is NOT on this vehicle: the PV pair streams '
                      'P0/P1 (pbeat) and hub reciprocals rz enter qkd_pv_fin_s as stimuli on their compiled slots from '
                      'kvs_attn pvfst (QK / softmax / PV tiles and ahub are TOKEN-PASS-QWEN KV single-die scope)'],
            no_link_codecs='no stimulus codec at either link end: the Q / CMD records are produced by native59 and consumed by '
                           'the kvs_attn programme; RESULT / STATUS produced by the programme (beats from pvfin through the '
                           'face) and consumed by native59; KVN by native59 x3 -> d2d_kv kvn word'),
        checks=['bit-exact Q at the KV consumer (golden qbeat), RESULT at dr_o (golden obeat = pvfin fp32 output), STATUS at the '
                'native59 rx pins == namespace {q_ready 0, done 1, fault 0, busy 0, ready 1}, KVN word at the KV end == '
                'compute x3 word (identity + generation + tag + data; the K/V values are native59 formatter output)',
                'every frame on its compiled slot at both D2D ends (end RX/TX calendars fault otherwise), programme '
                'rx/tx_time + native59 rx/tx_time codecs (fault on any off-slot record), landing table below',
                'no fault (ends, native59, programme, root, face, pvfin, calendar), no ready/credit wait',
                'all 35 layers identical (static)'],
        landing=landing, mutants=mut, gen_bound_txdp=gen_txdp, exchanges=ex,
        configs={n: dict(passed=r['passed'], E=r['E'], cfg=r['cfg'], meas_layer1=r['meas'][0] if r['meas'] else None,
                         log=f'{a.rel}/{n}/run.log') for n, r in cfgs.items()},
        vs_earlier=dict(record='results/rtl/xdie_qwen_1018/record.json (TOKEN-XDIE-QWEN, composed vc+vk, run_r3)',
                        earlier_per_layer_exposed=63, earlier_vs_priced_L1_L35=1120,
                        paired_per_layer_exposed=L1['per_layer_exposed'] if L1 else None,
                        paired_attn_window_extension_X_per_layer=L1['attn_window_extension_X'] if L1 else None,
                        paired_vs_priced_L1_L35=35 * L1['attn_window_extension_X'] if L1 else None,
                        paired_L0_X=L0['attn_window_extension_X'] if L0 else None,
                        earlier_attn_segment_q0_to_r31_land=1846,
                        paired_attn_segment_q0_to_r31_land=L1['attn_segment_q0slot_to_r31_land'] if L1 else None,
                        paired_attn_segment_vs_priced_L1_L35=35 * L1['attn_segment_vs_priced_1814'] if L1 else None,
                        paired_attn_segment_vs_priced_L1_L35_phy9=(35 * ex['pair_phy9']['attn_segment_vs_priced_1814']
                                                                   if 'pair_phy9' in ex else None)),
        token_compose=tcomp)
    (R / 'record.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(verdict=rec['verdict'], per_layer_exposed={n: e['per_layer_exposed'] for n, e in ex.items()},
                          X={n: e['attn_window_extension_X'] for n, e in ex.items()},
                          mutants={n: m['ok'] for n, m in mut.items()}), indent=1))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
