"""Read-only source-backed PC0 reservation projection; never starts producer jobs."""
import gzip,hashlib,importlib.util,json,re,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
PRODUCER=Path('/tmp/opentallas-C0-production-execution-20261002')
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools');sys.dont_write_bytecode=True
from hbm_provider_microvm_r21 import SectorProvider,Identity
spec=importlib.util.spec_from_file_location('calendar_projection',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
p=SectorProvider({('DeepSeek',0):[dict(base=0,bytes=64)]},tags=1)
p.seed('DeepSeek',0,0,bytes(32));schema={}
for serial,direction in enumerate(['read','write']):
    first=len(p.events);t=p.submit(Identity('DeepSeek',0,1,0,serial,0),write=direction=='write',payload=bytes(32) if direction=='write' else b'');p.wait(t);p.finish(t)
    schema[direction]=[event['event'] for event in p.events[first:]]
packet=PRODUCER/'results/uarch/h4_c0_ds_native_execution_20261002/r2/addressed_prefix_price.json'
receipt=PRODUCER/'results/uarch/h4_c0_ds_native_execution_20261002/r4/reviewed_publication/record.json'
log=PRODUCER/'results/uarch/h4_c0_ds_native_execution_20261002/r4/publication.log'
cal=json.loads(receipt.read_text());cal['wall_seconds']=json.loads(log.read_text().splitlines()[-1])['wall_seconds']
inputs=dict(packet=json.loads(packet.read_text()),phase_schema=schema,calibration={k:cal[k] for k in ['total_events','wall_seconds','journal_sqlite_bytes','actual_journal_reserved_bytes']})
# Structural row bounds use the actual PC0 scratch allocation metadata and
# actual provider log records, not a sampled bytes/event average.
native_path=Path('/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz')
raw_native=native_path.read_bytes()
if hashlib.sha256(raw_native).hexdigest()!='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264':raise ValueError('actual current native input required')
op=json.loads(gzip.decompress(raw_native))['instructions'][0]
owner=[0,[w['version'] for w in op['writes']],95,0,1]
upper=inputs['packet']['sector_transactions_upper_per_rank'];row_bounds={}
for direction in ['read','write']:
    rows=[e for e in p.events if e['event'] in schema[direction]]
    # Pick only this direction's ordered transaction.
    serial=0 if direction=='read' else 1
    rows=[e for e in rows if e['identity']['serial']==serial]
    bounds=[]
    for event in rows:
        event=dict(event,allocation_identity=dict(address_class='scratch',native_owner=owner),tick=upper*128,tag=3,generation=upper,stack=3,local_sector31=786431)
        event['identity']=dict(target='DeepSeek',rank=95,epoch=1,pc=0,serial=upper,sector=3145727)
        if 'resident' in event:event['resident']=4
        n=len(json.dumps(event,sort_keys=True,separators=(',',':')).encode())
        # zlib compressBound, independent of observed compression ratio.
        encoded=n+(n>>12)+(n>>14)+(n>>25)+13
        bounds.append(dict(event=event['event'],json_bytes_upper=n,zlib_bytes_upper=encoded,journal_reserve_bytes_upper=8*(encoded+64)))
    row_bounds[direction]=bounds
read=inputs['packet']['original_staged_read_bytes_per_rank'];write=inputs['packet']['original_staged_write_bytes_per_rank']
r=(read+31)//32;w=(write+31)//32;extra=upper-r-w
reserve_per_rank=r*sum(e['journal_reserve_bytes_upper'] for e in row_bounds['read'])+(w+extra)*sum(e['journal_reserve_bytes_upper'] for e in row_bounds['write'])
structural=dict(schema='H4_PC0_ACTUAL_SCRATCH_PHASE_ROW_UPPER_V1',source_native_sha256=hashlib.sha256(raw_native).hexdigest(),PC=0,ranks=96,native_owner=owner,phase_rows=row_bounds,
    source_phase_sector_transactions_upper_per_rank=upper,
    exact_provider_schema_journal_accounting_upper_all96_bytes=reserve_per_rank*96+131072,
    scope='actual PC0 source owner and r30 scratch metadata, r21 default positive costs/tags; fixed AW27 extent/counter maxima, zlib worst case; source/publication/receipt journals additional UNKNOWN',
    actual_sqlite_footprint=None,actual_PC0_runtime_seconds=None,full_prefix_executed=False,
    empirical_event_density_used_for_this_bound=False,arbitrary_caps_injected=False,
    actual_shared_RF_L2_physical_calendar_qualified=False)
outputs={'pc0_phase_row_upper.json':structural,'pc0_projection_inputs.json':inputs,'pc0_96rank_projection.json':c.project_pc0_provider_journal(**inputs)}
paths=[packet,receipt,log,Path('/home/ubuntu/OpenTallas/tools/h3_ds_checkpoint_provider_r30.py'),Path('/home/ubuntu/OpenTallas/tools/hbm_provider_microvm_r21.py'),Path('/home/ubuntu/OpenTallas/tools/hbm_bound_event_journal_r30.py')]
archive=BASE/'source_inputs';archive.mkdir(exist_ok=True);pins=[]
for path in paths:
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest();dest=archive/(sha+'.gz')
    if dest.exists() and gzip.decompress(dest.read_bytes())!=raw:raise ValueError('immutable source archive collision')
    if not dest.exists():dest.write_bytes(gzip.compress(raw,mtime=0))
    pins.append(dict(path=str(path),sha256=sha,bytes=len(raw),archive=str(dest.relative_to(BASE)),producer_commit='WIP explicitly hash pinned' if str(path).startswith(str(PRODUCER)) else 'parent integrated source, exact bytes pinned'))
outputs['pc0_projection_source_pins_r2.json']=pins
for name,obj in outputs.items():
    data=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode();path=BASE/name
    if '--verify' in sys.argv:
        if path.read_bytes()!=data:raise ValueError('PC0 projection/source pins changed: '+name)
    elif path.exists():
        if path.read_bytes()!=data:raise ValueError('existing projection changed')
    else:path.write_bytes(data)
print(json.dumps(outputs['pc0_96rank_projection.json'],sort_keys=True))
