import sys
from pathlib import Path
sys.path.insert(0,"/src/tools")
import run_abi3_physical as R
p=Path("/work/results/asap7/opentallas_ot_hgi_coll_gq_issue_asap7_ref_gate/base/1_2_yosys.v")
print("CANONICAL_NORMALISE",R.normalise_netlist(p,p))
