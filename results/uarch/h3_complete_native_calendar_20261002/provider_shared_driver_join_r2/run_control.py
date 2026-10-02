"""Join actual df6/r36 provider control to the64KiB journalled shared path.
Control payloads remain explicitly seeded; no checkpoint token launch.
"""
import gzip,hashlib,importlib.util,json,sys,sqlite3,zlib,tempfile,os
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
PEER=Path(os.environ.get('H3_DF6_SOURCE_ROOT',str(ROOT if (ROOT/'tools/test_h4_c0_ds_tiled_continuation.py').exists() else Path('/tmp/opentallas-C0-operand-windows-20261002'))))
sys.dont_write_bytecode=True
sys.path[:0]=[str(PEER/'tools'),'/home/ubuntu/OpenTallas/tools']
spec=importlib.util.spec_from_file_location('peer_control',PEER/'tools/test_h4_c0_ds_tiled_continuation.py');test=importlib.util.module_from_spec(spec);spec.loader.exec_module(test)
spec=importlib.util.spec_from_file_location('current_calendar_join',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
from hbm_provider_microvm_r21 import Identity
from hbm_bound_event_journal_r30 import BoundSectorProvider
case=test.ContinuationTests('test_actual64_tile_run_and_mirrored_publication');case.setUpClass();case.setUp()
memories={};calls=[]
class Memory:
    def __init__(self,owner):
        self.base=16777216+owner['SM']*65536;self.extent=dict(base=self.base,bytes=65536,rank=owner['rank'],SM=owner['SM']);self.serial=0
        self.p=BoundSectorProvider({('DeepSeek',owner['rank']):[dict(base=self.base,bytes=65536)]},journal_budget=case.budget,tags=1,allocation_identity=owner)
    def transact(self,offset,*,write,payload,length):
        chunks=[]
        for first in range(0,length,32):
            tx=self.p.submit(Identity('DeepSeek',self.extent['rank'],1,case.pc,self.serial,(self.base+offset+first)//32),write=write,payload=payload[first:first+32] if write else b'');self.serial+=1
            chunks.append(self.p.wait(tx));self.p.finish(tx)
        return b''.join(chunks)
def factory(owner):
    if owner['SM'] not in memories:memories[owner['SM']]=Memory(owner)
    memory=memories[owner['SM']];memory.p.allocation_identity=owner;return memory
inputs=BASE.parent/'group128_execution_join_r1/source_inputs'
primitive_sources=dict(bounded_native=gzip.decompress((inputs/'h3_qwen_bounded_native.py.gz').read_bytes()),arithmetic_helpers=gzip.decompress((inputs/'h3_qwen_complete_native.py.gz').read_bytes()))
try:
    record=c.execute_ds_provider_group128(case.run,case.pc,0,generation=1,identity=case.identity,source_store_view=case.writer['native_result_binding'],shared_factory=factory,primitive_sources=primitive_sources,movement_observer=calls.append)
    import numpy as np
    a=case.data;f=((a[0]+a[1])+(a[2]+a[3]))+((a[4]+a[5])+(a[6]+a[7]));u=f.view(np.uint32)
    expected=((u+np.uint32(32767)+((u>>16)&np.uint32(1)))&np.uint32(0xffff0000)).reshape(-1)
    np.testing.assert_array_equal(case.p.published[case.writer['version'],0].view(np.uint32),expected)
    assert not case.p._leased(case.version)
    record['scope']='Actual production provider/continuation implementation and shared microVM; seeded retained producer bytes, not trained numerical token'
    record['actual_movement_calls']=calls
    # Actual provider receipts retain file-relative IDs/ranges; paths in the
    # temporary control are normalised, never used as a production file claim.
    for receipt in record['actual_source_receipts']:receipt['journal_path']='control-events.sqlite'
    case.budget.db.commit()
    # Source receipt metadata contains ephemeral host filenames. Export a
    # canonical COPY; original live producer journal is never changed.
    def normalise(value):
        if isinstance(value,dict):return {k:('control-events.sqlite' if k=='journal_path' and v==str(case.budget.path) else normalise(v)) for k,v in value.items()}
        if isinstance(value,list):return [normalise(v) for v in value]
        return value
    with tempfile.TemporaryDirectory() as tmp:
        archive=Path(tmp)/'events.sqlite';db=sqlite3.connect(archive)
        db.execute('pragma journal_mode=OFF')
        db.execute('create table event(journal integer,seq integer,value blob not null,primary key(journal,seq))')
        for jid,seq,blob in case.budget.db.execute('select journal,seq,value from event order by journal,seq'):
            value=normalise(json.loads(zlib.decompress(blob)))
            encoded=zlib.compress(json.dumps(value,sort_keys=True,separators=(',',':')).encode(),1)
            db.execute('insert into event values(?,?,?)',(jid,seq,encoded))
        db.commit();db.close();raw=archive.read_bytes()
    record['journal_export_scope']='canonical event copy; only temporary receipt journal_path metadata relocated; sector events and source proof hashes unchanged'

    record['journal_uncompressed_sha256']=hashlib.sha256(raw).hexdigest()
    for name,data in [('execution.json.gz',gzip.compress(json.dumps(record,sort_keys=True,separators=(',',':')).encode(),mtime=0)),('events.sqlite.gz',gzip.compress(raw,mtime=0))]:
        path=BASE/name
        if '--verify' in sys.argv:
            if path.read_bytes()!=data:
                mismatch=BASE/('failed_replay_'+name)
                if not mismatch.exists():mismatch.write_bytes(data)
                raise ValueError('byteexact actual provider/shared join replay changed: '+name)
        else:
            if path.exists():raise ValueError('fresh evidence required')
            path.write_bytes(data)
    # Pin/archive all actual imported provider code, excluding this evolving
    # calendar. Large immutable native input is a prerequisite, not duplicated.
    source_dir=BASE/'source_inputs';source_dir.mkdir(exist_ok=True);pins={}
    for module in list(sys.modules.values())+[test]:
        filename=getattr(module,'__file__',None)
        if not filename:continue
        path=Path(filename)
        if path.suffix!='.py' or not path.name.startswith(('h3_','h4_','hbm_','test_h4_')) or path.name=='h3_complete_native_calendar.py':continue
        if not path.is_file():continue
        source=path.read_bytes();sha=hashlib.sha256(source).hexdigest();dest=source_dir/(sha+'.gz')
        if dest.exists() and gzip.decompress(dest.read_bytes())!=source:raise ValueError('source snapshot mismatch')
        if not dest.exists():dest.write_bytes(gzip.compress(source,mtime=0))
        if path.name in pins and pins[path.name]['sha256']!=sha:raise ValueError('ambiguous provider source')
        pins[path.name]=dict(sha256=sha,bytes=len(source),archive=str(dest.relative_to(BASE)))
    pins['native.json.gz']=dict(sha256=record['source_native_sha256'],archive=None,required_input='/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz',portable_closure=False)
    data=(json.dumps(pins,sort_keys=True,indent=2)+'\n').encode();dest=BASE/'source_pins.json'
    if '--verify' in sys.argv:
        if not dest.exists():dest.write_bytes(data)
        elif dest.read_bytes()!=data:raise ValueError('exact provider import source inventory changed')
    elif dest.exists():raise ValueError('fresh source inventory required')
    else:dest.write_bytes(data)
    print('PASS_ACTUAL_DF6_R36_SOURCE_SHARED_AND_MIRRORED_PUBLICATION')
    print(json.dumps(dict(source_spans=len(record['actual_source_receipts']),shared64=record['actual_shared_movements']['scratch64'],source_view_released=record['source_global_view_released'],mirror_journal=record['actual_RF_mirror_journal'],data_bound=record['total_operand_and_staging_bound_bytes'],production_closed=0,full_program_executed=False),sort_keys=True))
finally:case.tearDown()
