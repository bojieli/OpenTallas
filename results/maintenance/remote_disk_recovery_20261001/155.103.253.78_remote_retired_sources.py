import pathlib as P,json,os,subprocess as S,time,hashlib,tarfile,re
paths=['/home/ubuntu/w19-production-recovery','/home/ubuntu/w19-production-protocol.vvp','/home/ubuntu/w19-vvp11','/home/ubuntu/w19-ivl11'];out=P.Path('/tmp/opentallas-maintenance-remote-source-20261001');out.mkdir(exist_ok=True);records=[]
# All process cwd/cmd/fd/maps must be readable; do not stop any process.
def live(path):
 hits=[];errors=[]
 for d in P.Path('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   cmd=(d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace');links=[]
   for n in ['cwd','exe','root']:
    try:links.append(os.readlink(d/n))
    except FileNotFoundError:pass
   for f in (d/'fd').iterdir():
    try:links.append(os.readlink(f))
    except FileNotFoundError:pass
   maps=(d/'maps').read_text(errors='replace')
   if re.search(re.escape(path)+r'(?=$|[\s/\"\'])',cmd) or any(x==path or x.startswith(path+'/') for x in links) or path+'/' in maps:hits.append(int(d.name))
  except FileNotFoundError:pass
  except PermissionError:errors.append(str(d))
 ps=S.run(['docker','ps','-aq'],capture_output=True,text=True);assert ps.returncode==0,ps.stderr
 if ps.stdout.split():
  ins=S.run(['docker','inspect',*ps.stdout.split()],capture_output=True,text=True);assert ins.returncode==0,ins.stderr
  for c in json.loads(ins.stdout):
   if not c['State'].get('Running'):continue
   cfg=c['Config'];cwd=cfg.get('WorkingDir','');cmd=' '.join(cfg.get('Cmd') or [])
   if cwd==path or cwd.startswith(path+'/') or re.search(re.escape(path)+r'(?=$|[\s/\"\'])',cmd) or any(m.get('Source','')==path or m.get('Source','').startswith(path+'/') for m in c.get('Mounts',[])):hits.append('docker:'+c['Id'])
 assert not errors,errors;return hits

safe={'/home/ubuntu/v41bt/wtF': '95b9b7825f8f7f8324fb17220f6dab04c945223d', '/tmp/opentallas-qwen-integrate-candidate': '7e848835265dcae82bbcd27c096caed546c71835', '/tmp/claude-1000/-home-ubuntu-OpenTallas/451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/head-wt': 'bf8e382131000b9d9fe38ef6ac383be46ab76b71', '/tmp/claude-1000/pxw5': 'fd852d7a0cac9ee2d56219b9a2bae892691e6509', '/tmp/claude-1000/pxw3': 'fd852d7a0cac9ee2d56219b9a2bae892691e6509', '/home/ubuntu/v41bt/wtH': '95b9b7825f8f7f8324fb17220f6dab04c945223d', '/tmp/opentallas-qwen-merge-latest': '5117cdbc2de8d903bbfa4ced0f08b72527b8b2e0', '/tmp/claude-1000/wt/w11-st9': '0c3666ab3221f3df114dbe3b7cf68eb58a02cb7b', '/tmp/claude-1000/pxw2': 'fd852d7a0cac9ee2d56219b9a2bae892691e6509', '/tmp/claude-1000/-home-ubuntu-OpenTallas/451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/wt-baseline': '518260f16d4adca60b8d81a49043bd5ce1ac3cff', '/home/ubuntu/w15bmain': '321cc6e450313512364585e4dab73cfa8be4086b', '/tmp/claude-1000/-home-ubuntu-OpenTallas/451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/head_check': '56009ef54189b5daf40c41c90bceb14ea3cad2a8', '/tmp/ot-atlas-verify-6e8fc6aa': '6e8fc6aa967081349d7960490c9fb71f14a56070', '/tmp/claude-1000/wt/w16b': 'af06e43acc1569994a574dfd54329a2e139f1cac', '/tmp/claude-1000/wt/w11-st7': '0c3666ab3221f3df114dbe3b7cf68eb58a02cb7b', '/tmp/opentallas-atlas-evidence': '8afa8c4136a5b7096fc4b8a5c920489550b7a360', '/tmp/claude-1000/pxw6': 'fd852d7a0cac9ee2d56219b9a2bae892691e6509', '/home/ubuntu/otwt3': '3fab90f25a98fecf4c9fd4e485a60d632929796e', '/home/ubuntu/otwt': '46b2405d05b2b680067c55362e56b559ddcb742a', '/home/ubuntu/v41bt/wtG': '95b9b7825f8f7f8324fb17220f6dab04c945223d', '/tmp/opentallas-qwen-fullshape-int8-image': 'ad99f60adced58f82664ad11bb6ed9c14095a348', '/tmp/opentallas-qwen-hbm-saturation': '8d158b2ca4fbe30ae42aaa2dd57db548cd6ed881', '/tmp/opentallas-qwen-int8-rom-pipeline': 'eadcbcc7162241665f560d54fb7ff02e858bc8b6', '/tmp/opentallas-qwen-m5-reprice': 'dbd32470dbba24bb217600c512f322e78473973f', '/tmp/opentallas-qwen-o4-hbm-comparator': 'edd500129eeb5d0e2eb2c408ae5750fd93268f2d', '/tmp/opentallas-qwen-o4-hbm-streamer': '71eae8afe4c21777320343a56aecb38bff653a1f', '/tmp/opentallas-qwen-o4-physical-lane': '4e734897ae130458edf94a8ebb569a0d6801cf08', '/tmp/opentallas-qwen-o4-scale-physical': '8f4141fc2c95c4209e1a0444042ce143a0afb557', '/tmp/qwen-composition-budget': '73be6d00c7046c58a12055efed28b3ed52423be8', '/tmp/qwen-fullshape-isa-rtl': 'a80d6a30a83e9ea145bd1999a73b61672f313ef8', '/tmp/claude-1000/wt/w12gb': '5560c98d4b6a55ef28d7d57b853e96008e30d13d', '/tmp/claude-1000/wt/w12gc': '5560c98d4b6a55ef28d7d57b853e96008e30d13d', '/tmp/claude-1000/wt/w12gd': '5560c98d4b6a55ef28d7d57b853e96008e30d13d', '/home/ubuntu/OpenTallas/.claude/worktrees/qwen-o4-reprice': 'fdb5070bf66b7827027e81590294da7211b2f046', '/home/ubuntu/w15btest': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1', '/home/ubuntu/w15bwt2': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1', '/home/ubuntu/w15bwt3': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1', '/home/ubuntu/w15bwt4': '19ecd2fb4d64c2ace60ec6f18d36a1d754db55bb', '/home/ubuntu/w15bwt5': 'c9d1a7514580e78d2ae6faf81e566a889a939bf1', '/home/ubuntu/w15bwt6': 'c9d1a7514580e78d2ae6faf81e566a889a939bf1', '/home/ubuntu/w15bwt10': '19ecd2fb4d64c2ace60ec6f18d36a1d754db55bb', '/home/ubuntu/w15bwt11': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1', '/home/ubuntu/w15bwt1': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1', '/home/ubuntu/w15bwt12': '50f5165ba84ed035d3062d091a7f6d7479a8e9d1', '/tmp/claude-1000/wt/w19c': 'b6780b4f9d017229d644d2e6ed5d0cdc10832e85', '/tmp/claude-1000/wt/w19-runtime-fetch': '3b15b18e997ad0a05cc7acf474a7329847e38845', '/tmp/claude-1000/wt/qcnam': 'd2631dd9051c30d7ab1aeab6fdaab4f9200d3f5a'}

initial_refs={'/home/ubuntu/v41bt/wtF': [], '/tmp/opentallas-qwen-integrate-candidate': [], '/tmp/claude-1000/-home-ubuntu-OpenTallas/451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/head-wt': [], '/tmp/claude-1000/pxw5': [], '/tmp/claude-1000/pxw3': [], '/home/ubuntu/v41bt/wtH': [], '/tmp/opentallas-qwen-merge-latest': [], '/tmp/claude-1000/wt/w11-st9': [], '/tmp/claude-1000/pxw2': [], '/tmp/claude-1000/-home-ubuntu-OpenTallas/451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/wt-baseline': [], '/home/ubuntu/w15bmain': [], '/tmp/claude-1000/-home-ubuntu-OpenTallas/451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/head_check': [], '/tmp/ot-atlas-verify-6e8fc6aa': [], '/tmp/claude-1000/wt/w16b': [], '/tmp/claude-1000/wt/w11-st7': [], '/tmp/opentallas-atlas-evidence': [], '/tmp/claude-1000/pxw6': [], '/home/ubuntu/otwt3': [], '/home/ubuntu/otwt': [], '/home/ubuntu/v41bt/wtG': [], '/tmp/opentallas-qwen-fullshape-int8-image': [], '/tmp/opentallas-qwen-hbm-saturation': [], '/tmp/opentallas-qwen-int8-rom-pipeline': [], '/tmp/opentallas-qwen-m5-reprice': [], '/tmp/opentallas-qwen-o4-hbm-comparator': [], '/tmp/opentallas-qwen-o4-hbm-streamer': [], '/tmp/opentallas-qwen-o4-physical-lane': [], '/tmp/opentallas-qwen-o4-scale-physical': [], '/tmp/qwen-composition-budget': [], '/tmp/qwen-fullshape-isa-rtl': [], '/tmp/claude-1000/wt/w12gb': [], '/tmp/claude-1000/wt/w12gc': [], '/tmp/claude-1000/wt/w12gd': [], '/home/ubuntu/OpenTallas/.claude/worktrees/qwen-o4-reprice': [], '/home/ubuntu/w15btest': [], '/home/ubuntu/w15bwt2': [], '/home/ubuntu/w15bwt3': [], '/home/ubuntu/w15bwt4': [], '/home/ubuntu/w15bwt5': [], '/home/ubuntu/w15bwt6': [], '/home/ubuntu/w15bwt10': [], '/home/ubuntu/w15bwt11': [], '/home/ubuntu/w15bwt1': [], '/home/ubuntu/w15bwt12': [], '/tmp/claude-1000/wt/w19c': [], '/tmp/claude-1000/wt/w19-runtime-fetch': [], '/tmp/claude-1000/wt/qcnam': []}
repo='/home/ubuntu/repo.git';actions=[]
def git(*args):return S.run(['git','--git-dir',repo,*args],capture_output=True,text=True)
listed=git('worktree','list','--porcelain');assert listed.returncode==0,listed.stderr
for block in listed.stdout.strip().split('\n\n'):
 fields={}
 for line in block.splitlines():
  k,_,v=line.partition(' ');fields[k]=v
 path=fields.get('worktree');expected=safe.get(path)
 if not expected:continue
 rec={'path':path,'expected_head':expected,'timestamp':time.time()};actions.append(rec)
 try:
  assert 'locked' not in fields,'locked';assert fields.get('HEAD')==expected,'HEAD differs from retired safe-list pin'
  rec['initial_manifest_references']=initial_refs.get(path,[]);assert not rec['initial_manifest_references'],'external full host/process manifest references'
  rec['live_refs']=live(path);assert not rec['live_refs'],'live'
  # Full manifests already audited by controller. Re-read current local stream manifests; any exact reference remains protected.
  refs=[]
  for root in ['/tmp/claude-1000/queue','/home/ubuntu/queue']:
   for manifest in P.Path(root).glob('*.manifest'):
    if re.search(re.escape(path)+r'(?=$|[\s/\"\'])',manifest.read_text(errors='replace')):refs.append(str(manifest))
  rec['current_manifest_references']=refs;assert not refs,'current manifest references'
  st=S.run(['git','-C',path,'status','--porcelain=v1','--untracked-files=all'],capture_output=True,text=True);rec['status']=st.stdout;assert st.returncode==0 and not st.stdout,'dirty/untracked'
  ref='refs/maintenance/remote-recovery-20261001/retired-'+hashlib.sha256(path.encode()).hexdigest()[:16]
  rr=git('update-ref',ref,expected,'0'*40);assert rr.returncode==0,rr.stderr;rec['preserved_remote_head_ref']=ref
  rec['allocated_bytes_before']=int(S.check_output(['du','-s','-B1',path],text=True).split()[0]);v=os.statvfs('/home/ubuntu');rec['free_before']=v.f_bavail*v.f_frsize
  with open(out/(hashlib.sha256(path.encode()).hexdigest()[:16]+'_before.json'),'x') as f:json.dump(rec,f,indent=2)
  rr=git('worktree','remove',path);rec.update(returncode=rr.returncode,stderr=rr.stderr,path_exists=P.Path(path).exists());v=os.statvfs('/home/ubuntu');rec['free_after']=v.f_bavail*v.f_frsize;rec['filesystem_free_delta']=rec['free_after']-rec['free_before']
 except Exception as e:rec['skip_reason']=str(e)
 with open(out/'retirement_actions.json','w') as stream:json.dump(actions,stream,indent=2)
print(json.dumps({'worktrees_before':listed.stdout,'actions':actions,'repo':repo}))
