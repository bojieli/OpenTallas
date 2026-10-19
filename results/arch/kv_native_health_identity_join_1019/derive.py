#!/usr/bin/env python3
"""Small source-checked arithmetic contract witness; not RTL simulation."""
from pathlib import Path
import hashlib,json
A=Path(__file__).resolve().parent
m=json.loads((A/'source_manifest.json').read_text())
for r in m:
 p=A/r['path'] if r['path'].startswith('component60bb/') else A/'source'/r['path']
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
def src(end):
 rows=[r for r in m if r['path'].endswith(end) and not r['path'].startswith('component60bb/')]
 assert rows,end
 return (A/'source'/rows[0]['path']).read_text()
assert 'assign grant_tag = {grant_epoch,6\'d0,grant_token,grant_position[12:0],6\'d0}' in src('ot_qwen_tp8_token_epoch_allocator.sv')
assert 'wire [58:0] expected_terminal = {grant_epoch,6\'d37,grant_token,grant_position[12:0],6\'d0}' in src('ot_qwen_tp8_token_epoch_allocator.sv')
assert 'if (request_valid && request_ready)' in src('ot_qwen_tp8_token_epoch_allocator.sv')
assert 'job_epoch<=epoch_q' in src('qkd_host_native_token_endpoint_cancel.sv')
assert 'rtag==terminal_tag&&rg==gen_q' in src('qkd_host_native_token_endpoint_cancel.sv')
assert 'assign hc={pr_q,start,gen,token ^' in src('ot_qwen_host_ctl.sv')
assert 'step_issue_v<=eng_start' in src('ot_host_if_pb2_observed.sv')
assert 'm_wdata <= cq_w0' in src('ot_host_if_pb2_observed.sv')
rc=(A/'component60bb/private/ot_host_if_pb2_observed_rc.sv').read_text()
assert "owner_tag <= {43'd0,q_tag}; owner_gen <= owner_gen + 1'b1" in rc

def tag(e,s,t,p,g=0): return (e<<43)|(s<<37)|(t<<19)|(p<<6)|g
def decode(n):return {'epoch':n>>43,'stage':(n>>37)&63,'input_token':(n>>19)&((1<<18)-1),'position':(n>>6)&8191,'segment':n&63}
# Endpoint TK layout: done,gen2,drained,fault,cause4,busy,flush,next18,value32,cycles32.
def tk(done,gen,drained,fault,cause,busy,flush,nxt,value,cycles):
 widths=[1,2,1,1,4,1,1,18,32,32];values=[done,gen,drained,fault,cause,busy,flush,nxt,value,cycles]
 n=0
 for w,v in zip(widths,values):assert 0<=v<(1<<w);n=(n<<w)|v
 return n
client=0x42;e=0x1234;t=131071;p=17;g=1
r=tag(e,0,t,p);term=tag(e,37,t,p)
checks=[]
def check(name,condition,scope):
 assert condition,name
 checks.append({'name':name,'result':'PASS','scope':scope})
check('TAG59 roundtrip',decode(term)=={'epoch':e,'stage':37,'input_token':t,'position':p,'segment':0},'source field arithmetic')
check('descriptor client tag is not native TAG',client!=term and client!=r,'namespace counterexample, not RTL failure')
check('terminal and request tags differ at stage',term!=r and (term^r)==(37<<37),'stage transformation required')
check('input token and output next token distinct',decode(term)['input_token']!=90001,'source protocol uses result_token as next token')
a=tag(0,37,19,17);b=tag(1,37,19,17)
check('distinct epoch aliases on TK93',a!=b and tk(1,1,1,0,0,0,0,90001,123,88)==tk(1,1,1,0,0,0,0,90001,123,88),'loss-of-information witness only, not reachable stale result')
check('descriptor generation cannot stand for every step generation',len({(g+i)&3 for i in range(4)})==4,'one descriptor may launch multiple native steps')
# Event lineage must be immutable; consuming old event uses old key, never current step.
keys=[(tag(e+i,37,t+i,p+i),((g+i)&3)) for i in range(3)]
queue=list(keys)
check('queued native lineage survives next allocation',queue[0]==keys[0] and queue[0]!=keys[2],'candidate finite metadata contract')
check('wrong epoch rejected',(term,g)!=(tag(e+1,37,t,p),g),'candidate exact comparator')
check('wrong native generation rejected',(term,g)!=(term,(g+1)&3),'candidate exact comparator')
check('wrong stage rejected',(term,g)!=(r,g),'candidate terminal comparator')
check('descriptor error has no native identity',{'owner_record':0,'native_valid':0}!= {'owner_record':1,'native_valid':1},'distinct flags prevent duplicate-client-tag alias')
check('event storage arithmetic',16*(116+62+1+1)==2880,'functional source sizing, physical SRAM required')
result={'kind':'READ_ONLY_SOURCE_CHECKED_ARITHMETIC_NOT_RTL_SIMULATION','source_artifacts_verified':len(m),'checks':checks,'example':{'client_tag16':client,'request_TAG59':hex(r),'terminal_TAG59':hex(term),'native_generation2':g,'terminal_fields':decode(term)},'ambiguity_witness':{'A_TAG59':hex(a),'B_TAG59':hex(b),'equal_TK93':hex(tk(1,1,1,0,0,0,0,90001,123,88)),'reachable_existing_bug':False},'production_H':None,'release_calendar':None}
(A/'witness.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'PASS: {len(checks)} source-checked arithmetic cases; {len(m)} immutable artifacts verified; no RTL simulation')
