"""QW-CLUSTER3/HEAD 10-19: production four-user W slice goldens with the structurally safe head qfd_dv_lane_h_safe1
(rtl/qwen_dv/qfd_dv_head_safe1.sv), otherwise exactly run_production.py (same parent, same benches, same flags)."""
import os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for key in ('DV2_SAFE_RESET','DV2_SAFE_AMAX_RESET','DV2_SAFE_SCALAR_RESET','DV2_SAFE_CFG'):
    os.environ[key]='1'
sys.path.insert(0,str(ROOT/'rtl/test/qwen_dv'))
import dv_bench2 as B
B.SRCS2=[s.replace('qfd_dv_slice2_rsafe.sv','qfd_dv_slice2_landed_rsafe.sv').replace('qfd_dv_su8_entries.sv','qfd_dv_su8_landed.sv') for s in B.SRCS2]
B.XSRCS=[s.replace('rtl/qwen_dv/qfd_dv_su_lane.sv','rtl/test/qwen_dv/qfd_dv_su_lane_safe1_fixture.sv') for s in B.XSRCS]
B.SRCS2 += ['rtl/common/landed_parent/ot_pl_stream_land.sv','rtl/qwen_dv/qfd_dv_head_safe1.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v','physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v']
B.RESET_WARM=18
if __name__=='__main__': B.main()
