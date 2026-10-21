# S81-IDX3R 10-20: pre-gate native census recipe (same as results/rtl/s81_l20rd2_1020/native: ORFS RVT TT libs, the
# ot_keep_regs.tcl canonicalize hook (kept copies stay flops), flatten, abc -D 770, textbook 32 / 405).
#   python3 prepare.py rg3 | ctrl3 | ctrl2    (rg3 = dsdv_idx_rg3 with the closed hslice view; ctrl3 / ctrl2 =
#   dsfd_ctrl_rg3 / the record dsfd_ctrl_rg2 under -DS81CTRL_NATIVE32, the n32s CTRL view's define)
import sys, gzip
from pathlib import Path
which = sys.argv[1]
p = Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs = []
for name in ['AO', 'INVBUF', 'OA', 'SEQ', 'SIMPLE']:
    f = next(p.glob('asap7sc7p5t_' + name + '_RVT_TT_nldm_*'))
    out = Path('/work') / (name + '.lib'); out.write_bytes(gzip.open(f, 'rb').read() if f.suffix == '.gz' else f.read_bytes()); libs.append(str(out))
extra = []
if which == 'rg3':
    extra = ['/work/physical/ref_tile/ot_hdc_v41x_idx_hslice_m5/views/ot_hdc_v41x_idx_hslice/ot_hdc_v41x_idx_hslice_tt.lib']
    sources = ['rtl/lib/ot_rst_relay.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_prefix.sv',
               'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat_nr.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv',
               'rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv',
               'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv', 'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv',
               'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v']
    top, mod, inst, defs = 'idxrg3_native_top', 'dsdv_idx_rg3', 'dsdv_idx_rg3 #(.SRAM_MACRO(1))', '-DOT_IDX_HSLICE_HARD -DSYNTHESIS'
    modfile = 'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv'
else:
    m = 'dsfd_ctrl_rg3' if which == 'ctrl3' else 'dsfd_ctrl_rg2'
    sources = ['rtl/lib/ot_rst_relay.sv', 'rtl/dsrom_sys/s81_ph/ot_s81ph_afifo.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv',
               'rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g.sv', 'rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv',
               'rtl/dsrom_sys/s81_ph/ctrl/' + m + '.sv']
    top, mod, inst, defs = m + '_native_top', m, m, '-DS81CTRL_NATIVE32 -DSYNTHESIS'
    modfile = 'rtl/dsrom_sys/s81_ph/ctrl/' + m + '.sv'
rows = ['yosys read_liberty -lib ' + f for f in libs + extra]
rows += ['yosys read_verilog -sv ' + defs + ' /work/' + f for f in sources]
txt = Path('/work/' + modfile).read_text().split('module ' + mod + ' #(', 1)[1]
porttext = txt.split(') (', 1)[1].split(');', 1)[0]
Path('/work/census_top.sv').write_text('module ' + top + ' (' + porttext + ');\n' + inst + ' u (.*);\nendmodule\n')
rows += ['yosys read_verilog -sv /work/census_top.sv', 'yosys hierarchy -check -top ' + top,
         'source /work/physical/common_flow/ot_keep_regs.tcl',
         'yosys synth -top ' + top + ' -flatten', 'yosys dfflibmap -liberty /work/SEQ.lib',
         'yosys abc ' + ' '.join('-liberty ' + f for f in libs) + ' -D 770', 'yosys clean', 'yosys stat',
         'yosys write_verilog -noattr /work/mapped.v', 'yosys write_verilog /work/mapped_attr.v']
Path('/work/synth.tcl').write_text('\n'.join(rows) + '\n')
Path('/work/census_top.txt').write_text(top + '\n')
