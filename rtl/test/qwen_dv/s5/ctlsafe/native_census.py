"""Strict mapped fanout census; includes raw ports and reset, collapses BUF/INV."""
import sys,json,hashlib,gzip
from pathlib import Path
root=Path(__file__).resolve().parents[5];sys.path.insert(0,str(root/'tools'))
import textbook_lint as T
p=Path(sys.argv[1]);data=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
g,top=T.flatten(T.parse_verilog(data.decode()),None);a=T.build(g,None);clocks,_=T.clock_nets(g,a)
rows=[];maxloads=0;portloads={}
for bit,(cell,pin) in a['driver'].items():
 if bit in clocks or bit<=3 or (cell>=0 and a['kind'][cell] in ('buf','tie')):continue
 count,ffs,ex=T.bufinv_fanout(g,a,bit,clocks);maxloads=max(maxloads,count)
 if cell<0:portloads[pin]=count
 if count>32:rows.append(dict(driver=T.net_label(g,a,bit),loads=count,flop_loads=ffs,port_driver=cell<0,flop_driver=cell>=0 and a['kind'][cell]=='ff'))
rows.sort(key=lambda x:x['loads'],reverse=True)
b=T.analyse(g,None,dict(T.THRESHOLDS))
out=dict(top=top,sha256=hashlib.sha256(data).hexdigest(),nonclock_drivers_over32=len(rows),flop_drivers_over32=sum(r['flop_driver'] for r in rows),raw_ports_over32=sum(r['port_driver'] for r in rows),max_nonclock_loads=maxloads,rst_n_loads=sum(v for k,v in portloads.items() if k in ('rst_n','rst_n[0]')) or None,metrics=b['metrics'],violations=rows,verdict='FAIL' if rows else 'PASS_FANOUT_ONLY',qualification='Mapped fanout census only; reset landing/pins/reach/storage still require their own proof')
print(json.dumps(out,indent=2))
