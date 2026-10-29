"""Copy the exact selected RTL and immutable macro models to owned runtime."""
from pathlib import Path
import subprocess,sys
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
paths='''rtl/hbm_next/idxn/ot_hnx_idxn_calendar.sv
rtl/hbm_next/idxq/ot_hnx_idxq_qctl.sv
rtl/hbm_next/idx/ot_hnx_idx_vm_query_static_n12.sv
rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv
rtl/hbm_accel/index/ot_hbm_idx_query_static.sv
rtl/hbm_accel/index/ot_hbm_idx_query_owned_native.sv
rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv
rtl/hdc/ot_hdc_delay_rf.sv
rtl/hdc/ot_hdc_delay.sv
rtl/hdc/ot_hdc_fpu.sv
rtl/hdc/ot_hdc_fp32_mul_pipe.sv
rtl/proto/ot_fp32_add_rne_pipe.sv
rtl/lib/ot_rst_relay.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v'''.splitlines()
for p in paths:(out/Path(p).name).write_bytes(subprocess.check_output(['git','show','HEAD:'+p],cwd=root))
here=Path(__file__).parent
for p in ['tb_idx_rows_numeric.sv','run.sh']:(out/p).write_bytes((here/p).read_bytes())
for rt,n in [(171,1566),(173,1568)]:
 p=root/f'results/tok_hbm_7_1029/prog/calendar_instructions_rt{rt}_vp1.hex'
 (out/f'prog{rt}.hex').write_bytes(p.read_bytes())
print('staged',len(paths),'selected RTL/macro files')
