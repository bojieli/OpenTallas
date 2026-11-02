"""Reuse already gated non-down placement plans; re-solve every down phase.

Actual compile_frame/add_planned/write_images still rebuild the field from its
fixture. No historical down source span, assignment or CAP calendar is reused.
The caller must use this within one isolated worker (not concurrent threads).
"""
from contextlib import contextmanager
from copy import deepcopy
import os

@contextmanager
def reuse_nondown(X,baseline):
    if os.environ.get('OT_XS_DOWN_CAP_PLAN')!='1' or os.environ.get('OT_XS_FINAL_FFN_PAIR_ROWS')!='1':
        raise ValueError('CAP-safe source reuse requires both explicit flags')
    entries=[p for p in baseline['phases'] if p['phase'] and p.get('fmt')!='bf16']
    original=X.phase_plan;state=dict(index=0,reused=0,rebuilt_down=0)
    def selected(master,lk,pairs,off,mat,x,nseg,iters,**kwargs):
        i=state['index'];state['index']+=1
        if i>=len(entries):raise ValueError('new field has an extra FP phase')
        old=entries[i]
        if master!=baseline['master'] or lk!=baseline['lk'] or mat.name!=old['mat'] or mat.fmt!=old['fmt'] or mat.K!=old['K'] or nseg!=old['nseg']:
            raise ValueError('cached source phase identity differs')
        if old['op']=='ffn.down':
            if kwargs.get('ret_score') is None:raise ValueError('down source needs its fresh FIN score')
            state['rebuilt_down']+=1
            return original(master,lk,pairs,off,mat,x,nseg,iters,**kwargs)
        if mat.rows!=old['rows'] or kwargs.get('ret_score') is not None:raise ValueError('cached non-down shape differs')
        plan=deepcopy(old['plan'])
        if plan['faults'] or plan['calendar']!='measured_class':raise ValueError('cached source phase was not legalised')
        # Cached assignments are in the whole field's slot space. The ordinary
        # compile_frame path below translates pair-local slots back exactly once.
        plan['assign_slots']=[(pairs.index(baseline['pairs'][slot]),row,seg) for slot,row,seg in plan['assign_slots']]
        state['reused']+=1
        return plan
    X.phase_plan=selected
    try:
        yield state
        if state['index']!=len(entries) or not state['rebuilt_down']:raise ValueError('cached source phase sequence incomplete')
    finally:X.phase_plan=original
