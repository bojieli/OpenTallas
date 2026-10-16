#!/usr/bin/env python3
"""H-NETLIST/hceng 2026-10-16: v16 spec hceng_0030.json -- the static HC engine hc_eng (ot_hbm_hc_eng_static) and
its two host programme collars, bound to the four quadrant HC clients hc_<q> (ot_hbm_hc_q_static).

  hc_eng_tgt  ot_static_program_target TARGET 164: engine event programme (cfg rows + start base/limit/loops)
  hc_tbl_tgt  ot_static_program_target TARGET 165: bases/scales table rows (its programme-row write port);
              its start outputs have no consumer (a table is data, never launched); program_active = hc_eng's
  hc_eng      ot_hbm_hc_eng_static: consumes hc_<q>.x_wave_v/x_wave_word/x_wave and gathered_mix_* (HC_ENGINE_INPUTS,
              28 ports / 32,976 b) and drives hc_<q>.result_v/result_position/result (G-HC-ENG, 12 ports / 3,088 b).
    usage: hceng_spec_gen.py <basis_commit> <out.json>
"""
import json, sys

Q = ['SW', 'SE', 'NW', 'NE']
D = 'rtl/hbm_accel/generic/peers/static_hc/'
SRC = D + 'ot_hbm_hc_eng_static.sv'
DEPS = [D + 'ot_hbm_hc_eng_seq_static.sv', D + 'ot_hbm_hc_bank_static.sv', D + 'ot_hbm_hc_tail_unit_static.sv',
        D + 'ot_hdc_v41x_hcp_sys1_static.sv', D + 'ot_hgi_hc_tail_static.sv', 'rtl/hdc/v41x/ot_hdc_v41x_hcp.sv',
        'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv',
        'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fastfp_lat.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_sfu.sv',
        'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv', 'rtl/hdc/v41/ot_hdc_fdiv.sv', 'rtl/hdc/v41/ot_hdc_sinkhorn.sv',
        'rtl/hdc/v41/ot_hdc_sk_arith.sv', 'rtl/hdc/v41/ot_hdc_sk_recip_rom.sv',
        'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v',
        'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
TGT = 'rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv'
OWN = 'HC owner (H-NETLIST hceng)'
BENCH = ('rtl/test/tb_hbm_hc_eng_static.sv + tools/rtl_hbm_hc_eng_static_gate.py '
         '(results/rtl/hbm_hc_eng_0030/receipt.json)')
inst, edges, clocks = [], [], []


def E(s, d, bits, basis):
    edges.append(dict(src=s, dst=d, bits=bits, clock='stream', basis=basis))


inst.append(dict(name='hc_eng', master='ot_hbm_hc_eng_static', source=SRC, rtl_deps=DEPS, params={}, slot='hc_eng',
                 owner=OWN, note='Static full-form HC engine (HC.HC_MIX: 2,048 FP32 MAC lanes W256 in 8 bank tiles, '
                 '4 weight slots in 256 x 1024x256 macros, 2 exact tail units, event programme, bases/scales table). '
                 'Pin-registered (every input a pin flop, every output a flop). Area estimate ~9.5 mm2 '
                 '(results/uarch/hbm_hc_eng_0030/model.json). Bench ' + BENCH))
for name, tid, what in [('hc_eng_tgt', 164, 'engine event programme'), ('hc_tbl_tgt', 165, 'bases/scales table rows')]:
    inst.append(dict(name=name, master='ot_static_program_target', source=TGT, params=dict(TARGET=f"8'd{tid}", PCW=10),
                     slot=None, owner=OWN, note=f'F20 programme target {tid}: {what} of hc_eng (H-NETLIST ids 164..167 '
                     'reserved for hceng); host_cp_ingress TARGET_MASK must admit it'))
    for p, w in [('cfg_v', 1), ('cfg_target', 8), ('cfg_addr', 12), ('cfg_data', 256), ('desc_v', 1),
                 ('desc_base', 12), ('desc_limit', 13), ('desc_loops', 16), ('launch_v', 1)]:
        E(['host_cp_ingress', p], [name, p], w, TGT + ' F20 broadcast consumer (as hc_tgt_<q>)')
    E(['hc_eng', 'program_active'], [name, 'program_active'], 1,
      'launch/install interlock: no table or programme rows while the engine programme runs')
B = 'ot_static_program_target PCW10 port ABI -> ot_hbm_hc_eng_static programme (ot_hbm_hc_eng_seq_static) pins'
for a, b, w in [('program_cfg_we', 'cfg_we', 1), ('program_cfg_addr', 'cfg_addr', 10), ('program_cfg_data', 'cfg_data', 256),
                ('program_start_v', 'start_v', 1), ('program_start_base', 'start_base', 10),
                ('program_start_limit', 'start_limit', 11), ('program_start_loops', 'start_loops', 16)]:
    E(['hc_eng_tgt', a], ['hc_eng', b], w, B)
for a, b, w in [('program_cfg_we', 'tbl_we', 1), ('program_cfg_addr', 'tbl_addr', 10), ('program_cfg_data', 'tbl_data', 256)]:
    E(['hc_tbl_tgt', a], ['hc_eng', b], w, 'table rows: set s = rows 4s..4s+3 (bases 0..2, scales row 3 [95:0]) '
      'written through the target row port into the engine table macro')
BQ = ('rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_q_static.sv -> ot_hbm_hc_eng_static quadrant q slice '
      '(x_wave [q*8192+:8192], word [q*10+:10], gathered row [q*5+:5] pos [q*3+:3] data [q*32+:32]); bench ' + BENCH)
for qi, q in enumerate(Q):
    c = f'hc_{q}'
    for p, w in [('x_wave_v', 1), ('x_wave_word', 10), ('x_wave', 8192), ('gathered_mix_v', 1),
                 ('gathered_mix_row', 5), ('gathered_mix_pos', 3), ('gathered_mix_data', 32)]:
        E([c, p], ['hc_eng', p, qi * w, qi * w + w], w, BQ)
    for p, w in [('result_v', 1), ('result_position', 3), ('result', 768)]:
        E(['hc_eng', p, qi * w, qi * w + w], [c, p], w,
          BQ + '; emit event drives the quadrant result pins from tail unit u (fixed latency 496 + 1 edges)')
for i in ('hc_eng', 'hc_eng_tgt', 'hc_tbl_tgt'):
    clocks.append(dict(inst=i, port='clk', domain='stream', kind='clock'))
    clocks.append(dict(inst=i, port='rst_n', domain='stream', kind='reset'))
spec = dict(region='hceng', author='Claude H-NETLIST sub-agent hceng (2026-10-16)', basis_commit=sys.argv[1],
            instances=inst, retire_v15=[], edges=edges, drop_v15_edges=[], clocks=clocks, straps=[], gaps=[],
            notes=['Closes G-HC-ENG (hc_<q>.result_v/result_position/result, 12 ports / 3,088 b) and the required '
                   'output join HC_ENGINE_INPUTS (hc_<q>.x_wave_v/x_wave_word/x_wave + gathered_mix_*, 28 ports / '
                   '32,976 b) with ONE new die master hc_eng = ot_hbm_hc_eng_static and two existing '
                   'ot_static_program_target collars (TARGET 164 programme, 165 table).',
                   'HC weights: next (layer, attn|ffn) set reaches the quadrant VM by the existing DMA.LOAD / kshare '
                   'VM fill windows (vmks_<q><k>), and the hc_<q> residual reader moves it into the engine weight '
                   'macros as weight waves (1,920 waves = 1,920 edges a set, 4 quadrants staggered one wave an edge); '
                   'no dedicated HBM PC or new K-port wiring.',
                   'Static timing contract (programme time t of hc_eng): ingest event T -> quadrant wave n on '
                   'x_wave pins at t = T + 1 + 4n (hc_<q> reader launched 23 edges earlier); launch TL -> raw a at '
                   'TL + RAW0 + 10a; tail launch -> result 496 edges later; emit -> result pins +1, hc_<q> result '
                   'store +1 (pin) and its write-done +19. Measured values: results/rtl/hbm_hc_eng_0030/receipt.json.'])
json.dump(spec, open(sys.argv[2], 'w'), indent=1)
print(len(inst), len(edges), sum(e['bits'] for e in edges))
