from pathlib import Path
import hashlib,json,sys
lane=Path('/srv/opentallas-scratch2/claude/codex-s81-h9cts-1021');r=lane/'run_outputs';src=r/'src';c=r/'routes/gate/work/orfs';kit='physical/ref_tile/s81frame_col_h9_rf3rlfs1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
odb=c/'results/asap7/opentallas_col_h9_l4_lp_asap7_ref_gate/base/3_place.odb';assert sha(odb)=='7d677c7eb92511fcd3d2b6257b3c2591219730fd1a79189d31336c6352f1bc40'
changes=[]
for name,h in json.loads((lane/'output_overlay/hashes.json').read_text()).items():
 p=lane/'output_overlay'/name;assert sha(p)==h;dst=src/name
 changes.append(dict(path=name,before=sha(dst) if dst.exists() else None,after=h));dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(p.read_bytes())
sys.path.insert(0,str(src/'tools/ref_tile'));import forwarded_clock_outputs as O
specpath=src/kit/'spec.json';spec=json.loads(specpath.read_text());assert 'forwarded_clock_outputs' not in spec
spec['forwarded_clock_outputs']=[dict(input=f'xk[{i}]',output=f'xok[{i}]',inst=f'u_xo{i}',master='dsfd_dvrly_276_NS',input_pin='ck',output_pin='ck_o') for i in range(4)]
metadata=O.metadata(spec,src).rstrip();assert metadata.startswith('set ::ot_ce_fwd_outputs ') and len(O.contract(spec,src))==4
changes.append(dict(path=str(specpath.relative_to(src)),before=sha(specpath)));specpath.write_text(json.dumps(spec,indent=2)+'\n');changes[-1]['after']=sha(specpath)
pre=src/kit/'pre_cts.tcl';cached=c/'hooks/pre_cts_pre_cts.tcl';assert sha(pre)==sha(cached)=='a36725046e851b46e79f60d5a89c218a96ba5c86b66592ef9578793c2bea5ed5'
marker='source /src/physical/common_flow/clock_entries.tcl';text=pre.read_text();assert text.count(marker)==1 and metadata not in text
new=text.replace(marker,metadata+'\n'+marker)
for p in (pre,cached):changes.append(dict(path=str(p.relative_to(r)),before=sha(p)));p.write_text(new);changes[-1]['after']=sha(p)
sdc=src/kit/'clock_entry.sdc';old=sdc.read_text();assert 'set ::ot_ce_fwd_outputs ' not in old
# Restore exact declared metadata before any SDC consumer; constraints/timing unchanged.
sdc.write_text(metadata+'\n'+old);changes.append(dict(path=str(sdc.relative_to(src)),before=hashlib.sha256(old.encode()).hexdigest(),after=sha(sdc)))
config=(c/'config.mk').read_text();assert 'export PRE_CTS_TCL = /work/hooks/pre_cts_ot_cts_fix.tcl' in config
wrapper=c/'hooks/pre_cts_ot_cts_fix.tcl';assert 'source /work/hooks/pre_cts_pre_cts.tcl' in wrapper.read_text()
runner=(lane/'continue_cachefix.sh').read_text();oldroot=str(lane/'run_cachefix');assert oldroot in runner
runner=runner.replace(oldroot,str(r)).replace('GATE_HELPER_MAIN=99eff96d0ee86f973604b0190e0cebd01388cc2f','GATE_HELPER_MAIN=1a872af33')
assert 'FLOW_VARIANT=base -o /work/$NB/3_place.odb cts' in runner
(lane/'continue_outputs.sh').write_text(runner)
receipt=dict(parent_run=str(lane/'run_cachefix'),parent_failed_guard='OT_FORWARDED_SOFT undeclared xk[0] -> xok[0]',helper_publication='1a872af33',runtime_verified='INPROCESS-SYNC 2026-10-21T15:43:09-07:00, sixfocusedPASS/pairedNEW0',placement_sha256=sha(odb),changes=changes,exact_contract=spec['forwarded_clock_outputs'],resolved_pre_cts='/work/hooks/pre_cts_ot_cts_fix.tcl -> /work/hooks/pre_cts_pre_cts.tcl',wrapper_sha256=sha(wrapper),source_hook_sha256=sha(pre),cached_hook_sha256=sha(cached),clock_entries_sha256=sha(src/'physical/common_flow/clock_entries.tcl'),runner_sha256=sha(lane/'continue_outputs.sh'),scope='ONE saved-placement normal CTS/clock/path/GRT continuation. Four exact source-proven positive hard clock-through outputs. No source RTL/Lib/ODB/layout/timing changes. No original mutation or GPL repeat.')
(lane/'source_manifest_outputs.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
