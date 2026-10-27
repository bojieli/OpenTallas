import odb,json
from pathlib import Path
D=odb.dbDatabase.create();odb.read_db(D,'/work/mesh_straps.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
cells={}
for i in b.getInsts():
 assert i.getMaster().getName()=='BUFx24_ASAP7_75t_R'
 r=i.getBBox();cx=(r.xMin()+r.xMax())/(2*u);cy=(r.yMin()+r.yMax())/(2*u)
 cells[i.getName()]=[round(cx-2,6),round(cy-.7,6),round(cx+2,6),round(cy+.7,6)]
ports={}
for n in ['clk','o0','o1','o2','o3']:
 t=b.findBTerm(n);ss=[r for p in t.getBPins() for r in p.getBoxes()];assert len(ss)==1
 r=ss[0];assert r.getTechLayer().getName()==('M7' if n=='o0' else 'M9')
 if n=='o0':assert (r.xMax()-r.xMin(),r.yMax()-r.yMin())==(32,768)
 ports[n]=[getattr(r,k)()/u for k in ('xMin','yMin','xMax','yMax')]
Path('/work/access_regions.json').write_text(json.dumps({'basis':'Explicit4x1.4umclockcellislandscenteredactualpre-routeBUF24bbox; portsEXACTnativeM9boxesandgen_physnativeM7tap32x768nmbox','units':'um','source':'mesh_straps.odb','cells':cells,'ports':ports},indent=2)+'\n')
Path('/work/all_nets.txt').write_text('ck_mesh\nVDD\nVSS\nclk\no0\no1\no2\no3\n')
Path('/work/preconnected.txt').write_text('ck_mesh\nVDD\nVSS\n')
Path('/work/clock_nets.txt').write_text('clk\no0\no1\no2\no3\nck_mesh\n')
print('PRE_ROUTE_ACCESS_REGIONS_PUBLISHED',cells,ports)
