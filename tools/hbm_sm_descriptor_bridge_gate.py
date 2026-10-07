#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,tempfile
from hbm_sm_descriptor_bridge_model import model
ROOT=Path(__file__).resolve().parents[1]
BASE='rtl/hbm_accel/control_20261007/descriptor/'
RTL=BASE+'ot_hbm_sm_descriptor_bridge.sv';TB=BASE+'tb_hbm_sm_descriptor_bridge.sv'
DEPS=['rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
def main():
 runs=[]
 with tempfile.TemporaryDirectory(prefix='sm-descriptor-gate-') as tmp:
  for hops,mut in [(0,None),(1,None),(12,None),(40,None),(81,None),(12,'reservation_as_delivery')]:
   rtl=(ROOT/RTL).read_text()
   if mut:rtl=rtl.replace('pending && a_ack && b_ack','pending && a_ready && b_ready')
   src=Path(tmp)/'dut.sv';src.write_text(rtl);exe=Path(tmp)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_hbm_sm_descriptor_bridge',f'-Ptb_hbm_sm_descriptor_bridge.HOPS={hops}','-o',str(exe),str(src),str(ROOT/TB),*[str(ROOT/p)for p in DEPS]],check=True)
   r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
   if (r.returncode==0)!=(mut is None):raise RuntimeError(r.stdout)
   runs.append(dict(hops=hops,mutation=mut,returncode=r.returncode,output=r.stdout.strip()))
 return dict(model=model(),scope='component finite transport; actual route/hops/timing unqualified',runs=runs,sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [RTL,TB,*DEPS,'tools/hbm_sm_descriptor_bridge_model.py','tools/hbm_sm_descriptor_bridge_gate.py']},passed=True,selected=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
