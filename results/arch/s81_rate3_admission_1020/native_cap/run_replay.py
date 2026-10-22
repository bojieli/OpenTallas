"""Replay observed producer RET pins into exact unqualified native CAPC5c source."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
R=Path.cwd();P=R/'results/arch/s81_rate3_admission_1020/native_cap';O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'));sys.path.insert(0,str(R/'tools/s81_slice'))
import lower_xs as L
import dv_layer_compile as C
import cap_model as CM
D=C.Die(C.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'));fx=L.load_fixture('/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0')
V=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator';version=subprocess.check_output([str(V),'--version'],text=True);assert '5.050' in version
sources=(P/'sources.txt').read_text().split()+[str(P/'tb_aproj_cap_replay.sv')]
shas={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in sources};(O/'sources.json').write_text(json.dumps(shas,indent=1)+'\n')
cmd=[str(V),'--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--top-module','tb_aproj_cap_replay','-Mdir',str(O/'obj'),*sources,'--build-jobs','4','-MAKEFLAGS','OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0']
with (O/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,('BUILD_FAILED',r.returncode)
exe=O/'obj/Vtb_aproj_cap_replay';results=[];base=Path('/srv/opentallas-scratch/codex/s81-rate3-admission-1020/out/aproj_rank_tags')
for fr in ['u_f_0R03','u_f_7R00']:
 folder=base/fr/'gold';m=json.loads((folder/'meta.json').read_text());sl=m['slice'];contract=L.aproj_capture_contract(D,sl,fx,1)
 parts=D.inst[sl]['conns']['rt'].split(',');lanes=[]
 for part in reversed(parts):
  part=part.strip();empty=re.fullmatch(r"(\d+)'d0",part)
  if empty:lanes += [None]*(int(empty[1])//70)
  else:
   n=re.search(r'w_r_(f_\w+)_(?:src|dst|lnd)',part);assert n,part;lanes.append('u_'+n[1])
 lane=lanes.index(fr);rows={int(k):v for k,v in m['rows'].items()};expected=[]
 for row,v in rows.items():
  bad,leaf,port,addr,data=CM.decode(((1<<14)|row)<<13,int(v['bf16'])<<16,contract['cfg']);assert not bad
  expected.append((leaf<<45)|(port<<44)|(addr<<32)|data)
 observed=[(int(t),int(w,16)) for t,w in re.findall(r'^RET (\d+) ([0-9a-f]+)',(folder/'run.log').read_text(),re.M)]
 assert observed and not m['plan']['faults']
 source_row=next(iter(rows));foreign=next(r for r in range(448) if r not in [x['rank_row'] for x in contract['rows']])
 for mutant in ['gold','wrongowner','missingpartial']:
  out=O/(fr+'_'+mutant);out.mkdir();rt_idle=sum(1<<(70*i) for i in range(8));stim=[rt_idle]*2048
  cfg=int(contract['cfg_d'],16);stim[200]|=(1<<720)|(cfg<<560)
  for index,(t,w) in enumerate(observed):
   if mutant=='missingpartial' and index==0:continue
   if mutant=='wrongowner':
    tag=(w>>1)&0xffffffff
    if ((tag>>13)&0x3fff)==source_row:
     tag=(tag&~(0x3fff<<13))|(foreign<<13);w=(w&~(0xffffffff<<1))|(tag<<1)
   rt=(w<<2)|((w&1)<<1)|1
   stim[t]=(stim[t]&~(((1<<70)-1)<<(70*lane)))|(rt<<(70*lane))
  if mutant=='missingpartial':stim[800]|=(1<<720)|(cfg<<560) # actual F11 phase boundary exposes the dropped sibling
  (out/'stim.hex').write_text(''.join(f'{w:0181x}\n' for w in stim))
  (out/'expected.hex').write_text(''.join(f'{w:012x}\n' for w in expected+[0]*(512-len(expected))))
  rr=subprocess.run([str(exe),f'+DIR={out}','+T=1100',f'+N={len(expected)}'],capture_output=True,text=True);log=rr.stdout+rr.stderr;(out/'run.log').write_text(log)
  ok=rr.returncode==0 and 'PASS actual_aproj_to_candidate_CAP' in log
  r=dict(frame=fr,slice=sl,physical_lane=lane,mutant=mutant,PASS=ok,expected_PASS=mutant=='gold',exit=rr.returncode,
   expected_rows=len(expected),observed_root_words=len(observed),capture_lines=[x for x in log.splitlines() if x.startswith(('CAP_WRITE','CAP_FAULT','CAP_MISSING','CAP_REPLAY_END','FAIL','PASS'))],
   frame_log_sha256=hashlib.sha256((folder/'run.log').read_bytes()).hexdigest(),frame_meta_sha256=hashlib.sha256((folder/'meta.json').read_bytes()).hexdigest(),contract=contract)
  (out/'check.json').write_text(json.dumps(r,indent=1)+'\n');results.append(r);print('NATIVE_CAP_REPLAY',fr,lane,mutant,'PASS' if ok else 'FAIL',r['capture_lines'][-2:],flush=True)
  assert ok==(mutant=='gold'),r
summary=dict(scope='ACTUAL_PRODUCER_RET_TO_CAP_PIN_MECHANISM_ONLY',full_stage_qualified=False,physical_qualified=False,
 producer_source='d4350d97c',cap_source='dc702fbe899e0ef127317079eecbc8b1d976513f',candidate=json.loads((P/'candidate.json').read_text()),
 clock_scope='five clocks at common phase, functional source only; real E/F physical clock/GRT FAIL remains',
 transport_scope='actual observed frame RET then native CAP pin replay; current die source-to-pin links and simultaneous whole-slice arrival calendar NOT qualified',
 verilator=version,binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),sources=shas,results=results)
(O/'summary.json').write_text(json.dumps(summary,indent=1)+'\n');print('NATIVE_CAP_PIN_MECHANISM_PASS',len(results),flush=True)
