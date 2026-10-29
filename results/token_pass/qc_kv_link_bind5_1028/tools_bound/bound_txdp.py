#!/usr/bin/env python3
"""TOK-QK-XD3 10-26: read the BOUND D2D master TXDP word from a strict-bind output dir (tools/die_plan/bind.py --out).

  bound_txdp.py --die {qwen_compute,qwen_kvsys} BINDDIR [--json OUT]

Source of truth = the bound RTL the bind emitted (BINDDIR/rtl/*.sv): the single D2D master instance
  qwen_compute: qfd_d2d_static* #(... .TXDP(<v>) ...) u_d2d_rom
  qwen_kvsys:   qkd_d2d_static* #(... .TXDP(<v>) ...) u_d2d_kv
Cross-checked against BINDDIR/param_regen.json 'changed' (inst d2d_rom / d2d_kv, param TXDP, bound).  Exactly one
instance must exist and both sources must agree, else exit 1.  Prints the word as 8 hex digits (stdout last line).
"""
import argparse, glob, json, re, sys

INST = {'qwen_compute': ('qfd_d2d_static', 'u_d2d_rom', 'd2d_rom'), 'qwen_kvsys': ('qkd_d2d_static', 'u_d2d_kv', 'd2d_kv')}


def val(v):
    v = str(v).strip()
    m = re.fullmatch(r"(?:\d+)?'h([0-9a-fA-F_]+)", v)
    return int(m.group(1).replace('_', ''), 16) if m else int(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die', required=True, choices=sorted(INST))
    ap.add_argument('bind')
    ap.add_argument('--json')
    a = ap.parse_args()
    mod, inst, pinst = INST[a.die]
    hits = []
    pat = re.compile(rf"\b({mod}\w*)\s*#\(([^;]*?)\)\s*{inst}\s*\(", re.S)
    for f in sorted(glob.glob(f'{a.bind}/rtl/*.sv')):
        for m in pat.finditer(open(f, errors='replace').read()):
            t = re.search(r"\.TXDP\(([^)]+)\)", m.group(2))
            if t:
                hits.append(dict(file=f.split('/rtl/')[-1], module=m.group(1), value=val(t.group(1))))
    pr = json.load(open(f'{a.bind}/param_regen.json'))
    prv = [val(c['bound']) for c in pr.get('changed', []) if c.get('inst') == pinst and c.get('param') == 'TXDP']
    rec = dict(die=a.die, instance=inst, rtl=hits, param_regen=[f'{x:08x}' for x in prv])
    ok = len(hits) == 1 and all(x == hits[0]['value'] for x in prv)
    rec['ok'] = ok
    if ok:
        w = hits[0]['value']
        rec['word'] = f'{w:08x}'
        rec['ports'] = [(w >> (8 * p)) & 0xff for p in range(4)]
    if a.json:
        json.dump(rec, open(a.json, 'w'), indent=1)
    if not ok:
        print('BOUND_TXDP_ERROR', json.dumps(rec), file=sys.stderr)
        return 1
    print(f"BOUND_TXDP {a.die} {inst} {hits[0]['module']} ports={rec['ports']} param_regen={rec['param_regen']}", file=sys.stderr)
    print(rec['word'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
