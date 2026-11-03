#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent;base=p.parent
v=Path('/srv/opentallas-scratch/claude/codex-hg9-q1-lec-PREP-0805/kit/1_2_yosys.v')
assert hashlib.sha256(v.read_bytes()).hexdigest()=='0192e029133af666b4471c050351de321f789c6199626cc1332761b2dd71f35e'
master='ot_sram_1r1w_128x256_m1_r2c2';names=re.findall(r'\b'+master+r'\s+\\(\S+)\s*\(',v.read_text());assert len(names)==4
lef=(base/'macros'/(master+'.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups());assert (w,h)==(94.824,41.064)
xy=[(17.28,17.28),(131.52,17.28),(17.28,114.432),(131.52,114.432)]
rows=[dict(inst=n,master=master,x=x,y=y,orient='R0',size_um=[w,h]) for n,(x,y) in zip(names,xy)]
pins=json.loads((base/'plan/pins/qkd_ectlk_q1_pins_243.json').read_text())['pins'];assert len(pins)==1968
fig,ax=plt.subplots(figsize=(14,10));ax.add_patch(Rectangle((0,0),243.648,172.8,fill=False,lw=2));ax.add_patch(Rectangle((4.32,4.32),235.008,164.16,fill=False,ls='--',color='gray'))
for i,r in enumerate(rows):
 x,y=r['x'],r['y'];color='#a8caeb' if i<2 else '#abd7b0';ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,ls=':',ec='#666666'));ax.add_patch(Rectangle((x,y),w,h,fc=color,ec='black'));ax.text(x+w/2,y+h/2,('A' if i<2 else 'B')+str(i%2)+'\n'+f'{x:g},{y:g} R0\n94.824 × 41.064 µm',ha='center',va='center',fontsize=10);ax.plot(x,y+.78,'r*',ms=9)
for pin in pins:
 color='crimson' if pin['name']=='ck[0]' else '#555555' if pin['name']=='rst_n[0]' else '#f09c32' if pin['name'].startswith('t0[') else '#4969b0'
 ax.plot(pin['x'],pin['y'],'.',ms=2,color=color)
 if pin['name'] in ['ck[0]','rst_n[0]']:ax.annotate(pin['name'],(pin['x'],pin['y']),xytext=(8,6),textcoords='offset points',color=color)
ax.text(121.8,86.4,'OPEN soft-cell/cross-bus corridor\nActual 9,785 sequential cells remain unplaced\nclock/PDN/routing NOT qualified',ha='center',va='center',fontsize=10)
ax.set(xlim=(-5,249),ylim=(-5,178),aspect='equal',xlabel='µm',ylabel='µm',title='Current q1 native SYNTH: deliberate four-SRAM source floorplan PREP\nExact 1968 plan pins; all cells unplaced; no FP/CTS/GRT/route')
fig.tight_layout();fig.savefig(p/'q1_four_sram_PREP.png',dpi=160);plt.close(fig)
# Isolated proposal; never installed in the current generated kit.
lines=['# PREP ONLY: NOT installed/admitted. Actual mapped four SRAM names and native LEF.','foreach {inst master x y orient} {']
for r in rows:lines.append('  {'+r['inst']+'} '+master+f" {r['x']} {r['y']} R0")
lines+=['} {','  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact','}']
(p/'macro_placement_PROPOSAL.tcl').write_text('\n'.join(lines)+'\n')
json.dump({'status':'PREP_ONLY_NO_FP_OR_ADOPTION','actual_mapped_macro_count':4,'placements':rows,'halo_um':4.32,'horizontal_macro_gap_um':xy[1][0]-(xy[0][0]+w),'vertical_macro_gap_um':xy[2][1]-(xy[0][1]+h),'clock_center_pin':next(x for x in pins if x['name']=='ck[0]'),'source_netlist_sha256':hashlib.sha256(v.read_bytes()).hexdigest(),'macro_lef_sha256':hashlib.sha256(lef.encode()).hexdigest(),'source_only_holds':['actual source-to-SYNTH official LEC pending','macro-clock capsule/balanced insertion and related pairs','PDN metal/via/PG obstruction continuity','actual std-cell/face FF/relay placement and exact perbus reach','normal FP not authorized']},open(p/'model.json','w'),indent=2)
