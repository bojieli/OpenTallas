"""TOK-VERIFY-1: build a +-1 mutant of a strict bind for ONE lane (one more / one fewer bound stage), as if the emitted
RTL had one relay station more / less on that lane.  The mutant dir holds symlinks to the source bind's files except the
two rewritten records: bus_groups.json (every landing/internal member of the lane: bound_stages and landed_stages += d)
and bind_latency.json (the lane bound_stages and plan_cycles += d).  --groups-only rewrites only the members, --table-bound-only only the
lane bound_stages (bound != plan: the compiler must refuse the bind).  Used as the +-1 controls of prog_vs_bind.py.
usage: mk_bind_mutant.py SRC_BIND OUT_DIR LANE DELTA [--groups-only|--table-bound-only]"""
import json, os, sys
from pathlib import Path
src, out, lane, d = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
mode = sys.argv[5] if len(sys.argv) > 5 else 'consistent'
out.mkdir(parents=True, exist_ok=False)
for p in src.iterdir():
    if p.name not in ('bus_groups.json', 'bind_latency.json'):
        os.symlink(os.path.realpath(p), out / p.name)
g = json.loads((src / 'bus_groups.json').read_text()); n = 0
for key in ('landing', 'internal'):
    for grp in g.get(key) or []:
        for m in (grp.get('members') if isinstance(grp, dict) and 'members' in grp else [grp]):
            if m.get('lane') == lane and mode in ('consistent', '--groups-only'):
                m['bound_stages'] += d; n += 1
                if 'landed_stages' in m: m['landed_stages'] += d
lat = json.loads((src / 'bind_latency.json').read_text()); t = 0
for b in lat['buses']:
    if b.get('lane') == lane:
        if mode in ('consistent', '--table-bound-only'):
            b['bound_stages'] += d; t += 1
        if mode == 'consistent':
            b['plan_cycles'] += d
(out / 'bus_groups.json').write_text(json.dumps(g)); (out / 'bind_latency.json').write_text(json.dumps(lat, indent=1))
(out / 'MUTANT.json').write_text(json.dumps(dict(source=str(src), lane=lane, delta=d, mode=mode, members=n, table_rows=t)))
print(dict(lane=lane, delta=d, mode=mode, members=n, table_rows=t))
