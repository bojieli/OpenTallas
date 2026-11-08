import csv,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
root=Path('/tmp/qc-hc3-flat-state-1113')
r=list(csv.reader((root/'hc0w_north_strip.tsv').open(),delimiter='\t'))
fig,(ax,bx)=plt.subplots(1,2,figsize=(13,5),layout='constrained')
for status,color,label in [('FIRM','#b44d12','FIRM storage/read flops'),('PLACED','#206b98','PLACED logic / buffers')]:
 pts=[(float(x[2]),float(x[3])) for x in r if x[4]==status]
 ax.scatter(*zip(*pts),s=7,alpha=.65,color=color,label=label)
ax.add_patch(Rectangle((514.3,1314.3),30,10,fill=False,color='black',linewidth=1.2,label='Actual high-density bin'))
ax.axhline(1321.92,color='purple',linestyle='--',label='RSF keyed-FF window north edge')
ax.set(xlim=(512,547),ylim=(1312,1327),xlabel='x (µm)',ylabel='y (µm)',title='Actual HC0W north strip: 1,115 cell centers')
ax.legend(loc='lower left',fontsize=8)
bx.axis('off')
text='Actual mapped budget\n\n'
text+='RSF: 12,539 cells, 1,801.24 µm² master area\n'
text+='  2,713 FIRM FFs: 798.62 µm²\n  9,826 PLACED logic / buffers: 1,002.62 µm²\n\n'
text+='FF window: 88.912 × 51.840 µm\n'
text+='  nominal area budget 4,609.20 µm²\n  logic may spill outside; this is not containment/utilization\n\n'
text+='Actual ports: 515 (257 M5, 258 M7)\n'
text+='Tech pitch: M3 0.036 / M5 0.048 / M7 0.064 µm\n'
text+='Gross vertical tracks across width: 2469 / 1852 / 1389\n'
text+='  geometric ceiling only; blockages/vias/local wires reduce it\n  M7 port access does not establish available routing capacity\n\n'
text+='Candidate: existing keyed 3-row FF constructor\n'
text+='  same RTL, pins and window; PIN CYCLES 0\n'
text+='  actual-family width and band-fit cap already implemented\n'
text+='  spreads fixed FFs to leave local logic / escape space\n'
text+='  no detailed-routability claim; no physical pilot launched'
bx.text(0,1,text,va='top',fontsize=10,linespacing=1.45)
fig.suptitle('Reviewed source-form candidate — slw_hc0__cl1bc59e1c attempt 10',fontsize=13)
fig.savefig(root/'images/hc0w_strip_model.png',dpi=160)
(root/'strip_model.md').write_text(text+'\n\nActual geometry image: images/hc0w_density.png; read-only OpenROAD probe E6 unit4141811-1794167022 exit0.\n')
