#!/usr/bin/env python3
"""qwen-1010/a 2026-10-10: re-price the ROM die + KV die pair with the option-4 control plane (r22ko4).

reprice.json (tools/qwen_kv_die/reprice.py) charges the r22k sequencer <-> tree-top / SU relays as the measured r22k_ml10
L0-L2 run against s22ml7 (split_relays.json: +454 on L0, +623 a layer).  Option 4 replaces that term by the MEASURED
L0-L2 run of the actual masters at the r22ko4 relay counts (tools/redesign_qwen/option4_die.py: seq_su_bi + ctlm_i,
SU pin stations + endpoint accepted counter, die relays between the masters' pin flops), against the same s22ml7.

Also priced here (none is in reprice.json):
  fec        the 72 AR256 a token carry no board-SerDes FEC term (the stream4 collective LAT 339 has none; the link
             adapter leaves FEC to the PHY).  The package pair puts half of each TP4 ring on a board leg: charged
             +100 cycles a collective (DS RS(544,514) rule), bound +240 (HBM 0.2 us rule at 1.2 GHz)
             (budget audit qrom_ar_link_fec).
  bounds     words the vehicle does not carry, from the r22ko4 record against r22k (per layer, one-way stage deltas):
             kvd / kv_ok now leave the control tile (41 / 43 relays to d2d_rom vs the sequencer word's 12 / 13).

    python3 tools/qwen_kv_die/reprice_o4.py --o4 <L3 result.json> [--o4-name bi16] --out results/arch/qwen_kv_die_20261009/reprice_o4.json
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / 'results/arch/qwen_kv_die_20261009'
CLOCK = 1.2e9
AR_PER_TOKEN = 72
FEC = dict(ds_rule=100, hbm_rule=240)
FECD = json.loads((ROOT / 'tools/qwen_kv_die/fec_derivation.json').read_text())   # extra FEC per all-reduce: headline 0


def sha16(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--o4', type=Path, required=True, help='L3 run of option4_die.py: {stage_cycles: {L0, L1, L2}, exact}')
    ap.add_argument('--o4-name', default='o4')
    ap.add_argument('--extra', type=str, nargs='*', default=[], help='further L3 runs (sensitivities), name=path')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--kv-basis', type=Path, default=D / 'reprice.json',
                    help="the KV-die reprice the option-4 term is applied to (e.g. (b)'s relay + leaf-plan basis)")
    ap.add_argument('--cbuf-wait', type=int, default=0,
                    help='constant-buffer stage-start waits a steady-state token (cycles, measured: tb_qfd_crom_lbuf GATE 1)')
    ap.add_argument('--refresh-step', type=int, nargs=2, default=None, metavar=('MEAN', 'WORST'),
                    help='PROVISIONAL timed-REFpb KV step increase per layer (cycles, mean / worst)')
    a = ap.parse_args()
    a.kv_basis = a.kv_basis.resolve()
    rp = json.loads(a.kv_basis.read_text())
    sr = json.loads((D / 'split_relays.json').read_text())
    o4rec = json.loads((D / 'rom_r22ko4.json').read_text())
    svrec = json.loads((D / 'rom_r22ksv.json').read_text())

    def vm_ar(rec):
        s = rec['crossing_bus_stages']
        return s.get('seq_vrd', 0) + s.get('vm_seq_q', 0) + s.get('seq_vwr', 0)
    vmar_r22k, vmar_o4 = AR_PER_TOKEN * vm_ar(svrec), AR_PER_TOKEN * vm_ar(o4rec)
    ref = sr['reference']['s22ml7']
    adopted = sr['runs'][sr['adopted_for_price'].split()[0]]['vs_s22ml7']

    def run_of(path):
        r = json.loads(Path(path).read_text())
        sc = r['stage_cycles']
        return dict(exact=bool(r.get('exact')), L0=sc['L0'], L1=sc['L1'], L2=sc.get('L2'),
                    vs_s22ml7=dict(L0=sc['L0'] - ref['L0'], L1=sc['L1'] - ref['L1']))
    o4 = run_of(a.o4)
    out = dict(schema='opentallas.qwen-kv-die.reprice-o4.v1', date='2026-10-10', clock_hz=CLOCK,
               inputs={str(p.relative_to(ROOT)): sha16(p) for p in (a.kv_basis, D / 'split_relays.json',
                                                                      D / 'rom_r22ko4.json', D / 'rom_r22ksv.json')} | {str(a.o4): sha16(a.o4)},
               r22k_relay_term=dict(run=sr['adopted_for_price'], L0=adopted['L0'], layer=adopted['L1'],
                                    token=adopted['L0'] + 35 * adopted['L1']),
               o4_run=dict(name=a.o4_name, **o4), cases={})
    o4_token = o4['vs_s22ml7']['L0'] + 35 * o4['vs_s22ml7']['L1'] + a.cbuf_wait
    out['o4_relay_term'] = dict(L0=o4['vs_s22ml7']['L0'], layer=o4['vs_s22ml7']['L1'], token=o4_token,
                                cbuf_wait_per_token=a.cbuf_wait,
                                cbuf_note='constant-buffer stage-start waits (seq_su ot_qfd_stage_gate + 8 SRAM groups, far ROM 17 '
                                          'edges): 466 cycles on the first token, 111 a steady token (rtl/test/redesign_qwen/'
                                          'tb_qfd_crom_lbuf.sv GATE 1, NTOK 1 / 2); the chain vehicle prices the buffer as SU ML 7')
    st = o4rec['crossing_bus_stages']
    # the KV-die bench prices the step from the q word (x3) leaving the ROM faces; a launch descriptor on a longer path
    # than x3 delays the step by the difference (r22ko4: kvd from seq_su)
    kvd_extra = max(0, st.get('o4_kvd', 0) - st.get('x3', 25))
    for case, c in rp['cases'].items():
        base = c['token_cycles']
        tok = base - out['r22k_relay_term']['token'] + o4_token
        fec = AR_PER_TOKEN * FEC['ds_rule']
        fec_b = AR_PER_TOKEN * FEC['hbm_rule']
        out['cases'][case] = dict(
            r22k_token_cycles=base, r22k_tok_s=c['tok_s'],
            o4_token_cycles=tok, o4_tok_s=round(CLOCK / tok, 1),
            o4_fec_token_cycles=tok + fec, o4_fec_tok_s=round(CLOCK / (tok + fec), 1),
            o4_fec_bound_tok_s=round(CLOCK / (tok + fec_b), 1),
            r22k_fec_tok_s=round(CLOCK / (base + fec), 1),
            kvd_bound_tok_s=round(CLOCK / (tok + fec + 36 * kvd_extra), 1),
            r22k_fec_vmar_tok_s=round(CLOCK / (base + fec + vmar_r22k), 1),
            r22k_fecb_vmar_tok_s=round(CLOCK / (base + fec_b + vmar_r22k), 1),
            o4_fec_vmar_tok_s=round(CLOCK / (tok + fec + vmar_o4), 1),
            o4_fecb_vmar_tok_s=round(CLOCK / (tok + fec_b + vmar_o4), 1),
            r22k_fec0_vmar_tok_s=round(CLOCK / (base + vmar_r22k), 1),
            o4_fec0_vmar_tok_s=round(CLOCK / (tok + vmar_o4), 1))
    out['vm_ar'] = dict(per_token_r22k=vmar_r22k, per_token_o4=vmar_o4, stages_r22ksv=vm_ar(svrec), stages_r22ko4=vm_ar(o4rec),
                        note='the sequencer <-> VM all-reduce word path (read request, word back, write) was not in the r22k '
                             'die or price; each of the 72 all-reduces pays its die relays once (the stream rate is kept: '
                             'ot_qwen_tp_seq_w12_vrl), the masters\' own stations are in the measured vehicle')
    out['bounds'] = dict(
        kvd_kok_extra_stages_per_layer=kvd_extra,
        kvd_note='the launch descriptor leaves seq_su (r22ko4): stages beyond the q word path (x3), charged per layer in kvd_bound',
        tree_words=dict(pword_0=st.get('pword_0'), tt_ty=st.get('tt_ty'), r22k=dict(pword_0=39, tt_ty=39),
                        note='band words reach the 2 x 2 upper-tile group +8 stages later than the r22k tree top (TWS '
                             'sensitivity run), tt_ty +3'))
    for e in a.extra:
        name, path = str(e).split('=', 1)
        r = run_of(path)
        t = r['vs_s22ml7']['L0'] + 35 * r['vs_s22ml7']['L1']
        out.setdefault('sensitivities', {})[name] = dict(**r, token_term=t, tok_s_typical=round(
            CLOCK / (rp['cases']['typical']['token_cycles'] - out['r22k_relay_term']['token'] + t + AR_PER_TOKEN * FEC['ds_rule']), 1))
    c = out['cases']['typical']
    out['headline'] = dict(o4_tok_s=c['o4_tok_s'], o4_fec_tok_s=c['o4_fec_tok_s'], r22k_tok_s=c['r22k_tok_s'],
                           r22k_fec_tok_s=c['r22k_fec_tok_s'], o4_exact=o4['exact'],
                           fec_headline_cycles=FECD['extra_fec_cycles_per_allreduce']['headline'],
                           fec_verdict=FECD['verdict'][:120],
                           price_fec0=dict(r22k=c['r22k_fec0_vmar_tok_s'], o4=c['o4_fec0_vmar_tok_s']),
                           price_fec100=dict(r22k=c['r22k_fec_vmar_tok_s'], o4=c['o4_fec_vmar_tok_s']),
                           price_fec240=dict(r22k=c['r22k_fecb_vmar_tok_s'], o4=c['o4_fecb_vmar_tok_s']),
                           layer_relay_cycles=dict(r22k=adopted['L1'], o4=o4['vs_s22ml7']['L1']))
    if a.refresh_step:
        mean_c, worst_c = (36 * x for x in a.refresh_step)
        tok0 = CLOCK / c['o4_fec0_vmar_tok_s']
        out['kv_refresh_provisional'] = dict(
            status='PROVISIONAL: DQ128 / P8 + SRAM row buffer on timed REFpb HBM (qwen-1010/b); the controller RTL refreshes in '
                   'a fixed rotation, so these may be optimistic; refresh-aware REFpb RTL in progress',
            step_increase_per_layer=dict(mean=a.refresh_step[0], worst=a.refresh_step[1]),
            o4_fec0_tok_s=dict(mean=round(CLOCK / (tok0 + mean_c), 1), worst=round(CLOCK / (tok0 + worst_c), 1)))
        out['headline']['kv_refresh_provisional'] = out['kv_refresh_provisional']['o4_fec0_tok_s']
    out['kv_basis'] = str(a.kv_basis.relative_to(ROOT))
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['headline']))


if __name__ == '__main__':
    main()
