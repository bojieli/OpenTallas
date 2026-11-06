from pathlib import Path
import re,json,hashlib
p=Path(__file__).parent
source=p.parent/'flat_binding/source_readonly.sv'
if not source.exists():source=Path('/srv/opentallas-scratch2/claude/wt/codex-bodyctl-rcp1-1106/rtl/hbm_accel/cores_split/reform_1105s/q3/ot_hfd_coll_q3_body_ctl.sv')
s=source.read_text();sha=hashlib.sha256(s.encode()).hexdigest();expected_sha='f732f5b5486b744e0480b9de4833d7d5665b94c5a72117c676c445f76998a318';assert sha==expected_sha
manifest=json.loads((p/'source_capture_manifest.json').read_text());assert manifest['base_source_sha256']==sha
assigns=list(re.finditer(r'^\s*assign (.*?) = (.*?);$',s,re.M))
esc=lambda x:re.findall(r'\\[^\s]+',x)
lex=lambda x:re.findall(r'\\[^\s]+|[{},]',x)
# An accepted capture must be literally an unconditional, single-statement posedge process.
allcaptures={}
for m in re.finditer(r'^  always @\(posedge ([A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])?)\)\s*\n    (_\d+_) <= ([^;]*);',s,re.M):
 allcaptures.setdefault(m[2],[]).append({'clock':m[1],'D':m[3],'source_statement':m[0],'reset':False,'enable':False})
def capture(reg):
 assert reg in allcaptures,('not literal unconditional posedge FF',reg)
 assert re.search(r'^\s*reg\s+(?:\[\d+:\d+\]\s+)?'+re.escape(reg)+r';$',s,re.M),('missing plain uninitialized reg declaration',reg)
 assert not re.search(r'(?<![A-Za-z_0-9])'+re.escape(reg)+r'\s*=(?!=)',s),('unexpected blocking/initialization writer',reg)
 # No additional conditional/reset/enable writer may coexist with the accepted process.
 writers=re.findall(r'(?<![A-Za-z_0-9])'+re.escape(reg)+r'\s*<=',s)
 assert len(writers)==1,(reg,'multiple sequential writers',len(writers))
 assert len(allcaptures[reg])==1
 return allcaptures[reg][0]
def conn(module):
 m=re.search(re.escape(module)+r'\s+(\w+)\s*\((.*?)\);',s,re.S);assert m
 return {a:b.strip() for a,b in re.findall(r'\.(clk_\w+)\(([^()]*)\)',m[2])}
outer=conn('ot_hfd_coll_q3_body_ctl__mc');middle=conn('ot_hfd_coll_q3_body_ctl_x')
expect={'clk_control':'clk','clk_program':'clk','clk_upipe':'{16{clk}}','clk_issue':'clk','clk_qslots':'{29{clk}}'}
for k,v in expect.items():
 assert re.sub(r'\s','',outer[k])==v,(k,outer[k]);assert middle[k]==k,(k,middle[k])
def root(clock):
 m=re.fullmatch(r'(clk_\w+)(?:\[(\d+)\])?',clock);assert m
 name,bit=m.groups();assert middle[name]==name
 v=outer[name]
 if bit is not None:
  n=re.fullmatch(r'\{(\d+)\{clk\}\}',re.sub(r'\s','',v));assert n and int(bit)<int(n[1])
 else:assert v=='clk'
 return 'clk'
input_rows=[];raw={};input_caps={}
for field,width in [('it',32),('b',16),('c',16),('d',16)]:
 matches=[]
 for m in assigns:
  names=re.findall(r'u_mul\.'+field+r'\[(\d+)\]',m[1])
  if len(names)==width and re.fullmatch(r'_\d+_',m[2]):matches.append((m,names))
 assert len(matches)==1,(field,len(matches));m,names=matches[0];q=m[2];cap=capture(q)
 assert [int(i) for i in names]==list(reversed(range(width)))
 bits=esc(cap['D']);assert len(bits)==width and re.sub(r'\\[^\s]+','X',cap['D']).replace('X','').strip().replace('{','').replace('}','').replace(',','').strip()==''
 assert root(cap['clock'])=='clk';raw[field]=bits;input_caps[field]={'register':q,**cap}
 aliases=esc(m[1]);assert len(aliases)==width
 for alias,bit,d in zip(aliases,reversed(range(width)),bits):input_rows.append({'alias_Q':alias,'register_Q':q,'register_bit':bit,'capture_D_scalar':d,'clock':cap['clock'],'root_clock':root(cap['clock']),'unconditional':True,'reset':False,'enable':False})
assert len(input_rows)==80
concat=lambda bs:'{ '+', '.join(b+' ' for b in bs)+' }'
vector=lambda bs:concat([concat(bs[i:i+8]) for i in range(0,len(bs),8)])
assert [o['register'] for o in manifest['outputs']]==['_237566_','_237567_','_237568_']
checks=[];output_caps=[]
for o,field in zip(manifest['outputs'],['b','c','d']):
 it=vector(raw['it']);step=vector(raw[field]);assert lex(it)==lex(o['iteration_D']),(o['output'],'iteration mismatch');assert lex(step)==lex(o['step_D']),(o['output'],'step mismatch')
 cap=capture(o['register']);assert cap['clock']==o['clock']=='clk_control';assert re.sub(r'\s+',' ',cap['source_statement']).strip()==re.sub(r'\s+',' ',o['old_capture']).strip();assert root(cap['clock'])=='clk'
 checks.append({'output':o['output'],'iteration_D_token_identity':True,'step_D_token_identity':True,'iteration_D_reconstructed':it,'step_D_reconstructed':step});output_caps.append({'register':o['register'],**cap,'root_clock':root(cap['clock'])})
products=[]
for field in ['pb','pc','pd']:
 regs={}
 for m in assigns:
  names=re.findall(r'u_mul\.'+field+r'\[(\d+)\]\[(\d+)\]',m[1])
  if len(names)==16 and re.fullmatch(r'_\d+_',m[2]):
   indices={int(n[0]) for n in names};assert len(indices)==1;ix=indices.pop();assert ix not in regs;regs[ix]=m[2]
 assert set(regs)==set(range(7))
 for ix,reg in sorted(regs.items()):
  cap=capture(reg);assert cap['clock']=='clk_control' and root(cap['clock'])=='clk';products.append({'field':field,'index':ix,'register':reg,**cap,'root_clock':root(cap['clock'])})
assert len(products)==21 and len(output_caps)==3
result={'verdict':'PASS','source_sha256':sha,'production_manifest_sha256':hashlib.sha256((p/'source_capture_manifest.json').read_bytes()).hexdigest(),'input_scalar_count':80,'input_vector_captures':input_caps,'scalar_rewinds':input_rows,'manifest_vector_checks':checks,'native_product_captures':products,'original_output_captures':output_caps,'wrapper_clock_bindings':{'top_to_mc':outer,'mc_to_x':middle,'all_used_capture_clocks':sorted({r['clock'] for r in input_rows+products+output_caps}),'audited_wrapper_ports':list(expect),'helper_clock':'clk_control','resolved_root_clock':'clk'},'scope':'Functional equality after original three-capture pipeline fill for defined arbitrary D inputs. Native input/product/output FFs have no reset; initial unknown states are not equated. Any upstream holds or reset-driven changes remain encoded in unconstrained D and are sampled on the same root clock. No added protocol cycles. Arithmetic source-binding SAT and helper three-edge stream proofs remain separate unchanged evidence.'}
(p/'capture_binding_audit.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS:80 exact scalar rewinds;3 manifest iteration/stride vectors match token-for-token;21 product+3 output captures unconditional/no reset/no enable; all same root clk.')
