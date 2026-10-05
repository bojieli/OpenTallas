#!/usr/bin/env python3
"""Compose measured ctl deltas using actual caller schedule counts, no rate claim."""
import argparse
import json
from pathlib import Path

def compose(counts):
    names=('union_flushes','argmax_rows','scratch_reads')
    for name in names:
        if name not in counts or type(counts[name]) is not int or counts[name]<0:
            raise ValueError('actual nonnegative integer count required: '+name)
    cycles=sum(counts[name] for name in names)
    return dict(additional_cycles=cycles,additional_ns_at_target_1p2GHz=cycles/1.2,
        per_event_cycle_deltas=dict(union_flushes=1,argmax_rows=1,scratch_reads=1),
        union_delta_is_startup_not_per_emitted_expert=True,
        actual_counts=counts,complete_accelerator_qualified=False,
        parent_calendar='UNKNOWN unless caller supplies actual causal schedule; sum is nonoverlapped delta, not a new token headline',
        blocked_spec_state_exactness=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--actual-counts',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=compose(json.loads(a.actual_counts.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
