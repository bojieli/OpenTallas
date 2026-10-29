"""Propose START stage siting on a legal existing clock-net leg.
The clock drivers/proof arrivals are never changed. Geometry-only overrides are
for a provisional START plan; ALL added clock stubs need as-built extraction.
"""
import copy,math

def propose(failed,ctx,site):
 nominal=next(iter(ctx.values()));meta=nominal['meta'];taps=nominal['taps'];xy=meta['node_xy_um'];out={}
 for e in failed:
  parent=e['fork_node']; cap=taps[e['capture']];end=cap['tree_path'];a=xy[parent];b=cap['xy_um']
  path=next((end[:n] for n in range(len(parent)+1,len(end)+1) if end[:n] in xy),None)
  if path is None:raise ValueError('no actual clock child for '+e['port'])
  c=xy[path];dx,dy=c[0]-a[0],c[1]-a[1]
  if abs(dx)>1e-5 and abs(dy)>1e-5:raise ValueError('non-Manhattan actual leg '+path)
  reach=sum(abs(x-y) for x,y in zip(a,b));move=reach-390
  length=abs(dx)+abs(dy)
  if not 0<move<length:raise ValueError('no reserved midleg site for '+e['port'])
  q=[a[0]+dx/length*move,a[1]+dy/length*move]
  q=[round(round(q[0]/.054)*.054,6),round(round(q[1]/.27)*.27,6)]
  # Conservative row envelope for up to eight adjacent FF bodies, including
  # the normal emitter's two-site offset. All real mapped logic follows later.
  rect=[q[0]+2.16,q[1],q[0]+2.16+8*1.08,q[1]+.27]
  if not all(site.legal(v) for v in [(rect[0],rect[1]),(rect[2],rect[3])]):
   raise ValueError('midleg row conflicts with actual core/PHY '+e['port'])
  if path in out and out[path]['stage_anchor_um']!=q:raise ValueError('incompatible reused node '+path)
  out[path]=dict(path=path,node_cell=meta['node_cell'][path],driver_xy_um=c,stage_anchor_um=q,
    actual_clock_leg_um=[a,c],provisional_clock_stub_um=sum(abs(x-y) for x,y in zip(q,c)),
    scope='START stage only; clock cells stay fixed; measured loaded stage clock required')
 return out

def contexts_with_geometry(ctx,overrides):
 out={}
 for corner,c in ctx.items():
  out[corner]=dict(c,meta=dict(c['meta'],node_xy_um=dict(c['meta']['node_xy_um'])))
  for path,v in overrides.items():out[corner]['meta']['node_xy_um'][path]=v['stage_anchor_um']
 return out
