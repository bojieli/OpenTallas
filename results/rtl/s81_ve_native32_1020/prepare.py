from pathlib import Path
import gzip
p=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM')
libs=[]
for name in ['AO','INVBUF','OA','SEQ','SIMPLE']:
 f=next(p.glob('asap7sc7p5t_'+name+'_RVT_TT_nldm_*'))
 out=Path('/work')/(name+'.lib');out.write_bytes(gzip.open(f,'rb').read() if f.suffix=='.gz' else f.read_bytes());libs.append(str(out))
sources=['rtl/lib/ot_rst_relay.sv', 'rtl/hdc/ot_hdc_fastfp.sv', 'rtl/hdc/ot_hdc_fp32_f12.sv', 'rtl/hdc/ot_hdc_fp32_mul_lat.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv', 'rtl/hdc/ot_hdc_prefix.sv', 'rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv', 'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv', 'rtl/hdc/v41x/ot_dsrom_su_add6.sv', 'rtl/hdc/v41x/ot_dsrom_su_norm.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_delay_rf.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fpu.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/hdc/ot_hdc_fastfp_lat_f12.sv', 'rtl/hdc/v41/ot_hdc_fsqrt.sv', 'rtl/hdc/v41/ot_hdc_fdiv.sv', 'rtl/hdc/v41/ot_hdc_softplus.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv', 'rtl/hdc/v41/ot_hdc_actquant.sv', 'rtl/hdc/v41x/ot_dsrom_aq12.sv', 'rtl/hdc/v41x/ot_dsrom_divc.sv', 'rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv', 'rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv', 'rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv', 'rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv']
rows=['read_liberty -lib '+f for f in libs]+['read_verilog -sv /work/'+f for f in sources]
rows+=['hierarchy -check -top ot_s81sl_ve','tcl /work/ot_keep_regs.tcl','synth -top ot_s81sl_ve -flatten','dfflibmap -liberty /work/SEQ.lib','abc '+' '.join('-liberty '+f for f in libs)+' -D 770','clean','stat','write_verilog -noattr /work/mapped.v','write_json /work/mapped.json']
Path('/work/synth.ys').write_text('\n'.join(rows)+'\n')
