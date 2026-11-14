import csv,json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
h=list(csv.DictReader(open(sys.argv[1])));mac=list(csv.DictReader(open(sys.argv[2])));out=sys.argv[3]
fig,ax=plt.subplots(figsize=(11,11));old=[];new=[];movement=[]
for r in mac:
 x,y,w,z=[float(r[k]) for k in ['x','y','w','h']];ax.add_patch(Rectangle((x,y),w,z,facecolor='#d0d0d0',edgecolor='black',lw=.6))
for r in h:
 sx,sy,lx,ly,cx,cy,px,py=[float(r[k]) for k in ['source_x','source_y','latch_x','latch_y','capture_x','capture_y','planned_x','planned_y']]
 old.append(abs(lx-cx)+abs(ly-cy));new.append(abs(sx-px)+abs(sy-py));movement.append(abs(cx-px)+abs(cy-py))
 ax.plot([lx,cx],[ly,cy],color='#bbbbbb',alpha=.12,lw=.35)
 ax.plot(sx,sy,'.',color='#0050a0',ms=2)
 ax.plot(px,py,'.',color='#b00000',ms=2)
 if int(r['bit'])==440:
  ax.plot([lx,cx],[ly,cy],color='#f09000',lw=2,label='Existing worst bit 440 latch/capture')
  ax.plot([sx,px],[sy,py],color='red',lw=2,label='Planned bit 440 launch/capture')
  ax.annotate('bit 440 capture moves beside launch FF',(px,py),xytext=(40,540),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.plot([],[],'b.',label='Launch FF stays');ax.plot([],[],'r.',label='Planned capture + latch / hop buffers')
ax.set(xlim=(0,648),ylim=(0,648),aspect='equal',xlabel='µm',ylabel='µm',title='BKSEL i0: exact 593 launch/latch/capture hops; move captures to launch side')
ax.legend(fontsize=8,loc='lower left');fig.tight_layout();fig.savefig(out,dpi=150)
r={'hops':len(h),'unique_captures':len(set(r['capture'] for r in h)),'old_max_latch_capture_manhattan_um':max(old),'planned_max_launch_capture_manhattan_um':max(new),'max_capture_move_manhattan_um':max(movement),'moved_buffers':sum(int(r['buffers']) for r in h),'bit440':next(r for r in h if int(r['bit'])==440)}
print(json.dumps(r,indent=2));open(out+'.json','w').write(json.dumps(r,indent=2)+'\n')
