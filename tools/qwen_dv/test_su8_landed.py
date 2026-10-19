"""Run real slice2 goldens against experimental landed SU8 (fleet only)."""
import os
from pathlib import Path
import sys
os.environ["DV2_SAFE_RESET"]="1"
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"rtl/test/qwen_dv"))
import dv_bench2 as B
B.SRCS2=[s.replace("qfd_dv_slice2_rsafe.sv","qfd_dv_slice2_landed_rsafe.sv").replace("qfd_dv_su8_entries.sv","qfd_dv_su8_landed.sv") for s in B.SRCS2]
B.XSRCS=[s.replace("qfd_dv_su_lane.sv","qfd_dv_su_lane_landed.sv") for s in B.XSRCS]
B.SRCS2 += ["rtl/common/landed_parent/ot_pl_land.sv","rtl/common/landed_parent/ot_pl_stream_land.sv"]
# Added reset release leaf contributes two deterministic boot edges only.
B.RESET_WARM=10
if __name__=="__main__": B.main()
