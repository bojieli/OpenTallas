#!/usr/bin/env python3
"""Conditional geometry lower bound for a corresponding input broadcast in a trial."""
import argparse,gzip,hashlib,json,math
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
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--prototype',type=Path,required=True);a.add_argument('--graph',type=Path,required=True);a.add_argument('--output',type=Path,required=True);p=a.parse_args();p.output.write_text(json.dumps(build(p.prototype,p.graph),indent=2)+'\n')
