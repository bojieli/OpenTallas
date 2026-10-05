"""Lossless replay of parent's reviewed complete joined movement stream."""
import gzip,hashlib,importlib.util,json,sqlite3,zlib,tempfile,shutil,tarfile,io,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];SOURCE=BASE.parent/'provider_shared_driver_join_r2'
spec=importlib.util.spec_from_file_location('compact_calendar',ROOT/'tools/h3_complete_native_calendar.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
expected=json.loads((SOURCE/'manifest.json').read_bytes())['files']['events.sqlite.gz']['sha256']
if hashlib.sha256((SOURCE/'events.sqlite.gz').read_bytes()).hexdigest()!=expected:raise ValueError('retained actual movement archive source changed')
start=time.monotonic();records=[];total=0;transactions=0
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp);raw=tmp/'source.sqlite'
    with gzip.open(SOURCE/'events.sqlite.gz','rb') as source,raw.open('wb') as out:shutil.copyfileobj(source,out)
    db=sqlite3.connect('file:'+str(raw)+'?mode=ro',uri=True)
    budget=c.CompactJournalBudget(tmp/'compact',1<<30)
    for jid, in db.execute('select distinct journal from event order by journal'):
        events=c.CompactDiskEvents(budget)
        if events.id!=jid:raise ValueError('retained actual source journal membership changed')
        source_digest=hashlib.sha256();source_count=0
        for blob, in db.execute('select value from event where journal=? order by seq',(jid,)):
            canonical=zlib.decompress(blob);event=json.loads(canonical)
            if canonical!=json.dumps(event,sort_keys=True,separators=(',',':')).encode():raise ValueError('source canonical replay contract')
            events.append(event);source_digest.update(len(canonical).to_bytes(8,'little')+canonical);source_count+=1
            if event['event']=='request_accept':transactions+=1
        source_framed=source_digest.hexdigest();replay=hashlib.sha256();replay_count=0
        for event in events:
            canonical=json.dumps(event,sort_keys=True,separators=(',',':')).encode();replay.update(len(canonical).to_bytes(8,'little')+canonical);replay_count+=1
        if source_framed!=events.digest.hexdigest() or source_framed!=replay.hexdigest() or replay_count!=source_count:raise ValueError('lossless full source journal replay changed')
        if events.validator.live or events.fault:raise ValueError('source complete reverse lifecycle not closed')
        summary=events.summary();summary.pop('path');summary.pop('aggregate_reserved_bytes');summary.pop('aggregate_cap_bytes');summary.update(source_framed_SHA256=source_framed,byteexact_canonical_replay=True)
        records.append(summary);total+=source_count;events.close()
    budget.db.commit();budget.db.close();db.close()
    files={str(p.relative_to(budget.root)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(budget.root.rglob('*')) if p.is_file()}
    archive=io.BytesIO()
    with tarfile.open(fileobj=archive,mode='w') as tar:
        for name in sorted(files):
            data=(budget.root/name).read_bytes();entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=0;entry.mode=0o644;tar.addfile(entry,io.BytesIO(data))
    encoded=gzip.compress(archive.getvalue(),mtime=0)
    record=dict(schema='H4_LOSSLESS_PARENT_JOINED_STREAM_COMPACT_REPLAY_V1',source_gzip_SHA256=expected,
        events=total,sector_transactions=transactions,journals=records,files=files,all_actual_events_retained=True,
        source_version_ownership_unchanged=True,all_source_lifecycles_drained=True,aggregate_accounting_bytes=budget.used,
        compact_files_bytes=sum(f['bytes'] for f in files.values()),archive_SHA256=hashlib.sha256(encoded).hexdigest(),
        extent_admission_from_sample_ratio=False,production_calls_closed=0,production_unknown_shared_calls=193316,
        scope='all source events of reviewed provider/shared/writer join, no disconnected replacement payload or fewer-rank qualification',hardware_qualified=False)
    for name,data in [('lossless_compact_events.tar.gz',encoded),('lossless_replay.json',(json.dumps(record,sort_keys=True,indent=2)+'\n').encode())]:
        path=BASE/name
        if '--verify' in sys.argv:
            if path.read_bytes()!=data:raise ValueError('compact encoded archive/source replay changed '+name)
        elif path.exists():raise ValueError('fresh evidence required')
        else:path.write_bytes(data)
print(json.dumps(dict(status='PASS_ALL_PARENT_SOURCE_EVENTS_LOSSLESS',events=total,sector_transactions=transactions,source_journals=len(records),compact_files_bytes=record['compact_files_bytes'],accounting_bytes=budget.used,wall_seconds=time.monotonic()-start),sort_keys=True))
