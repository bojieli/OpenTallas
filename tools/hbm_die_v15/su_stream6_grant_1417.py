#!/usr/bin/env python3
"""Source-exact diagnostic six-SRAM/7-related-root SU stream calendar grant."""
import hashlib,json,subprocess,sys,tempfile,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));import hbm_die_views as V
REF='617d216c1';top='ot_hbm_su_stream_calendar6_pin';path='rtl/hbm_accel/generic/adapters/static_su/programme/'+top+'.sv';core=path.replace(top,'ot_hbm_su_programme');blob=lambda p:subprocess.check_output(['git','show',REF+':'+p],cwd=R)
with tempfile.TemporaryDirectory() as td:
 f=Path(td)/'s.sv';f.write_bytes(blob(path));ports=V.L.parse_module(str(f),top)['ports']
W,H=369.36,151.2;snap=lambda x:round(.012+round((x-.012)/.048)*.048,6)
pins=[]
def add(n,face,centres):
 d,w=ports[n];assert len(centres)==w
 for i,x in enumerate(centres):
  assert abs((x-.012)/.048-round((x-.012)/.048))<1e-5
  pins.append(dict(name=n if w==1 else f'{n}[{i}]',direction=d.upper(),face=face,layer='M4' if face in 'WE' else 'M5',offset=x,offset_pending_view=False))
for face,names in [('W',['cfg_we','cfg_bank','cfg_row','cfg_data','start','length']),('E',['busy','valid','done','fault','edge_index','command'])]:
 count=sum(ports[n][1] for n in names);pitch=int((H-4)/(count-1)/.048)*.048;start=snap((H-(count-1)*pitch)/2);i=0
 for n in names:
  width=ports[n][1];add(n,face,[round(start+(i+j)*pitch,6) for j in range(width)]);i+=width
add('clk','N',[snap(W/2)]);add('rst_n','N',[snap(W/2)+.192])
macros=[]
for i in range(6):
 x=[12.96,136.08,259.2][i%3];y=23.76 if i<3 else 86.4;orient='R0' if i<3 else 'MX';n=f'clk_macro{i}';add(n,'S' if i<3 else 'N',[round(x+.012,6)]);macros.append(dict(index=i,view='ot_sram_1r1w_128x256_m1_r2c2',origin_um=[x,y],outline_um=[94.824,41.04],orient=orient,raw_clock='clk',clock_entry=n,raw_clock_rect_reference_um=[0,.768,.024,.792],raw_clock_center_global_um=[x+.012,y+.78 if i<3 else y+41.04-.78]))
assert len(pins)==sum(x[1] for x in ports.values())==389
sourcehash={p:hashlib.sha256(blob(p)).hexdigest() for p in [path,core]}
out=dict(schema='opentallas.hier_contract.v1',die='hbm_v15',version=5,clock_period_ps=833.333,slots=[dict(name='su_stream6_pin_diagnostic',cell=top,source=path,source_sha256=sourcehash[path],source_prerequisite=REF,source_dependencies_sha256=sourcehash,parent='UNPLACED_SU_stream_programme_group',origin=dict(x=0,y=0,orient='R0'),outline=dict(w=W,h=H),pins=pins,macros=macros,clock_entries=[dict(port=n,face=next(p['face'] for p in pins if p['name']==n),offset=next(p['offset'] for p in pins if p['name']==n),delivery='same-phase1200MHz phi minus independently measured leaf raw/internal insertion R; no clock ownership collapse') for n in ['clk']+[f'clk_macro{i}' for i in range(6)]],raw_macro_area_um2=23349.46176,added_declared_input_FF=298,mapped_std_um2=None,mapped_FF=None)],diagnostic_only=True,production_binding_adopted=False,canonical_die_contract_mutated=False,qualification=False,scope='NEW source-exact diagnostic grant with explicit7related roots and6actual macro homes. No parent home/oldprogramme gate/native qualification inherited. Actual ODB IO rectangles, track and PG-clear readback MUST PASS before CTS; refuse pin relocation or clock-root swap. Exact 3x2 source index mapping must be verified in synthesized hierarchy. Macro coordinates are lower-left boxes with stated orientation.',source_calendar=dict(II=1,config_start_reset_added_edges=1,start_to_present=4,start_to_consumer=5),open=['Parent 900/1200MHz3:4 compiler calendar and real producer joins','Measured mapped area, actual clockR/spread/L220/C190/native ports','TT setup/FFhold/DRC0; SS sensitivity only','Current SU parent packing/clock/PG/feedthrough incident transport'])
p=R/'results/arch/hbm_die_v15/su_stream6_grant_1417.json';p.write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({'pins':len(pins),'clock_entries':7,'macro_area_um2':23349.46176,'qualified':False}))
