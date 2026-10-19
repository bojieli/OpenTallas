import odb, json, sys, re, hashlib, collections
from pathlib import Path

db=odb.dbDatabase.create(); odb.read_db(db,sys.argv[1]); b=db.getChip().getBlock(); scale=b.getDbUnitsPerMicron()
def xy(obj):
    if hasattr(obj,'getInst'):
        box=obj.getInst().getBBox(); return [(box.xMin()+box.xMax())/2/scale,(box.yMin()+box.yMax())/2/scale]
    boxes=[p for bp in obj.getBPins() for p in bp.getBoxes()]
    return [(boxes[0].xMin()+boxes[0].xMax())/2/scale,(boxes[0].yMin()+boxes[0].yMax())/2/scale] if boxes else None
def item(p):
    if hasattr(p,'getInst'):
        inst=p.getInst(); master=inst.getMaster().getName(); pin=p.getMTerm().getName()
        return dict(name=inst.getName()+'/'+pin,master=master,pin=pin,xy=xy(p),kind='ff' if re.search('DFF|SDFF',master) else ('transparent' if re.match(r'(BUF|INV)',master) else 'comb'))
    return dict(name=p.getName(),master=None,pin=p.getName(),xy=xy(p),kind='input' if str(p.getIoType())=='INPUT' else 'output')
def transparent(p):return re.match(r'(BUF|INV)',p.getInst().getMaster().getName()) is not None
def sinks(net,seen):
    if net.getId() in seen: raise RuntimeError('transparent loop')
    seen=seen|{net.getId()}; out=[]
    for p in net.getITerms():
        if str(p.getIoType())!='INPUT':continue
        if transparent(p):
            for q in p.getInst().getITerms():
                if str(q.getIoType())=='OUTPUT' and q.getNet():out.extend(sinks(q.getNet(),seen))
        else:out.append(item(p))
    out.extend(item(p) for p in net.getBTerms() if str(p.getIoType())=='OUTPUT')
    return out
roots=[]; direct_reach=0; unknown=[]
for net in b.getNets():
    if str(net.getSigType()) in ('POWER','GROUND'):continue
    drivers=[p for p in net.getITerms() if str(p.getIoType())=='OUTPUT']+[p for p in net.getBTerms() if str(p.getIoType())=='INPUT']
    for p in drivers:
        if hasattr(p,'getInst') and transparent(p):continue
        d=item(p); ends=sinks(net,set()); d.update(net=net.getName(),clock=str(net.getSigType())=='CLOCK',loads=len(ends),endpoints=ends)
        d['max_reach_um']=max((abs(d['xy'][0]-e['xy'][0])+abs(d['xy'][1]-e['xy'][1]) for e in ends if d['xy'] and e['xy']),default=0)
        roots.append(d)
    if not drivers and (net.getITerms() or net.getBTerms()):unknown.append(net.getName())
nonclock=[r for r in roots if not r['clock'] and not (r['kind']=='input' and r['name']=='clk')]
counts=collections.Counter(r['kind'] for r in nonclock)
bad=[r for r in nonclock if r['loads']>32]
inputs=[r for r in nonclock if r['kind']=='input']
outputdrivers={e['name']:r for r in nonclock for e in r['endpoints'] if e['kind']=='output'}
summary=dict(odb=sys.argv[1],odb_sha256=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(),dbu=scale,roots=len(roots),nonclock_roots=len(nonclock),counts=counts,max_loads=max((r['loads'] for r in nonclock),default=0),unsafe_roots=len(bad),max_reach_um=max((r['max_reach_um'] for r in nonclock),default=0),unknown_driver_nets=unknown,inputs=len(inputs),input_non_ff=[dict(name=r['name'],ends=[e for e in r['endpoints'] if e['kind']!='ff' or e['pin'] not in ('D','RESETN','RN','SN','CLK')]) for r in inputs if any(e['kind']!='ff' or e['pin'] not in ('D','RESETN','RN','SN','CLK') for e in r['endpoints'])],outputs=len(outputdrivers),output_non_ff={n:{k:v for k,v in r.items() if k!='endpoints'} for n,r in outputdrivers.items() if r['kind']!='ff'})
Path(sys.argv[2]).write_text(json.dumps(dict(summary=summary,unsafe=bad,all_roots=roots),indent=2)+'\n')
print(json.dumps(summary,indent=2))
