#!/usr/bin/env python3
"""Exact released-column/home interval bound; no sampling of token histories."""
import hashlib,json
from pathlib import Path
import hbm_engram_partition as E
import hdc_v41_engram_shipped as S

def prove():
    t=S.shipped_tables();layers=[]
    for li,nrows in enumerate(E.RELEASED_ROWS):
        rph=E.rows_per_home(nrows);primes=t.primes[li].reshape(-1);offset=t.offsets[li].reshape(-1)
        columns=[dict(column=c,begin=int(offset[c]),end=int(offset[c]+primes[c])) for c in range(24)]
        assert columns[0]['begin']==0 and columns[-1]['end']==nrows
        assert all(a['end']==b['begin'] for a,b in zip(columns,columns[1:]))
        homes=[]
        for h in range(8):
            begin=h*rph;end=min(nrows,(h+1)*rph)
            intersections=[dict(column=c['column'],begin=max(begin,c['begin']),end=min(end,c['end'])) for c in columns if c['begin']<end and begin<c['end']]
            assert 1<=len(intersections)<=4
            assert sum(x['end']-x['begin'] for x in intersections)==end-begin
            homes.append(dict(rank=E.HOMES[li][h],begin=begin,end=end,possible_columns=intersections,max_rows=len(intersections)))
        layers.append(dict(layer=E.LAYERS[li],columns=columns,homes=homes))
    root=Path(__file__).resolve().parents[1]
    return dict(schema='opentallas.hbm.engram.released_home_bound.v1',status='pass',homes_per_layer=8,rows_per_token=24,max_rows_per_home=4,
        method='Each of24 hash columns emits exactly one residue+offset inside its own released prime interval; a home intersects atmost4 intervals. This counts all possible row addresses, not sampled histories.',
        layers=layers,source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),root/'tools/hbm_engram_partition.py',root/'tools/hdc_v41_engram_shipped.py',root/'rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv',root/'rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv']},
        claim='Source-address bound only, not formal sequential RTL or physical/performance qualification')
if __name__=='__main__':print(json.dumps(prove(),indent=2))
