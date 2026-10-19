import sys,json,collections
from pathlib import Path
p=Path(sys.argv[1]);sys.path[:0]=[str(p/'kit'),str(p/'kit/vendor')]
from dft.liberty import read_liberty
from strict_contract import native_cells
load=lambda f:json.loads((p/f).read_text())
a=next(iter(load('output/native/raw.json')['modules'].values()))['cells'];b=next(iter(load('output/pre_native/raw.json')['modules'].values()))['cells'];new=set(a)-set(b);paths=sorted((p/'input/native_libs').glob('*_TT_*.lib*'));libs=read_liberty(paths);caps=native_cells(paths,used_masters={a[n]['type'] for n in new})
rows=[]
for n in sorted(new):
 c=a[n];l=caps[c['type']];cp=sum(float(v['native_capacitance']['capacitance']) for pin,v in l['pins'].items() if v['direction']=='input');openout=all(not bs for pin,bs in c['connections'].items() if c['port_directions'][pin]=='output');rows.append(dict(instance=n,master=c['type'],native_area_um2=libs[c['type']]['area'],native_TT_input_cap_fF=cp,open_output_clock_load=openout))
j=dict(schema='int8.postcts.readonly.cost.v1',new_cells=len(rows),new_native_area_um2=sum(r['native_area_um2'] for r in rows),new_TT_input_cap_fF=sum(r['native_TT_input_cap_fF'] for r in rows),open_output_loads=sum(r['open_output_clock_load'] for r in rows),open_output_load_area_um2=sum(r['native_area_um2'] for r in rows if r['open_output_clock_load']),open_output_TT_input_cap_fF=sum(r['native_TT_input_cap_fF'] for r in rows if r['open_output_clock_load']),rows=rows)
(p/'output/cost_readonly.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps({k:v for k,v in j.items() if k!='rows'},indent=2))
