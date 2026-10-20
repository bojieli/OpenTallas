
import pathlib,hashlib,re,json
B=pathlib.Path('/srv/opentallas-scratch/claude/hd4g/gen2e2'); S=B/'src_6f783d0a1'; R=B/'syn'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={}
for cell in CELLS:
 O=pathlib.Path(OUTPUTS[cell])
 if not O.is_dir(): continue
 top='v16w_'+cell; log=O/(cell+'.log'); etm=O/'etm.log'
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
   widths={name:int(width) for name,width in re.findall(r'\btype\s*\(\s*"?([^\s\)";]+)"?\s*\)\s*\{[^}]*?bit_width\s*:\s*(\d+)\s*;',t,re.S)}
   assert widths=={name:abs(hi-lo)+1 for name,(hi,lo) in types.items()},('Liberty bit_width mismatch',widths,types)
   expected_types={name:(v[1],v[2]) for name,v in wd.items() if v[1]!=v[2]}
   assert types==expected_types,('wrong ETM bus bit ranges',types,expected_types)
   library=re.findall(r'\blibrary\s*\(\s*([^\s\)]+)\s*\)',t)
   assert library==[top+'_synth_'+corner],('wrong library name',library)
   libs[p.name]=h(p);checks[corner]={'cell':top,'library':library[0],'port_names':sorted(pins),'bus_bit_ranges':types}
  for corner in ['tt','ff']:
   lt=(O/(top+'_synth_'+corner+'.lib')).read_text()
   actual={name:direction for name,direction in re.findall(r'\bpin\s*\(\s*"?([^\s\)";]+)"?\s*\)\s*\{\s*direction\s*:\s*(input|output|inout)\s*;',lt)}
   expected={ (name+'['+str(i)+']' if hi!=lo else name):direction for name,(direction,hi,lo) in wd.items() for i in range(min(hi,lo),max(hi,lo)+1)}
   assert actual==expected,('Liberty pin directions/bit coverage mismatch',corner,len(actual),len(expected),list(set(actual)^set(expected))[:20])
   checks[corner]['exact_pin_directions_and_bit_coverage']=True
  files=json.loads((O/(cell+'.files.json')).read_text())
  paths=set(files['files']+[m['file'] for m in files['macros']]+['v16w/'+top+'.sv'])
  helper=S.parent/'failed_resume_1019/synth_master.sh'
  rec['runtime_helper_hashes']={str(p):h(p) for p in [helper,S/'tools/hbm_die_v15/master_filelist.py',S/'tools/hbm_die_v15/synth_etm.sh']}
  assert h(helper)==HELPER_EXPECTED,'runtime overlay digest mismatch'
  rec['overlay_inputs']={str(S/p):h(S/p) for p in EXPECTED}
  assert all(h(S/p)==v for p,v in EXPECTED.items()),'frozen scoped input mismatch'
  rec['actual_ys_text']=(O/(cell+'.ys')).read_text()
  rec.update(status='PASS_SYNTH_ETM_IDENTITY_NOT_PHYSICAL',top=top,ports=np,exact_port_names_order=True,etm_port_checks=checks,etm_hashes=libs,input_hashes={p:h(S/p) for p in sorted(paths)},artifact_hashes={p.name:h(p) for p in [net,log,etm,O/(cell+'.stat'),O/(cell+'.ys'),O/(cell+'.files.json')]},macro_area='UNKNOWN_NOT_ZERO')
 except Exception as e: rec.update(status='IDENTITY_CHECK_FAIL',error=str(e))
print(json.dumps(result))
