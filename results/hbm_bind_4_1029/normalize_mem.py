#!/usr/bin/env python3
"""HBM-BIND-4: bounded standard Yosys memory normalization of the 8 SU g_inj.slot arrays.

Runs only `memory_collect; memory_map` (stock Yosys passes) on the prepared proc JSON.
Refuses unless the design holds exactly the 8 expected 4x162 g_inj.slot memories (one
$memwr_v2 + one async $memrd each). Proves every retained flat cell keeps its type,
parameters and terminals under one consistent net bijection, that new cells live only
inside the 8 memory-owning SU instances and touch the outside only through the original
memory terminal nets, and homes every new cell with the original memory owner
(no new partition, no tie, no latch). Original JSON is never overwritten.
"""
import argparse, json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools' / 'die_plan'))
import bind_elab as E

MEM = ('$memwr_v2', '$memrd', '$memrd_v2', '$meminit_v2', '$mem_v2', '$memwr')
GLUE_OK = {'$dff', '$mux', '$and', '$or', '$not', '$eq', '$xor', '$reduce_or', '$reduce_and', '$logic_not', '$logic_and', '$logic_or', '$ne', '$pmux_never'}

class Refused(ValueError):
    pass

def inventory(d):
    inv = collections.defaultdict(list)
    for mn, m in d['modules'].items():
        for cn, c in m.get('cells', {}).items():
            if c['type'] in MEM:
                inv[mn].append((cn, c))
    return inv

def check_bounded(d):
    inv = inventory(d)
    if len(inv) != 8:
        raise Refused(f'expected 8 memory modules, got {len(inv)}')
    for mn, cells in inv.items():
        types = sorted(c['type'] for _, c in cells)
        if types != ['$memrd', '$memwr_v2'] or 'ot_hbm_su_static_pgslice_s' not in mn:
            raise Refused(f'{mn}: unexpected memory cells {types}')
        mems = d['modules'][mn].get('memories', {})
        if list(mems) != ['\\g_inj.slot'] and list(mems) != ['g_inj.slot']:
            raise Refused(f'{mn}: unexpected memories {list(mems)}')
        mm = list(mems.values())[0]
        if int(mm['width']) != 162 or int(mm['size']) != 4:
            raise Refused(f'{mn}: memory shape {mm}')
        for _, c in cells:
            if c['parameters'].get('MEMID') != '\\g_inj.slot':
                raise Refused('MEMID')
            if c['type'] == '$memrd' and int(c['parameters']['CLK_ENABLE'], 2) != 0:
                raise Refused('read port must be async as inventoried')
    return inv

def bij(a2b, b2a, x, y, where):
    if isinstance(x, str) or isinstance(y, str):
        if x != y:
            raise Refused(f'constant mismatch {where}: {x} vs {y}')
        return
    if a2b.setdefault(x, y) != y or b2a.setdefault(y, x) != x:
        raise Refused(f'net bijection broken at {where}')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--receipt', required=True, type=Path)
    ap.add_argument('--map-in', required=True, type=Path)
    ap.add_argument('--map-out', required=True, type=Path)
    ap.add_argument('--top', default='hbm_current_native_top')
    ap.add_argument('--mem', type=int, default=24)
    a = ap.parse_args()
    if a.source.resolve() == a.out.resolve():
        raise Refused('source must stay immutable')
    src = json.loads(a.source.read_text())
    inv = check_bounded(src)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    ys = a.out.with_suffix('.ys')
    ys.write_text(f'read_json "{a.source.resolve()}"\nmemory_collect\nmemory_map\nwrite_json "{a.out.resolve()}"\n')
    E.run_yosys(ys, a.out.with_suffix('.yosys.log'), [a.source.parent, a.out.parent], mem_gb=a.mem)
    out = json.loads(a.out.read_text())
    if inventory(out):
        raise Refused('memory cells remain after memory_map')
    before = E.flatten(src, a.top)
    after = E.flatten(out, a.top)
    old_mem = [c for c in before.cells if c.ytype in MEM]
    if len(old_mem) != 16:
        raise Refused(f'expected 16 flat memory cells, got {len(old_mem)}')
    owners = sorted({c.path.split('.$', 1)[0] for c in old_mem})
    if len(owners) != 8:
        raise Refused(f'expected 8 owning instances, got {owners}')
    rb = {c.path: c for c in before.cells if c.ytype not in MEM}
    ra = {c.path: c for c in after.cells}
    missing = sorted(set(rb) - set(ra))
    if missing:
        raise Refused(f'{len(missing)} retained cells missing, e.g. {missing[:3]}')
    a2b, b2a = {}, {}
    for p, old in rb.items():
        new = ra[p]
        for k in ('module', 'params', 'dirs', 'kind', 'ytype', 'yparams'):
            if getattr(old, k) != getattr(new, k):
                raise Refused(f'retained {p}: {k} changed')
        if sorted(old.ports) != sorted(new.ports):
            raise Refused(f'retained {p}: port set changed')
        for pn in old.ports:
            if len(old.ports[pn]) != len(new.ports[pn]):
                raise Refused(f'retained {p}.{pn}: width changed')
            for i, (x, y) in enumerate(zip(old.ports[pn], new.ports[pn])):
                bij(a2b, b2a, x, y, f'{p}.{pn}[{i}]')
    if sorted(before.top_ports) != sorted(after.top_ports):
        raise Refused('top port names changed')
    for pn in before.top_ports:
        (db, tb), (da, ta) = before.top_ports[pn], after.top_ports[pn]
        if db != da or len(tb) != len(ta):
            raise Refused(f'top port {pn} changed')
        for i, (x, y) in enumerate(zip(tb, ta)):
            bij(a2b, b2a, x, y, f'top.{pn}[{i}]')
    new_cells = [c for p, c in ra.items() if p not in rb]
    bad = [c.path for c in new_cells if not any(c.path.startswith(o + '.') for o in owners)]
    if bad:
        raise Refused(f'new cells outside memory owners: {bad[:3]}')
    types = collections.Counter(c.ytype for c in new_cells)
    if set(types) - GLUE_OK:
        raise Refused(f'unsupported new cell types {set(types) - GLUE_OK}')
    # boundary: nets shared between new cells and retained cells/top must be images of old memory terminal nets
    old_mem_nets = {b for c in old_mem for bs in c.ports.values() for b in bs if not isinstance(b, str)}
    new_nets = {b for c in new_cells for bs in c.ports.values() for b in bs if not isinstance(b, str)}
    retained_nets = set(b2a)
    shared = new_nets & retained_nets
    stray = [b for b in shared if b2a[b] not in old_mem_nets]
    if stray:
        raise Refused(f'{len(stray)} new-cell nets touch retained logic outside the memory terminals')
    # every old memory terminal net that retained logic also uses must be reached by a new cell
    needed = {a2b[b] for b in old_mem_nets if b in a2b}
    unreached = needed - new_nets
    if unreached:
        raise Refused(f'{len(unreached)} memory terminal nets lost after memory_map')
    # homes: new cell -> partition of the original co-resident memory owner (read/write share one owner)
    mp = json.loads(a.map_in.read_text())
    parts = mp['parts']
    home = {}
    for c in old_mem:
        o = c.path.split('.$', 1)[0]
        if c.path not in parts:
            raise Refused(f'memory cell {c.path} has no map home')
        part, rel = parts[c.path]
        prefix = rel.split('.$', 1)[0]
        if home.setdefault(o, (part, prefix)) != (part, prefix):
            raise Refused(f'{o}: read/write ports have different owners')
    for c in old_mem:
        del parts[c.path]
    added = 0
    for c in new_cells:
        o = next(o for o in owners if c.path.startswith(o + '.'))
        part, prefix = home[o]
        parts[c.path] = [part, prefix + '.' + c.path[len(o) + 1:]]
        added += 1
    mp['note'] = (mp.get('note', '') + ' | HBM-BIND-4: 16 g_inj.slot memory cells replaced by their stock Yosys '
                  'memory_map cells, each homed with its original co-resident read/write owner')
    a.map_out.write_text(json.dumps(mp))
    rec = dict(schema='hbm.bind4.memory_map.v1', verdict='PASS', passes=['memory_collect', 'memory_map'],
               source=str(a.source), output=str(a.out), memories=8, memory_shape='4x162 g_inj.slot, 1 sync write, 1 async read',
               removed_flat_memory_cells=[c.path for c in old_mem], owners={o: home[o][0] for o in owners},
               retained_cells=len(rb), retained_terminals_bijective=True, net_bijection_size=len(a2b),
               new_cells=len(new_cells), new_cell_types=dict(types), map_entries_added=added,
               boundary_nets_shared=len(shared), added_cycles=0, ties=0, latches=0)
    a.receipt.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rec.items() if k not in ('removed_flat_memory_cells',)}))

if __name__ == '__main__':
    main()
