#!/usr/bin/env python3
"""Feasibility-only coupled repair; same pinned constraints, no L1 optimisation."""
import argparse,numpy as np
import s81_ph_vm_fe_joint_repair as J
_original=J.milp
def feasible(c,*args,**kwargs):
    return _original(np.zeros_like(c),*args,**kwargs)
J.milp=feasible
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--placements',required=True);a.add_argument('--master-pins',required=True);a.add_argument('--assigned-capture',required=True);a.add_argument('--out',required=True);a.add_argument('--radius',type=float,default=345.6);a.add_argument('--margin',type=float,default=0);a.add_argument('--nodes',type=int,default=20000);q=a.parse_args();J.solve(q.placements,q.master_pins,q.assigned_capture,q.out,q.radius,q.margin,q.nodes)
