#!/usr/bin/env python3
"""Read-only, source-bound geometry screen. Produces proposals, never allocations."""
import argparse, hashlib, json, subprocess
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def area(a, b):
    return max(0., min(a[2], b[2])-max(a[0], b[0])) * max(0., min(a[3], b[3])-max(a[1], b[1]))


def box(row):
    x, y = row['xy_um']
    return [x, y, x+row['w_um'], y+row['h_um']]


def overlaps(rect, children):
    hits = [(c['instance'], area(rect, box(c)), bool(c.get('view_lef'))) for c in children if area(rect, box(c)) > 1e-6]
    return {'count': len(hits), 'real_view_count': sum(r[2] for r in hits), 'intersection_um2': sum(r[1] for r in hits), 'instances': [r[0] for r in hits]}


def pack(rows, reservation, outlines):
    """Two banks, four windows/bank; R0 only; every source path exactly once."""
    if len(rows) != 40 or len({r['path'] for r in rows}) != 40:
        raise ValueError('require exactly forty unique source-bound leaf paths per quarter')
    sw,sh=outlines['ot_hgi_hc_win_sector']; cw,ch=outlines['ot_hgi_hc_win_ctl']
    gap=12.96; window_w=2*sw+gap; window_h=2*sh+2*gap+ch
    bank_w=2*window_w+gap
    out=[]
    for row in rows:
        master=row['master']; w,h=outlines[master]
        win=row['window_index'] % 4; bank=row['bank'] % 2
        x=reservation['xy_um'][0]+21.6+bank*(bank_w+gap)+(win%2)*(window_w+gap)
        y=reservation['xy_um'][1]+21.6+(win//2)*(window_h+gap)
        if master == 'ot_hgi_hc_win_sector':
            sector=int(row['path'].split('g_sector[')[1].split(']')[0])
            x+=(sector%2)*(sw+gap); y+=(sector//2)*(sh+gap)
        elif master == 'ot_hgi_hc_win_ctl':
            x+=(window_w-cw)/2; y+=2*sh+2*gap
        else:
            raise ValueError('unsupported master')
        item={'source_path':row['path'], 'master':master,'clock':row['clock'], 'reset_driver':row['reset_driver'], 'orientation':'R0','xy_um':[round(x,6),round(y,6)],'w_um':w,'h_um':h,'assigned':False}
        if abs(area(box(item),box(reservation))-w*h)>1e-5:
            raise ValueError('leaf does not fit reservation')
        if any(area(box(item),box(p))>1e-6 for p in out):
            raise ValueError('leaf overlap')
        out.append(item)
    return out


def git_bytes(repo, rev, path):
    return subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=repo)


def build(repo, rev, package, source_repo):
    cp='results/arch/hbm_native_1013/die_v13/candidate.json'
    raw=git_bytes(repo,rev,cp); candidate=json.loads(raw)
    graph_raw=(package/'native_connection_graph.json').read_bytes(); graph=json.loads(graph_raw)
    demand_raw=(package/'physical_pin_demand.json').read_bytes(); demand=json.loads(demand_raw)
    request_raw=(package/'slot_partition_request.json').read_bytes(); request=json.loads(request_raw)
    for path, sha in graph['source_sha256'].items():
        if digest(git_bytes(source_repo,graph['source_commit'],path)) != sha:
            raise ValueError(f'source mismatch: {path}')
    if graph['source_sha256'] != request['source_sha256']:
        raise ValueError('request and graph source sets differ')
    outlines={r['master']:r['measured_outline_um'] for r in demand['inventory']}
    outline_conflicts=[]
    for inv in demand['inventory']:
        if not inv.get('actual_pin_coordinates_file'): continue
        pinfile=source_repo/inv['actual_pin_coordinates_file']
        pin=json.loads(pinfile.read_bytes()); rect=pin['die']; actual=[rect[2]-rect[0],rect[3]-rect[1]]
        if any(abs(a-b)>1e-6 for a,b in zip(actual,inv['measured_outline_um'])):
            outline_conflicts.append({'master':inv['master'],'inventory_um':inv['measured_outline_um'],'private_pin_dump_um':actual,'pin_dump_sha256':digest(pinfile.read_bytes()),'binding_qualified':False})
            outlines[inv['master']]=[max(a,b) for a,b in zip(actual,inv['measured_outline_um'])]
    sectors=[r for r in graph['scalar_leaf_instances'] if r['master'] in ['ot_hgi_hc_win_sector','ot_hgi_hc_win_ctl']]
    if len(sectors)!=160: raise ValueError('incomplete scalar source inventory')
    reservations=candidate['unresolved_regions']
    proposals=[]
    for q in range(4):
        # This one-to-one geographic permutation is a proposal, not a producer ABI binding.
        res=reservations[q]; placed=pack([r for r in sectors if r['quarter']==q],res,outlines)
        for row in placed:
            row['candidate_reservation']=res['instance']; row['source_quarter_to_geography_proven']=False
            row['existing_child_overlap']=overlaps(box(row),candidate['children'])
            row['reserved_corridor_overlap']=[r['name'] for r in candidate['routing_corridor_reservations']+candidate['ring_device_column_reservations'] if area(box(row),r['rect_um'])>1e-6]
        proposals+=placed
    legacy={
        'hb_quant/u_qdq':[14761.872,15984.,15383.952,16580.16],
        'hb_hc_eng':[16794.,12204.,21178.8,13770.],
        'hb_su_SW':[11173.248,7976.88,13189.392,10784.88],
        'idx_score_SW':[11736.576,1596.24,13736.736,4242.24],
        'hb_hc_SW':[8563.968,11136.96,10827.648,12636.],
    }
    audits={n:dict(rect_um=rect,**overlaps(rect,candidate['children']),corridors=[{'name':r['name'],'intersection_um2':area(rect,r['rect_um'])} for r in candidate['routing_corridor_reservations']+candidate['ring_device_column_reservations'] if area(rect,r['rect_um'])>0]) for n,rect in legacy.items()}
    return {'schema':'opentallas.hbm_die_feasibility.v1','qualified':False,'geometry_revision':rev,'geometry_sha256':digest(raw),'geometry_path':cp,'published_contract_sha256':digest(git_bytes(repo,rev,'results/arch/hier_contract_1011/r25gq.json')),'hc_source_commit':graph['source_commit'],'inputs_sha256':{'native_connection_graph.json':digest(graph_raw),'physical_pin_demand.json':digest(demand_raw),'slot_partition_request.json':digest(request_raw)},'all_13_source_blobs_verified':len(graph['source_sha256']),'private_pin_outline_conflicts':outline_conflicts,'private_pin_binding_qualified':False,'legacy_slot_overlay':audits,'hc_scalar_proposals':proposals,'hc_summary':{'proposed_leaves':len(proposals),'assigned_leaves':0,'overlapping_existing_children':sum(bool(r['existing_child_overlap']['count']) for r in proposals),'overlapping_reserved_corridors':sum(bool(r['reserved_corridor_overlap']) for r in proposals),'per_reservation_used_envelope_um':[8*outlines['ot_hgi_hc_win_sector'][0]+7*12.96,470.88],'reservation_um':[1356.48,756],'not_covered':['retained bank control and arithmetic parents','source-quarter geographic binding','final routed views/pin access/PG','actual peer endpoint routes','production clock and reset driver graph','per-corner propagated entry paths/slew and setup/hold']},'idx_lower_bound':{'leaves_per_scorer':512,'old_leaf_um':[172.8,103.68],'old_slot_um':[2000.16,2646.],'leaf_only_mm2_per_scorer':512*172.8*103.68/1e6,'old_slot_mm2':2000.16*2646/1e6,'area_ratio':512*172.8*103.68/(2000.16*2646),'fresh_leaf_views_qualified':False,'whole_parent_census':{'source':'6bef69dff','ff_bits':746910,'inferred_memory_bits':2426892,'clock_entries':2166,'selector_ff_bits':241250},'no_fit_claim':True},'clock_reset_policy':{'tree_period_ps':833.333,'vm_period_ps':1111.111,'tree_setup_ps_shallow':150,'tree_setup_ps_either_deep':210,'tree_hold_ps':100,'forwarded_hold_ps_only_bound_no_tree':25,'source_binding':None,'tap_assignment':None,'reset_release_binding':None,'no_corner_or_source_fallback':True}}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--revision',required=True);ap.add_argument('--hc-package',type=Path,required=True);ap.add_argument('--hc-repo',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    a.output.write_text(json.dumps(build(a.repo,a.revision,a.hc_package,a.hc_repo),indent=2)+'\n')
