"""Bounded disk event journal; preserves exact software events without RAM list.
No clock/PHY qualification. Disk budget exhaustion fails with live debt retained.
"""
import collections,hashlib,json,sqlite3,zlib,uuid
from pathlib import Path
from hbm_provider_microvm_r21 import SectorProvider as Original
class JournalBudget:
    def __init__(self,root,bytes):
        self.root=Path(root)
        if self.root.exists() and any(self.root.iterdir()):raise ValueError('fresh aggregate journal root required')
        self.root.mkdir(parents=True,exist_ok=True)
        if bytes<131072:raise ValueError('positive bounded journal capacity')
        self.cap=bytes;self.used=0;self.next_journal=0;self.reserve(131072)
        self.path=self.root/'events.sqlite';self.db=sqlite3.connect(self.path)
        self.db.execute('pragma journal_mode=OFF');self.db.execute('pragma cache_size=-128')
        self.db.execute('create table event(journal integer,seq integer,value blob not null,primary key(journal,seq))')
    def reserve(self,n):
        if n<0 or self.used+n>self.cap:raise BufferError('aggregate journal disk budget; no discarded events')
        self.used+=n
class Slice:
    def __init__(self,j,start,end):self.j=j;self.start=start;self.end=end
    def __iter__(self):
        for row, in self.j.db.execute('select value from event where journal=? and seq>=? and seq<? order by seq',(self.j.id,self.start,self.end)):yield json.loads(zlib.decompress(row))
class DiskEvents:
    def __init__(self,budget):
        self.budget=budget;self.path=budget.path;self.db=budget.db;self.id=budget.next_journal;budget.next_journal+=1
        self.count=0;self.digest=hashlib.sha256();self.counts=collections.Counter();self.closed=False
    def append(self,event):
        if self.closed:raise ValueError('retired journal cannot accept new events')
        raw=json.dumps(event,sort_keys=True,separators=(',',':')).encode();encoded=zlib.compress(raw,1)
        # Conservative8x page/index allocation plus fixed128KiB per journal.
        self.budget.reserve(8*(len(encoded)+64));self.db.execute('insert into event values(?,?,?)',(self.id,self.count,encoded));self.count+=1;self.digest.update(len(raw).to_bytes(8,'little')+raw);self.counts[event['event']]+=1
        if self.count%128==0:self.flush()
    def __len__(self):return self.count
    def __iter__(self):return iter(Slice(self,0,self.count))
    def __getitem__(self,index):
        if isinstance(index,slice):
            start,end,step=index.indices(self.count)
            if step!=1:raise ValueError('bounded sequential journal slice only')
            return Slice(self,start,end)
        index=index+self.count if index<0 else index
        row=self.db.execute('select value from event where journal=? and seq=?',(self.id,index)).fetchone()
        if row is None:raise IndexError(index)
        return json.loads(zlib.decompress(row[0]))
    def flush(self):
        self.db.commit()
        if self.path.stat().st_size>self.budget.used:raise BufferError('journal page bound underestimated')
    def summary(self):
        self.flush();return dict(path=str(self.path),journal_id=self.id,events=self.count,event_counts=dict(self.counts),framed_event_SHA256=self.digest.hexdigest(),sqlite_bytes=self.path.stat().st_size,aggregate_reserved_bytes=self.budget.used,aggregate_cap_bytes=self.budget.cap,in_memory_event_list=False)
    def close(self):
        if not self.closed:self.flush();self.closed=True
class CompactSectors(dict):
    def __setitem__(self,key,value):
        super().__setitem__(key,bytearray(value) if all(x is not None for x in value) else value)
class BoundSectorProvider(Original):
    def __init__(self,extents,*,journal_budget,allocation_identity=None,**kw):
        super().__init__(extents,**kw);self.allocation_identity=allocation_identity;self.events=DiskEvents(journal_budget);self.backing=CompactSectors()
    def submit(self,identity,write=False,payload=b''):
        if self.events.closed:raise ValueError('retired provider cannot accept requests')
        # Reserve a conservative host-journal allowance BEFORE source admission.
        # Metadata reserve only, not an extra physical queue or data buffer.
        if self.events.budget.cap-self.events.budget.used<65536*(len(self.live)+1):raise BufferError('journal capacity before request acceptance')
        return super().submit(identity,write,payload)
    def log(self,event,t,**kw):
        if self.allocation_identity is not None:kw['allocation_identity']=self.allocation_identity
        return super().log(event,t,**kw)
