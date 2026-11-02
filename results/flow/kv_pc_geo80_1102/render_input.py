from pathlib import Path
import json,re,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
R=Path(__file__).parent
j=json.load(open(sys.argv[1]));a=np.array(j['real_cells']);assert len(a)>100000
s=(R/'selected_native_nets.def').read_text();m=re.search(r'^\s*- net41987\b.*?;',s,re.S|re.M);assert m
segments=[]
for section in re.split(r'\b(?:NEW|ROUTED)\s+',m.group())[1:]:
    prior=None
    for x,y in re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',section.split('RECT')[0]):
        if prior is None and '*' in (x,y):continue
        xy=(prior[0] if x=='*' else int(x)/j['units'],prior[1] if y=='*' else int(y)/j['units'])
        if prior and xy!=prior:segments.append((prior,xy))
        prior=xy
fig,ax=plt.subplots(figsize=(10,9));ax.hist2d(a[:,0],a[:,1],bins=(180,165),cmap='Blues',cmin=1)
for n,(u,v) in enumerate(segments):ax.plot([u[0],v[0]],[u[1],v[1]],color='red',lw=1.7,label='Actual net41987 native metal' if n==0 else None)
ax.scatter([153.036,183.870],[69.660,220.320],color='red',s=35)
ax.annotate('wire41988 maxBUF16 driver',(153.036,69.660),xytext=(180,40),arrowprops={'arrowstyle':'->'})
ax.annotate('_217823_ input (shared worst setup cone)',(183.870,220.32),xytext=(203,250),arrowprops={'arrowstyle':'->'})
ax.set(xlim=(0,397.44),ylim=(0,362.88),aspect='equal',xlabel='x (um)',ylabel='y (um)',title='Actual current PC native placement input to bounded geometric repair')
ax.legend(loc='upper right',fontsize=8)
fig.text(.06,.025,f"Native final DEF: {len(a):,} real placed cells / {j['rows']} rows; {j['fillers_hidden']:,} fillers hidden.\nNo layout edit, new buffers, free-site or new route claim. Exact input: real native DEF + immutable60b net metal.\nProposed scope: current DRV nets + exact net41987, maxwire80; normal MM setup/hold repair, clock/FF masters fixed.",fontsize=9)
fig.tight_layout(rect=(0,.09,1,1));fig.savefig(R/'actual_current_native_input.png',dpi=150);plt.close(fig)
record={k:v for k,v in j.items() if k!='real_cells'};record['real_cell_count']=len(a);record['status']='ACTUAL_INPUT_RENDER_ONLY_NO_CAD';(R/'INPUT_RENDER.json').write_text(json.dumps(record,indent=2)+'\n');print(record)
