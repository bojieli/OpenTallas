# S81-L20RD2 10-20: pre-gate native census of dsdv_idx_rg2 (paired reader; hardened head-key slices as the CLOSED view's
# liberty cell).  Same recipe as results/rtl/s81_l20tok_1020/native_e1 (c7ad5f455 / 2a006c746): external wrapper, ORFS
# RVT TT libs, the ot_keep_regs.tcl canonicalize hook (kept copies stay flops), flatten, abc -D 770, textbook 32 / 405.
from pathlib import Path
import gzip
p = Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs = []
for name in ['AO', 'INVBUF', 'OA', 'SEQ', 'SIMPLE']:
    f = next(p.glob('asap7sc7p5t_' + name + '_RVT_TT_nldm_*'))
    out = Path('/work') / (name + '.lib'); out.write_bytes(gzip.open(f, 'rb').read() if f.suffix == '.gz' else f.read_bytes()); libs.append(str(out))
hs_lib = '/work/physical/ref_tile/ot_hdc_v41x_idx_hslice_m5/views/ot_hdc_v41x_idx_hslice/ot_hdc_v41x_idx_hslice_tt.lib'
sources = ['rtl/lib/ot_rst_relay.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_prefix.sv',
           'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat_nr.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv',
           'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v']
rows = ['yosys read_liberty -lib ' + f for f in libs + [hs_lib]]
rows += ['yosys read_verilog -sv -DOT_IDX_HSLICE_HARD -DSYNTHESIS /work/' + f for f in sources]
porttext = Path('/work/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv').read_text().split('module dsdv_idx_rg2 #(', 1)[1].split(') (', 1)[1].split(');', 1)[0]
Path('/work/census_top.sv').write_text('module idxrg2_native_top (' + porttext + ');\ndsdv_idx_rg2 #(.SRAM_MACRO(1)) u (.*);\nendmodule\n')
rows += ['yosys read_verilog -sv /work/census_top.sv', 'yosys hierarchy -check -top idxrg2_native_top',
         'source /work/physical/common_flow/ot_keep_regs.tcl',
         'yosys synth -top idxrg2_native_top -flatten', 'yosys dfflibmap -liberty /work/SEQ.lib',
         'yosys abc ' + ' '.join('-liberty ' + f for f in libs) + ' -D 770', 'yosys clean', 'yosys stat',
         'yosys write_verilog -noattr /work/mapped.v', 'yosys write_verilog /work/mapped_attr.v']
Path('/work/synth.tcl').write_text('\n'.join(rows) + '\n')
