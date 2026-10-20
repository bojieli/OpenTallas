"""Read-only fixed-endpoint planning model over the original full sequential cones."""
import gzip
import hashlib
import json
from pathlib import Path
import odb

path = Path('/out/full_sequential_cones.json.gz')
with gzip.open(path, 'rt') as f:
    audit = json.load(f)
if audit['status'] != 'PASS' or audit['role_errors']:
    raise RuntimeError('original full cone audit did not PASS')
db = odb.dbDatabase.create()
odb.read_db(db, audit['odb_path'])
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
radii = {}
for i in block.getInsts():
    if not i.getMaster().isBlock():
        b = i.getBBox()
        radii[i.getName()] = ((b.xMax()-b.xMin()) + (b.yMax()-b.yMin()))/(2*dbu)
rings = {r['instance']: r for r in audit['rings']}
row_boxes = [m['bbox_um'] for m in audit['macro_inventory'] if m['instance'] not in rings]
width, height, pitch, gap = 388.8, 432.0, 43.2, 20.0
rw, rh = next(iter(rings.values()))['master_size_um']
def disjoint(a, b):
    return a[2]+gap <= b[0]+1e-8 or b[2]+gap <= a[0]+1e-8 or a[3]+gap <= b[1]+1e-8 or b[3]+gap <= a[1]+1e-8
points = []
for ix in range(1, 10):
    for iy in range(1, 11):
        x,y = round(ix*pitch, 6),round(iy*pitch, 6)
        box = [x,y,x+rw,y+rh]
        if x < gap or y < gap or x+rw+gap > width+1e-8 or y+rh+gap > height+1e-8:
            continue
        if all(disjoint(box, b) for b in row_boxes):
            points.append([x,y])
coupled = sorted({(e['root'].get('instance'),e['endpoint'].get('instance'))
                  for r in rings.values() for e in r['edges']
                  if e['root'].get('instance') in rings and e['endpoint'].get('instance') in rings
                  and e['root']['instance'] != e['endpoint']['instance']})
def evaluate(e, assignment):
    coords = []
    for endpoint in ('root','endpoint'):
        d = e[endpoint]
        p = list(d['xy_um'])
        name = d.get('instance')
        if name in assignment:
            old = rings[name]['placement_lower_left_um']
            p = [p[k]+assignment[name][k]-old[k] for k in range(2)]
        coords.append(p)
    manhattan = abs(coords[0][0]-coords[1][0])+abs(coords[0][1]-coords[1][1])
    radius = sum(radii.get(e[x].get('instance'),0) for x in ('root','endpoint'))
    return manhattan,manhattan+radius
matrix = []
for name,r in rings.items():
    values = []
    for p in points:
        measures = [evaluate(e,{name:p}) for e in r['edges']]
        dist,bound = max(x[0] for x in measures),max(x[1] for x in measures)
        values.append({'point_um':p,'max_endpoint_manhattan_um':round(dist,6),
                       'max_endpoint_upper_bound_um':round(bound,6),'within405_with_proxy_bound':bound<=405+1e-8})
    matrix.append({'instance':name,'old_placement_lower_left_um':r['placement_lower_left_um'],
                   'values':values,'feasible_point_count':sum(v['within405_with_proxy_bound'] for v in values)})

# With no inter-ring combinational stage, fixed-endpoint constraints are independent;
# a bipartite matching therefore proves the reach/packing model for the 32 identities.
def matching(threshold):
    occupied = {}
    def place(i,seen):
        choices = sorted(range(len(points)),key=lambda j:matrix[i]['values'][j]['max_endpoint_upper_bound_um'])
        for j in choices:
            if j in seen or matrix[i]['values'][j]['max_endpoint_upper_bound_um'] > threshold+1e-8:
                continue
            seen.add(j)
            if j not in occupied or place(occupied[j],seen):
                occupied[j]=i
                return True
        return False
    for i in range(len(matrix)):
        if not place(i,set()):
            return None
    return {matrix[i]['instance']:points[j] for j,i in occupied.items()}

assignment = None if coupled else matching(float('inf'))
best = None
if assignment:
    costs=sorted({v['max_endpoint_upper_bound_um'] for r in matrix for v in r['values']})
    lo,hi=0,len(costs)-1
    while lo<hi:
        mid=(lo+hi)//2
        if matching(costs[mid]):hi=mid
        else:lo=mid+1
    best=costs[lo]
    assignment=matching(best)
def projection(positions):
    edges = [dict(e,ring=r['instance'],projected_manhattan_um=round(evaluate(e,positions)[0],6),
                  projected_upper_bound_um=round(evaluate(e,positions)[1],6))
             for r in rings.values() for e in r['edges']]
    edges.sort(key=lambda e:-e['projected_upper_bound_um'])
    return {'max_endpoint_manhattan_um':max(e['projected_manhattan_um'] for e in edges),
            'max_endpoint_upper_bound_um':edges[0]['projected_upper_bound_um'],
            'over405_count':sum(e['projected_upper_bound_um']>405+1e-8 for e in edges),'top20':edges[:20]}
candidate_path=Path('/inputs/candidate_origins.json')
candidate=json.loads(candidate_path.read_text())
proposed={r['inst']:r['new_origin_um'] for r in candidate['assignment']}
candidate_errors=[]
for r in candidate['assignment']:
    if r['inst'] not in rings:
        candidate_errors.append('unknown candidate identity:'+r['inst'])
    elif any(abs(r['old_origin_um'][k]-rings[r['inst']]['placement_lower_left_um'][k])>1e-6 for k in range(2)):
        candidate_errors.append('candidate old lower-left differs:'+r['inst'])
result={'schema':'opentallas.grp_fixed_endpoint_full_cone_placement_model.v1',
        'scope':'MODEL ONLY: translate actual oriented macro pins with unchanged orientation; all standard cells, ports, four row SRAMs fixed at original CTS coordinates. Endpoint distances are not routed wirelength. New placement/clock/parent-boundary timing still requires gates.',
        'anchor_semantics':'Grid/candidate origins mean placement BBOX LOWER-LEFT, not raw OpenDB getOrigin (differs for MY). Pin offsets retained from actual ODB.',
        'audit_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'candidate_input_sha256':hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        'outline_um':[width,height],'lattice_um':pitch,'macro_to_row_and_die_margin_um':gap,
        'row_macro_boxes_um':row_boxes,'legal_points_um':points,'legal_point_count':len(points),
        'proxy_bound':'Add each standard-cell endpoint BBox half-L1 extent to its centre-based reach; macro points are exact actual pin averages.',
        'max_endpoint_cell_proxy_radius_um':max(radii.get(e[x].get('instance'),0) for r in rings.values() for e in r['edges'] for x in ('root','endpoint')),
        'original':projection({}), 'inter_ring_stage_pairs':coupled,'per_ring_grid_matrix':matrix,
        'identity_fixed_matching_status':'COUPLED_NOT_SOLVED' if coupled else ('FEASIBLE' if assignment and best<=405+1e-8 else 'INFEASIBLE'),
        'minimum_bottleneck_upper_bound_um':best,'minimum_bottleneck_assignment_lower_left_um':assignment,
        'minimum_bottleneck_assignment_projection':projection(assignment) if assignment else None,
        'reach_safe_assignment_lower_left_um':assignment if assignment and best<=405+1e-8 else None,
        'parent_displacement_assignment_errors':candidate_errors,
        'parent_displacement_assignment_projection':None if candidate_errors else projection(proposed)}
result['original_top_path_witnesses']=[dict(e,combinational_path_witness=[
    dict(p,master=block.findInst(p['cell_output'].rsplit('/',1)[0]).getMaster().getName())
    for p in e.get('combinational_path_witness',[])]) for e in audit['top30']]
Path('/out/candidate_projection.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k in ('legal_point_count','max_endpoint_cell_proxy_radius_um','identity_fixed_matching_status','minimum_bottleneck_upper_bound_um','parent_displacement_assignment_errors')})
