#!/usr/bin/env python3
from pathlib import Path
import subprocess, json, re, hashlib
p=Path(__file__).resolve().parent
s=(p/'private/ot_host_if_pb2_observed_rc.sv').read_text()
old="""                D_ERR:
                    if (err_st != ST_OK || (ENABLE_RETAINED_COMMIT && (bad_next || poison_q))) begin
                        if (dp_ok) d_st <= D_IDLE;"""
new="""                D_ERR:
                    if ((ENABLE_RETAINED_COMMIT && !admission_ok) || (err_st != ST_OK)) begin
                        if ((ENABLE_RETAINED_COMMIT && !admission_ok) || dp_ok) d_st <= D_IDLE;"""
assert s.count(old)==1
m=s.replace(old,new)
d=p/'scheduler_descriptor_mutant_drop';d.mkdir(exist_ok=True)
(d/'source.sv').write_text(m)
b=(p/'scheduler_descriptor_bench.sv').read_text()
b=b.replace('SCHED_TIMEOUT case=', 'DESC_MISSING_ACCEPTED_ERROR case=')
b=b.replace('if(dut.d_st==7 && dut.ep_v && !dut.dp_ok)priority_collisions<=priority_collisions+1;', 'if(dut.d_st==7 && dut.ep_v && !dut.dp_ok)begin priority_collisions<=priority_collisions+1;$display("DESC_PRIORITY_COLLISION edge=%0d",edge_n);end')
(d/'bench.sv').write_text(b)
v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
with (d/'build.log').open('w') as f:
 rc=subprocess.call([v,'--binary','--timing','-Wno-fatal','--top-module','scheduler_descriptor_bench','--Mdir',str(d/'obj'),'-j','8',str(d/'bench.sv'),str(d/'source.sv')],stdout=f,stderr=subprocess.STDOUT)
assert rc==0
with (d/'fail.log').open('w') as f:
 rc=subprocess.call([str(d/'obj/Vscheduler_descriptor_bench'),'+CASE=27'],stdout=f,stderr=subprocess.STDOUT)
t=(d/'fail.log').read_text()
caught=rc!=0 and 'DESC_MISSING_ACCEPTED_ERROR' in t and 'DESC_PRIORITY_COLLISION' in t and 'COMMIT' in t and 'DESC_PUSH' not in t
r=dict(name='restore_faulty_D_ERR',case=27,exit=rc,caught=caught,fail_regex='DESC_MISSING_ACCEPTED_ERROR',requires=['DESC_PRIORITY_COLLISION','COMMIT','no DESC_PUSH'],source_sha256=hashlib.sha256(s.encode()).hexdigest(),mutant_sha256=hashlib.sha256(m.encode()).hexdigest())
(p/'scheduler_descriptor_mutant.json').write_text(json.dumps(r,indent=2)+'\n')
assert caught,r
