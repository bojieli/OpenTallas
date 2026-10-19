#!/usr/bin/env python3
"""Audit delayed HC pre provenance and isolate NORMR's measured model delta.

This is a partial analytical projection, never a native token qualification.
The immutable price remains unchanged. No current-HC wait is charged to pre.
"""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_price as dp
import dv_layer_price as lp

ROOT = dp.ROOT

def audit():
    g = lp.facts(ROOT / 'results/arch/s81_dv_1016/p4l/plan.json',
                 ROOT / 'results/arch/s81_dv_1016/landing/p4l3/land_plan.json', True)
    out = dict(status='PARTIAL_NOT_NATIVE', native_token_cycles=None, native_token_rate=None,
               finding='NORMR consumes previous sublayer pre, not current sublayer pre',
               operand_sources={'attn.hc_pre': 'entry.previous_ffn.pre (row 1008; physical transfer unbound)',
                                'ffn.hc_pre': 'attn.pre (row 1000; full producer/transfer unbound)'},
               blockers=['entry pre transfer/row lifetime not source-bound',
                         '16-slice norm composition and full token execution not measured'],
               measured_delta=dict(norm_imm_go_to_partial=112, normr_go_to_partial=115,
                                   source='results/rtl/s81_layer_tput_1018/compiler/bench_vp/check.json'),
               workloads={}, sources={})
    for p in ['tools/s81_dv/dv_layer_fixtures.py', 'tools/s81_dv/dv_layer_compile.py',
              'tools/s81_dv/dv_price.py', 'tools/s81_dv/layer_prog/lower_vpx.py']:
        out['sources'][p] = hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    for wl, name in [('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')]:
        doc = json.loads((dp.TP / (name + '.json')).read_text())
        delta, _ = dp.dv_deltas(doc, g)
        _, old = dp.solve_with_wave(doc, delta)
        nodes = [n['id'] for n in doc['nodes'] if n.get('op') in ('attn.quant', 'ffn.norm.scale')]
        changed = dict(delta)
        for i in nodes:
            changed[i] = changed.get(i, 0) + 3
        _, new = dp.solve_with_wave(doc, changed)
        out['workloads'][wl] = dict(projection_only=True, baseline_dv_cycles=old,
                                    normr_adjusted_cycles=new, added_cycles=new-old,
                                    relative_cycle_loss_pct=100*(new-old)/new,
                                    changed_nodes=len(nodes), unexplained_wait_1416_charged=False)
    return out

if __name__ == '__main__':
    print(json.dumps(audit(), indent=1))
