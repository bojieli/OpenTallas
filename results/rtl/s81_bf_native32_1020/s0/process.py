import gzip,hashlib,importlib.util,json,re,shutil,subprocess,sys
from pathlib import Path
W=Path('/work');src=Path('/src');L=W/'libs';L.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def runys(name,script,expect=0):
 (W/(name+'.ys')).write_text(script)
 r=subprocess.run(['yosys','-Q','-T','-q','-l',str(W/(name+'.log')),'-s',str(W/(name+'.ys'))],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (W/(name+'.stdout')).write_text(r.stdout)
 if expect==0:assert r.returncode==0,(name,r.stdout[-3000:])
 return r
libs=[];manifest=[]
for family in ('AO','INVBUF','OA','SEQ','SIMPLE'):
 ps=list(Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('asap7sc7p5t_'+family+'_RVT_SS_*.lib*'));assert len(ps)==1,ps
 p=ps[0];raw=p.read_bytes();data=gzip.decompress(raw) if p.suffix=='.gz' else raw
 q=L/(family+'.lib');q.write_bytes(data);libs.append(q)
 manifest.append(dict(original_path=str(p),original_sha256=sha(p),loaded_path=str(q),loaded_sha256=sha(q)))
load='\n'.join('read_liberty -lib '+str(p) for p in libs)+'\n'
v=W/'results/asap7/bf_s0_bound/base/1_2_yosys.v'
runys('mapped_json',load+f'read_verilog {v}\nhierarchy -check -top ot_v41_fadd_s0\nwrite_json /work/mapped.json\n')
sys.path.insert(0,'/tools');import svc7_bound_graph as B
spec=importlib.util.spec_from_file_location('native','/admission/tools/ref_tile/native_census.py');N=importlib.util.module_from_spec(spec);spec.loader.exec_module(N)
roles,_=N.liberty_roles(libs)
d=json.loads((W/'mapped.json').read_text());m,c,i,o,origins,clones=B.bound(d,'ot_v41_fadd_s0',24,())
used=sorted({x['type'] for x in c.values()});assert all(t in roles and not roles[t]['sequential'] for t in used),used
assert not m.get('memories'),m.get('memories')
drivers={b:n for n,cell in c.items() for p,bs in cell['connections'].items() if cell['port_directions'][p]=='output' for b in bs}
assert not B.cyclic_cells(i,drivers)
text=B.emit(m,c,i,o,'ot_v41_fadd_s0_n32');(W/'native.v').write_text(text)
modelnames=set(used)|{'INVx1_ASAP7_75t_R','BUFx2_ASAP7_75t_R'}
harness=['module model_harness();']
for k,t in enumerate(sorted(modelnames)):
 pins=[]
 for pn,role in roles[t]['pins'].items():
  if role['direction']=='internal':continue
  assert role['direction'] in ('input','output'),(t,pn,role)
  pins.append('.'+pn+'('+("1'b0" if role['direction']=='input' else '')+')')
 harness.append(t+' u'+str(k)+'('+','.join(pins)+');')
harness.append('endmodule');(W/'model_harness.sv').write_text('\n'.join(harness)+'\n')
models='\n'.join('read_liberty -ignore_miss_func '+str(p) for p in libs)+'\nread_verilog -overwrite /src/canonical_ASR_normalized.v\nread_verilog -overwrite /src/canonical_DFF_normalized.v\nread_verilog /work/model_harness.sv\nhierarchy -check -top model_harness\nproc\nwrite_verilog /work/library_model_all.v\n'
runys('models',models)
allmodels=(W/'library_model_all.v').read_text();blocks={}
for match in re.finditer(r'(?m)^module\s+\\?([^\s(]+).*?\bendmodule',allmodels,re.S):blocks[match.group(1)]=match.group(0)
# Include the explicit BUF negative-control cell model as well as emitted inverters.
modelnames=set(used)|{'INVx1_ASAP7_75t_R','BUFx2_ASAP7_75t_R'}
assert all(t in blocks for t in modelnames),modelnames-blocks.keys()
(W/'models_used.v').write_text('\n\n'.join(blocks[t] for t in sorted(modelnames))+'\n')
(W/'miter.sv').write_text('module miter(input valid_in,input[31:0] a,b,output bad);wire[104:0] gold,cand;ot_v41_fadd_s0 original(.valid_in(valid_in),.a(a),.b(b),.o0(gold));ot_v41_fadd_s0_n32 candidate(.valid_in(valid_in),.a(a),.b(b),.o0(cand));assign bad=|(gold^cand);endmodule\n')
base='read_verilog -sv /work/models_used.v /src/ot_v41_fadd2.sv /src/ot_prefix.sv {native} /work/miter.sv\nhierarchy -check -top miter\nproc\nflatten\nopt_clean\nstat\nselect -assert-none t:$*ff* t:$*latch* t:$mem*\nwrite_json /work/{prefix}_prepared.json\nsat -set-def-inputs -prove bad 0 -verify -show-inputs -show-outputs\n'
runys('proof',base.format(native='/work/native.v',prefix='proof'))
assert 'SUCCESS!' in (W/'proof.log').read_text()
prepared=json.loads((W/'proof_prepared.json').read_text())['modules']['miter']
assert not prepared.get('memories');assert all(t['type'].startswith('$') and not re.search(r'(dff|adff|latch|mem|anyconst|anyseq)',t['type'],re.I) for t in prepared['cells'].values())
mut=text.replace('INVx1_ASAP7_75t_R inv0 (','BUFx2_ASAP7_75t_R inv0 (',1);assert mut!=text
(W/'native_mut.v').write_text(mut)
r=runys('proof_mut',base.format(native='/work/native_mut.v',prefix='proof_mut'),expect=1)
assert r.returncode!=0 and 'model found: FAIL!' in (W/'proof_mut.log').read_text(),r.stdout[-1500:]
libargs=[x for p in libs for x in ['--liberty',str(p)]]
for stem,path,top in [('before',v,'ot_v41_fadd_s0'),('after',W/'native.v','ot_v41_fadd_s0_n32')]:
 r=subprocess.run([sys.executable,'/admission/tools/ref_tile/native_census.py','--netlist',str(path),'--top',top,'--out',str(W/(stem+'_native.json')),*libargs],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (W/(stem+'_native.stdout')).write_text(r.stdout)
 p=json.loads((W/(stem+'_native.json')).read_text());assert not p['role_errors'],p['role_errors']
 if stem=='after':assert r.returncode==0 and p['status']=='PASS',p['violations'][:2]
ledger=dict(source_top='ot_v41_fadd_s0',candidate_top='ot_v41_fadd_s0_n32',source_commit='4496f1308',source_files={str(p):sha(p) for p in [src/'ot_v41_fadd2.sv',src/'ot_prefix.sv']},canonical_packet='4b45be3c8',canonical_files={str(p):sha(p) for p in [src/'canonical_ASR_normalized.v',src/'canonical_DFF_normalized.v']},liberty=manifest,abc_path=shutil.which('yosys-abc'),abc_sha256=sha(shutil.which('yosys-abc')),cloner_commit='cf32860cf',cloner_sha256=sha('/tools/svc7_bound_graph.py'),mapped_sha256=sha(v),mapped_json_sha256=sha(W/'mapped.json'),candidate_sha256=sha(W/'native.v'),models_used_sha256=sha(W/'models_used.v'),source_cells=len(m['cells']),candidate_cells=len(c),clones=clones,cell_types=used,state_cells=0,storage_cells=0,unknown_cells=0,cyclic_cells=0,proved_output_bits=105,arbitrary_input_bits=65,initialization='No state exists in the extracted cone; all binary parent cutpoint values arbitrary, no init/reset/valid assumption or mask.',formal='PASS all105 bits',negative_control='INV->BUF actual all-input SAT counterexample, no compiler failure',origins=origins)
(W/'ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
print('S0_GRAPH_PROOF PASS clones='+str(clones)+' cells='+str(len(c))+' zeroFF/storage/unknown/cycles, all105bits arbitrary65inputs, native32PASS',flush=True)
