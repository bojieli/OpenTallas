#!/usr/bin/env python3
"""Conditional geometry lower bound for a corresponding input broadcast in a trial."""
import argparse,gzip,hashlib,json,math,subprocess
from pathlib import Path

def bounds(rows):
    if len(rows)!=16:raise ValueError('sixteen mapper destinations required')
    if len({(r['w_um'],r['h_um'],r['orientation']) for r in rows})!=1:raise ValueError('corresponding-pin bound requires identical orientations/outlines')
    points=[r['xy_um'] for r in rows]
    if not all(math.isfinite(v) for p in points for v in p):raise ValueError('nonfinite geometry')
    diameter=max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in points for b in points)
    return {'corresponding_input_destination_L1_diameter_um':diameter,'optimal_single_source_worst_L1_lower_bound_um':diameter/2}

def build(prototype,graph):
    pr=prototype.read_bytes();gr=graph.read_bytes();p=json.loads(pr);g=json.loads(gzip.decompress(gr))
    rows=[r for r in p['children'] if r['instance'].startswith('mapper')]
    d=bounds(rows)
    control=[r for r in p['children'] if r['instance'].startswith('control')]
    left=min(rows,key=lambda r:r['xy_um'][0]);column_left=min(r['xy_um'][0] for r in control)
    d.update({'schema':'opentallas.sfu_broadcast_conditional_geometry.v1','prototype_sha256':hashlib.sha256(pr).hexdigest(),'literal_source_graph_gzip_sha256':hashlib.sha256(gr).hexdigest(),'source_graph_reported_sha256':g['source_sha256'],'source_blob_verification':False,'source_graph_statement':g['controller_to_mapper'],'dynamic_bits_reported_by_source_owner':1022,'destinations':16,'actual_remaining_E1_E2_source_pins_bound':False,'right_control_column_to_left_mapper_face_lower_bound_um':column_left-(left['xy_um'][0]+left['w_um']),'qualified':False,'actual_RC_delay_ps':None,'actual_launch_capture_window_ps':None,'new_mapper_physical_pins_bound':False,'assumption':'Each corresponding input uses identical local coordinates on sixteen identically oriented requested mapper masters. This is a trial geometry condition; new mapper physical views and actual remaining E1/E2 launch pins are unbound.','required_next_action':'Bind exact E1/E2 source endpoints and actual mapper views; compare every dynamic bit to actual corner timing windows; derive coherent registered distribution if required without assuming extra edge acceptance.'})
    return d
def bind_remaining(d,repo,revision):
    path='results/arch/hbm_native_1013/sfu_native_quarter/remaining_E1_E2_root_census.json'
    raw=subprocess.check_output(['git','show',revision+':'+path],cwd=repo);c=json.loads(raw)
    source=subprocess.check_output(['git','show',revision+':'+c['source']],cwd=repo)
    if hashlib.sha256(source).hexdigest()!=c['sha256']:raise ValueError('remaining-controller source hash mismatch')
    d.update({'remaining_controller_census_revision':revision,'remaining_controller_census_sha256':hashlib.sha256(raw).hexdigest(),'remaining_controller_source_sha256_verified':c['sha256'],'remaining_controller_declared_post_S_FF_upper':c['post_S_declared_FF_upper'],'remaining_controller_total_FF_count':None,'remaining_controller_total_count_scope':c['physical_root'],'trial_includes_remaining_controller_master':False,'full_quarter_fit_proven':False,'mixed_stage_broadcast_source_statement':c['cws_bus_vs_broadcast'],'unregistered_E1_source_field_bits':c['export_fields'][0]['bits'],'remaining_controller_physical_pins_bound':False,'C2_terminal_boundary_R_ps':c['C2_handles']['TT_R_boundary_ps'],'C3_live_handles_last_reported':c['C3_handles']})
    return d

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--prototype',type=Path,required=True);a.add_argument('--graph',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--remaining-repo',type=Path);a.add_argument('--remaining-revision');p=a.parse_args()
    if bool(p.remaining_repo)!=bool(p.remaining_revision):a.error('remaining repo and revision required together')
    d=build(p.prototype,p.graph)
    if p.remaining_repo:d=bind_remaining(d,p.remaining_repo,p.remaining_revision)
    p.output.write_text(json.dumps(d,indent=2)+'\n')
