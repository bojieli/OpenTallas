"""A0 MODEL ONLY: natural local post-ICG trees, then one common trunk per domain.
No fixed whole-tree stage count, measured arrival, per-pair skew or RTL change.
Domain trunk sizing is separate joint TT/FF NLDM planning, before physical build.
"""
import argparse,collections,copy,gzip,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gen_a0_clock_corridor as G

class ExactCorridor(G.CorridorPlanner):
    def corridor(self,a,b,step=3.0):
        # Coordinate-compressed visibility grid preserves narrow planned clock
        # columns that a fixed3um raster can miss. Only physical plan geometry.
        import heapq,bisect
        key=(tuple(round(x,5)for x in a),tuple(round(x,5)for x in b))
        if not hasattr(self,'wire_path_cache'):self.wire_path_cache={}
        if key in self.wire_path_cache:return self.wire_path_cache[key]
        xs={G.BOX[0],G.BOX[2],a[0],b[0]};ys={G.BOX[1],G.BOX[3],a[1],b[1]}
        for x0,y0,x1,y1 in self.boxes:
            xs.update((x0,x1));ys.update((y0,y1))
        for x0,y0,x1,y1 in G.CLOCK_COLUMNS:
            xs.update((x0,(x0+x1)/2,x1));ys.update((y0,y1))
        xs=sorted(x for x in xs if G.BOX[0]<=x<=G.BOX[2]);ys=sorted(y for y in ys if G.BOX[1]<=y<=G.BOX[3])
        start=(xs.index(a[0]),ys.index(a[1]));goal=(xs.index(b[0]),ys.index(b[1]));distance={start:0.};previous={};pq=[(G.man(a,b),0.,start)]
        while pq:
            _,d,u=heapq.heappop(pq)
            if u==goal:break
            if d>distance[u]+1e-10:continue
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                v=(u[0]+dx,u[1]+dy)
                if not(0<=v[0]<len(xs)and 0<=v[1]<len(ys)):continue
                vx,vy=xs[v[0]],ys[v[1]];ux,uy=xs[u[0]],ys[u[1]]
                if v!=goal and self.blocked(vx,vy):continue
                if self.blocked((ux+vx)/2,(uy+vy)/2):continue
                nd=d+abs(vx-ux)+abs(vy-uy)
                if nd<distance.get(v,1e99)-1e-9:
                    distance[v]=nd;previous[v]=u;heapq.heappush(pq,(nd+abs(vx-b[0])+abs(vy-b[1]),nd,v))
        if goal not in distance:raise ValueError('No declared macro-clear/island clock corridor')
        path=[];u=goal
        while u!=start:path.append([xs[u[0]],ys[u[1]]]);u=previous[u]
        path=[list(a)]+path[::-1];out=[path[0]]
        for j in range(1,len(path)-1):
            if (path[j][0]-out[-1][0])*(path[j+1][1]-path[j][1])!=(path[j][1]-out[-1][1])*(path[j+1][0]-path[j][0]):out.append(path[j])
        out.append(path[-1]);self.wire_path_cache[key]=out;return out

def main():
 a=argparse.ArgumentParser();a.add_argument('--kit',required=True);a.add_argument('--census',required=True);a.add_argument('--clock-islands',required=True);a.add_argument('--connectivity');a.add_argument('--out',required=True);a.add_argument('--report',required=True);o=a.parse_args()
 kd=Path(o.kit);sl=json.load(open(kd/'master_slice.json'));fr=json.load(open(o.clock_islands));outline=fr['outline_um'];hard={h['inst']:h for h in fr['hard_children']}
 declared=fr['candidate_clock_corridors'];G.CLOCK_ISLANDS[:]=[r for c in declared for r in c['clock_islands_um']];G.CLOCK_COLUMNS[:]=[c['clock_reserved_rect_um'] for c in declared]
 if o.connectivity:
  import csv
  for r in csv.DictReader(open(o.connectivity),delimiter='\t'):
   norm=lambda x:x.replace(chr(92),'').rsplit('/',1)[0]
   G.AFFINITY.add((norm(r['startpoint']),norm(r['endpoint'])))
 raw=[];gates={};port=None
 for line in gzip.open(o.census,'rt'):
  if line.startswith('port '):
   q=line.split();port=list(map(float,q[2:4]));continue
  f=line.rstrip().split('\t')
  if not f or f[0]!='S':continue
  path,depth,inst,pin,master,x,y=f[1],int(f[2]),f[3],f[4],f[5],float(f[6]),float(f[7])
  row=dict(path=path,inst=inst,pin=pin,master=master,xy=[x,y])
  if master.startswith('ICG') and pin=='CLK':gates[inst]=dict(inst=inst,master=master,xy_um=[x,y],domain='planned')
  elif (master.startswith(('DFF','SDFF','ot_qwen_tile_'))) and pin in ('CLK','clk','CK'):raw.append(row)
 if port is None:raise ValueError('missing actual clock entry')
 boxes=[];geo={}
 for h in hard.values():
  if h['master'] not in geo:geo[h['master']]=G.lef_geom(kd/'macros'/f"{h['master']}.lef")
  w,hh,_=geo[h['master']];x,y=h['at'];boxes.append((x-G.HALO[0],y-G.HALO[1],x+w+G.HALO[0],y+hh+G.HALO[1]))
 P=ExactCorridor(boxes,100.);domains=collections.defaultdict(list);root=[]
 for r in raw:
  # The last real functional gate in the path determines ownership; accidental
  # pre-CTS clock buffers do not create a new clock domain or lose sinks.
  owners=[n for n in gates if n in r['path']]
  if owners:domains[max(owners,key=lambda n:r['path'].rfind(n))].append(r)
  else:root.append(r)
 if set(domains)!=set(gates):raise ValueError('functional gate sink census mismatch')
 leaves=[];entries=[];groups=[]
 def local_register_tree(label,points,parent,origin):
  clusters=G.adaptive_groups(G.connectivity_groups(points,4),P)
  fan=math.ceil(math.log(max(1,len(clusters)),4));far=max(G.man(origin,G.centroid(c)) for c in clusters)
  depth=max(2,fan+1,math.ceil(far/100.)+1)
  start=P.node('natural_domain',P.legal(origin),parent,'BUFx24_ASAP7_75t_R');items=[];leaf_names=[]
  for i,c in enumerate(clusters):
   n=dict(name=f'mp_natural_leaf_{len(leaves)}',master='BUFx8_ASAP7_75t_R',xy_um=P.legal(G.centroid(c)),parent=None)
   P.nodes.append(n);leaf=dict(node=n['name'],sinks=[q[2] for q in c],load_class='register');leaves.append(leaf);leaf_names.append(n['name'])
   items.append(dict(xy=n['xy_um'],goal=depth-1,attach=lambda par,n=n:n.update(parent=par)))
  P.feed(start['name'],start['xy_um'],0,items,'natural_local')
  groups.append(dict(name=label,kind='register',anchor=parent,trunk_child=start['name'],leaf_nodes=leaf_names,sinks=sum(len(c)for c in clusters),natural_local_depth=depth))
  return start
 for gate_name,rs in sorted(domains.items()):
  gate=gates[gate_name];origin=gate['xy_um'];macros=[r for r in rs if r['master'].startswith('ot_qwen_tile_')]
  if macros:
   if len(rs)!=1:raise ValueError('mixed macro/register functional domain '+gate_name)
   r=rs[0];hn=r['inst'].replace(chr(92),'');h=hard[hn];w,hh,clock=geo[h['master']]
   target=G.place_pin(h['at'],h['orient'],w,hh,clock);end=P.legal(target);path=P.corridor(P.legal(origin),end)
   if G.man(origin,path[0])>1e-6:path=[origin]+path
   length=sum(G.man(x,y)for x,y in zip(path,path[1:]));count=max(1,math.ceil(length/80.));parent=gate_name;first=None
   for k in range(count):
    pos=P.along(path,length*(k+1)/count);n=P.node('natural_macro',pos,parent,'BUFx12f_ASAP7_75t_R');parent=n['name'];first=first or n['name']
   ins={};receipt=[]
   for corner in ('TT','FF'):
    f=kd/'macros'/f"{h['master']}_{corner.lower()}.lib";ins[corner]=G.lib_insertion(f);receipt.append(corner+':'+hashlib.sha256(f.read_bytes()).hexdigest())
   leaf=dict(node=parent,sinks=[r['inst']+'/'+r['pin']],load_class='macro',early_tap_ps=ins,early_tap_view=';'.join(receipt));leaves.append(leaf)
   groups.append(dict(name=gate_name,kind='macro',anchor=gate_name,trunk_child=first,leaf_nodes=[parent],sinks=1,natural_local_depth=count,macro_clock_pin_xy_um=target))
  else:
   points=[(*r['xy'],r['inst']+'/'+r['pin'])for r in rs]
   regions=G.adaptive_groups(G.split(points,G.equal_counts(len(points),math.ceil(len(points)/96))),P,cap=80.)
   local_entries=[]
   for j,region in enumerate(regions):
    center=P.legal(G.centroid(region));n=local_register_tree(f'{gate_name}_region_{j}',region,None,center);local_entries.append(dict(node=n,xy=center))
   distance=max(G.man(origin,q['xy'])for q in local_entries)
   branch_depth=max(2,math.ceil(math.log(max(1,len(local_entries)),4))+1,math.ceil(distance/100.)+1)
   branch_items=[dict(xy=q['xy'],goal=branch_depth,attach=lambda par,n=q['node']:n.update(parent=par))for q in local_entries]
   P.feed(gate_name,origin,0,branch_items,'natural_gated_feed')
 # Direct-clock registers get small spatial neighborhoods, rather than one
 # giant root fanout tree that shares no path with nearby functional domains.
 if root:
  roots=G.adaptive_groups(G.split([(*r['xy'],r['inst']+'/'+r['pin'])for r in root],G.equal_counts(len(root),math.ceil(len(root)/96))),P,cap=80.)
  for j,points in enumerate(roots):
   origin=P.legal(G.centroid(points));n=local_register_tree(f'root_neighborhood_{j}',points,None,origin)
   entries.append(dict(node=n,xy=origin))
 upper=P.node('natural_source',port,'port:ck','BUFx24_ASAP7_75t_R');items=[]
 for gate in gates.values():items.append(dict(xy=gate['xy_um'],goal=0,attach=lambda par,g=gate:g.update(parent=par)))
 for e in entries:items.append(dict(xy=e['xy'],goal=0,attach=lambda par,n=e['node']:n.update(parent=par)))
 reach=max(G.man(port,q['xy'])for q in items);global_depth=max(3,math.ceil(math.log(len(items),4))+1,math.ceil(reach/100.)+1)
 for q in items:q['goal']=global_depth
 P.feed(upper['name'],port,0,items,'natural_global')
 parents={n['name']:n['parent']for n in P.nodes};parents.update({n:g['parent']for n,g in gates.items()});dep={'port:ck':0}
 def depth(n):
  if n not in dep:dep[n]=depth(parents[n])+1
  return dep[n]
 for n in parents:depth(n)
 nodes=sorted(P.nodes,key=lambda n:(dep[n['name']],n['name']))
 tree=dict(clock_port='ck',nodes=nodes,gates=list(gates.values()),leaves=leaves,equal_load=False,load_balance='joint_nldm_plan',stage_basis='electrical_latency',latency_target_ps={'TT':1000.,'FF':800.},note='MODEL ONLY spatially bounded local-region trees; common joint-NLDM trunk per functional/root neighborhood domain remains to size; no measured arrival/RTL change')
 sl['core_tree']=tree;sl.pop('cell_placements',None);sl['electrical_domain_plan']=groups
 xy={n['name']:n['xy_um']for n in nodes};xy.update({n:g['xy_um']for n,g in gates.items()});xy['port:ck']=port
 legs=[G.man(xy[n],xy[par])for n,par in parents.items()];macro_last=[]
 for group in groups:
  if group['kind']=='macro':macro_last.append(G.man(xy[group['leaf_nodes'][0]],group['macro_clock_pin_xy_um']))
 original=[r['inst']+'/'+r['pin']for r in raw];actual=[q for l in leaves for q in l['sinks']]
 if len(actual)!=len(set(actual))or set(original)!=set(actual):raise ValueError('lost/duplicated sink identity')
 report=dict(scope='MODEL ONLY, no passing timing/physical view',functional_gates=len(gates),domains=len(groups),clock_nodes=len(nodes),clock_sinks=len(actual),register_leaf_count=sum(l['load_class']=='register'for l in leaves),global_natural_depth=global_depth,max_clock_node_leg_um=max(legs),max_macro_final_leg_um=max(macro_last),new_clock_micro_islands=len(G.CLOCK_ISLANDS),source_membership_preserved=True,rtl_cycles_added=0,pending='pureNLDM common-domain trunk sizing then full geometry/electrical feasibility before build')
 Path(o.out).write_text(json.dumps(sl,indent=1)+'\n');Path(o.report).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
