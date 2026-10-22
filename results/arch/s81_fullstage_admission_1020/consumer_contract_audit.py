"""Observe actual source emitter refusal and tag domains; no consumer qualification."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
R=Path.cwd();O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
FX='/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'
results=[]
for merge in ['0','1']:
 env=dict(os.environ,OT_XS_QPAIRS='12',OT_XS_GU_MERGE=merge)
 dest=O/('cap_merge'+merge+'.json')
 cmd=[sys.executable,str(R/'tools/s81_dv/layer_prog/xs_calendar.py'),'cap','--fixtures',FX,'--layer','L0','--out',str(dest)]
 r=subprocess.run(cmd,env=env,capture_output=True,text=True)
 log=O/('cap_merge'+merge+'.log');log.write_text(r.stdout+r.stderr)
 results.append(dict(merge=merge,exit=r.returncode,output_exists=dest.exists(),
  expected='baseline emitter success' if merge=='0' else 'structural contiguous-share refusal',
  expected_verdict=(r.returncode==0) if merge=='0' else (r.returncode!=0 and 'slice share not contiguous' in r.stderr)))
sys.path.insert(0,str(R/'tools/s81_slice'));import cap_model as C
trace=Path('/srv/opentallas-scratch/codex/s81-stage-admission-1020/out/compact_fseq/experts_gu/run_P145.log')
events=[]
for line in trace.read_text().splitlines():
 m=re.fullmatch(r'RET (\d+) ([0-9a-f]+)',line)
 if m:
  word=int(m[2],16);tag=(word>>1)&0xffffffff
  events.append(dict(edge=int(m[1]),tag=f'{tag:08x}',row=(tag>>13)&65535,row_flags=(tag>>27)&3))
assert events
r=dict(scope='SOURCE_EMITTER_AND_ACTUAL_FRAME_TAG_AUDIT_ONLY',full_stage_qualified=False,
 results=results,all_expected_verdicts=all(x['expected_verdict'] for x in results),
 actual_compact_gu_trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
 actual_row_flag_domains=sorted({e['row_flags'] for e in events}),first_actual_RET=events[0],
 descriptor_gap='rank-tag remap preserves row[15:14] op flags; real cfg_d updates must follow actual FIN lifetime and registered cfg path, not one unflagged descriptor',
 production_image_gap='xs_place.write_images writes field.cfg unchanged; bench-only remap_tags is not invoked there',
 a_proj_gap=dict(rows_per_slice=28,rows_per_frame=4,six_frame_slice_rows=24,total_missing_rank_rows=8,
  source='lower_xs.placement',scope='unmodified immutable c347 source'),
 inputs={f:hashlib.sha256((R/f).read_bytes()).hexdigest() for f in [
  'tools/s81_dv/layer_prog/xs_place.py','tools/s81_dv/layer_prog/lower_xs.py','tools/s81_dv/layer_prog/xs_calendar.py','tools/s81_slice/cap_model.py']})
(O/'consumer_audit.json').write_text(json.dumps(r,indent=1)+'\n')
print('CONSUMER_CONTRACT_AUDIT',json.dumps(r),flush=True)
assert r['all_expected_verdicts'],r
