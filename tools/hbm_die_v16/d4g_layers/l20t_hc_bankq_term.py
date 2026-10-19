#!/usr/bin/env python3
"""LH-UNREAD F-T (10-19): the four HC ring terminal banks hcb_<q>7 become ot_hbm_hc_bankq_term_static.

Bank 7 is the last bank of each quadrant chain: its forward descriptor (o_v, o_ss, o_nv, o_wa, o_xa; 29 b) has no
consumer (held unread class terminal_chain_control, 4 x 29 = 116 bits). The terminal master has no such ports; every
retained output is cycle-exact with ot_hbm_hc_bankq_static (bench tb_hc_bankq_term_eq). Fails closed if any removed
port has a sink edge, if the instance is not a CPI1/CPO1 plain bank, or if the retained wiring differs.
The die copy is an l14-style private namespace (scoped_d4g/hcbt.sv, identifier-only, inverse byte-exact).
No view is admitted: the new master needs fresh source-bound synthesis.
"""
import argparse, copy, gzip, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from l14_scoped_rtl import scope_family  # noqa: E402

OLD = 'ot_hbm_hc_bankq_static'
NEW = 'ot_hbm_hc_bankq_term_static'
TERMS = ['hcb_SW7', 'hcb_SE7', 'hcb_NW7', 'hcb_NE7']
REMOVED = {'o_v': 1, 'o_ss': 1, 'o_nv': 7, 'o_wa': 10, 'o_xa': 10}
G = 'rtl/hbm_accel/generic/peers/static_hc/'
FAMILY = dict(master=NEW, sources=[
    G + 'ot_hbm_hc_bank_static.sv', G + 'ot_hbm_hc_bankq_term_static.sv',
    'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
    'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/v41x/ot_hdc_v41x_hcp.sv', 'rtl/lib/ot_rst_relay.sv',
    'rtl/hdc/v41/ot_hdc_fsqrt.sv', 'rtl/hdc/v41/ot_hdc_fsqrt_c12.sv'])


def apply(original, root=ROOT):
    c = copy.deepcopy(original)
    fam = scope_family(Path(root), 'hcbt', FAMILY)
    removed_bits = 0
    for n in TERMS:
        v = c['instances'][n]
        if v['master'] != OLD or v['params'] != {'CPI': 1, 'CPO': 1}:
            raise ValueError(f'{n}: not a CPI1/CPO1 plain ring bank ({v["master"]} {v["params"]})')
        for p, w in REMOVED.items():
            if v['ports'].get(p, {}).get('direction') != 'output' or v['ports'][p]['bits'] != w:
                raise ValueError(f'{n}.{p}: unexpected port')
        sinks = [e for e in c['edges'] if e['source'][0] == n and e['source'][1] in REMOVED]
        if sinks:
            raise ValueError(f'{n}: removed forward port has a consumer {sinks[0]["sink"]} -- not a chain terminal')
        kept_out = sorted(e['source'][1] for e in c['edges'] if e['source'][0] == n)
        if kept_out != ['f_out', 'sum_out', 'wfault']:
            raise ValueError(f'{n}: retained outputs differ {kept_out}')
        for p, w in REMOVED.items():
            del v['ports'][p]; removed_bits += w
        v.update(master=NEW, source=fam['source'], rtl_deps=[])
        v['note'] += ' | l20t: chain TERMINAL -> ot_hbm_hc_bankq_term_static (no forward descriptor ports; LH-UNREAD F-T)'
    before = len(c['open_outputs'])
    c['open_outputs'] = [o for o in c['open_outputs'] if not (o[0] in TERMS and o[1] in REMOVED)]
    dropped = before - len(c['open_outputs'])
    if dropped != len(TERMS) * len(REMOVED):
        raise ValueError(f'open_outputs: expected {len(TERMS) * len(REMOVED)} entries, dropped {dropped}')
    c['masters'][OLD] -= len(TERMS); c['masters'][NEW] = len(TERMS)
    c['summary']['masters'] = len([m for m, k in c['masters'].items() if k])
    c['summary']['open_output_ports'] -= dropped
    for s in c.get('straps', []):
        if s.get('inst') in TERMS:
            raise ValueError('terminal bank carries a strap: unexpected')
    r = dict(layer='l20t_hc_bankq_term', instances=TERMS, old_master=OLD, master=NEW, source=fam['source'],
             removed_ports=REMOVED, removed_bits=removed_bits, open_outputs_dropped=dropped,
             scoped_family=fam, generic_sha256=hashlib.sha256((Path(root) / (G + NEW + '.sv')).read_bytes()).hexdigest(),
             retained_outputs=['sum_out', 'f_out', 'wfault'], added_edges=0, cycles_changed=0,
             qualification='SOURCE_ONLY_NEEDS_SYNTH (no view admitted)')
    return c, r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True)
    a = p.parse_args()
    with gzip.open(a.inp, 'rt') if a.inp.endswith('.gz') else open(a.inp) as f:
        c = json.load(f)
    c, r = apply(c)
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n')
    Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print(f'L20T_HC_BANKQ_TERM terminals={len(TERMS)} removed_bits={r["removed_bits"]} open_outputs_dropped={r["open_outputs_dropped"]}')


if __name__ == '__main__':
    main()
