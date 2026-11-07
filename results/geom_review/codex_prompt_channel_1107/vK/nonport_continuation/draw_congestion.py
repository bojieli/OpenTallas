import json,sys,numpy as np,matplotlib.pyplot as p
j=json.load(open(sys.argv[1]));g=j['congestion'];f,aa=p.subplots(2,3,figsize=(15,10));xs=g['xs'];ys=g['ys']
for a,m in zip(aa.flat,g['maps']):
 v=np.array(m['cells']);us=v[:,:,0];cap=v[:,:,1];ratio=np.divide(us,cap,out=np.full(us.shape,np.nan),where=cap>0)
 q=a.imshow(ratio,origin='lower',extent=[xs[0],xs[-1],ys[0],ys[-1]],vmin=0,vmax=1.2,cmap='inferno');a.set_title(m['layer']+' usage/capacity; overflow '+str(int(np.maximum(us-cap,0).sum())));a.set_aspect('equal');f.colorbar(q,ax=a)
f.suptitle(sys.argv[3]);f.tight_layout();f.savefig(sys.argv[2],dpi=125)
