"""Opt-in fixed-count FT siting, with atomic per-bit occupied-row fallback."""
import numpy as np
import ft_sites_unblock as F

def slot(s,k,pins,gate,grow,free,budget,smax,al,tn,name,k0):
 pi,po=pins[name+'_i'],pins[name+'_o'];bits=sorted(set(pi)|set(po));pts={};bad=0;cell=(al.cw,al.ch)
 for b in bits:
  A=pi.get(b)or po[b];B=po.get(b)or pi[b]
  ia={'E':(A[0]-1,A[1]),'W':(A[0]+1,A[1]),'N':(A[0],A[1]-1),'S':(A[0],A[1]+1)}[A[2]]
  ib={'E':(B[0]-1,B[1]),'W':(B[0]+1,B[1]),'N':(B[0],B[1]-1),'S':(B[0],B[1]+1)}[B[2]]
  route=F.C.zroute(ia,ib,A[2],B[2]);length=F.C.plen(route);ps=[F.C.point_at(route,length*j/k)for j in range(1,k)]
  pts[b]=(ia,ib,route,length,ps);bad+=sum(F.inside(p,gate)for p in ps)
 seed_failure=None
 try:moved=F._move(pts,bits,k,grow,free,budget,tn,name)
 except SystemExit as e:
  # Seed budget is conservative; only occupied actual-row reach proves failure.
  moved=None;seed_failure=str(e)
 slot_saved=set(al.used);sites=[[None]*len(bits)for _ in range(k-1)];fallbacks=[];worst=0.
 for b in bits:
  ia,ib,route,length,ps=pts[b];ib=getattr(al,'terminal_goals',{}).get((name,b),ib);bit_saved=set(al.used);allocated=[]
  try:
   previous=ia
   for j,p in enumerate(ps):
    following=ps[j+1]if j+1<len(ps)else ib
    centre,_=al.allocate_reachable(p,previous,following,reach=smax,max_radius_um=80.)
    allocated.append(centre);previous=centre
  except ValueError as local:
   al.used=bit_saved
   try:
    allocated,stats=al.allocate_chain(ia,ib,ps,reach=smax-.5)
    fallbacks.append(dict(bit=b,max_hop_um=stats['max_hop_um'],local_failure=str(local)))
   except ValueError as e:
    al.used=slot_saved
    return dict(type=tn,slot=name,stations=k,infeasible=str(e),bit=b,phase='occupied_row_joint_path',joint_fallbacks=fallbacks,slot_reservations_rolled_back=True)
  for j,(x,y)in enumerate(allocated):sites[j][b]=[round(x-cell[0]/2,6),round(y-cell[1]/2,6)]
  chain=[ia]+[(sites[j][b][0]+cell[0]/2,sites[j][b][1]+cell[1]/2)for j in range(k-1)]+[ib]
  worst=max(worst,max(F.man(a,z)for a,z in zip(chain,chain[1:])))
 if worst>smax+1e-6:
  al.used=slot_saved
  return dict(type=tn,slot=name,stations=k,infeasible=f'actual row hop{worst}>{smax}',slot_reservations_rolled_back=True)
 s['stations']=k;s['bit_site_cell_um']=list(cell);s['bit_sites_um']=sites
 return dict(type=tn,slot=name,width=s['width'],stations=k,stations_added=k-k0,in_macro_points=bad,moved=moved,max_bit_hop_um=worst,joint_fallbacks=fallbacks,geometry_seed_failure=seed_failure)
