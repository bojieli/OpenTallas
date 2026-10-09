#!/usr/bin/env python3
"""Minimum static-map invariant gate; run remotely through admission."""
import json,sys
from qwen_protected_phy_bank_map import sidecar_location
mutant='--mutant' in sys.argv
result=[]
for emb,rows in [(False,range(36)),(True,range(24427,24576))]:
    pairs=set();words=set();rowset=set();count=0
    for row in rows:
        for bank in range(32):
            for col in range(32):
                erow,ebank,ecol,lane=sidecar_location(emb,row,bank,col,mutant=mutant)
                assert bank!=ebank,('same bank',emb,row,bank,col,erow,ebank,ecol)
                key=(erow,ebank,ecol,lane)
                assert key not in pairs,('collision',key)
                pairs.add(key);words.add(key[:3]);rowset.add(erow);count+=1
    assert len(pairs)==count and len(words)*8==count
    result.append(dict(embedding=emb,logical_sectors=count,unique_sidecar_words=len(words),sidecar_rows=len(rowset),bank_disjoint=True,bijection=True))
print(json.dumps(dict(PASS=True,cases=result),indent=2))
