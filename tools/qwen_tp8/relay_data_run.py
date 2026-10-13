#!/usr/bin/env python3
"""Build the tp8b Qwen die once and record what the data-relay plan needs (relay-data 2026-10-13):
relay stages per bus, the generator's own pin-to-pin reach gate, the fine cut scan (results/arch/qwen_tp8_1012/cuts.py,
CAP_MODE v3: bits per cut vs usable tracks, relay pin faces included as hop endpoints) and relay_token_cost.

usage (repo root): python3 tools/qwen_tp8/relay_data_run.py OUTDIR   -> OUTDIR/relay_run.json, OUTDIR/rom_tp8b.json
Set OT_RELAY_DUMP=FILE for the allocator's per-chain dump, OT_RELAY_GATE=warn to record misses instead of raising."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, 'tools'); sys.path.insert(0, 'results/arch/qwen_tp8_1012')
import die_top_lint as D, cuts as C
import qwen_rom_fulldie_b3r2 as G

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); t = time.time()
D.QWEN_RECIPE = 'tp8b'; D._QW.clear(); D.QSRC = None
v, m = D.load_qwen()[:2]
ins = [dict(n=i.name, m=getattr(i, 'master', ''), x=i.x, y=i.y, w=i.w, h=i.h) for i in m['insts']]
json.dump(dict(insts=ins, buses=[(b, c, bits, [e[0] for e in eps]) for b, c, bits, eps in m['buses']]), open(out / 'rom_tp8b.json', 'w'))
C.CAP_MODE = 'v3'
A = C.Net(str(out / 'rom_tp8b.json'))
fine = [dict(ax=r['ax'], pos=float(r['pos']), win=[float(q) for q in r['win']] if isinstance(r['win'], (list, tuple)) else r['win'],
             bits=float(r['bits']), usable=float(r['usable']), util=float(r['util']), fam={str(k): float(x) for k, x in r['fam'].items()})
        for r in A.fine(top=40)]
try:
    cost = G.relay_token_cost(v, m)
except Exception as e:   # noqa: BLE001
    import traceback
    cost = dict(error=repr(e), trace=traceback.format_exc()[-1500:])
r = dict(m.get('r21_relays') or {})
rec = dict(schema='opentallas.qwen-tp8.relay-data-run.v1', recipe='tp8b', die=m['die'], build_s=round(time.time() - t),
           relays={k: r.get(k) for k in ('pitch_um', 'max_um', 'relays', 'masters', 'classes', 'clock_nets_missing', 'repaired',
                                         'unrepaired', 'cut_over', 'off_plan', 'relay_flop_bits', 'relay_area_mm2', 'reach_um',
                                         'max_pin_to_pin_um', 'over_reach')},
           tp8b_kv={k: (m.get('tp8b_kv') or {}).get(k) for k in ('kept_relays', 'torn_chains', 'pin_moves')},
           stage_of=m.get('r21_stage_of'), masters=sorted({i['m'] for i in ins if '_rly' in i['m']}),
           cuts=dict(tool='results/arch/qwen_tp8_1012/cuts.py', cap_mode='v3', rule='bits / usable tracks <= 0.60',
                     worst=max((f['util'] for f in fine), default=None), fine_top=fine), relay_token_cost=cost)
(out / 'relay_run.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps(dict(relays=r.get('relays'), max_pin_to_pin_um=r.get('max_pin_to_pin_um'), over_reach=len(r.get('over_reach') or []),
                      unrepaired=len(r.get('unrepaired') or []), worst_cut=rec['cuts']['worst'], build_s=rec['build_s'])))
