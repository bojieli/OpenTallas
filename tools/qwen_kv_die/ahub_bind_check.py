#!/usr/bin/env python3
"""KV-INTEG/AHUB 2026-10-18: bind check of the static die hub on the PLANNED static KV die (no case / GEN needed).

    ahub_bind_check.py --out OUT.json        (env: kvj-g2-env.sh + the KV-PLAN3 placing flags; prep's kv_die flags)

Builds the kv_die --split model as kvsys_prep's case does (--kv-wq-mirror --host-v14 --host-north --host-trees --v143,
OT_KV_STATIC_DIE=1) and checks, for the die instances ahub (qkd_ahub), pvfin (fr) and kvs_attn (ahs):
  every die port on a bus has the width of its BINDINGS RTL ports (parameter defaults), every RTL input of the hub is
  on a die bus, the legacy hub buses hs / ares are gone, and reports the plan-priced hub parameters (ahub_ages).
Exit 0 when the hub / fr / ahs faces are clean (the ASTK end of ap_<st> is reported, not gated: ASTK swap (a))."""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import kv_die as K  # noqa: E402
import kv_static_die as KSD  # noqa: E402
import die_port_bind_kv as PB  # noqa: E402


def die_ports(m, inst):
    w = defaultdict(int)
    for bid, cl, bits, eps in m['buses']:
        loads = list(eps) + list((m.get('forks') or {}).get(bid, []))
        for e in loads:
            if e[0] == inst:
                w[e[1]] = bits
    return dict(w)


def rtl_check(mst, dp):
    b = K.BINDINGS[mst]
    params, ports = PB.header((K.ROOT / b['file']).read_text(errors='replace'), b['module'])
    params = dict(params or {}, **{k: str(v) for k, v in (b.get('parameters') or {}).items()})
    rw = {p: PB.evalw(w, params) for p, (d, w) in ports.items()}
    sliced = b.get('sliced') or {}
    grp = defaultdict(int)
    for d_, w in dp.items():
        grp[sliced.get(d_, d_)] += w
    bad = [dict(die_port=d_, die=w, rtl=sum(rw[p] for p in b['ports'][d_])) for d_, w in grp.items()
           if d_ in b['ports'] and w != sum(rw[p] for p in b['ports'][d_])]
    nob = [d_ for d_ in dp if sliced.get(d_, d_) not in b['ports']]
    used = {p for d_ in grp for p in b['ports'].get(d_, [])}
    unin = sorted(p for p, (d, _) in ports.items() if d == 'input' and p not in used and p not in b.get('classed', {}))
    unout = sorted(p for p, (d, _) in ports.items() if d == 'output' and p not in used and p not in b.get('classed', {}))
    return dict(module=b['module'], file=b['file'], width_mismatch=bad, die_ports_not_bound=nob,
                rtl_inputs_unconnected=unin, rtl_outputs_unread=unout)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    K.HOST_V14.update(on=True, north=True, trees=True)
    K.V143['on'] = True
    m = K.build(K.R, kv_wq_leaves=True, kv_wq_binary=True, kv_wq_leaf_s=True, kv_wq_head=False, kv_wq_wide=True,
                kv_wq_mirror=True, split=True)
    by = {i.name: i for i in m['insts']}
    rec = dict(schema='opentallas.qwen_kv.ahub_bind_check.v1', ahub_static=KSD.AHUB_STATIC,
               ahub_master=by['ahub'].master, ahub_module=K.BINDINGS[by['ahub'].master]['module'])
    rec['ahub'] = dict(die_ports=die_ports(m, 'ahub'), **rtl_check(by['ahub'].master, die_ports(m, 'ahub')))
    rec['pvfin_fr'] = {k: v for k, v in die_ports(m, 'pvfin').items() if k in ('fr', 'fs')}
    rec['pvfin'] = rtl_check(by['pvfin'].master, die_ports(m, 'pvfin'))
    rec['kvs_attn_ahs'] = KSD.all_tiles()['kvs_attn']['ports'].get('ahs', {}).get('width')
    rec['legacy_hub_buses_left'] = [b[0] for b in m['buses'] if b[0] in ('hs', 'ares')]
    rec['hub_buses'] = {b[0]: dict(bits=b[2], eps=b[3], stages=m.get('relay_stages', {}).get(b[0]))
                        for b in m['buses'] if any(e[0] == 'ahub' for e in b[3])}
    rec['astk_ap_end'] = {st: rtl_check(by[f'astk_{st}'].master, die_ports(m, f'astk_{st}'))['width_mismatch']
                          for st in K.STACKS}
    rec['ahub_ages'] = KSD.ahub_ages(m)
    rec['static_die_opens_ahub'] = [o for o in m.get('static_die', {}).get('opens', []) if 'seq.ar' in o['where'] or
                                    'pvfin.fr' in o['where']]
    h = rec['ahub']
    ok = (rec['ahub_module'] == 'qkd_ahub_static_dw' and not h['width_mismatch'] and not h['die_ports_not_bound'] and
          not h['rtl_inputs_unconnected'] and not h['rtl_outputs_unread'] and rec['pvfin_fr'].get('fr') == 145 and
          not [x for x in rec['pvfin']['width_mismatch'] if x['die_port'] == 'fr'] and 'rz_valid' not in
          rec['pvfin']['rtl_inputs_unconnected'] and rec['kvs_attn_ahs'] == 165 and not rec['legacy_hub_buses_left'])
    rec['verdict'] = 'PASS' if ok else 'FAIL'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str) + '\n')
    print(f"AHUB_BIND {rec['verdict']} module={rec['ahub_module']} ahub_mismatch={h['width_mismatch']} "
          f"unconn={h['rtl_inputs_unconnected']} unread={h['rtl_outputs_unread']} fr={rec['pvfin_fr'].get('fr')} "
          f"ahs={rec['kvs_attn_ahs']} FR_OFS={rec['ahub_ages']['FR_OFS']} AP_OFS={rec['ahub_ages']['AP_OFS']}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
