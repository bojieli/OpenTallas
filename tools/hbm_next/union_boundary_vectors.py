#!/usr/bin/env python3
"""Real IDX/SW-slice fixtures including equal-U24, different-cardinality routes."""
import copy
import hnx_idx_union_vectors as V
from union_variants import counterexample
orig=V.make_records

def records(rng,count):
    recs=orig(rng,count)
    for i,(name,rows) in enumerate(counterexample()['rows'].items()):
        r=copy.deepcopy(recs[8])
        r.update(a=52000+128*i,a_str=8,o=52480+64*i,d=52608+8*i,r=53248+2048*i,
            rows=rows,kind='U24_'+name)
        recs.append(r)
    return recs
V.make_records=records
if __name__=='__main__':V.main()
