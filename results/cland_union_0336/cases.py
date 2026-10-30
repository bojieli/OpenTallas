from pathlib import Path
import random,json
from replay import run
b=Path(__file__).resolve().parent;r=random.Random(913)
obs=[[0,0,108,270],[108,0,162,270],[162,0,162,270],[1080,270,540,540],[1440,540,540,270],[5300,810,162,540],[600,1350,0,270],[108,2700,432,270],[300,2700,400,270]]
cells=[[f'u_cland_test/c{i}',r.choice([54,108,162,216,324,540]),r.choice([270,540]),0,0,[0,0,10.8,4.32],'ring:test']for i in range(32)]
d={'core':[0,0,10800,4320,1000],'rows':[[y,'R0'if y//270%2==0 else'MX']for y in range(0,4320,270)],'row_height':270,'site_width':54,'obstacles':obs,'cells':cells}
reports=[]
for column,cursor in [(False,0),(False,1),(True,0),(True,1)]:
 a=run(b/'baseline.tcl',d,column=column,cursor=cursor);c=run(b.parents[1]/'tools/die_plan/landing_placement.tcl',d,column=column,cursor=cursor)
 ok=a['positions']==c['positions'] and a['fail']==c['fail'] and not a['fail'] and a['placed']==c['placed']==len(cells)
 reports.append({'column':column,'cursor':cursor,'mixed_height_cells':sum(x[2]>270 for x in cells),'placed':c['placed'],'equal_positions':a['positions']==c['positions'],'failures':c['fail'],'verdict':'PASS'if ok else'FAIL'})
 if not ok:print(a,c);raise SystemExit(1)
(b/'mixed_cases.json').write_text(json.dumps({'cases':reports,'coverage':'mixed widths/heights, overlapping/nested/touching reservations, a zero-width legacy point, row/column modes with and without cursor'},indent=2)+'\n')
print(json.dumps(reports))
