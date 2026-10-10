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


def sha16(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--o4', type=Path, required=True, help='L3 run of option4_die.py: {stage_cycles: {L0, L1, L2}, exact}')
    ap.add_argument('--o4-name', default='o4')
    ap.add_argument('--extra', type=Path, nargs='*', default=[], help='further L3 runs (sensitivities), name=path')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    rp = json.loads((D / 'reprice.json').read_text())
    sr = json.loads((D / 'split_relays.json').read_text())
    o4rec = json.loads((D / 'rom_r22ko4.json').read_text())
    ref = sr['reference']['s22ml7']
    adopted = sr['runs'][sr['adopted_for_price'].split()[0]]['vs_s22ml7']

    def run_of(path):
        r = json.loads(Path(path).read_text())
        sc = r['stage_cycles']
        return dict(exact=bool(r.get('exact')), L0=sc['L0'], L1=sc['L1'], L2=sc.get('L2'),
                    vs_s22ml7=dict(L0=sc['L0'] - ref['L0'], L1=sc['L1'] - ref['L1']))
    o4 = run_of(a.o4)
    out = dict(schema='opentallas.qwen-kv-die.reprice-o4.v1', date='2026-10-10', clock_hz=CLOCK,
               inputs={str(p.relative_to(ROOT)): sha16(p) for p in (D / 'reprice.json', D / 'split_relays.json',
                                                                      D / 'rom_r22ko4.json')} | {str(a.o4): sha16(a.o4)},
               r22k_relay_term=dict(run=sr['adopted_for_price'], L0=adopted['L0'], layer=adopted['L1'],
                                    token=adopted['L0'] + 35 * adopted['L1']),
               o4_run=dict(name=a.o4_name, **o4), cases={})
    o4_token = o4['vs_s22ml7']['L0'] + 35 * o4['vs_s22ml7']['L1']
    out['o4_relay_term'] = dict(L0=o4['vs_s22ml7']['L0'], layer=o4['vs_s22ml7']['L1'], token=o4_token)
    st = o4rec['crossing_bus_stages']
    kvd_extra = max(0, st.get('o4_kvd', 0) - 12) + max(0, st.get('o4_kok', 0) - 13)
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
            kvd_bound_tok_s=round(CLOCK / (tok + fec + 36 * kvd_extra), 1))
    out['bounds'] = dict(
        kvd_kok_extra_stages_per_layer=kvd_extra,
        kvd_note='charged in kvd_bound_tok_s only if the KV-die launch waits on the control tile\'s descriptor word '
                 '(36 layers x the extra one-way stages of kvd + kv_ok); fix: announce the KV descriptor from seq_su '
                 '(its controller decodes the same instruction) or carry it with the q word',
        tree_words=dict(pword_0=st.get('pword_0'), tt_ty=st.get('tt_ty'), r22k=dict(pword_0=39, tt_ty=39),
                        note='band words reach the 2 x 2 upper-tile group +8 stages later than the r22k tree top (TWS '
                             'sensitivity run), tt_ty +3'))
    for e in a.extra:
        name, path = e.split('=', 1)
        r = run_of(path)
        t = r['vs_s22ml7']['L0'] + 35 * r['vs_s22ml7']['L1']
        out.setdefault('sensitivities', {})[name] = dict(**r, token_term=t, tok_s_typical=round(
            CLOCK / (rp['cases']['typical']['token_cycles'] - out['r22k_relay_term']['token'] + t + AR_PER_TOKEN * FEC['ds_rule']), 1))
    c = out['cases']['typical']
    out['headline'] = dict(o4_tok_s=c['o4_tok_s'], o4_fec_tok_s=c['o4_fec_tok_s'], r22k_tok_s=c['r22k_tok_s'],
                           r22k_fec_tok_s=c['r22k_fec_tok_s'], o4_exact=o4['exact'],
                           layer_relay_cycles=dict(r22k=adopted['L1'], o4=o4['vs_s22ml7']['L1']))
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['headline']))


if __name__ == '__main__':
    main()
