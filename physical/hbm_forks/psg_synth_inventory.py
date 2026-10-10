#!/usr/bin/env python3
"""Characterize full RTL using current ORFS synthesis, stopping before physical placement.
This intentionally produces no closure verdict or hardened-view claim.
"""
import sys,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
import run_abi3_physical as F
original=F.normalise_netlist
receipt=Path(sys.argv[1]);args=sys.argv[2:]
def stop_after_synth(src,dst):
    result=original(src,dst)
    path=Path(dst)
    if path.name=='1_2_yosys.v' and 'results' in path.parts:
        receipt.write_text(json.dumps({'schema':'hgi.psg.synth-inventory.v1','time':time.time(),'mapped_netlist':str(path),'mapped_netlist_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'mapped_netlist_bytes':path.stat().st_size,'normalization':result,'scope':'fullshape ORFS synthesis only; no floorplan/route/STA/export/closure','source_override':'ENABLE1 REARM1 NC8 NOG12 SYNCPHY1','current_flow_stop':'normalise mapped ORFS1_2_yosys output then exit before phase2'},indent=2)+'\n')
        raise SystemExit(0)
    return result
F.normalise_netlist=stop_after_synth
F.main(args)
