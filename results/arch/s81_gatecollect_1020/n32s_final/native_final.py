import sys,glob,json,hashlib
from pathlib import Path
sys.path.insert(0,"/audit/tools/ref_tile")
import native_census as C
libs=glob.glob("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*")+glob.glob("/src/physical/asap7_memory_macros/*/*_tt.lib")
sys.argv=["native_census","--netlist","/audit/grt.v","--top","dsfd_ctrl_rg2","--out","/audit/native_final.json"]+sum((["--liberty",p] for p in libs),[])
raise SystemExit(C.main())
