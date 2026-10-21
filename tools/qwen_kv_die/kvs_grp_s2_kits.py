#!/usr/bin/env python3
"""KV-GRP2 2026-10-19: ref_tile specs of the safe group tiles qkd_kvs_grp_s2 / qkd_kvs_grp_h_s2 (kv_grp_safe2.py).

Three parallel clock variants per tile (owner PARALLEL rule; bind the first to close, cancel the losers):
  s2a  symmetric centre-fed insertion-aware spine on ck and hck (OT_SPINE_SYM, no tree padding, safe balance, 16-sink leaves)
  s2b  the same spine with tree padding (OT_SPINE_TREE_PAD=1)
  s2c  TritonCTS per clock (no spine), same floorplan
Floorplan (all variants, SAFE 6): 388.8 x 388.8 (the die slot already requested for sq1), four p192 landing-row macros
(94.824 x 80.472, 5.09 contacts/um) in two columns on the 43.2 lattice (x 43.2 / 216, y 43.2 / 172.8: 78-um column
channel, 49-um row channel), full-width upper standard-cell band y >= 253.3.  Faces: N i_ctl / o_ctl, S i_up / o_dn,
E K / V request + response, W the four PC faces + clocks / resets / straps / EST (pin order = the sq1 die contract).

    python3 tools/qwen_kv_die/kvs_grp_s2_kits.py          # writes physical/ref_tile/qkd_kvs_grp{,_h}_s2{a,b,c}/spec.json
    then: python3 tools/ref_tile/ref_tile.py gen physical/ref_tile/<kit>/spec.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_grp_safe2 as S2  # noqa: E402
import kvs_grp_s2_bench as B  # noqa: E402

SIDE = 388.8
MACRO_AT = [(43.2, 43.2), (216.0, 43.2), (43.2, 172.8), (216.0, 172.8)]
SOURCES = [S2.OUT, S2.MACRO_DIR + '/' + S2.MACRO + '_bb.v'] + [
    'rtl/lib/ot_async_fifo.sv', 'rtl/lib/ot_reset_sync.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_front_cal.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_kv_lvl_land.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_cdc.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_hop.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_landing.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_ownership.sv',
    'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_phase_launch.sv',
    'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v',
]
W_ORDER = ['i_pc0', 'i_pc0_h', 'o_pc0', 'o_pc0_h', 'i_pc1', 'i_pc1_h', 'o_pc1', 'o_pc1_h', 'ck', 'hck', 'af__fault', 'afk',
           'afu', 'afv', 'hrst_n', 'rst_n', 'slg__cfg_group', 'slg__cfg_stack', 'x__est', 'y__est__0_1', 'i_pc2', 'i_pc2_h',
           'o_pc2', 'o_pc2_h', 'i_pc3', 'i_pc3_h', 'o_pc3', 'o_pc3_h']
FACES = dict(N=['i_ctl', 'o_ctl'], S=['i_up', 'o_dn'], E=['kreq', 'krsp', 'rsp', 'vreq'], W=W_ORDER)
VARIANTS = {
    'a': dict(clock='spine', orfs=dict(OT_SPINE_PORTS='ck,hck', OT_SPINE_SYM='1', OT_SPINE_TREE_PAD='0',
                                       OT_SPINE_SAFE_BALANCE='1', OT_SPINE_LEAF_N='16'),
              what='symmetric centre-fed insertion-aware spine on ck and hck, no tree padding, safe balance, 16-sink leaves'),
    'b': dict(clock='spine', orfs=dict(OT_SPINE_PORTS='ck,hck', OT_SPINE_SYM='1', OT_SPINE_TREE_PAD='1',
                                       OT_SPINE_SAFE_BALANCE='1', OT_SPINE_LEAF_N='16'),
              what='the s2a spine with tree padding'),
    'c': dict(clock='cts', orfs={}, what='TritonCTS per clock root (ck, hck), no spine'),
}


def widths(top):
    text = (ROOT / S2.OUT).read_text()
    return {n: w for d, w, n in B.ports(text, top)}


def ranges(top, faces):
    """pin ranges along each face, proportional to bit count (1-um gaps), the sq1 / kvs_tile_kits_rep convention"""
    w = widths(top)
    out = {}
    for f, names in faces.items():
        names = [n for n in names if n in w]
        tot = sum(w[n] for n in names)
        span = SIDE - 2.5 - 2.5 - (len(names) - 1) * 1.0
        x = 2.5
        for n in names:
            ln = max(0.11, span * w[n] / tot)
            out[n] = [round(x, 2), round(x + ln, 2)]
            x += ln + 1.0
    return out


def spec(kind, v):
    top = 'qkd_kvs_grp_s2' if kind == 'grp' else 'qkd_kvs_grp_h_s2'
    name = f'{top}{v}'
    cfg = VARIANTS[v]
    w = widths(top)
    faces = {f: [n for n in names if n in w] for f, names in FACES.items()}
    faces = {f: n for f, n in faces.items() if n}
    pr = ranges(top, faces)
    macros = [dict(view=S2.MACRO_DIR, count=1, inst=f'*g_pc?{q}?*u_rows', at=list(MACRO_AT[q]), orient='R0')
              for q in range(4)]
    benches = []
    for m in [0] + sorted(S2.MUTANTS):
        b = dict(name=f's2_m{m}', cmd=f'python3 tools/qwen_kv_die/kvs_grp_s2_bench.py --out {{RUN}}/bench/s2_m{m} '
                                     f'--cases m{m} --raw', threads=8, peak_ram_gb=16, needs=['verilator'])
        if m == 0:
            b.update(expect='pass', pass_regex=r'^S2_PASS checks=\d+ edges=6000 mut=0', min_count_regex=r'checks=(\d+)',
                     pass_witness='results/rtl/qwen_kv_die/kvs_grp_s2_1019/b1/m0.log')
        else:
            b.update(expect='fail', pass_regex=r'^S2_PASS ', fail_regex=rf'^S2_FAIL tile=\w+ output=\w+ edge=\d+ side=\d mut={m} ',
                     fail_witness=f'results/rtl/qwen_kv_die/kvs_grp_s2_1019/b1/m{m}.log')
        benches.append(b)
    hck_out = [p for p in w if p.startswith('o_pc') and p.endswith('_h')]
    s = dict(
        name=name, top=top, kind='tile', sources=SOURCES, params={}, clock_port='ck', reset_ports=['rst_n', 'hrst_n'],
        outline=dict(w=SIDE, h=SIDE, exact=True), layer_cap='M5', macros=macros, pins=faces, pin_ranges=pr,
        route=dict(pd=0.5, threads=8, peak_ram_gb=64, hold_margin_ns=0.03, macro_halo_um=6.48, io_hold_margin_ns=0.03,
                   pin_balance=dict(group_max=1, h='M4', v='M5')),
        recipe=3,
        purpose=(f'KV-GRP2 10-19: flat leaf kit of the structurally safe KV landing-group tile {top} '
                 f'(x{28 if kind == "grp" else 4} on the KV MU die; rtl {S2.OUT}, generated by tools/qwen_kv_die/kv_grp_safe2.py; '
                 f'clock variant {v}: {cfg["what"]}).'),
        job=dict(owner='Claude:KV-GRP2', branch='claude/kv-grp2-1019', tag=f's2{v}', benches=benches,
                 extra_paths=['rtl', 'tools/qwen_kv_die', 'results/rtl/qwen_kv_die/kvs_grp_s2_1019', S2.MACRO_DIR,
                              'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2', 'physical/qkd_kvs_kits'],
                 reroute_reason=dict(kind='rtl_change', reason=(
                     'KV-GRP2 structural redesign (owner: one failed route = redesign): sq1 clock FAIL 114/124 ps and the '
                     'sq2/sq3 gates retired on source prerequisites (y__tep alias hold -74.9 ps, unregistered i_ctl cones, '
                     '9.98 contacts/um SRAM faces, 8-deep LD shift chain).  New RTL qkd_kvs_grp_s2 (registered faces, landed '
                     'resets, p192 rows 5.09/um, LD ring, Stage 1 private ABI, DOMSPLIT o_pc 33+95), new pins, new macros.')),
                 views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}'),
        pin_regs=dict(enable=False, reason=(
            'The RTL registers every face (tools/qwen_kv_die/kv_grp_safe2.py): i_ctl / i_up / x__est land on kept face '
            'flops (one copy per consumer leaf), PC / K / V inputs land on the landing / row-control input flops, every '
            'output leaves a flop (no combinational input->output path); the ages are bench-proven against the unchanged '
            'tile (kvs_grp_s2_bench.py) and handed to the die schedule.  A flow-inserted pin stage would add an unpriced '
            'cycle.')),
        children=[], inter=[], io_flop_at_pins=dict(cols=4, allow_none=True), inhold=True, outhold=True,
        keep_pin_regs=True, pin_reg_split=True, hold_pad=dict(cell='HB2xp67_ASAP7_75t_R', out_cell='HB1xp67_ASAP7_75t_R'),
        structural_change=(
            'KV-GRP2 10-19 structural redesign of the KV landing group (successor of sq1/sq2/sq3): Stage 1 private ABI '
            '(no tok/tep aliases, scalar EST; H no o_dn), registered faces with kept per-leaf copies, per-domain 2-stage '
            'reset landing with kept per-leaf copies, landing rows on the 0.192-um contact-pitch build of the same SRAM '
            '(5.09 /um), LD delay ring, DOMSPLIT PC faces; floorplan two macro columns (78-um channel) + full-width upper '
            f'band; clock {cfg["what"]}.'),
        kits_b=dict(frame=[SIDE, SIDE], kit_outline=[SIDE, SIDE], count=28 if kind == 'grp' else 4,
                    rep_instance='slg_WS_0' if kind == 'grp' else 'slg_WS_4', rtl=S2.OUT, hck_inputs=['hrst_n'],
                    hck_outputs=hck_out, mixed_domain_ports=[], critical=None,
                    pin_bound_waiver=('E face 2171 bits / 388.8 um = 5.58 pins/um (K + V responses, 2 x 1024 data bits); '
                                      'std cells ~10-12k um2 + four p192 SRAMs 30.5k um2 in 151k um2: the perimeter, not '
                                      'the area, sets the outline (pin-bound waiver as sq1, coordinator-accepted).')),
        sdc_extra=[f'physical/qkd_kvs_kits/{name}_hck.sdc'], boundary_tcl=[f'physical/qkd_kvs_kits/{name}_hck_boundary.tcl'],
        clock=cfg['clock'],
        reset_landing=dict(enable=False, reason=(
            'The RTL lands both resets (qkd_kvs_grp_s2_rst): rst_n on ck and hrst_n on hck, each 2 stages in its own '
            'domain (async assert, synchronous release) + one kept final-stage copy per leaf; the flow landing takes one '
            'clock and would land hrst_n on ck.')),
        fill_reason=dict(pin_bound=('4.6k signal pins on a 388.8 square (E 5.58 /um, W 4.5 /um); the outline is the die '
                                    'slot of the sq1 square; synthesis area alone would give ~200 x 200.')),
    )
    if cfg['orfs']:
        s['orfs_vars'] = dict(cfg['orfs'])
    return s


def main():
    tmpl_sdc = Path(sys.argv[1]).read_text() if len(sys.argv) > 2 else None
    tmpl_btcl = Path(sys.argv[2]).read_text() if len(sys.argv) > 2 else None
    for kind in ('grp', 'grp_h'):
        for v in VARIANTS:
            s = spec(kind, v)
            d = ROOT / 'physical/ref_tile' / s['name']
            d.mkdir(parents=True, exist_ok=True)
            (d / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
            if tmpl_sdc:
                k = ROOT / 'physical/qkd_kvs_kits'
                k.mkdir(parents=True, exist_ok=True)
                (k / f'{s["name"]}_hck.sdc').write_text(
                    re.sub(r'qkd_kvs_grp(_h)?_sq1', s['name'], tmpl_sdc).replace(
                        'GENERATED by tools/qwen_kv_die/kvs_tile_kits.py specs', 'GENERATED by tools/qwen_kv_die/kvs_grp_s2_kits.py'))
                (k / f'{s["name"]}_hck_boundary.tcl').write_text(
                    re.sub(r'qkd_kvs_grp(_h)?_sq1', s['name'], tmpl_btcl).replace(
                        'GENERATED by tools/qwen_kv_die/kvs_tile_kits_rep.py', 'GENERATED by tools/qwen_kv_die/kvs_grp_s2_kits.py'))
            print(s['name'], {f: len(n) for f, n in s['pins'].items()})


if __name__ == '__main__':
    main()
