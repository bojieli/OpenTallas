#!/usr/bin/env python3
"""L2H-GEN2E 10-19 l20s: the die IDX selector hb_idx__selector becomes ot_hbm_idx_selector_static_sel (selected-only).

The die reads only selected_v / selected_line / fault of the selector. Its emit-readback face (op 8: out_v 4, out_line
2368) and observation face (threshold_observe 16, selected_observe 56) had no consumer: 2,444 unread bits (held class
selector_optional_readback). The successor master has no such ports and no registers behind them (4,816 flops removed);
op 8 raises its sticky fault (the production IDX compiler never issues op 8). selected_v / selected_line / fault are
cycle-exact with the canonical for every op stream without op 8 (bench tools/hbm_die_v16/idx_selector_sel_bench.sh).
Fails closed if any removed port has a sink edge or the retained outputs differ. No view is admitted (fresh synthesis).
"""
import argparse, copy, gzip, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
INST = 'hb_idx__selector'
OLD = 'ot_hbm_idx_selector_static'
NEW = 'ot_hbm_idx_selector_static_sel'
SRC = 'rtl/hbm_accel/index/' + NEW + '.sv'
REMOVED = {'out_v': 4, 'out_line': 2368, 'threshold_observe': 16, 'selected_observe': 56}
KEPT_OUT = ['fault', 'selected_line', 'selected_v']


def apply(original, root=ROOT):
    c = copy.deepcopy(original)
    v = c['instances'][INST]
    if v['master'] != OLD or v.get('params', {}) != {}:
        raise ValueError(f'{INST}: unexpected master {v["master"]} {v.get("params")}')
    for p, w in REMOVED.items():
        if v['ports'].get(p, {}).get('direction') != 'output' or v['ports'][p]['bits'] != w:
            raise ValueError(f'{INST}.{p}: unexpected port')
    sinks = [e for e in c['edges'] if e['source'][0] == INST and e['source'][1] in REMOVED]
    if sinks:
        raise ValueError(f'{INST}: removed port has a consumer {sinks[0]["sink"]}')
    kept = sorted({e['source'][1] for e in c['edges'] if e['source'][0] == INST})
    if kept != KEPT_OUT:
        raise ValueError(f'{INST}: retained outputs differ {kept}')
    removed_bits = 0
    for p, w in REMOVED.items():
        del v['ports'][p]; removed_bits += w
    v.update(master=NEW, source=SRC)
    v['note'] = v.get('note', '') + ' | l20s: selected-only selector ot_hbm_idx_selector_static_sel (no emit/observe faces; L2H-GEN2E)'
    before = len(c['open_outputs'])
    c['open_outputs'] = [o for o in c['open_outputs'] if not (o[0] == INST and o[1] in REMOVED)]
    dropped = before - len(c['open_outputs'])
    if dropped != len(REMOVED):
        raise ValueError(f'open_outputs: expected {len(REMOVED)} entries, dropped {dropped}')
    nst = 0
    for s in c.get('straps', []):
        if s.get('inst') == INST:
            if s.get('port') in REMOVED:
                raise ValueError('strap on a removed port')
            s['master'] = NEW; nst += 1
    c['masters'][OLD] = c['masters'].get(OLD, 0) - 1
    if c['masters'][OLD] <= 0:
        del c['masters'][OLD]
    c['masters'][NEW] = c['masters'].get(NEW, 0) + 1
    c['summary']['masters'] = len([m for m, k in c['masters'].items() if k])
    c['summary']['open_output_ports'] -= dropped
    r = dict(layer='l20s_idx_selector_sel', instance=INST, old_master=OLD, master=NEW, source=SRC,
             source_sha256=hashlib.sha256((Path(root) / SRC).read_bytes()).hexdigest(),
             removed_ports=REMOVED, removed_bits=removed_bits, open_outputs_dropped=dropped, straps_remastered=nst,
             retained_outputs=KEPT_OUT, added_edges=0, cycles_changed=0,
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
    print(f'L20S_IDX_SELECTOR_SEL removed_bits={r["removed_bits"]} open_outputs_dropped={dropped_s(r)}')


def dropped_s(r):
    return r['open_outputs_dropped']


if __name__ == '__main__':
    main()
