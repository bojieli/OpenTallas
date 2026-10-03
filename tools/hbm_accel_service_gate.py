#!/usr/bin/env python3
"""Run pinned canonical RTL fixtures against original and HA4 successor.

No inference, Python controller, wall timeout, or production-source mutation.
Every run gets an exclusive evidence directory; failed receipts remain there.
"""
import argparse
import hashlib
import json
import re
import subprocess
import types
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='8564e79eaf906c820aec5eb92bfda1cca80ee43d'
ORIGINAL='rtl/model/qwen_kv_lifecycle_20261003/ot_gpu_qwen_kv_lifecycle_controller.sv'
SUCCESSOR='rtl/hbm_accel/service/ot_hbm_accel_kv_lifecycle.sv'
FIXTURE='tests/test_canonical_qwen_kv_controller.py'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
    src=subprocess.check_output(['git','show',BASE+':'+FIXTURE],cwd=ROOT,text=True)
    (out/'pinned_fixture.py').write_text(src)
    m=types.ModuleType('ha4_fixture'); m.__file__=str(ROOT/FIXTURE)
    exec(compile(src,str(ROOT/FIXTURE),'exec'),m.__dict__)
    cases=[]
    monitor='''
integer cycles=0, accepted=0;
always @(posedge clk) begin
 cycles<=cycles+1;
 if(cmd_valid && cmd_ready) begin accepted<=cycles; $display("CMD %0d %0d %0d",cmd_op,cmd_identity,cycles); end
 if(rsp_valid && rsp_ready) $display("RSP %0d %0d %0d",rsp_op,rsp_identity,cycles-accepted);
 if(payload_req_valid && payload_req_ready) $display("SECTOR %0d %0d %0d",payload_req_write,payload_req_sector,cycles);
end
'''
    def run_case(self,body,**kwargs):
        name=self._testMethodName
        for mode,rtl,modname in [('original',ORIGINAL,'ot_gpu_qwen_kv_lifecycle_controller'),
                                 ('successor',SUCCESSOR,'ot_hbm_accel_kv_lifecycle')]:
            d=out/name/mode; d.mkdir(parents=True)
            tb=m.bench(body,**kwargs).replace('ot_gpu_qwen_kv_lifecycle_controller',modname)
            tb=tb.replace('endmodule',monitor+'\nendmodule')
            (d/'tb.sv').write_text(tb)
            compile_run=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(ROOT/rtl),str(d/'tb.sv')],capture_output=True,text=True)
            (d/'compile.log').write_text(compile_run.stdout+compile_run.stderr)
            run=None
            if compile_run.returncode==0:
                run=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
                (d/'sim.log').write_text(run.stdout+run.stderr)
            log='' if run is None else run.stdout
            rec=dict(case=name,mode=mode,compile_exit=compile_run.returncode,
                     run_exit=None if run is None else run.returncode,
                     passed=run is not None and run.returncode==0 and 'PASS' in log,
                     commands=[list(map(int,x)) for x in re.findall(r'^CMD (\d+) (\d+) (\d+)$',log,re.M)],
                     responses=[list(map(int,x)) for x in re.findall(r'^RSP (\d+) (\d+) (\d+)$',log,re.M)],
                     sectors=[list(map(int,x)) for x in re.findall(r'^SECTOR (\d+) (\d+) (\d+)$',log,re.M)])
            (d/'receipt.json').write_text(json.dumps(rec,indent=1)+'\n'); cases.append(rec)
            self.assertTrue(rec['passed'],log[-2000:]+compile_run.stderr[-2000:])
    m.ControllerRTLTests.run_case=run_case
    # Directed RTL fixtures only; original source inventories and Python-only
    # APIs are unchanged and are not tests of the new timing repair.
    suite=unittest.TestSuite()
    for name in sorted(n for n in dir(m.ControllerRTLTests) if n.startswith('test_')):
        method=getattr(m.ControllerRTLTests,name)
        import inspect
        if 'self.run_case(' in inspect.getsource(method): suite.addTest(m.ControllerRTLTests(name))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [ORIGINAL,SUCCESSOR,'tools/hbm_accel_service_gate.py','tools/hbm_accel_service_model.py']}
    pairs=[]
    for name in sorted({c['case'] for c in cases}):
        pair={c['mode']:c for c in cases if c['case']==name}
        if set(pair)=={'original','successor'}:
            x,y=pair['original'],pair['successor']
            pairs.append(dict(case=name,response_identity_order_equal=[r[:2] for r in x['responses']]==[r[:2] for r in y['responses']],
                sector_order_equal=[r[:2] for r in x['sectors']]==[r[:2] for r in y['sectors']],
                response_latency_delta_cycles=[b[2]-a[2] for a,b in zip(x['responses'],y['responses'])]))
    ok=result.wasSuccessful() and all(p['response_identity_order_equal'] and p['sector_order_equal'] for p in pairs)
    record=dict(schema='opentallas.hbm_accel.ha4.directed.v1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        fixture_commit=BASE,fixture_sha256=hashlib.sha256(src.encode()).hexdigest(),source_sha256=pins,
        verdict='PASS_DIRECTED' if ok else 'FAIL_DIRECTED',cases=cases,comparisons=pairs,
        scope='actual RTL with test SRAM and held ready/valid endpoint fixtures; no production token/CDC/wire/refresh evidence',
        exact_program_gate='PENDING',area=None,route=None,SS_WNS=None,FF_WNS=None,adopt=False)
    (out/'record.json').write_text(json.dumps(record,indent=1)+'\n')
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
