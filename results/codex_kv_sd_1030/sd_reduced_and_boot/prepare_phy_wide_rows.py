"""SD-local row proposal; no physical install, clock model, or legality qualification."""
import json,re
from pathlib import Path
r=Path(__file__).resolve().parent
positions={};totals={};collisions=[];rows={}
for line in (r/'geom_sdpg_after/geom.tsv').read_text().splitlines():
 f=line.split('\t')
 if len(f)<9 or f[0]!='C' or f[2]!='S':continue
 name=f[8];slot=bit=None;kind=None
 m=re.search(r'u_tx\.mem\\?\[(\d+)\\?\]\\?\[(\d+)',name)
 if m:slot=int(m[1])+1;bit=int(m[2]);kind='TX'
 elif '.p_tx_d' in name:
  m=re.search(r'p_tx_d\\?\[(\d+)',name)
  if m:bit=int(m[1]);slot=0;kind='TX'
 else:
  m=re.search(r'u_rx\.mem\\?\[(\d+)\\?\]\\?\[(\d+)',name)
  if m:slot=int(m[1])+1;bit=int(m[2]);kind='RX'
  else:
   m=re.search(r'rq_d\\?\[(\d+)',name)
   if m:bit=int(m[1]);slot=0;kind='RX'
 if kind is None:continue
 assert 0<=bit<522 and 0<=slot<9,(name,slot,bit)
 x=1874.88+(bit%2)*10.8+slot*1.188
 if kind=='TX':
  g=(bit if bit<240 else bit-240)//2
  y=(76.14 if bit<240 else 329.4)+.54*g
 else:
  g=bit//2;y=594+.27*(g+g//3)
  if y>=637.74-1e-6:y+=5.4 # keep actual clk_t6/reset/control box clear
 width=float(f[6])-float(f[4]);height=float(f[7])-float(f[5])
 assert width<=1.134+1e-6 and abs(height-.27)<1e-6,(name,width,height)
 assert 1870.56<=x and x+width<=1896.48+1e-6
 assert abs((x-4.32)/.054-round((x-4.32)/.054))<1e-6
 assert abs((y-4.32)/.27-round((y-4.32)/.27))<1e-6
 assert not (x<1896.48 and x+width>1877.04 and y<329.184 and y+height>149.904)
 for a,b,other in rows.setdefault(round(y,6),[]):
  if x<b-1e-7 and x+width>a+1e-7:collisions.append([name,other])
 rows[round(y,6)].append((x,x+width,name))
 positions[name]={'xy_um':[round(x,6),round(y,6)],'master':f[3],'body_um':[round(width,6),height],'group':kind,'bit':bit,'slot':slot}
 totals[kind]=totals.get(kind,0)+1
assert totals=={'TX':4698,'RX':4698},totals
assert not collisions,collisions[:5]
report={'physical_qualified':False,'data_ff_only':True,'positions':positions,'counts':totals,'pairwise_data_ff_overlaps':len(collisions),'row_lattice':'actual geom.tsv site .054/row .27 origin4.32; width<=1.134','kept_clear':['PGdomainright1870.56','FDIFFbankx1877.04..1896.48y149.904..329.184','primaryE640 ±2.16/control row gap5.4'],'pending':['all other mapped logic/control/legalPG rows','actualFF bankpacking/clocknodes','TT/FF selectedroot electrical model','primarycapacityactualproposedfullinventory','all r2r/macro/pin reach actual G1','PGcontinuity/IR']}
(r/'phy_wide_data_ff_rows.json').write_text(json.dumps(report,indent=1))
print(json.dumps({k:v for k,v in report.items() if k!='positions'},indent=1))
