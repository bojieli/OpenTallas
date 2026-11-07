import json,sys,matplotlib.pyplot as p,numpy as np
from matplotlib.patches import Rectangle
j=json.load(open(sys.argv[1]));f,aa=p.subplots(1,2,figsize=(15,7));r=j['cells'];xs=np.array([(x[1]+x[3])/2 for x in r]);ys=np.array([(x[2]+x[4])/2 for x in r]);areas=np.array([(x[3]-x[1])*(x[4]-x[2]) for x in r]);bounds=[4.32,250.56];counts,_,_=np.histogram2d(xs,ys,bins=55,range=[bounds,bounds],weights=areas);a=aa[0];a.imshow(counts.T/((bounds[1]-bounds[0])/55)**2,origin='lower',extent=[*bounds,*bounds],cmap='magma',vmin=0,vmax=1);a.set_title('cell area / 4.48um bin area; macros and pins')
aa[1].scatter(xs,ys,s=.03,color='gray',alpha=.3)
for name,pts in j.get('clock',[]):
 c=np.mean(pts,axis=0)
 for q in pts:aa[1].plot([c[0],q[0]],[c[1],q[1]],color='blue',alpha=.035,lw=.4)
aa[1].set_title('clock net endpoint spans (connectivity, not routed wires)')
for a in aa:
 for n,x,y,X,Y in j['macros']:
  a.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='white',edgecolor='cyan'));a.text((x+X)/2,(y+Y)/2,n.split('/')[-1],ha='center',fontsize=6)
 a.scatter([x[1] for x in j.get('pins',[])],[x[2] for x in j.get('pins',[])],s=.1,color='lime');a.set_aspect('equal');a.set_xlim(0,255);a.set_ylim(0,255)
f.suptitle(sys.argv[3]);f.tight_layout();f.savefig(sys.argv[2],dpi=140)
