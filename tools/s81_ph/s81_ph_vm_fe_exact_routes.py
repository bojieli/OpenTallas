#!/usr/bin/env python3
"""Exact bit endpoints and strict edge routing for an unallocated FE candidate.

Boundary pins are candidate requests, not qualified launch drivers. This receipt
cannot close native timing or replace any producer clock/reset binding.
"""
import argparse,json
from pathlib import Path
import s81_ph_vm_fe_h_floorplan as f
from s81_ph_hrow_route_cuts import check
class ExactPlan(f.Plan):
    def __init__(self,variant):
        self.edges=[]
        super().__init__(variant)
    def hop(self,cls,a,pa,b,pb):
        super().hop(cls,a,pa,b,pb)
        self.edges.append(dict(source_pins=list(pa),sink_pins=list(pb)))
    def ext_hop(self,cls,face,inst,pins,drive_in=True):
        super().ext_hop(cls,face,inst,pins,drive_in)
        boundary=[f'candidate_{cls}_{len(self.edges)}[{i}]' for i in range(len(pins))]
        self.edges.append(dict(source_pins=boundary if drive_in else list(pins),sink_pins=list(pins) if drive_in else boundary))
    def rects(self):
        d=super().rects()
        d['FE.N']=(0,f.H,f.W,f.H+1,'UNALLOCATED_BOUNDARY_REQUEST')
        d['FE.S']=(0,-1,f.W,0,'UNALLOCATED_BOUNDARY_REQUEST')
        return d
    def check_place(self):
        # Boundary bookkeeping rectangles sit outside the candidate outline.
        original=self.rects
        self.rects=lambda:f.Plan.rects(self)
        try:return super().check_place()
        finally:self.rects=original

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--placements',required=True);ap.add_argument('--master-pins',required=True)
    ap.add_argument('--assigned-capture');ap.add_argument('--out',required=True)
    a=ap.parse_args();q=json.loads(Path(a.placements).read_text())
    f.W=q.get('width',1865.664);f.H=q.get('height',889.92)
    f.load_actual_master_pins(a.master_pins);p=ExactPlan(q.get('variant','B'))
    f.reposition(p,{n:(v['x'],v['y']) for n,v in q['instances'].items()},q.get('derive_external_pins',False))
    if a.assigned_capture:f.assign_capture(p,a.assigned_capture)
    bad=p.check_place();result=dict(schema='opentallas.vmfe-exact-route-candidate.v1',native_qualified=False,boundary_status='UNALLOCATED_SOURCE_AND_PIN_REQUEST',actual_clock_rc_budget_um=None,placement_violations=bad,pairs=sum(len(x[3]) for x in p.hops),source_pin_receipts=f.PIN_RECEIPTS)
    if bad:result['routes']='NOT_RUN: placement overlaps must be repaired'
    else:result['routes']=check(p,f.W,f.H,chunk=4,wire_limit_um=500,edge_limit=.60,dump_path=str(Path(a.out).with_suffix('.routes.json.gz')))
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result.get('routes')),flush=True)
if __name__=='__main__':main()
