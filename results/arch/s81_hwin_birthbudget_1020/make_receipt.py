import csv,collections,gzip,hashlib,json,shutil,re
from pathlib import Path
A=Path('/audit');P=A/'birthbudget_artifacts';P.mkdir(exist_ok=True)
CASE=Path('/case');prefix='results/arch/s81_hwin_birthbudget_1020/proof/'
def dump(name,data,compressed=False):
 raw=json.dumps(data,sort_keys=True,separators=(',',':')).encode()
 if compressed:raw=gzip.compress(raw,mtime=0)
 (P/name).write_bytes(raw)
 return {'path':prefix+name,'sha256':hashlib.sha256(raw).hexdigest()}
def record(name,raw):
 (P/name).write_bytes(raw);return {'path':prefix+name,'sha256':hashlib.sha256(raw).hexdigest()}
def population(filename):
 cells=[];masters={}
 for r in csv.reader((A/filename).open(),delimiter='\t'):
  inst,master,block,orient,status,x0,y0,x1,y1=r
  if block=='1'or re.search(r'TAPCELL|FILL|DECAP|ENDCAP|tapcell',master):continue
  area=(float(x1)-float(x0))*(float(y1)-float(y0));cells.append([inst,master])
  if master in masters:
   if abs(masters[master]['area_um2']-area)>1e-8:raise ValueError('inconsistent master dimensions '+master)
   masters[master]['count']+=1
  else:masters[master]={'area_um2':area,'count':1}
 cells.sort();return {'schema':'opentallas.native_master_population.v1','cells':cells,'masters':masters}
gate=json.loads((A/'previous_gate.json').read_text());priorpath='physical/ref_tile/dsdv_mu_hwin_c21k/spec.json';priorraw=(CASE/'src'/priorpath).read_bytes();spec=json.loads(priorraw)
binding=gate['source_binding'];snapshot={r['path']:r['sha256']for r in binding['files']};views={m['view']for m in spec['macros']}
files=set(spec['sources'])|{p for p in snapshot if any(p.startswith(v+'/')for v in views)}
for name in files:
 raw=(CASE/'src'/name).read_bytes()
 if hashlib.sha256(raw).hexdigest()!=snapshot[name]:raise ValueError('archive source/master mismatch '+name)
 dst=P/'source_tree'/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
source=population('instances_src.tsv');cts=population('instances.tsv')
mastersha=hashlib.sha256(json.dumps(source['masters'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
net=CASE/'routes/gate/work/orfs/results/asap7/opentallas_dsdv_mu_hwin_capture_1019_asap7_ref_gate/base/1_2_yosys.v'
native=CASE/'routes/gate/work/orfs/native_census.json'
r={'schema':'opentallas.hwin.planning_birth_budget.v1','scope':'PLANNING_ONLY','top':spec['top'],'source_commit':binding['start_commit'],'source_std_area_um2':spec['std_area_um2'],'previous_cts_area_um2':gate['measured_band_fill']['std_area_um2'],'previous_spec_source_path':priorpath,'previous_spec':record('previous_spec.json',priorraw),'previous_gate':record('previous_gate.json.gz',gzip.compress((A/'previous_gate.json').read_bytes(),mtime=0)),'source_files':{p:snapshot[p]for p in sorted(files)},'mapped_netlist':record('mapped_source.v.gz',gzip.compress(net.read_bytes(),mtime=0)),'native_census':record('native_census.json.gz',gzip.compress(native.read_bytes(),mtime=0)),'source_population':dump('source_population.json.gz',source,True),'cts_population':dump('cts_population.json.gz',cts,True),'source_master_sha256':mastersha,'provenance':{'prior_run':binding['remote_run'],'native_source_stage':'1_synth.odb','native_source_standard_cells':len(source['cells']),'native_source_area_um2':sum(m['area_um2']*m['count']for m in source['masters'].values()),'source_std_area_stage':'post-unbuffer/pre-GPL sizing source, previous exact spec9151.137','cts_stage':'4_cts.odb','cts_standard_cells':len(cts['cells']),'note':'Prior CTS/GRT trial later failed. Actual placed population is used ONLY as structural sizing budget, never as closure qualification or substitute for a new placed40..60 gate.'}}
meta=dump('receipt.json',r);meta.update({'approved_by':'ROOT','why':'ROOT authorized narrowly source-bound HWIN22l actual measured CTS birth population for PLANNING ONLY; new actual placed40..60 proof remains mandatory (10-20 takeover).'});(P/'approval.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'approval':meta,'source_cells':len(source['cells']),'cts_cells':len(cts['cells']),'master_digest':mastersha},indent=2))
