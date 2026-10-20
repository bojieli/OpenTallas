import argparse, pathlib, re, subprocess, json, hashlib, difflib
ap=argparse.ArgumentParser(); ap.add_argument('--candidate',required=True); a=ap.parse_args()
d=pathlib.Path(__file__).resolve().parent; w=d.parents[2]
def blob(rev,path): return subprocess.check_output(['git','-C',str(w),'show',rev+':'+path],text=True)
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def ports(s):
 h=re.sub(r'//[^\n]*','',s[s.index('module '):]); h=h[h.index('input '):h.index(');')]
 out={}; direction=None; width=''
 for t in h.split(','):
  t=t.strip(); m=re.fullmatch(r'(input|output)\s+(?:(?:wire|reg|logic)\s*)?(\[[^]]+\])?\s*(\w+)',t)
  if m: direction,width,name=m.groups(); width=width or ''
  elif re.fullmatch(r'\w+',t): name=t
  elif not t: continue
  else: raise ValueError(t)
  out[name]=(direction,width)
 return out
candidate=subprocess.check_output(['git','-C',str(w),'rev-parse',a.candidate],text=True).strip()
base_rev='60bb2c145'; prefix='results/arch/kv_native_owner_join_component_1019/private/'
base=blob(base_rev,'results/arch/kv_retained_commit_component_1019/private/ot_host_if_pb2_observed_rc.sv')
sched=blob(candidate,prefix+'ot_host_if_pb2_observed_rc.sv'); core=blob(candidate,prefix+'qkd_host_native_owner_join_rc.sv')
ps=ports(base); cs=ports(sched); outs=[n for n,(di,_) in ps.items() if di=='output']; assert len(outs)==70
extra={n:v for n,v in cs.items() if n not in ps and v[0]=='input'}
assert 'native_certificate_key_ok' in extra, extra
b=blob(base_rev,'results/arch/kv_retained_commit_component_1019/scheduler_descriptor_baseline.sv')
inst=re.search(r'  ot_host_if_pb2_observed_rc #\(.*?\) dut \(.*?\);',b,re.S).group()
ref=inst.replace('ot_host_if_pb2_observed_rc #','scheduler_baseline #',1).replace(') dut (',') refdut (')
for n in outs: ref=re.sub(r'\.'+n+r'\([^()]*\)',f'.{n}()',ref)
# Distinct changing bits drive each new input; avoid dependence on DUT outputs.
connections=[]
for i,(n,(_,width)) in enumerate(extra.items()):
 bits=1 if not width else int(width.strip('[]').split(':')[0])+1
 expr=f"{bits}'((edge_n*32'h9e3779b9) ^ (32'h13579bdf >> {i%16}))"
 if n=='native_certificate_key_ok': expr='edge_n[0]'
 connections.append(f'.{n}({expr})')
newinst=inst.replace(' dut (',' dut (\n    '+','.join(connections)+',\n')
checks='\ninteger compare_edges=0, attempt_low=0, attempt_high=0;\nalways @(negedge clk) begin\n compare_edges=compare_edges+1;\n'
checks+=' if (dut.cut_now) begin if(edge_n[0]) attempt_high=attempt_high+1; else attempt_low=attempt_low+1; end\n'
checks+=''.join(f' if(dut.{n} !== refdut.{n}) $fatal(1,"FINAL_DEFAULT_MISMATCH {n} edge=%0d",edge_n);\n' for n in outs)+'end\nfinal $display("DEFAULT_ELIGIBILITY_COVER edges=%0d low=%0d high=%0d",compare_edges,attempt_low,attempt_high);\n'
b=b.replace(inst,newinst+'\n'+ref+checks).replace('SCHED_PASS case=','FINAL_DEFAULT_SCHED_PASS outputs=70 case=')
cp=ports(core); inputs={n:v for n,v in cp.items() if v[0]=='input'}
sv='`timescale 1ns/1ps\nmodule disabled_core_compare;\n'
for n,(_,width) in inputs.items(): sv+=f'reg {width} {n}=0;\n'
sv+='always #5 clk=~clk;\nqkd_host_native_owner_join_rc dut ('+','.join(f'.{n}({n})' for n in inputs)+');\ninteger edge_n=0;\ninitial begin\n'
sv+='for(edge_n=0;edge_n<257;edge_n=edge_n+1) begin\n@(negedge clk);\n'
for i,(n,(_,width)) in enumerate(inputs.items()):
 if n=='clk': continue
 bits=1 if not width else int(width.strip('[]').split(':')[0])+1
 sv+=f"{n}={bits}'((edge_n*32'h9e3779b9) ^ (32'h13579bdf >> {i%16}));\n"
sv+='#1; if(dut.certificate_key_ok !== 1\'b1) $fatal(1,"DISABLED_CERTIFICATE_KEY_NOT_ONE"); if(dut.raw_cleanup_allow !== 1\'b1) $fatal(1,"RAW_CLEANUP_NOT_ONE");\nend\n$display("DISABLED_CORE_PASS edges=257 all_inputs_change=1"); $finish; end\nendmodule\n'
assert "assign raw_cleanup_allow = 1'b1;" in core
assert re.search(r'certificate_key_ok\s*=\s*!ENABLE_NATIVE_OWNER_JOIN\s*\|\|',core)
codec=[]
for kind in ['rank','coordinator']:
 path=prefix+f'qkd_host_peer_{kind}_codec_rc.sv'; old=blob('833713954',path); new=blob(candidate,path)
 assert old==new, f'{kind} changed; expand scope before compile'
 codec.append({'kind':kind,'path':path,'prior_revision':'833713954','candidate_sha256':digest(new),'unchanged':True})
files={'scheduler_candidate.sv':sched,'scheduler_baseline.sv':base.replace('module ot_host_if_pb2_observed_rc','module scheduler_baseline',1),'scheduler_compare.sv':b,'core_candidate.sv':core,'disabled_core_compare.sv':sv,'scheduler_source.diff':''.join(difflib.unified_diff(base.splitlines(True),sched.splitlines(True),fromfile='canonical60bb',tofile=candidate))}
for name,s in files.items():
 if (d/name).exists(): raise RuntimeError('Refuse overwrite '+name)
 (d/name).write_text(s)
coverage={'scheduler_original_outputs':outs,'adverse_new_inputs':extra,'core_inputs':inputs,'unchanged_codec_scope':codec}
(d/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
manifest={'candidate_revision':candidate,'baseline_revision':base_rev,'resources':{'mem_gb':4,'threads':2,'disk_gb':20},'sources':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(d.iterdir()) if p.is_file()]}
(d/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'candidate':candidate,'outputs':len(outs),'extra_inputs':list(extra),'codec_unchanged':True}))
