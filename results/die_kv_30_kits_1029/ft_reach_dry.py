#!/usr/bin/env python3
"""DIE-KV-30-KITS: dry-run ft_reach.resize (405 um x .98) on the 9 core-free types; reports slots that would need stations."""
import copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / 'tools/die_plan'))
import ft_reach
raw = json.load(open(sys.argv[2]))
types = sys.argv[3].split(',')
out = {}
for t in types:
    ch = ft_reach.resize(copy.deepcopy(raw), types=[t], macrofree_only=False)
    out[t] = dict(n_ft_slots=len(raw['partition_types'][t].get('ft_slots', [])), slots_needing_more_stations=len(ch), examples=ch[:3])
    print(t, 'ft_slots', out[t]['n_ft_slots'], 'over_reach_slots', len(ch), str(ch[:2])[:300])
Path(sys.argv[4]).write_text(json.dumps(out, indent=1, default=str) + '\n')
