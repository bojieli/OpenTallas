#!/usr/bin/env python3
"""HBM-RATE7 10-20 GEN2e5 layer (after l23): bind the two measured SM.MATVEC rate fixes in the d4g die contract.

(1) SMXL real x-batch path (HBM-SMXL2, DS SM.MATVEC 26,518/27,380 -> 18,429/21,941 edges dsA/dsB; DS 1148.3 -> 1340.4):
    svg_<q><k> (ot_hbm_svc_sm_group_rel_id): XSLOT=1, OPEN_IL=1.  xc_<q><k> (ot_hbm_svc_sm_xcal_rel_t): XSLOT=1 (the xc
    descriptor copy must accept descriptor[206:200] = xb, else xc fault, r1 xl_dsA fault 831).
    op_xb is BOUND, never tied: the record's x-store slot base xb travels in descriptor[206:200], which the die already
    carries on the existing desc_we/desc_addr/desc_data edges from cp_svg_<q><k>; issuer_rel copies it into the 53-b
    program context and feed_programmed_rel_id adds it to every issue word's xaddr[6:0] (mod 128) before sm_command.
    NO port and NO edge changes (CTXW 46 -> 53 is internal to the group).  XSLOT=0 compilers keep [206:200] = 0.
(2) Qwen wide INT8 front (HBM-QINT8B, Qwen 775.0 -> 1001.5): sm_<q><k> (ot_hbm_accel_smh_attn): INT8W=1 (command
    mode 3: one packed 128-code line an edge as two BF16 rows on the two column sides).  ENABLE_INT8 stays 1 (narrow
    path kept).  New rtl_deps: ot_hbm_sm_i8w_front.sv + this tree's ot_hbm_sm_attn_front_static.sv (INT8W param);
    ot_smh_int8_tile.sv (main: ENABLE_INT8 1 = the hard SAFE tile).  NO port / edge changes.
Both are parameter-only on existing masters: they need re-synthesis of the svc group / xc / SM masters and the PRE-GATE
native32 census on the mapped netlists before any gate; the compiler emits xb descriptors and mode-3 words.
Idempotent: re-application with the parameters already set is accepted and reports changed=0."""
import argparse, copy, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SVG, XC, SM = 'ot_hbm_svc_sm_group_rel_id', 'ot_hbm_svc_sm_xcal_rel_t', 'ot_hbm_accel_smh_attn'
SMX = 'rtl/hbm_accel/sm/attn/'
I8W_DEPS = [SMX + 'ot_hbm_sm_i8w_front.sv', SMX + 'ot_hbm_sm_attn_front_static.sv',
            'rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv']
SVC = 'rtl/hbm_accel/loader/service_native/'
SRC_SHA = [SVC + SVG + '.sv', SVC + 'ot_hbm_svc_sm_issuer_rel.sv', SVC + 'ot_hbm_svc_sm_feed_programmed_rel_id.sv',
           SVC + 'ot_hbm_svc_sm4pc_cdc_rel_id.sv', SVC + 'ot_hbm_svc_sm_xcal_rel.sv', SVC + XC + '.sv',
           SVC + 'ot_hbm_svc_static_sm_packed136.sv', SMX + 'ot_hbm_accel_smh_attn.sv'] + I8W_DEPS
WANT = {SVG: dict(XSLOT=1, OPEN_IL=1), XC: dict(XSLOT=1), SM: dict(INT8W=1)}
PFX = {SVG: 'svg_', XC: 'xc_', SM: 'sm_'}


def apply(original, root=ROOT):
    c = copy.deepcopy(original); I = c['instances']
    for f in SRC_SHA:  # the parameters must exist in this tree's RTL (no silent no-op bind)
        if not (root / f).exists():
            raise ValueError('missing source ' + f)
    for m, ps in WANT.items():
        src = (root / (SVC if m != SM else SMX) / (m + '.sv')).read_text()
        for p in ps:
            if not re.search(r'parameter\s+integer\s+' + p + r'\s*=', src):
                raise ValueError(f'{m}: no parameter {p} in this tree')
    rep = dict(layer='l24_sm_xslot_i8w', changed=0, instances={},
               sources={f: hashlib.sha256((root / f).read_bytes()).hexdigest() for f in SRC_SHA},
               ports_changed=0, edges_changed=0)
    for m, ps in WANT.items():
        names = sorted(n for n, v in I.items() if re.fullmatch(PFX[m] + r'(SW|NW|SE|NE)[0-7]', n))
        if len(names) != 16 or any(I[n]['master'] != m for n in names):
            raise ValueError(f'{m}: expected 16 {PFX[m]}* instances of this master, found {len(names)}')
        for n in names:
            v = I[n]; old = dict(v.get('params') or {})
            if m == SM and old.get('ENABLE_INT8') != 1:
                raise ValueError(n + ': ENABLE_INT8 1 expected (l13_int8)')
            new = dict(old, **ps)
            if new != old:
                v['params'] = new; rep['changed'] += 1
                v['note'] = v.get('note', '') + ' | l24 (HBM-RATE7): ' + ', '.join(f'{k}={x}' for k, x in ps.items())
            if m == SM:
                v['rtl_deps'] = sorted(set(v.get('rtl_deps') or []) | set(I8W_DEPS))
            rep['instances'][n] = ps
    return c, rep


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True)
    a = p.parse_args()
    op = __import__('gzip').open if a.inp.endswith('.gz') else open
    c = json.load(op(a.inp, 'rt')); c, r = apply(c)
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n'); Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print('L24_SM_XSLOT_I8W 16 svg XSLOT=1 OPEN_IL=1, 16 xc XSLOT=1, 16 sm INT8W=1; changed %d; ports/edges unchanged' % r['changed'])


if __name__ == '__main__':
    main()
