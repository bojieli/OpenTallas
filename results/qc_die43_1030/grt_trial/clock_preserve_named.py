# DIE-QC-43 diagnostic: preservation of the FIXED clock nets only (by source name),
# plus a census of nets that became CLOCK in the routed ODB.
import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--source',required=True);p.add_argument('--routed',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools)
import odb
from infra_replay import physical_snapshot
def load(path):
    d=odb.dbDatabase.create();odb.read_db(d,path);return d,d.getChip().getBlock()
def snap(b):
    out={}
    for n in b.getNets():
        st=str(n.getSigType()); w=n.getWire()
        out[n.getName()]=dict(sig=st, wire_len=(w.length() if w else 0), nsw=len(list(n.getSWires())))
    return out
ds,bs=load(a.source)
src_clk={}; src_meta=snap(bs)
for n in bs.getNets():
    if str(n.getSigType())=='CLOCK':
        src_clk[n.getName()]=hashlib.sha256(json.dumps(physical_snapshot(n),sort_keys=True,separators=(',',':')).encode()).hexdigest()
del ds
dr,br=load(a.routed)
rt_meta=snap(br)
changed=[];missing=[];sig_changed=[]
for name,h in src_clk.items():
    n=br.findNet(name)
    if n is None: missing.append(name);continue
    h2=hashlib.sha256(json.dumps(physical_snapshot(n),sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if h2!=h: changed.append(name)
    if str(n.getSigType())!='CLOCK': sig_changed.append(name)
new_clk=[k for k,v in rt_meta.items() if v['sig']=='CLOCK' and k not in src_clk]
from collections import Counter
cls=Counter((src_meta.get(k,{}).get('sig'), src_meta.get(k,{}).get('wire_len',0)>0, src_meta.get(k,{}).get('nsw',0)>0, rt_meta[k]['wire_len']>0) for k in new_clk)
newwire_sig=[k for k in new_clk if src_meta.get(k,{}).get('wire_len',0)!=rt_meta[k]['wire_len'] or src_meta.get(k,{}).get('nsw',0)!=rt_meta[k]['nsw']]
res=dict(source_clock_nets=len(src_clk),fixed_changed=len(changed),fixed_missing=len(missing),fixed_sig_not_clock=len(sig_changed),
  changed_sample=changed[:20],new_clock_nets=len(new_clk),new_clock_class={str(k):v for k,v in cls.items()},
  new_clock_sample=new_clk[:20],new_clock_wire_or_swire_changed=len(newwire_sig),
  verdict=('FIXED_CLOCK_UNCHANGED' if not changed and not missing else 'FAIL_FIXED_CLOCK_CHANGED'))
Path(a.out).write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
