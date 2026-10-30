#!/usr/bin/env python3
"""DIE-KV-33-SD 10-29: results/kv_serdes_pg_event27/gen_model.py with the abstract width B 1866.24 -> 1848.96 (E-side 17.28-um trim).

Why: the event27 x6 abstract leaves only the 17.28-um E rim (= the _storage_band outline margin), so no landing band of the
E-face buses i_host_fdi / i_host_link_rst_n can be legal and within 405 um of its pin (link_rst_n pin y433: S rim is 416 um
away). The trim opens a 12.96-um std-cell column between the macro halo and the band margin (E digital channel 34.56 um).
Area 1.7972 mm2 = 0.9907 x the half-x12 basis (1.8138); modeled abstract, no vendor GDS. Pins keep their y; x = new E edge.
"""

import json,sys,copy,math,hashlib
from pathlib import Path
W=Path(__file__).resolve().parents[2];sys.path.insert(0,str(W/'tools/mem_compiler'))
from views import Pin,Timing,write_liberty,blackbox_verilog
O=Path(__file__).resolve().parent;S=json.load(open(W/'physical/qwen_missing_phy/tp8_1013/ot_qfd_serdes_112g_x12_phy/ot_qfd_serdes_112g_x12_phy.json'))
H=972.;B=1848.96;origin=[17.28,54.];rows=[]
def snap(v):return round(.024+round((v-.024)/.048)*.048,6)
for tn,fw,part,orient in [('kv3_sys_SD',522,'sys_SW','R0'),('kv3_sys_SD_v1',521,'sys_SE','MY')]:
 name=f'ot_qfd_serdes_112g_x6_phy_w{fw}';d=O/name;d.mkdir(exist_ok=True)
 pins=[Pin('clk',1,'input','clock'),Pin('rst_n',1,'input','control'),Pin('tx_up',1,'output','control'),Pin('tx_v',1,'input','control'),Pin('tx_flit',fw,'input','data_in'),Pin('rx_v',1,'output','control'),Pin('rx_flit',fw,'output','data_out')]
 xy={};L=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;',f'MACRO {name}',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {B} BY {H} ;',' SYMMETRY X Y ;']
 for p in pins:
  for i,b in enumerate(p.bits()):
   y=snap(121.944+.144*i if p.name=='tx_flit' else 549.192+.144*i if p.name=='rx_flit' else dict(clk=300.024,rst_n=379.08,tx_up=806.328,tx_v=202.008,rx_v=630.024)[p.name]);xy[b]=[B,y]
   L += [f' PIN {b}',f' DIRECTION {p.direction.upper()} ;',f' USE {"CLOCK" if p.kind=="clock" else "SIGNAL"} ;',' PORT',' LAYER M4 ;',f' RECT {B-.48:.6f} {y-.012:.6f} {B:.6f} {y+.012:.6f} ;',' END',f' END {b}']
 pg={}
 for net,use,off in [('VDD','POWER',2.064),('VSS','GROUND',2.448)]:
  rr=[];y=off
  while y<H-.5:rr.append([.5,round(y-.144,6),B-.5,round(y+.144,6)]);y+=4.32
  pg[net]=rr;L += [f' PIN {net}',' DIRECTION INOUT ;',f' USE {use} ;',' PORT',' LAYER M6 ;']+[f' RECT {a} {b} {c} {d_} ;' for a,b,c,d_ in rr]+[' END',f' END {net}']
 L+=[' OBS']
 for layer in range(1,6):L += [f' LAYER M{layer} ;',f' RECT 0 0 {round(B-.6,6) if layer==4 else B} {H} ;']
 L+=[' END',f'END {name}','END LIBRARY'];(d/f'{name}.lef').write_text('\n'.join(L)+'\n')
 for c in ('tt','ff'):
  t=copy.deepcopy(S['timing'][c]);t['read_energy_fj']*=fw/1043;t['breakdown']['source_x12_scaled_fdi_width']=fw/1043
  lib=write_liberty(name,Timing(**t),pins,B*H,None,'MODELED x6 PHY boundary; native core-clock wrapper/FIFO outside IP, not analog implementation');(d/f'{name}_{c}.lib').write_text(lib)
 (d/f'{name}_bb.v').write_text(blackbox_verilog(name,pins,'MODELED physical specialization of unchanged x6 functional provider; alias binding pending'))
 rec=dict(schema='opentallas.kv-serdes-pg-candidate.v1',status='PLAN/PG candidate only; physical-synth alias and interface gate pending',partition_type=tn,part=part,physical_master=name,logical_module='ot_qfd_serdes_112g_x6_phy',parameter_W=fw,origin_type_um=origin,outline_um=[B,H],area_mm2=B*H*1e-6,area_basis='Half existing x12 assumed licensed-IP area (1.8138 mm2) x 0.9907: event27 1866.24 wide minus a 17.28-um E trim for the digital landing channel (DIE-KV-33-SD); no vendor GDS',x12_area_mm2=S['footprint']['area_mm2'],digital_keepouts=dict(bottom_strip=[0,0,1900.8,54],east_strip=[origin[0]+B,54,1900.8,1036.8],clock_tap_y_um=21.6),power_w=4.37,power_basis='existing infra_pg SER.MACRO6_POWER proxy, not new measurement',pg_interface=dict(layer='M6',partition_access_layer='M7',power_pin='VDD',domain_net='VDDPHY_'+part[4:],contacts=pg,macro_internal_grid='ASSUMED licensed IP, no analog/internal PG claim'),signal_pins=xy,physical_synth_alias='PENDING: specialize native W522/W521 leaves to unique physical_master; source functional RTL unchanged')
 (d/f'{name}.json').write_text(json.dumps(rec,indent=1)+'\n');rows.append(rec)
(O/'phy_footprints.json').write_text(json.dumps(rows,indent=1)+'\n');print('PG_MODEL_CANDIDATES',[(r['part'],r['area_mm2'],len(r['signal_pins'])) for r in rows])
