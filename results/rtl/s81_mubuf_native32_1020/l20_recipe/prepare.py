from pathlib import Path
import gzip
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[]
for name in ['AO','INVBUF','OA','SEQ','SIMPLE']:
 f=next(p.glob('asap7sc7p5t_'+name+'_RVT_TT_nldm_*'))
 out=Path('/work')/(name+'.lib');out.write_bytes(gzip.open(f,'rb').read() if f.suffix=='.gz' else f.read_bytes());libs.append(str(out))
sources=['rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv', 'rtl/hdc/v41x/ot_hdc_v41x_idx.sv', 'rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg.sv', 'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v']
rows=['read_liberty -lib '+f for f in libs]+['read_verilog -sv /work/'+f for f in sources]
porttext=Path('/work/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg.sv').read_text().split(') (',1)[1].split(');',1)[0]
Path('/work/census_top.sv').write_text('module idxrg_native_top ('+porttext+');\ndsdv_idx_rg #(.SRAM_MACRO(1)) u (.*);\nendmodule\n')
rows+=['read_verilog -sv /work/census_top.sv','hierarchy -check -top idxrg_native_top','synth -top idxrg_native_top -flatten','dfflibmap -liberty /work/SEQ.lib','abc '+' '.join('-liberty '+f for f in libs)+' -D 770','clean','stat','write_verilog -noattr /work/mapped.v','write_json /work/mapped.json']
Path('/work/synth.ys').write_text('\n'.join(rows)+'\n')
