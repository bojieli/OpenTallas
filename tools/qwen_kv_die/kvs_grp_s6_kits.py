#!/usr/bin/env python3
"""KV-GRP6 2026-10-20: ref_tile specs of the s6 group tiles (kv_grp_safe6.py: response payload delay in SRAM rings).

Floorplan (SAFE 5 / 6, both tiles, all variants): the s3 388.8 square, pins and the four p192 landing-row macros
unchanged (x 43.2 / 216, y 43.2 / 172.8; PC rd faces W).  The 32 ring macros (ot_sram_1r1w_4x32_m1_p192_grp_rsp,
19.656 x 14.328, pins on W / E only) sit in four ABUTTED N-S stacks of 8 (pitch 14.352 = height + 0.024, bare N / S
faces: ref_tile abutted_stack), MY so each read face points E (towards the rsp / krsp exit copies):
  middle column x 163.2 (25.2 um W / 33.1 um E channels): PC0 ring y 22.176.. (beside PC0), PC2 ring y 157.008..
  E column      x 335.52 (24.7 um W / 31.5 um E channels): PC1 ring y 22.176..,          PC3 ring y 157.008..
Each ring sits between its PC's read face and the E exit flops, centred between the bit's krsp and rsp pins (all
planned out_data -> ring and ring -> exit wires < 405 um); the 20-um gap at y 137..157 and the upper band (y > 278)
stay open for E-W routing.  Variants (owner PARALLEL rule): a = spine, no tree padding; b = spine + tree padding.

    python3 tools/qwen_kv_die/kvs_grp_s6_kits.py r            # synth-smoke kits qkd_kvs_grp{,_h}_s6r (RTL tops)
    then: python3 tools/ref_tile/ref_tile.py gen physical/ref_tile/<kit>/spec.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_grp_safe6 as S6  # noqa: E402
import kvs_grp_s2_kits as K  # noqa: E402

PITCH = 14.352
COLS = {0: (163.2, 22.176), 2: (163.2, 157.008), 1: (335.52, 22.176), 3: (335.52, 157.008)}
NOTE = (' KV-GRP6 s6 (Codex s5 storage audit c1e5bec49): the 1024-b response payload passed four unchanged flop '
        'captures (PC out e0 -> hop e1 -> idata e2 -> exit e3; the middle three a >= 3-deep delay line, SAFE 5).  s6: '
        'per PC branch the payload delay is a genuine SRAM ring (8 x 4x32 1R1W macros, write slot wp at e1, read the '
        'previous slot at e2, exit copies at e3; unreset self-phasing pointers, read != write slot), payload cleared '
        'exactly as the old hop cleared it; metadata keeps its hop; two kept exit copies on both tiles; +0 cycles.')


def ring_macros(pat):
    out = []
    for b in range(4):
        x, y0 = COLS[b]
        for k in range(8):
            out.append(dict(view=S6.RMACRO_DIR, count=1, inst=pat(b, k), at=[x, round(y0 + k * PITCH, 3)], orient='MY',
                            at_exact=True))
    return out


def spec_r(kind):
    K.GEN = 's6r'
    K.GEN_NOTE['s6r'] = K.GEN_NOTE['s3'] + NOTE
    s = K.spec(kind, 'a')
    top = S6.TOPS[0] if kind == 'grp' else S6.TOPS[1]
    s['name'] = top[:-1] + '6r'
    s['top'] = top
    s['sources'] = [s['sources'][0], S6.OUT, S6.RMACRO_DIR + '/' + S6.RMACRO + '_bb.v'] + s['sources'][1:]
    s['macros'] += ring_macros(lambda b, k: f'*g_hop?{b}?*g_m?{k}?*u_m')
    s['route']['synth_keep_modules'] = list(S6.KEEP)
    s['purpose'] = (f'KV-GRP6 10-20 SYNTH SMOKE ONLY (never routed / submitted): RTL {top} ({S6.OUT}); its mapped '
                    'netlist feeds the bounded-driver structural generator (kv_grp_safe5.py) whose output is gated.')
    s['job'].update(owner='Claude:KV-GRP6', branch='claude/kv-grp6-ring-1020', tag='s6r', benches=[])
    base = 'qkd_kvs_grp' if kind == 'grp' else 'qkd_kvs_grp_h'   # the s3a hck boundary (same ports / clocks)
    s['sdc_extra'] = [f'physical/qkd_kvs_kits/{base}_s3a_hck.sdc']
    s['boundary_tcl'] = [f'physical/qkd_kvs_kits/{base}_s3a_hck_boundary.tcl']
    s['structural_change'] += NOTE
    return s


def main():
    for kind in ('grp', 'grp_h'):
        s = spec_r(kind)
        d = ROOT / 'physical/ref_tile' / s['name']
        d.mkdir(parents=True, exist_ok=True)
        (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
        print(s['name'], s['sdc_extra'], s['boundary_tcl'], len(s['macros']))


if __name__ == '__main__':
    main()
