from pathlib import Path
import json,hashlib
p=Path(__file__).resolve().parent
m=json.loads((p/'source_manifest.json').read_text())
for row in m['files']:
 assert hashlib.sha256((p/row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
def source(name):
 return next((p/r['path']).read_text() for r in m['files'] if r['path'].endswith(name))
s=source('ot_host_if_pb2_observed.sv')
assert 'eng_token <= (sl_pos[eng_slot] < sl_plen[eng_slot]) ? pb_q : sl_tok[eng_slot];' in s
assert 'sl_tok[eng_slot] <= eng_next_token;' in s
n=source('qkd_host_native_token_endpoint_cancel.sv')
assert "wire[58:0]terminal_tag={job_epoch,6'd37,token_q,pos_q[12:0],6'd0};" in n
assert 'next_q<=rt;' in n
r=source('selected_qkd_kvs_emb.sv')
assert '.fill_begin(d2d__svc[24:24])' in r
assert '.fill_token(d2d__svc[109:92])' in r
assert '.fill_epoch(d2d__svc[89:74])' in r
# Source-branch arithmetic examples, not simulation or reachability claims.
def select(pos,plen,prompt,feedback):return prompt if pos<plen else feedback
cases=[dict(name='remaining_prompt',position=1,plen=2,prompt=11,feedback=13,input=select(1,2,11,13)),dict(name='generated',position=2,plen=2,prompt=11,feedback=13,input=select(2,2,11,13))]
assert cases[0]['input']==11 and cases[0]['input']!=cases[0]['feedback']
assert cases[1]['input']==13
# Pure TAG packing shows next token is separate from retained old input identity.
epoch=7;token=7;pos=0;gen=2;next_token=13
def tag(e,stage,t,pos,segment):return (e<<43)|(stage<<37)|(t<<19)|(pos<<6)|segment
request=tag(epoch,0,token,pos,0);terminal=tag(epoch,37,token,pos,0)
assert ((terminal>>19)&((1<<18)-1))==token
assert ((terminal>>43)&65535)==epoch
assert next_token!=token
assert 16+6+18+13+6==59 and 59+2+1==62 and 61-34==27
assert 5*62+27==337
out=dict(scope='source_literals_hashes_and_arithmetic_only',hashes=len(m['files']),prompt_cases=cases,request_tag=request,terminal_tag=terminal,result_next_token=next_token,old_tag_epoch=epoch,next_allocation_epoch=None,production_dates=None,simulations=0,qualification=False)
(p/'validation.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS: 6 hashes, 7 source authority assertions, 2 branch examples, TAG packing and conservative metadata arithmetic; no RTL execution')
