#!/usr/bin/env python3
"""Bounded source/fixture proof only. Never invokes an HDL engine."""
import ast, difflib, hashlib, json, pathlib, re, shutil, subprocess, sys, tarfile, types

BASE='c7dda512c67625f0e4db6310981d979bacf35a40'
ROOT=pathlib.Path(__file__).resolve().parents[3]
EVIDENCE=pathlib.Path(sys.argv[1])
OUT=pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True,exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(path):
 return subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path])
pre=json.loads((EVIDENCE/'FIRST_numeric_preflight.json').read_text())
audit=json.loads((EVIDENCE/'consumed_source_audit_FIRST_final.json').read_text())
assert audit['verdict']=='PASS' and audit['actual_files']==47 and audit['expected_superset_files']==53
with tarfile.open(EVIDENCE/'frozen_fixtures.tar.gz') as t:
 members=[m for m in t.getmembers() if m.isfile()]
 assert len(members)==307
 blobs={m.name:t.extractfile(m).read() for m in members}
inventory={r['path']:r for r in pre['files']}
assert sha((EVIDENCE/'consumed_source_audit_FIRST_final.json').read_bytes())==inventory['consumed_source_audit_FIRST_final.json']['sha256']
for name,data in blobs.items():assert sha(data)==inventory[name]['sha256'],name
with tarfile.open(EVIDENCE/'frozen_source.tar.gz') as t:
 frozen=t.extractfile('generated_clockfix/tb.sv').read()
assert frozen==blobs['generated_clockfix/tb.sv']
binding={'instances':{}}
for i in range(14):
 for prefix,instance in [('stu_SW_',f'ur{i}'),('std_SW_',f'dra{i}'),('std_SW_',f'drb{i}')]:
  suffix=f'{i:02d}'+('a' if instance.startswith('dra') else 'b' if instance.startswith('drb') else '')
  master=re.search(r'([A-Za-z_][A-Za-z_0-9]*) '+instance+r'\(',frozen.decode()).group(1)
  binding['instances'][prefix+suffix]={'master':master}
fields_ast=ast.parse(git('tools/hbm_static/su_arith_generate.py'))
fields=next(ast.literal_eval(n.value) for n in fields_ast.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='FIELDS' for x in n.targets))
stub=types.ModuleType('su_arith_generate');stub.FIELDS=fields;sys.modules['su_arith_generate']=stub
path='tests/hbm_record6_component/tb_generate.py'
old=git(path);new=(ROOT/path).read_bytes()
# Both generators consume the identical frozen images; no compiler or arithmetic generator runs.
emitted={}
for label,source in [('baseline',old),('successor',new)]:
 d=OUT/label;d.mkdir()
 for name,data in blobs.items():
  p=d/pathlib.Path(name).relative_to('generated_clockfix');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 ns={};exec(compile(source,path,'exec'),ns)
 ns['emit'](d,json.loads((d/'receipt.json').read_text()),binding)
 emitted[label]=(d/'tb.sv').read_bytes()
assert emitted['baseline']==frozen,'Baseline emitter must reproduce exact frozen compiled bench'
changed=[]
for name,data in blobs.items():
 rel=pathlib.Path(name).relative_to('generated_clockfix')
 if (OUT/'successor'/rel).read_bytes()!=data:changed.append(str(rel))
assert changed==['tb.sv'] or sorted(changed)==['tb.sv']
oldtree=ast.parse(old);newtree=ast.parse(new)
def strip_strings(tree):
 class Strip(ast.NodeTransformer):
  def visit_Constant(self,n):
   if isinstance(n.value,str):return ast.copy_location(ast.Constant(value='<STRING>'),n)
   return n
 return ast.dump(Strip().visit(tree),include_attributes=False)
assert strip_strings(oldtree)==strip_strings(newtree),'Only emitted source strings may change'
tb=emitted['successor'].decode()
assert 'qt-startqt' not in tb and tb.count('observed_serial_edge-startqt')==19
assert tb.count('always @(posedge clk)if(rq)qt=qt+1;')==1
assert tb.count('observed_serial_edge=qt+1;')==1
# Erasing exactly the observer additions and restoring observer counter reads
# must reproduce every original byte, including DUT instances and all drives.
normalized=tb
for line in tb.splitlines(True):
 if any(marker in line for marker in (
  '// Observer only:', '// qt remains the original drive counter;',
  'integer observed_serial_edge=-1;', 'always @(negedge clk)if(rq)observed_serial_edge=qt+1;',
  'reg observed_start_at_edge=0;', ' observed_start_at_edge=station_start;',
  'LAUNCH_CONSUMER_EDGE', 'PROGRAMME_START_EPOCH', 'PROGRAMME_START_POST_NBA')):
  normalized=normalized.replace(line,'',1)
normalized=normalized.replace('observed_serial_edge','qt')
assert normalized.encode()==frozen,'Any unapproved DUT, drive, delay, or predicate delta is refused'
assert 6010!=6011                    # Frozen startup active observer fails.
assert (6011+591)-6010!=591           # Mixed post-NBA root observer fails.
assert (6011+647)-6010!=647           # Old commit trigger is not model edge647.
# All assertion names and numeric target expressions remain; only the observer epoch changes.
assert re.findall(r'\$fatal\([^;]+',frozen.decode())==re.findall(r'\$fatal\([^;]+',tb)
rows=[]
for age in (0,591,613,646,647,648,650,651,670):
 e=6011+age
 # Stable negedge latch equals the same physical next posedge pre/post NBA.
 for counter_runs_first in (False,True):
  active_qt=e if counter_runs_first else e-1
  observed=e
  assert observed-6011==age
  rows.append(dict(age=age,edge=e,active_qt=active_qt,post_qt=e,observed=observed))
patch=''.join(difflib.unified_diff(frozen.decode().splitlines(True),tb.splitlines(True),fromfile='c7/generated_clockfix/tb.sv',tofile='proposal/generated_clockfix/tb.sv'))
(OUT/'bench.patch').write_text(patch)
input0=b''.join(int(w,16).to_bytes(4,'little')for w in (OUT/'baseline/input0.mem').read_text().split())
assert len(input0)==1280*4 and sha(input0)=='f2d1351fa018cc6708973313ba3d7fb4ac974ea4156553246faa710e04fd89c5'
assert (OUT/'baseline/gold.mem').read_text().split()==['40a2a1ed','3fa2a1ed']
r=dict(verdict='SOURCE_ONLY_PASS_NO_ENGINE_RUN',base=BASE,actual_inputs=47,allowed_inputs=53,fixture_files=307,unchanged_emitted_nonbench_files=306,changed_emitted_files=changed,generator_before_sha256=sha(old),generator_after_sha256=sha(new),bench_before_sha256=sha(frozen),bench_after_sha256=sha(emitted['successor']),bench_patch_sha256=sha(patch.encode()),original_A_words=1280,original_A_sha256=sha(input0),gold=['40a2a1ed','3fa2a1ed'],historical_compiler_calendar_digest='PENDING',same_edge_ordering_rows=rows)
(OUT/'source_proof.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items()if k!='same_edge_ordering_rows'},indent=2))
