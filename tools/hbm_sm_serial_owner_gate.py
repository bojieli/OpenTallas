#!/usr/bin/env python3
"""Native full-shape control owner gate; arithmetic and physical closure excluded."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from hbm_sm_serial_owner_model import model
ROOT=Path(__file__).resolve().parents[1]
BASE='rtl/hbm_accel/control_20261007/'
OWNER=BASE+'ot_hbm_sm_serial_owner.sv'
TB=BASE+'tb_sm_serial_owner.sv'
INGRESS=BASE+'ot_hbm_sm_seq_ingress.sv'
FIXTURE='results/rtl/hbm_sm_command_20261007/stress_seq.hex'
DEPS=[INGRESS,'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
def main():
    runs=[]
    changes=[('positive',None,None),
      ('unmasked_final_beat',"group==12 ? {{1408{1'b0}},x_data[639:0]} : x_data",'x_data'),
      ('early_retirement','state==WAIT_DONE && arrived && published','state==WAIT_DONE && arrived'),
      ('zero_allocated_base','weight_base<=alloc_rsp_base','weight_base<=0'),
      ('bad_memory_response_address',None,None),('bad_x_identity',None,None),('bad_publication_identity',None,None)]
    with tempfile.TemporaryDirectory(prefix='hbm-sm-owner-') as d:
      for name,old,new in changes:
        owner=(ROOT/OWNER).read_text();tb=(ROOT/TB).read_text()
        if old:
          assert old in owner;owner=owner.replace(old,new)
        if name=='bad_memory_response_address':tb=tb.replace('mem_rsp_addr<=mem_req_addr','mem_rsp_addr<=mem_req_addr+4')
        if name=='bad_x_identity':tb=tb.replace('x_record=xrec','x_record=xrec+1')
        if name=='bad_publication_identity':tb=tb.replace('publication_record<=ops','publication_record<=ops+1')
        op=Path(d)/'owner.sv';op.write_text(owner);bp=Path(d)/'tb.sv';bp.write_text(tb)
        exe=Path(d)/'sim'
        subprocess.run(['iverilog','-g2012','-s','tb_sm_serial_owner','-o',str(exe),str(op),str(bp),*[str(ROOT/x) for x in DEPS]],check=True)
        r=subprocess.run(['vvp',str(exe),'+SEQ='+str(ROOT/FIXTURE)],text=True,capture_output=True)
        if (r.returncode==0)!=(name=='positive'):raise RuntimeError(name+' '+r.stdout)
        runs.append(dict(case=name,returncode=r.returncode,output=r.stdout.strip()))
    return dict(scope='native record-reader and full NC8 operand/descriptor/retirement owner; SM consumer and external memory/allocation/result peers are component testbench models',
        model=model(),fixture_origin='byte-identical 130-word stress seq.hex from existing dshbm_sm_pq_seq.py recovery positive fixture; 13 original records',
        fixture_source='/tmp/codex-claude-recovery-20261007/hbm-sm/gate_preflight_current/positive/stress_haz1_g0_smh_a1/seq.hex',
        sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [OWNER,TB,*DEPS,FIXTURE,'tools/hbm_sm_serial_owner_model.py','tools/hbm_sm_serial_owner_gate.py']},
        runs=runs,passed=True,selected=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
