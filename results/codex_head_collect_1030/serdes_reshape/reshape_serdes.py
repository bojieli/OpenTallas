import json,re,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path('/tmp/head_collect_review/serdes_reshape');R.mkdir(exist_ok=True)
old=json.load(open('/tmp/head_collect_review/serdes_pins.json'));oldcanon=json.load(open('/tmp/head_collect_review/serdes_plan_pins.json'))
W,H=276.48,138.24;dx,dy=(W-216)/2,(H-194.4)/2
new=[]
for p in old:
 q=dict(p);f=q['face']
 if f in ['N','S']:q['x']=round(q['x']+dx,6);q['y']=H if f=='N' else 0
 elif f in ['W','E']:q['x']=0 if f=='W' else W;q['y']=round(q['y']+dy,6)
 else:q['x']=round(q['x']+dx,6);q['y']=round(q['y']+dy,6)
 new.append(q)
def name(p):return p['bus']+(('['+str(p['bit'])+']') if p.get('bit') is not None else '')
by={name(p):p for p in new};canonical=[]
for p in oldcanon['pins']:
 q=dict(p);f=by[p['name']]['face']
 if f in ['N','S']:q['x']=round(p['x']+dx,6);q['y']=round(p['y']+(H-194.4 if f=='N' else 0),6)
 elif f in ['W','E']:q['x']=round(p['x']+(W-216 if f=='E' else 0),6);q['y']=round(p['y']+dy,6)
 else:q['x']=round(p['x']+dx,6);q['y']=round(p['y']+dy,6)
 canonical.append(q)
assert len(new)==945 and len(canonical)==945 and set(by)=={p['name'] for p in canonical}
for p in canonical:assert 0<=p['x']<=W and 0<=p['y']<=H
io=Path('/tmp/head_collect_review/serdes_io.tcl').read_text()
coord={p['name']:p for p in canonical}
def sub(m):
 p=coord[m[1]];return m[0].replace(m[2],f"{p['x']:.4f} {p['y']:.4f}")
io=re.sub(r'place_pin -pin_name \{([^}]+)\} -layer \w+ -location \{([^}]+)\}',sub,io)
(R/'pins.json').write_text(json.dumps(new,indent=1)+'\n');(R/'io.tcl').write_text(io)
doc=dict(oldcanon,rule='RESHAPE PROPOSAL: unchanged945pin names/layers/sizes/faceorder; recentered groups on276.48x138.24; clock/reset unchanged relative center and .108gap',outline_um=[W,H],pins=canonical)
(R/'plan_pins.json').write_text(json.dumps(doc,indent=1)+'\n')
child=dict(inst='u_phy.u_link.u_dec.u_chn',module='ot_s81_kp4_dchn',origin_um=[967.68,8.64],track_offset_um=[0,-2.112],outline_um=[W,H],orient='R0',pins_file='core_pins/kp4_276x138_pins.json',cells=189510,obs_max='M5',note='PROPOSED NOT SIGNED: actual189510stdcells21631.646um2;945sameRTLports0cycles; recenteredpinprofile within150um digitalstrip. Parent origin967.68,8.64 + trackoffset0,-2.112; noLEF/lib until matching actualview.')
(R/'parent_core_proposal.json').write_text(json.dumps(child,indent=1)+'\n')
a=21631.64615995453;core=(W-8.64)*(H-8.64);clk=by['clk'];rst=by['rst_n'];gap=clk['x']-clk['size'][0]/2-rst['x']-rst['size'][0]/2
est=dict(scope='estimate BEFORE physical build; no adoption',std_cells=189510,std_area_um2=a,outline_um=[W,H],aspect=W/H,gross_util=a/(W*H),usable_util=a/core,reason_usable_above_0p60='150um PHY digital strip fixes height;aspect2limitswidth;usable.623 remains below.75hardGEOMceiling;no threshold waiver',child_clock_root=[clk['x'],clk['y']],max_root_manhattan_um=max(abs(x-clk['x'])+abs(y-clk['y']) for x in [0,W] for y in [0,H]),clk_reset_edge_gap_um=gap,macro_halo_um=4.32,parent_actual_origin_um=[967.68,6.528],parent_core_root_geometric_reference_only_um=abs(1442.88-(967.68+clk['x']))+abs(77.76-(6.528+clk['y'])),srams_preserved=[dict(name='cmem',origin_um=[1252.8,17.28],outline_um=[177.768,81]),dict(name='dmem',origin_um=[1486.08,34.56],outline_um=[178.632,81])],nearest_SRAM_edge_gap_um=1252.8-(967.68+W),halo_top_um=6.528+H+4.32,phy_start_y_um=150,child_clock_domain='PMA recovered pma_rck; actual parent pad site and input clock contract pending; parent core clk is not the source',pins=945,pin_names_layers_sizes_faceorder_unchanged=True,added_cycles=0,added_RTL=0)
(R/'estimate.json').write_text(json.dumps(est,indent=1)+'\n')
fig,(ax,pa)=plt.subplots(2,1,figsize=(15,7),gridspec_kw={'height_ratios':[2,1]})
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2));cols={'N':'teal','S':'purple','W':'orange','E':'brown','interior':'red'}
for f in cols:
 pp=[p for p in new if p['face']==f];ax.scatter([p['x'] for p in pp],[p['y'] for p in pp],s=4,c=cols[f],label=f'{f}: {len(pp)}')
ax.scatter([clk['x']],[clk['y']],marker='*',s=140,c='red');ax.set_aspect('equal');ax.set_xlim(-8,W+8);ax.set_ylim(-10,H+10);ax.legend(loc='upper right');ax.set_title('SerDes child reshape proposal —945same ports/RTL, recentered face groups,0cycles; root reach207.48um')
pa.add_patch(Rectangle((900,150),850,40,color='gray',alpha=.4,label='PHY starts y150'))
pa.add_patch(Rectangle((967.68,6.528),W,H,facecolor='teal',alpha=.25,label='proposed child'))
pa.add_patch(Rectangle((967.68-4.32,2.208),W+8.64,H+8.64,fill=False,ls='--',edgecolor='teal'))
for s in est['srams_preserved']:pa.add_patch(Rectangle(s['origin_um'],*s['outline_um'],facecolor='orange',alpha=.4));pa.text(s['origin_um'][0],s['origin_um'][1]+20,s['name'])
pa.scatter([1442.88],[77.76],marker='*',c='red',s=100,label='core clock root');pa.scatter([967.68+clk['x']],[6.528+clk['y']],marker='*',c='blue',s=100,label='child PHY RX clock input')
pa.set_xlim(900,1750);pa.set_ylim(-5,190);pa.set_aspect('equal');pa.legend(loc='upper right');pa.set_title('Parent digital strip —child+halo146.88<150,SRAMgap8.64; recovered-RX clock pad placement pending')
fig.tight_layout();fig.savefig(R/'preview.png',dpi=160)
print(json.dumps(est))
