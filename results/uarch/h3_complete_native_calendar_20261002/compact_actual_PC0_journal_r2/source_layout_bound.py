"""Whole actual PC0 record-layout upper; never a sampled compression ratio."""
import gzip,hashlib,importlib.util,json,sqlite3,tarfile,tempfile,sys
from pathlib import Path
from collections import Counter
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3]
spec=importlib.util.spec_from_file_location('compact_bound',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
source=json.loads((BASE/'lossless_replay.json').read_bytes());archive=BASE/'lossless_compact_events.tar.gz'
if hashlib.sha256(archive.read_bytes()).hexdigest()!=source['archive_SHA256']:raise ValueError('actual96 PC0 compact archive changed')
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp)
    with tarfile.open(archive,'r:gz') as tar:
        for entry in tar:
            if not entry.isfile() or len(Path(entry.name).parts)!=1 or entry.name not in source['files']:raise ValueError('exact compact archive member required')
            data=tar.extractfile(entry).read();pin=source['files'][entry.name]
            if len(data)!=pin['bytes'] or hashlib.sha256(data).hexdigest()!=pin['sha256']:raise ValueError('actual compact file source hash')
            (root/entry.name).write_bytes(data)
    db=sqlite3.connect('file:'+str(root/'dictionary.sqlite')+'?mode=ro',uri=True)
    descriptors={};dictionary_upper=131072
    for identifier,raw in db.execute('select id,value from dictionary order by id'):
        dictionary_upper+=8*(len(raw)+64);obj=json.loads(raw)
        if isinstance(obj,dict) and {'value','paths','metadata','checksum'}<=obj.keys():descriptors[identifier]=obj
    histogram=Counter();total=0
    for filename in sorted(root.glob('*.events')):
        with filename.open('rb') as stream:
            if stream.read(6)!=b'H3CJ1\0':raise ValueError('source event stream header')
            end=filename.stat().st_size
            while stream.tell()<end:
                size=c.compact_read_uint(stream);first=stream.tell();identifier=c.compact_read_uint(stream)
                if identifier not in descriptors or first+size>end:raise ValueError('source frame descriptor/extent')
                histogram[identifier]+=1;total+=1;stream.seek(first+size)
    if total!=5664480 or total!=source['events']:raise ValueError('whole actual96 PC0 event coverage')
    rows=[];record_upper=0
    for identifier,count in sorted(histogram.items()):
        d=descriptors[identifier];frame=10+10*len(d['paths'])+(10 if d['metadata'] else 0)+(32 if d['checksum'] else 0);bound=frame+len(c.compact_uint(frame))
        rows.append(dict(descriptor=identifier,event=d['value']['event'],events=count,integer_fields=len(d['paths']),frame_upper=bound))
        record_upper+=count*bound
    n=len(source['journals']);index_upper=sum(16*((j['events']+127)//128) for j in source['journals'])
    checksum_events=sum(j['event_counts'].get(k,0) for j in source['journals'] for k in ['software_backing_visible','software_read_capture'])+sum(j['event_counts'].get('software_backing_visible',0) for j in source['journals'])
    # Prospective actual provider wrapper adds32 raw checksum bytes + at most
    # one frame-length byte to write admissions/visibility and read captures.
    future_checksums_upper=checksum_events*33
    future_descriptor_upper=2*dictionary_upper
    upper=record_upper+future_descriptor_upper+index_upper+n*8192+65536*5+future_checksums_upper
    result=dict(schema='H4_ACTUAL96_PC0_COMPLETE_COMPACT_RECORD_LAYOUT_BOUND_V1',ranks=96,events=total,transactions=738816,
        source_SQLite_SHA256='6b4f32a19ab71908e90d51d9e6d292d73932c8d8d28d974fefc92f5b859940de',source_archive_SHA256=source['archive_SHA256'],
        all_source_event_layouts=rows,typed_record_bytes_upper=record_upper,source_dictionary_bytes_upper=dictionary_upper,
        augmented_dictionary_envelope_bytes=future_descriptor_upper,sparse_index_bytes_upper=index_upper,
        file_allocation_padding_bytes=n*8192,preacceptance_headroom_bytes=65536*5,
        prospective_actual_payload_checksum_bytes_upper=future_checksums_upper,
        complete_same_PC0_record_shape_disk_reservation_bytes=upper,integer_width_bits=64,
        all_actual_events_sized=True,sampled_ratio_used=False,records_discarded=0,
        scope='all actual96 PC0 source record shapes, plus actual payload-checksum fields; does not include unexecuted primitive scratch phases or unknown future-PC record shapes',
        full_program_journal_admission=False,primitive_scratch_transport_qualified=False,hardware_qualified=False)
    db.close()
path=BASE/'actual96_record_layout_bound.json';data=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
if '--verify' in sys.argv:
    if path.read_bytes()!=data:raise ValueError('all actual PC0 source layout bound changed')
elif path.exists():raise ValueError('fresh record required')
else:path.write_bytes(data)
print(json.dumps(dict(status='PASS_ALL_ACTUAL96_PC0_RECORD_SHAPES_SIZED',events=total,ranks=96,typed_disk_reservation_bytes=upper,sampled_ratio=False),sort_keys=True))
