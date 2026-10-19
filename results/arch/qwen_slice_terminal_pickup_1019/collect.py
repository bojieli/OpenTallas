import pathlib,json,hashlib,subprocess,tarfile,re,sys,datetime
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
def h(p):
 x=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''): x.update(b)
 return x.hexdigest()
def cp(p,name):
 import shutil
 shutil.copyfile(p,out/name)
mode=sys.argv[2]
if mode=='regional':
 root=pathlib.Path('/srv/opentallas-scratch/claude/safe-qw-regional-endpoints-1019-v2')
 names=['manifest.json','contract.json','run_v2.sh','diag/full_reset_census.json','diag/full_reset_summary.log','diag_tools/reset_census.py','diag_tools/soft_cone_inventory.py','out/netlist.json','out/yosys.log','src.tgz']
 inputs={p:{'sha256':h(root/p),'bytes':(root/p).stat().st_size} for p in names}
 manifest=json.loads((root/'manifest.json').read_text()); inputs['source_verification']={p: {'expected':v,'actual':h(root/p),'matches':h(root/p)==v} for p,v in manifest['sources'].items()}
 (out/'regional_identity.json').write_text(json.dumps(inputs,indent=2)+'\n')
 with tarfile.open(out/'regional_raw.tar.gz','w:gz',compresslevel=1) as t:
  for p in names:
   if p not in ['out/netlist.json','out/yosys.log']:t.add(root/p,arcname=p)
 (out/'regional_yosys_tail.log').write_text('\n'.join((root/'out/yosys.log').read_text().splitlines()[-12:])+'\n')
 units=['1080786-1792434153']
 (out/'regional_scope.log').write_text(subprocess.check_output(['journalctl','--user','-u','oth-ubuntu-'+units[0]+'.scope','--no-pager'],text=True))
else:
 root=pathlib.Path('/srv/opentallas-scratch/claude/codex-safe-qw-slice')
 runs={'r10_e':('prod_station_r10_e','src_station_scalar_r10','1881564-1792433616'),'r10_w':('prod_station_r10_w','src_station_scalar_r10','1881741-1792433616'),'r10_m14':('prod_station_r10_m14','src_station_scalar_r10','1881556-1792433616'),'r10_m15':('prod_station_r10_m15','src_station_scalar_r10','1881523-1792433616'),'r8_e':('prod_station_r8_e','src_station_math_r8','1833894-1792432760'),'r8_w':('prod_station_r8_w','src_station_math_r8','1833891-1792432760'),'cfg_positive':('cfg_station_r10','src_station_cfg_r10','1895606-1792433774'),'cfg_mutant':('cfg_station_r10','src_station_cfg_r10','1895580-1792433774')}
 result={}; added=set()
 with tarfile.open(out/'station_raw.tar.gz','w:gz',compresslevel=1) as tar:
  for key,(work,src,unit) in runs.items():
   journal=subprocess.check_output(['journalctl','--user','-u','oth-ubuntu-'+unit+'.scope','--no-pager'],text=True);(out/(key+'_scope.log')).write_text(journal)
   files=[];sources={};binary={};dats=list((root/work).rglob('*__verFiles.dat'))
   for p in dats:
    text=p.read_text(); files.append(p)
    for line in text.splitlines():
     if not line.startswith('S '):continue
     q=re.findall(r'"([^"]+)"',line)[-1]; f=pathlib.Path(q) if q.startswith('/') else root/src/q
     sources[q]={'sha256':h(f),'bytes':f.stat().st_size} if f.exists() else {'missing':True}
    for f in p.parent.iterdir():
     if f.is_file() and f.name.startswith('V') and f.suffix=='' and f.stat().st_mode&0o111:binary[str(f.relative_to(root))]={'sha256':h(f),'bytes':f.stat().st_size}
   files += [p for p in (root/work).glob('m*/*') if p.is_file() and p.suffix in ('.log','.ev')]
   files += [p for p in (root/work).glob('build*.log')]
   hashes={str(p.relative_to(root)):{'sha256':h(p),'bytes':p.stat().st_size} for p in files}
   for p in files:
    arc=str(p.relative_to(root))
    if arc not in added:tar.add(p,arcname=arc);added.add(arc)
   result[key]={'unit':unit,'work':work,'source':src,'terminal_scope':journal,'files':hashes,'source_inputs':sources,'binaries':binary,'verdict':'UNKNOWN: original stdout not persisted in work directory; build completion and scope end do not imply functional PASS'}
 (out/'station_identity.json').write_text(json.dumps(result,indent=2)+'\n')
