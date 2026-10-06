import pathlib,json,hashlib,collections,tarfile
r=pathlib.Path('/srv/opentallas-scratch/codex/epicurus-field-phase-matched-20261005-r1')
a=json.loads((r/'runs/summary.json').read_text()); assert(a['expected_cases'],a['completed'],a['passed'])==(640,640,640)
g=collections.defaultdict(list)
for x in a['results']:g[x['group']].append(x)
out=dict(scope=a['scope'],terminal_exit=int((r/'terminal.exit').read_text()),node_regions=640,admission_mode_runs=1280,source_commit='1002323510d8d64bbf90c97d0de7911d724218a5',calibration_passed=sum(x['calibration'] for x in a['results']),nodes=[],physical_admitted=False,fulltoken_adopted=False,peak_note='link.metrics404620KiB; run.metrics151888KiB is driver RSS, NOT aggregate worker maximum. Admission16GiB estimate with actual headroom/reserve; no arbitrary caps.')
for name,rs in g.items():
 n=dict(node=name,regions=len(rs),phases=rs[0]['phases'],modes={})
 for mode in ['serial','overlap']:
  ms=[x['results'][mode] for x in rs]
  n['modes'][mode]=dict(exact_rows=sum(x['rows'] for x in ms),first_accept=min(x['events']['A'][0][1] for x in ms),last_stored_vm_cycle_max_region=max(x['profile'][0]['last_vm_commit'] for x in ms),idle_cycle_max_region=max(x['node'][0]['idle'] for x in ms),first_go=min(x['events']['G'][0][0] for x in ms),input_bytes_per_region=sorted(set(x['profile'][0]['input_bytes'] for x in ms)),drain_after_vm_commit=sorted(set(x['profile'][0]['drain_after_vm_commit'] for x in ms)),go_sequences_uniform_all_regions=len(set(tuple(map(tuple,x['events']['G'])) for x in ms))==1)
 n['max_region_stored_visibility_difference_cycles']=n['modes']['serial']['last_stored_vm_cycle_max_region']-n['modes']['overlap']['last_stored_vm_cycle_max_region']
 out['nodes'].append(n)
out['rows_per_mode']=sum(n['modes']['serial']['exact_rows'] for n in out['nodes'])
out['actual_storage_value_assertions']=out['rows_per_mode']*2
out['all_write_commit_storage_assertions']=out['rows_per_mode']*2*3
out['region_max_scope']='Independent full-region measurements; not installed128-root global-barrier run. Same phase counts; noR93elimination credit. Full die-wire/broadcast/CDC/deadline composition Maxwell-owned.'
(r/'terminal.json').write_text(json.dumps(out,indent=2)+'\n')
with tarfile.open(r/'events.tar.gz','w:gz') as t:
 for p in sorted((r/'runs').rglob('*')):
  if p.is_file():t.add(p,arcname=str(p.relative_to(r)))
files=[r/n for n in ['events.tar.gz','terminal.json','launch_inputs.json','run.sh','link.log','run.log','link.metrics','run.metrics','terminal.exit','matched_tb','collect.py','collection_failure_r1.txt']]
(r/'terminal_hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2)+'\n')
print('640/640 nodes; 1280 modes; rows/mode',out['rows_per_mode'],'events compressed bytes',(r/'events.tar.gz').stat().st_size)
