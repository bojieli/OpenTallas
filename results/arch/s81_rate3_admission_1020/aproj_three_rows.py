"""Actual real-frame a_proj placement and release FSEQ tests; no consumer admission."""
import collections,copy,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import lower_xs as L
import xs_place as X
import dv_layer_compile as C
FX='/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0';DR='/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False);d=C.Die(C.die_tree(None,DR));fx=L.load_fixture(FX)
placements={};slices={};infos={}
for sl in sorted(d.slices(),key=lambda s:L.slice_index(d,s)):
 _,ps=L.placement(d,sl,fx);slices[sl]=ps
 for p in ps:placements[p['frame']]=p['rows'];infos[p['frame']]=(sl,p)
expected=set(range(len(L.a_proj_rows(fx))))
def cover(m):
 rows=[r for rs in m.values() for r in rs];return len(rows)==len(expected) and set(rows)==expected and len(set(rows))==len(rows) and all(1<=len(rs)<=4 for rs in m.values())
assert cover(placements) and len(placements)==122
assert all(len({L.a_proj_rows(fx)[r][0] for r in rs})==1 for rs in placements.values())
wrong=copy.deepcopy(placements);names=list(wrong);wrong[names[0]][0]=wrong[names[1]][0];assert not cover(wrong)
missing=copy.deepcopy(placements);missing[names[0]]=missing[names[0]][1:];assert not cover(missing)
os.environ['OT_XS_APROJ_TOPO']='0';legacy={}
for sl in slices:
 for p in L.placement(d,sl,fx)[1]:legacy[p['frame']]=p['rows']
assert not cover(legacy)
os.environ['OT_XS_APROJ_TOPO']='1'
# Span must be measured, not copied from a different matrix/row-placement vehicle.
exe_root=Path('/srv/opentallas-scratch/claude/toksim-s81c-fseq');cases=[]
for tensor in ['wq_a','wkv']:
 cases.append(next(fr for fr in placements if len(placements[fr])==3 and L.a_proj_rows(fx)[placements[fr][0]][0]==tensor))
results=[];binary_sources={}
for fr in cases:
 sl,p=infos[fr];master=p['master'];E=L.land_e(p['lk'])
 bld='v_h10_e2' if master.startswith('col_h10') else ('v_h9MX_e1' if 'MX' in master else f'v_h9nx_e{E}')
 exe=exe_root/bld/'obj/Vtb_toksim_fgu_seq';assert exe.exists(),(fr,master,E,bld)
 binary_sources[bld]=dict(binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),source_manifest_sha256=hashlib.sha256((exe_root/bld/'sources.sha256').read_bytes()).hexdigest(),verilator=(exe_root/bld/'verilator.version').read_text().strip())
 for mutant in [None,'swap','shift']:
  v=O/fr/(mutant or 'gold');a=SimpleNamespace(out=str(v),die_ref=None,die_src=DR,slice=sl,frame=fr,fixtures=FX,mutant=mutant,cycles=2000)
  L.cmd_gen(a);meta=json.loads((v/'meta.json').read_text());assert meta['plan']['faults']==0
  (v/'seq.hex').write_text(f"{meta['nrows']<<16:08x}\n");(v/'seqw.hex').write_text(f"{len(meta['plan']['ret']):04x}\n")
  cmd=[str(exe),f'+OT_ROM_DIR={v}','+T=2000','+K=5120',f'+OPS={meta["nrows"]}','+PH=0','+NPH=1','+PER=146','+RETIRE=1']
  run=subprocess.run(cmd,capture_output=True,text=True);(v/'run.log').write_text(run.stdout+run.stderr)
  errs,summ=L.check_words(meta,run.stdout+run.stderr);ok=run.returncode==0 and not errs
  go=int(re.search(r'^GO 0 (\d+)',run.stdout,re.M)[1]);ret=[int(x) for x in re.findall(r'^RET (\d+)',run.stdout,re.M)]
  r=dict(frame=fr,master=master,slice=sl,physical_frames=len(slices[sl]),mutant=mutant,rows=placements[fr],PASS=ok,expected_PASS=mutant is None,errors=errs[:10],summary=summ,spine_go_to_last_ret=max(ret)-go if ret else None)
  (v/'check.json').write_text(json.dumps(r,indent=1)+'\n');results.append(r);print('APROJ_FRAME',fr,master,len(slices[sl]),mutant,'PASS' if ok else 'FAIL',r['spine_go_to_last_ret'],errs[:1],flush=True)
  assert ok==(mutant is None),r
# Source cfg identity: actual formerly-empty eighth frame now has a_proj0 followed by wq_b1..11.
rec,field=X.compile_frame(d,'u_f_0R03',FX,['attn.wq_b'],only=set())
ids=[p['phase'] for p in rec['phases'] if p['op']=='attn.wq_b'];assert ids==list(range(1,12)),ids
inputs={}
for mod in list(sys.modules.values()):
 p=getattr(mod,'__file__',None)
 if p and str(p).startswith(str(R)) and str(p).endswith('.py'):inputs[str(Path(p).relative_to(R))]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=dict(scope='PRODUCER_PLACEMENT_FRAME_MECHANISM_ONLY',source='8665cb182',full_stage_qualified=False,
 complete_row_cover=cover(placements),physical_frames=len(placements),matrices=['wq_a','wkv'],row_count=448,
 rows_per_frame_histogram=dict(collections.Counter(map(len,placements.values()))),placements=placements,
 wrongowner_guard_rejected=not cover(wrong),missingrow_guard_rejected=not cover(missing),legacy_map_rejected=not cover(legacy),
 eighth_frame_wqb_phases=ids,producer_added_phases=0,producer_added_edges=0,
 consumer_gather_source_ages=None,consumer_admitted=False,results=results,binaries=binary_sources,imported_sources=inputs)
(O/'summary.json').write_text(json.dumps(r,indent=1)+'\n')
print('APROJ_MECHANISM_PASS',len(results),'source/golden/frame only; consumer ownership unadmitted',flush=True)
