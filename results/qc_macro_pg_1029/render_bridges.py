import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[1]));pg=json.load(open(sys.argv[2]));D=p['dbu'];q=max(p['paths'],key=lambda r:r['m8_dbu'][2]-r['m8_dbu'][0]);x,y=[v/D for v in q['via78']];xx,yy=[v/D for v in q['via89']];fig,ax=plt.subplots(1,2,figsize=(14,6))
for n,col in [('VDD','#e03c31'),('VSS','#1764b2')]:
 cc=[r for r in p['paths'] if r['net']==n];ax[0].scatter([r['via78'][0]/D for r in cc],[r['via78'][1]/D for r in cc],s=3,c=col,label=n)
ax[0].set(xlim=(0,31216.32),ylim=(0,26265.6),title='1690 short native PG fragments / zero failed bridges',xlabel='um',ylabel='um');ax[0].legend();ax[0].set_aspect('equal')
for n,ly,a,b,A,B in pg:
 if A<min(x,xx)-.7 or a>max(x,xx)+.7 or B<y-.7 or b>y+.7:continue
 ax[1].add_patch(Rectangle((a,b),A-a,B-b,facecolor='#f6a29d' if n=='VDD' else '#a2c4eb',alpha=.55))
for r,col,label in [(q['native_pin_dbu'],'#ef6a5e','native M7'),(q['m8_dbu'],'#7a46ac','new M8')]:
 a,b,A,B=[v/D for v in r];ax[1].add_patch(Rectangle((a,b),A-a,B-b,facecolor=col,alpha=.8,label=label))
ax[1].plot([x,xx],[y,y],'k+',ms=8);ax[1].set(xlim=(min(x,xx)-.7,max(x,xx)+.7),ylim=(y-.7,y+.7),title=q['inst']+'/'+q['pin']+' maximum bridge 4.044 um',xlabel='um',ylabel='um');ax[1].set_aspect('equal');ax[1].legend();fig.suptitle('Native M7 via78 → reserved M8 gap bridge → same-net M9 via89. No signal detour.');fig.tight_layout();fig.savefig(sys.argv[3],dpi=160)
