"""Compile each field once; preserve source-pinned cache before calendar admission."""
import hashlib,json,os,pickle,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_field_calendar as F
import dv_layer_compile as C
D=Path('/srv/opentallas-scratch/codex/s81-rom12-1020')
O=D/'out/pack_real';O.mkdir(parents=True,exist_ok=True)
die=C.Die(C.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'))
for L in sys.argv[1:]:
 cache=O/(L+'.pickle')
 if cache.exists():r=pickle.loads(cache.read_bytes())
 else:
  r=F.compile_ops(die,'u_s_0S',f'/srv/opentallas-scratch/claude/s81-calpipe/fixtures/{L}',L)
  cache.write_bytes(pickle.dumps(r))
 lc=F.layer_calendar(r['cals'])
 F.write_layer_images(lc,r['phase'],r['stream'],O/L)
 mu=[]
 for name in ['ar','mtp']:
  m=json.loads((Path('/srv/opentallas-scratch/claude/s81-calpipe/mu')/f'calendar_{name}_cal1.json').read_text())
  mu.append(dict(mode=m['mode'],**F.mu_check(lc['windows'],[s['shift'] for s in m['slots']],m['period'],m['slot'])))
 rec=dict(layer=L,frame=r['frame'],ops={c['op']:F.record(c) for c in r['cals']},rows=lc['rows'],segments=lc['segments'],unique_intervals=lc['unique_intervals'],layer_windows=lc['windows'],action_edge_proof=True,mu=mu)
 (O/L/'field_calendar.json').write_text(json.dumps(rec,indent=1)+'\n')
 loaded={str(Path(m.__file__).resolve().relative_to(R)):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(R)}
 (O/L/'compiler_sources.json').write_text(json.dumps(loaded,indent=1)+'\n')
 print('REAL_PACK',L,'oldrows',sum(c['cal_rows'] for c in r['cals']),'rows',lc['rows'],'intervals',len(lc['segments']),'unique',lc['unique_intervals'],'mu',[(m['mode'],m['PASS']) for m in mu],flush=True)
