#!/usr/bin/env python3
"""Build source-exact TT CORE/SCALE candidates from the die lead's pin grant."""
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'physical/qwen_tt_partition_1015'
R = 'rtl/qwen_sys/tt_tree_partition_20261015'
WIDTHS = dict(clk=1, rst_n=1, me_acc_o=24, me_idle_o=1, me_prog_o=16,
  up_fault=1, land_cnt=16, t_sel_e=13, t_tv_e=13, tr_fault=16,
  p_v_e2=1, p_f_e2=113, p_am=306, p_fault=6, fab_fault=1, ov=1,
  mx_we=1, mx_addr=24, mx_mask=16, mx_data=512, cmd=380, ret=95,
  scale_tag=91, scale_v=1, scale_rst_n=1)


def bits(names, widths):
    return [n if widths[n] == 1 else f'{n}[{i}]' for n in names for i in range(widths[n])]


def snap(x):
    return round(round(x / .048) * .048, 6)


def main():
    P.mkdir(parents=True, exist_ok=True)
    old = json.loads((ROOT / 'rtl/qwen_sys/tt_tree_partition_20261015/source_manifest.json').read_text())
    core_faces = dict(W=['p_am', 'p_fault', 'p_f_e2', 'p_v_e2', 't_sel_e', 't_tv_e', 'up_fault'],
      S=['mx_we', 'mx_addr', 'mx_mask', 'mx_data', 'land_cnt'],
      E=['cmd', 'ret', 'me_acc_o', 'me_idle_o', 'me_prog_o', 'ov', 'fab_fault', 'tr_fault', 'clk', 'rst_n'],
      N=['scale_tag', 'scale_v', 'scale_rst_n'])
    scale_widths = dict(clk=1, rst_n=1, tag_payload=91, s3_v=1, scale_re=1, scale_gre=24, scale_addr=576)
    scale_faces = dict(W=['scale_addr', 'scale_gre', 'scale_re', 'clk'], S=['tag_payload', 's3_v', 'rst_n'])
    plans = {'core': {}, 'scale': {}}

    def put(which, name, face, pos):
        coord = {'W': [.096, snap(pos)], 'E': [345.504, snap(pos)],
                 'S': [snap(pos), .096], 'N': [snap(pos), 215.904]}[face]
        assert name not in plans[which]
        plans[which][name] = dict(face=face, layer='M4' if face in ('W', 'E') else 'M5', xy=coord)

    for i, n in enumerate(bits(core_faces['W'], WIDTHS)):
        put('core', n, 'W', 5.424 + .384*i)
    sbits = bits(core_faces['S'], WIDTHS)
    for i, n in enumerate(sbits):
        put('core', n, 'S', 172.8 - (len(sbits)-1)*.192 + .384*i)
    ebits = bits(core_faces['E'][:-2], WIDTHS)
    for i, n in enumerate(ebits):
        k = i if i < 267 else i - 267
        put('core', n, 'E', (8.64 if i < 267 else 117.504) + .336*k)
    put('core', 'clk', 'E', 108)
    put('core', 'rst_n', 'E', 112.032)
    nbits = bits(core_faces['N'], WIDTHS)
    seam = [168.384 + .096*i for i in range(len(nbits))]
    assert len(nbits) == 93
    for n, x in zip(nbits, seam):
        put('core', n, 'N', x)
    for n, x in zip(bits(scale_faces['S'], scale_widths), seam):
        put('scale', n, 'S', x)
    for band, center in enumerate([50.016, 108., 166.032]):
        names = [f'scale_addr[{band*192+i}]' for i in range(192)]
        names += [f'scale_gre[{band*8+i}]' for i in range(8)]
        if band == 1:
            names.insert(100, 'scale_re')
        start = snap(center - .048*(len(names)-1))
        for i, n in enumerate(names):
            put('scale', n, 'W', start + .096*i)
    put('scale', 'clk', 'W', 190.032)
    record = dict(schema='opentallas.tt_partition_pin_candidate.v1',
      authority='Q-COMPUTE-DIE /root/qwen_compute_1417, 2026-10-15 14:33-14:36',
      outer_frame=[777.6, 1814.4], outline=[345.6, 216],
      homes={'core': [43.2, 777.6], 'scale': [43.2, 1015.2]},
      status='candidate: exact RTL and physical/native gates required before adoption',
      independent_clock_entries=['core.clk', 'scale.clk'],
      clock_delivery='same PLL frequency; each leaf pin phi minus measured leaf R',
      data_cycles_added=0, seam_bits=93, seam_wire_um=21.792,
      source_manifest=old, pins=plans)
    for which, mapping in plans.items():
        xy = [(x['layer'], *x['xy']) for x in mapping.values()]
        assert len(xy) == len(set(xy)), 'pin collision'
        assert all(0 <= x['xy'][0] <= 345.6 and 0 <= x['xy'][1] <= 216 for x in mapping.values())
        text = '# Candidate top-down pin contract; numeric identities retained.\n'
        for n, x in mapping.items():
            text += f"place_pin -pin_name {{{n}}} -layer {x['layer']} -location {{{x['xy'][0]:.6f} {x['xy'][1]:.6f}}}\n"
        (P / f'{which}_pins.tcl').write_text(text)
    (P / 'pin_plan.json').write_text(json.dumps(record, indent=2) + '\n')
    sources = (ROOT / R / 'sources.txt').read_text().splitlines()
    sources = [s.replace('_r2c2.v', '_r2c2_bb.v') if '/asap7_memory_macros/' in s else s for s in sources if not s.endswith('tb_tt_tree_partition.sv')]
    benches = [dict(name=f'tt_split_m{m}_p{prod}',
      cmd=f'bash {P.relative_to(ROOT)}/run_exact.sh {m} {prod} {{RUN}}/bench/tt_m{m}',
      expect='fail' if m else 'pass', threads=4, peak_ram_gb=8, needs=['verilator'],
      **({'fail_regex': 'TT_SPLIT_FAIL.*valid_scale_errors=[1-9]'} if m else {'pass_regex': 'TT_SPLIT_PASS.*PROD=1'}))
      for m, prod in [(0, 1), (1, 0), (2, 0)]]
    for which, faces, top in [('core', core_faces, 'qfd_tt_core_leaf'), ('scale', scale_faces, 'qfd_tt_scale_leaf')]:
        spec = dict(name=top, top=top, kind='tile', sources=sources, params={}, clock_port='clk',
          reset_ports=['rst_n'], outline=dict(w=345.6, h=216), recipe=2, layer_cap='M5',
          pins=faces, io_tcl=f'{P.relative_to(ROOT)}/{which}_pins.tcl',
          macros=[dict(view='physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2',
            count=1, at=[32.4, y], orient='R0', inst=f'*u_{"tag" if which=="core" else "pretag"}*g_b?{b}?*u_m')
            for b, y in enumerate([43.2, 129.6])],
          route=dict(pd=.5, threads=8, peak_ram_gb=16, hold_margin_ns=.03, macro_halo_um=5.4),
          io_flop_at_pins=dict(cols=4, allow_none=False), inhold=True, outhold=True,
          keep_pin_regs=True, pin_reg_split=True, hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
          orfs_vars=dict(POST_IO_PLACEMENT_TCL='physical/common_flow/macro_channel_block.tcl',
            POST_RESIZE_TCL='physical/common_flow/post_resize_relocate.tcl', OT_CHANNEL_BLOCK_UM='20', OT_ROW_MIN_UM='6'),
          structural_change='Actual functional CORE/SCALE partition of the failing 10622-FF/4-SRAM TT tree; '
            'separate clock roots, each owns two real SRAMs in a W column with >=20um corridors, '
            'existing registered 93-bit seam across21.6um candidate gap, all output stations retained, zero added data edges. '
            'Replaces t4 congestion3405 and insertion382/spread107.6; no inherited clock/native qualification.',
          slot_change_request='Q-COMPUTE-DIE 14:33-14:36 candidate two345.6x216 homes inside777.6x1814.4; physical/qwen_tt_partition_1015/pin_plan.json',
          job=dict(owner='Codex:Q-COMPUTE-ELEM1417', branch='codex/qwen-compute-elements-1417', tag='fs1',
            hold_merge=True, purpose='TT real functional partition candidate, native clocks/pins unqualified until measured',
            benches=benches, extra_paths=[R, str(P.relative_to(ROOT)), 'tools/qwen_split/derive_tt_tree_partition.py']))
        p = P / f'{which}.json'
        p.write_text(json.dumps(spec, indent=2) + '\n')
        subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen', str(p)], cwd=ROOT, check=True)
    print('CORE/SCALE source-exact candidate kits and all pin identities generated')


if __name__ == '__main__':
    main()
