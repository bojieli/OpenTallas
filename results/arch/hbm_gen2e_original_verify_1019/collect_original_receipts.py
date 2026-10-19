import concurrent.futures,json,pathlib,subprocess
A=pathlib.Path(__file__).resolve().parent
M=json.loads((A/'view_manifest_proposal.json').read_text())
CELLS=sorted(set(M['old_successes'])|set(M['preserve_original_live']))
DRIVE={c:json.loads((A.parent/'vplan_a/drive'/(c+'.json')).read_text()) for c in CELLS}
code=r'''
import pathlib,hashlib,re,json
B=pathlib.Path('/srv/opentallas-scratch/claude/hd4g/gen2e2'); S=B/'src_6f783d0a1'; R=B/'syn'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={}
for cell in CELLS:
 O=R/cell
 if not O.is_dir(): continue
 cell=O.name; top='v16w_'+cell; log=O/(cell+'.log'); etm=O/'etm.log'
 rec={'output':str(O),'status':'INCOMPLETE','synth_terminal':False,'tt_done':False,'ff_done':False}
 result[cell]=rec
 if not log.exists(): continue
 lt=log.read_text(errors='replace'); et=etm.read_text(errors='replace') if etm.exists() else ''
 rec['files_present']=sorted(p.name for p in O.iterdir() if p.is_file())
 rec.update(synth_terminal='End of script.' in lt and 'ERROR:' not in lt,tt_done='OT_ETM_DONE_tt' in et,ff_done='OT_ETM_DONE_ff' in et)
 if not all(rec[k] for k in ['synth_terminal','tt_done','ff_done']): continue
 try:
  net=O/(cell+'.netlist.v'); wrapper=S/('v16w/'+top+'.sv')
  ports=lambda t:re.search(r'module\s+\\?'+top+r'\s*\((.*?)\);',t,re.S).group(1)
  nt=net.read_text(); wt=wrapper.read_text()
  np=[x.strip().lstrip('\\') for x in ports(net.read_text()).split(',')]
  wp=[re.findall(r'[A-Za-z_][A-Za-z0-9_$]*',x)[-1] for x in ports(wrapper.read_text()).split(',')]
  assert np==wp,'netlist port name/order mismatch'
  body=re.search(r'module\s+\\?'+top+r'\s*\(.*?\);(.*?)endmodule',nt,re.S).group(1)
  decl=lambda t:{name:(direction,int(hi or 0),int(lo or 0)) for direction,hi,lo,name in re.findall(r'\b(input|output|inout)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s+)?(\\?[^\s,;]+)',t)}
  wd=decl(ports(wt));nd=decl(body)
  assert wd==nd,('port direction/bit range mismatch',wd,nd)
  rec['port_directions_bit_ranges']=wd
  rec['port_bits']=sum(abs(v[1]-v[2])+1 for v in wd.values())
  libs={};checks={}
  for corner in ['tt','ff']:
   p=O/(top+'_synth_'+corner+'.lib');t=p.read_text()
   cells=re.findall(r'\bcell\s*\(\s*"?([^\s\)";]+)"?\s*\)',t)
   assert cells==[top],('wrong ETM cell',cells)
   pins={re.sub(r'\[.*','',x) for x in re.findall(r'\b(?:pin|bus)\s*\(\s*"?([^\s\)";]+)"?\s*\)',t)}
   assert pins==set(np),('wrong ETM ports',sorted(pins-set(np)),sorted(set(np)-pins))
   types={name:tuple(map(int,(hi,lo))) for name,hi,lo in re.findall(r'\btype\s*\(\s*"?([^\s\)";]+)"?\s*\)\s*\{[^}]*?bit_from\s*:\s*(\d+)\s*;[^}]*?bit_to\s*:\s*(\d+)\s*;',t,re.S)}
   expected_types={name:(v[1],v[2]) for name,v in wd.items() if v[1]!=v[2]}
   assert types==expected_types,('wrong ETM bus bit ranges',types,expected_types)
   library=re.findall(r'\blibrary\s*\(\s*([^\s\)]+)\s*\)',t)
   assert library==[top+'_synth_'+corner],('wrong library name',library)
   libs[p.name]=h(p);checks[corner]={'cell':top,'library':library[0],'port_names':sorted(pins),'bus_bit_ranges':types}
  files=json.loads((O/(cell+'.files.json')).read_text())
  paths=set(files['files']+[m['file'] for m in files['macros']]+['v16w/'+top+'.sv'])
  rec.update(status='PASS_SYNTH_ETM_IDENTITY_NOT_PHYSICAL',top=top,ports=np,exact_port_names_order=True,etm_port_checks=checks,etm_hashes=libs,input_hashes={p:h(S/p) for p in sorted(paths)},artifact_hashes={p.name:h(p) for p in [net,log,etm,O/(cell+'.stat'),O/(cell+'.ys'),O/(cell+'.files.json')]},macro_area='UNKNOWN_NOT_ZERO')
 except Exception as e: rec.update(status='IDENTITY_CHECK_FAIL',error=str(e))
print(json.dumps(result))
'''
def collect(host):
 hostcells=[c for c in CELLS if DRIVE[c]['host']==host]
 p=subprocess.run(['ssh','-o','ConnectTimeout=8',host,'python3 -'],input='CELLS='+repr(hostcells)+'\n'+code,text=True,capture_output=True,timeout=110,check=True)
 return host,json.loads(p.stdout)
result=dict(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(collect,sorted(set(d['host'] for d in DRIVE.values()))))
(A/'original_verified_receipts.json').write_text(json.dumps(result,indent=2)+'\n')
print({host:{cell:rec['status'] for cell,rec in rows.items()} for host,rows in result.items()})
