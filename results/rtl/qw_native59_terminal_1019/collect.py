import pathlib,hashlib,json,tarfile,re,datetime,sys
out=pathlib.Path('/srv/opentallas-scratch/claude/qw-native59-terminal-1019');out.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
for name in ['safe3','safe3b']:
 root=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/qfd_native59_dv_service_'+name+'-20261019-113209')
 files=[];checkpoints=[]
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  rel=str(p.relative_to(root));s=p.stat()
  checkpoint=p.suffix in ['.odb','.v'] and '/results/' in rel
  source=rel.startswith(('src/rtl/','src/physical/ref_tile/qfd_native59_dv_service_'+name+'/','src/physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1/','src/tools/closure_loop/','src/tools/ref_tile/','src/tools/common_flow/'))
  evidence=(not rel.startswith('src/')) and (p.suffix in ['.log','.json','.rpt','.mk','.sdc','.tcl','.tsv'] or rel in ['bin/docker','routes/gate/STATUS','routes/gate/status'])
  if checkpoint or source or evidence or rel=='src/SOURCE_COMMIT':
   row={'path':rel,'bytes':s.st_size,'mtime_utc':datetime.datetime.fromtimestamp(s.st_mtime,datetime.timezone.utc).isoformat(),'sha256':sha(p),'archived':bool((source or evidence or rel=='src/SOURCE_COMMIT') and not checkpoint and p.name not in ['gate_layout_floorplan.json','mem.json'])}
   files.append(row)
   if checkpoint:checkpoints.append(row)
 with tarfile.open(out/(name+'.evidence.tar.gz'),'w:gz') as tar:
  for row in files:
   if row['archived']:tar.add(root/row['path'],arcname=row['path'],recursive=False)
 execution=(root/'execution.log').read_text();cts=(root/'cts.log').read_text()
 summary={'source_root':str(root),'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'gate_result_exists':(root/'gate_result.json').exists(),'source_commit':(root/'src/SOURCE_COMMIT').read_text(),'terminal_lines':[x for x in execution.splitlines() if x.startswith(('GATE_CTS_RC','GATE_CK_SKIPPED','GATE_PATH_CLASSES_SKIPPED','GATE_PLACED_LAYOUT_SKIPPED','GATE_GRT_SKIPPED','GATE_SCRIPT_RC','GATE_DONE','GATE_TOOL_IMAGE','GATE_SOURCE_ARCHIVE'))],'stall_lines':[x for x in cts.splitlines() if 'GATE_STALL' in x],'last_repair_row':next((x for x in reversed(cts.splitlines()) if re.match(r'\s*\d+ \|',x)),None),'read_liberty':sorted(set(x for x in cts.splitlines() if x.startswith('read_liberty '))),'files':files,'checkpoints':checkpoints,'claims':{'terminal':'CTS_STALL_TIMEOUT_14400_SECONDS','oom':'NOT_ESTABLISHED','final_timing':None,'native_all_role_fanout':None,'final_pg':None,'clock_spread':None,'routing_drc':None}}
 (out/(name+'.inventory.json')).write_text(json.dumps(summary,indent=2)+'\n')
 print(name,len(files),len(checkpoints),(out/(name+'.evidence.tar.gz')).stat().st_size,summary['last_repair_row'],flush=True)
