"""Exact native leaf port-bit identities for matching physical station endpoints.

Usage: native_leaf_ports.py TOP HUB_GRAPH OUT NAME [NAME ...]
No virtual sidecar aliases or physical coordinates are inferred.
"""
from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/hbm_b2'))
from b2_top import Die,parse_expr
top,graph,out=map(Path,sys.argv[1:4]);names=sys.argv[4:]
d=Die(top,{})
rows={x['path']:x for x in json.loads(graph.read_text())['cells']}
records=[]
for name in names:
    cell=d.insts[name];row=rows[name]
    assert cell['master']==row['module'],(name,'selected master differs')
    ports={}
    for pn,expr in cell['conns'].items():
        bits=[]
        for s in parse_expr(expr,d.widths):
            if s[0]=='n':
                for index in range(s[2],s[3]+1):
                    driver=d.driver.get(s[1])
                    bits.append(dict(net=s[1],bit=index,direct_driver=list(driver) if driver else None))
            else:
                bits.extend(dict(constant='x' if s[2]=='x' else str((s[2]>>i)&1)) for i in range(s[1]))
        ports[pn]=dict(expression=expr,width=len(bits),bits=bits)
    records.append(dict(path=name,module=row['module'],partition=row['partition'],
                        plan_instance=row['plan_instance'],params=cell['params'],ports=ports))
rec=dict(schema='opentallas.hbm.native_leaf_port_bits.v1',source=str(top),
         source_sha256=hashlib.sha256(top.read_bytes()).hexdigest(),cells=records,
         status='SOURCE_IDENTITIES_ONLY_NOT_PHYSICAL_STATION_BIND',
         note='LSB-first actual port bit expressions and direct native drivers; no aliases, stations, cycles or endpoints invented.')
out.write_text(json.dumps(rec,separators=(',',':'))+'\n')
print('native leaf ports',len(records),sum(v['width'] for r in records for v in r['ports'].values()),flush=True)
