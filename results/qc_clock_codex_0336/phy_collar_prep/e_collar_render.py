import json,gzip
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open('/tmp/qcclock0336/e_collar_placement_prep.json'));fig,axes=plt.subplots(1,3,figsize=(13,8));q=json.load(gzip.open('/tmp/qcclock0336/e_collar_connected_clock_prep.json.gz','rt'));p['cells']=q['cells'];colors={'CONNECTED_CLOCK_BUF24':'cyan','DFF_INV':'royalblue','DATA_BUF24':'#ba29ab','ASR_INV_TIEHI':'red','CONTROL_DFF_LOGIC':'orange','BUF8':'green','BUF24':'green'}
for ax in axes:
 ax.add_patch(Rectangle((.270,0),1563.57,2320.056,fc='#ddd',ec='black'));ax.add_patch(Rectangle((0,0),1632.96,2393.28,fill=False,ec='black'));ax.add_patch(Rectangle((2.16,2322.216),1628.64,68.904,fc='lightgreen',alpha=.4));ax.add_patch(Rectangle((1566,2.16),64.8,2388.96,fc='lightgreen',alpha=.4))
 for kind,col in colors.items():
  rr=[c for c in p['cells'] if c['kind']==kind];ax.scatter([c['origin_um'][0] for c in rr],[c['origin_um'][1] for c in rr],s=.4 if kind=='DATA_BUF24' else 1.8,c=col,label=kind,rasterized=True)
 for n in q['clock_nets']:
  if n['corner']!='TT' or '.clkL0.' in n['driver']:continue
  for e in n['tree_edges'].values():
   ax.plot([z[0] for z in e['path']],[z[1] for z in e['path']],color='cyan',lw=.35,alpha=.7)
 ax.set_aspect('equal');ax.set_xlabel('local x(um)');ax.set_ylabel('local y(um)')
axes[0].set_xlim(0,1680);axes[0].set_ylim(0,2440);axes[0].set_title('Actual body excluded; PREP only');axes[0].legend(loc='center',fontsize=7)
axes[1].set_xlim(700,1650);axes[1].set_ylim(2290,2410);axes[1].set_title('N collar: 68.904um clear after halos')
axes[2].set_xlim(1540,1645);axes[2].set_ylim(1650,2250);axes[2].set_title('E collar: 64.8um clear\nblue FF+INV; purple dataBUF24')
s=p['summary'];fig.suptitle(f"E9bank geometry PREP: {s['data_FF']} dataFF + {s['data_repeater_cells']} BUF24\nmax FFhop {s['max_actual_pin_hop_um']:.3f}um; max buffered section {s['max_buffered_wire_section_um']:.3f}um; 468 connected localclock BUF24; global clock/PG/RTL HOLD")
fig.tight_layout();fig.savefig('/tmp/qcclock0336/e_collar_placement_prep.png',dpi=170)
