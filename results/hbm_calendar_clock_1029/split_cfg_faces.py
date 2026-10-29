"""Source-bit-identity proposal aligned to actual SRAM wd_in pin faces."""
import json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2];pinsfile,leffile,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=False)
s=leffile.read_text();native={}
for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1',s,re.S):
 if not name.startswith('wd_in['):continue
 a=list(map(float,re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body).groups()));x=(a[0]+a[2])/2;y=(a[1]+a[3])/2
 face='W'if x<.1 else'E'if x>174.6 else'S'if y<.1 else'N';native[int(name[6:-1])]=dict(face=face,xy_um=[x+21.6,y+17.34])
assert len(native)==256 and [i for i in range(256)if native[i]['face']=='W']==list(range(136)) and [i for i in range(256)if native[i]['face']=='E']==list(range(136,256))
pins=json.loads(pinsfile.read_text());assert len(pins)==555
for p in pins:
 if not p['name'].startswith('cfg_data['):continue
 i=int(p['name'][9:-1]);face=native[i]['face'];p.update(layer='M4',x=.096 if face=='W'else 215.904,y=round(32.856+i*.288 if face=='W'else 6.648+(i-136)*.288,6))
guides=[]
for face,bs,rect in [('W',range(136),[4.32,30.24,17.28,74.52]),('E',range(136,256),[200.664,4.32,211.68,47.52])]:
 prefixes=[f'u_fcore.u_target.{stage}[{i}]'for stage in ['data_q','program_cfg_data']for i in bs]
 guides.append(dict(name='calendar_cfg_'+face,prefixes=prefixes,rect_um=rect,expected_cells=len(prefixes),actual_cell_area_um2=len(prefixes)*1.08*.27,release='before DPL'))
for n,d in [('pins.json',pins),('guides.json',guides),('native_wd_pins.json',native)]: (out/n).write_text(json.dumps(d,indent=1)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(11,6));ax.add_patch(Rectangle((0,0),216,112.32,fill=False));ax.add_patch(Rectangle((21.6,17.34),174.744,70.488,color='gray',alpha=.35));ax.add_patch(Rectangle((17.28,13.02),183.384,79.128,fill=False,linestyle='--'))
for g,c in zip(guides,['cyan','orange']):
 a,b,d,e=g['rect_um'];ax.add_patch(Rectangle((a,b),d-a,e-b,color=c,alpha=.3));ax.text((a+d)/2,(b+e)/2,f"{g['expected_cells']} existing FF",rotation=90,ha='center',va='center',fontsize=7)
for face,color in [('W','green'),('E','purple')]:
 ps=[p for p in pins if p['name'].startswith('cfg_data[') and native[int(p['name'][9:-1])]['face']==face];ax.scatter([p['x']for p in ps],[p['y']for p in ps],s=5,c=color,label=f'cfg_data {len(ps)} {face}')
 ns=[p['xy_um']for p in native.values()if p['face']==face];ax.scatter([p[0]for p in ns],[p[1]for p in ns],s=4,c=color)
rest=[p for p in pins if not p['name'].startswith('cfg_data[')];ax.scatter([p['x']for p in rest],[p['y']for p in rest],s=2,c='gray')
for a,b,d,e in [[116.64,95.04,125.28,103.68],[108.,95.04,116.64,103.68]]:ax.add_patch(Rectangle((a,b),d-a,e-b,fill=False,color='red'))
ax.set_aspect('equal');ax.set_xlim(-5,221);ax.set_ylim(-5,117.32);ax.legend();ax.set_title('VM CAL actual SRAM write-data faces:136W +120E\nSame555pinABI/RTL/cycles; split512existingFF guides releasedbeforeDPL');fig.tight_layout();fig.savefig(out/'proposal.png',dpi=150)
(out/'status.json').write_text(json.dumps(dict(status='SOURCE_EXACT_PIN_FACE_PROPOSAL_NOT_PLACED',pins=555,changed_face_bits=120,relocated_cfg_pins=256,cfg_identity_preserved=True,existing_ff=512,cycles_added=0,source_reason='actual SRAM LEF wd_in[0:135] W, [136:255] E; wholeWguide caused1.099verticalcut',remaining=['independent image review','new privatekitGEN/PLACE','actualG1','parent FT/tap/CA/PG recomposition']),indent=1)+'\n')
