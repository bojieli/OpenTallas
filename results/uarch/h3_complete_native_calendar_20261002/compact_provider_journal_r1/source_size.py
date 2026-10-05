"""Actual PC0 source/home phase sizing and explicit runtime alias receipt."""
import gzip,hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools');sys.dont_write_bytecode=True
import hbm_bound_event_journal_r30 as journal
import h3_ds_checkpoint_provider_r30 as r30
import h3_ds_checkpoint_provider_r34 as r34
import h3_ds_query_provider_r36 as query
import h3_ds_history_provider_r36 as history
from hbm_provider_microvm_r21 import Identity
spec=importlib.util.spec_from_file_location('compact_calendar_sizing',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
packet_path=BASE.parent/'provider_shared_driver_join_r2/pc0_projection_inputs.json';packet=json.loads(packet_path.read_bytes())['packet']
raw=Path('/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz').read_bytes()
if hashlib.sha256(raw).hexdigest()!='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264':raise ValueError('current native pin')
native=json.loads(gzip.decompress(raw));pc0=native['instructions'][0]
home_path=Path('/home/ubuntu/OpenTallas')/native['residence_archive'];raw_home=home_path.read_bytes();homes=json.loads(gzip.decompress(raw_home))['homes']
with tempfile.TemporaryDirectory() as tmp:
    budget=c.CompactJournalBudget(Path(tmp)/'journal',1<<20)
    actual=c.compact_sector_provider_class(journal.BoundSectorProvider)
    provider=actual({('DeepSeek',95):[dict(base=0,bytes=32)]},journal_budget=budget,tags=1,
        allocation_identity=dict(address_class='scratch',native_owner=[0,[w['version'] for w in pc0['writes']],95,0,1]))
    provider.seed('DeepSeek',95,0,bytes(32));phases={}
    for serial,direction in enumerate(['read','write']):
        first=len(provider.events);t=provider.submit(Identity('DeepSeek',95,1,0,serial,0),write=direction=='write',payload=bytes(32) if direction=='write' else b'')
        provider.wait(t);provider.finish(t);phases[direction]=list(provider.events[first:])
    provider.events.close();budget.db.close()
model=c.size_compact_pc0_journals(packet,phases,pc0,homes)
model.update(native_sha256=hashlib.sha256(raw).hexdigest(),home_sha256=hashlib.sha256(raw_home).hexdigest(),native_input_path='/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz',home_input_path=native['residence_archive'],source_packet_sha256=hashlib.sha256(packet_path.read_bytes()).hexdigest(),producer_phase_parameters=provider.costs)
source_projection=dict(native_PC0=pc0,homes={str(i):homes[i] for w in pc0['writes'] for i in w['home_indices']},phase_events=phases,packet=packet)
install=c.install_compact_provider_journals([journal,r30,r34,query,history])
# Source files stay immutable; both the actual scratch constructor and writer
# namespaces now reference the source-guarded compact provider in this process.
if r30.BoundSectorProvider is not journal.BoundSectorProvider or r30.JournalBudget is not c.CompactJournalBudget:raise ValueError('actual scratch/RF factory aliases not joined')
outputs={'PC0_full96_source_phase_bound.json':model,'runtime_installation.json':install,'source_projection.json.gz':source_projection}
for name,obj in outputs.items():
    data=json.dumps(obj,sort_keys=True,separators=(',',':')).encode() if name.endswith('.gz') else (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
    if name.endswith('.gz'):data=gzip.compress(data,mtime=0)
    path=BASE/name
    if '--verify' in sys.argv:
        if path.read_bytes()!=data:raise ValueError('source-sized compact model/install changed '+name)
    elif path.exists():raise ValueError('fresh source model required')
    else:path.write_bytes(data)
print(json.dumps(dict(status='PASS_SOURCE_BOUND_COMPACT_PC0_FULL96_PHASE_ENCODING',ranks=96,events_upper=model['provider_phase_events_upper'],phase_disk_bytes=model['provider_phase_disk_reservation_bytes'],read_transaction_bytes=model['transaction_bytes_upper']['read'],write_transaction_bytes=model['transaction_bytes_upper']['write'],publication_transactions=sum(r['read_sector32']+r['write_sector32'] for r in model['source_publication_per_rank']),sampled_ratio=False,whole_journal_admission_complete=model['whole_journal_admission_complete']),sort_keys=True))
