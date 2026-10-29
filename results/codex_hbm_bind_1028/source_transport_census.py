"""Export every actual mapped crossing bit and its exact plan allocation.

This stops before type uniformisation and emission. Unmapped/undriven source
errors remain explicit; the output is a transport construction input, not PASS.
Usage: source_transport_census.py PLAN ASBUILT MANIFEST OUT
"""
import collections,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/die_plan'))
import bind as B
plan,asbuilt,manifest,out=map(Path,sys.argv[1:])
p=json.loads(plan.read_text());ab=json.loads(manifest.read_text())
if ab.get('map_file') and not Path(ab['map_file']).is_absolute():
    ab['map_file']=str(manifest.parent/ab['map_file'])
p['asbuilt']=ab;b=B.Binder(p,json.loads(asbuilt.read_text()),plan.parent,ab.get('base',str(root)))
b.map_cells();b.analyse();b.build_buses()
sinks=collections.defaultdict(list)
def walk(d,ci,pn,bit):
    if d[0]=='x':
        sinks[(d[1],d[6],d[2],d[3],d[4])].append(dict(path=b.F.cells[ci].path,port=pn,bit=bit,asbuilt_stages=d[5]))
    elif d[0] in ('or','and'):
        for sub in d[1]:walk(sub,ci,pn,bit)
for (ci,pn,bit),d in b.sinks.items():walk(d,ci,pn,bit)
pairs=[]
for (sp,dp),groups in sorted(b.cross.items()):
    rows=[]
    for (ci,pn),bits in sorted(groups.items()):
        cell=b.F.cells[ci]
        for bit in sorted(bits):
            key=(sp,dp,ci,pn,bit);link,index=b.bitpos[key]
            rows.append(dict(driver=cell.path,module=cell.module,port=pn,bit_index=bit,
                             source_plan_instance=b.rel_of(ci),sinks=sinks[key],
                             lane=link.get('lane'),lane_bit=index,
                             unplanned=bool(link.get('unplanned')),landed_cycles=b.bitcyc[key]))
    pairs.append(dict(src=sp,dst=dp,bits=len(rows),unplanned_bits=sum(r['unplanned'] for r in rows),drivers=rows))
rec=dict(schema='opentallas.hbm.source_transport_census.v1',source_json=str(asbuilt),manifest=str(manifest),
         counts=b.counts,errors=b.errors,pairs=pairs,unplanned_pairs=sum(bool(x['unplanned_bits']) for x in pairs),
         unplanned_bits=sum(x['unplanned_bits'] for x in pairs),
         status='DIAGNOSTIC_NO_TYPE_UNIFORMISATION_OR_EMISSION',
         note='Mapped source bits only. source_unmapped/undriven counts block completeness; no missing source is invented.')
out.write_text(json.dumps(rec,separators=(',',':'))+'\n')
print('source transport pairs',len(pairs),'unplanned',rec['unplanned_pairs'],'bits',rec['unplanned_bits'],flush=True)
