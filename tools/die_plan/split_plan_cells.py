"""Materialize inherited plan cells and project their exact connectivity onto split pieces.

split(ev, T) is Event._plan_cells' replacement. Routes use tuple(base_partitions)
so the caller creates one physical lane per replica and calls each callback once.
Cross-piece rewired sinks and sliced remote output sinks fail closed.
"""
import copy
import json
import re
import sys
from pathlib import Path


def _context(ev):
    module = sys.modules.get(type(ev).__module__)
    if module is None or not all(hasattr(module, n) for n in ('SplitError', 'rpath', 'ROOT')):
        import type_split as module
    return module


def _interfaces(ev, doc):
    import bind_elab as E
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import die_port_bind as D
    ROOT = _context(ev).ROOT
    ab = ev.ab
    idx = E.module_index(ab.get('rtl_roots', ['rtl']), ab.get('files', []), ROOT)
    prefer = [str(Path(ROOT) / f) if not Path(f).is_absolute() else f for f in ab.get('prefer', [])]
    out = {}
    for row in doc.values():
        for c in row.get('cells', {}).values():
            m = c['module']
            if m in out:
                continue
            f, _ = E.pick(idx, m, prefer)
            if f is None:
                raise ValueError(f'plan cell module {m}: source missing')
            mods = {x.name: x for x in D.parse_modules(Path(f).read_text(errors='replace'), f)}
            if m not in mods:
                raise ValueError(f'plan cell module {m}: interface missing')
            out[m] = mods[m]
    return out


def split(ev, T):
    context = _context(ev)
    SplitError, rpath = context.SplitError, context.rpath
    src = ev.spec.get('plan_cells', ev.ab.get('plan_cells'))
    if not src:
        return None
    ev.pc_path = rpath(src)
    doc = json.loads(ev.pc_path.read_text())
    out = copy.deepcopy(doc)
    TT = out['types']
    ev.pc_routes = []
    ev.rep['plan_cells'] = {}
    effective = {}
    for tn, ts in ev.ts.items():
        base = ts.t.get('landing_base_type')
        if tn in TT:
            effective[tn] = copy.deepcopy(TT[tn])
        elif base in TT:
            effective[tn] = copy.deepcopy(TT[base])
    try:
        iface = _interfaces(ev, effective)
    except (ValueError, KeyError) as e:
        raise SplitError(str(e)) from e
    for tn, d in effective.items():
        ts = ev.ts[tn]
        bases = tuple(ev.ts_parts(tn))
        if not bases:
            raise SplitError(f'{tn}: no plan-cell replicas')
        # The inherited base row belongs to other cohorts too; only remove an explicit split row.
        TT.pop(tn, None)
        new = [dict(cells={}, leaf_binds=[], bus_drivers=[], rewired=[], replicas=[]) for _ in range(ts.n)]
        for i in range(ts.n):
            new[i]['replicas'] = [ts.pname[b][i] for b in bases]
        rec = dict(cells={}, bus_drivers={}, inherited_from=ts.t.get('landing_base_type'), replicas=list(bases))
        bdir = {b['name']: b['dir'] for b in ts.t.get('buses', [])}
        bw = {b['name']: int(b['width']) for b in ts.t.get('buses', [])}

        def owner(inst):
            cores = {h['inst']: h for h in ts.t.get('hard_cores', [])}
            if inst in cores:
                return ts.core_piece(cores[inst])
            if inst in ts.content_piece:
                return ts.content_piece[inst]
            for rx, i in ev.spec.get('contents', {}).get(tn, []):
                if re.fullmatch(rx, inst):
                    return int(i)
            return None

        def route(frm, to, stem, width, kind, done):
            ev.pc_routes.append((bases, ts, frm, to, stem, width, kind, f'plan cell {stem}', done))

        homes = {}
        for inst, c in d['cells'].items():
            home = owner(inst)
            if home is None:
                refs = {ts.bp(e[k]) for es in c.get('conns', {}).values() for e in es for k in ('bus', 'epoch') if k in e}
                refs |= {owner(e['inst']) for es in c.get('conns', {}).values() for e in es if 'inst' in e}
                refs.discard(None)
                if len(refs) != 1:
                    raise SplitError(f'{tn}: cell {inst} has no unique declared home: {sorted(refs)}')
                home = refs.pop()
            homes[inst] = home

        def width(e):
            if 'bits' in e:
                lo, hi = e['bits']
                if not (isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi):
                    raise SplitError(f'{tn}: invalid slice {e}')
                return hi - lo + 1
            if 'bus' in e:
                return bw[e['bus']]
            if 'epoch' in e or 'net' in e:
                return 1
            raise SplitError(f'{tn}: source needs explicit bits: {e}')

        def source_owner(e):
            if 'bus' in e:
                return ts.bp(e['bus'])
            if 'epoch' in e:
                return ts.bp(e['epoch'])
            if 'cell' in e:
                return homes[e['cell']]
            if 'inst' in e:
                v = owner(e['inst'])
                if v is None:
                    raise SplitError(f'{tn}: unplaced leaf {e["inst"]}')
                return v
            if 'net' in e:
                return None
            raise SplitError(f'{tn}: unknown source {e}')

        def input_entry(e, home, stem):
            source = source_owner(e)
            if source is None or source == home:
                return
            if 'epoch' in e:
                raise SplitError(f'{tn}: cross-piece epoch requires efault decomposition: {e}')
            w = width(e)
            original = copy.deepcopy(e)
            def done(sb, db, e=e, source=source, original=original, w=w):
                new[source]['bus_drivers'].append(dict(bus=sb, drivers=[copy.deepcopy(original)]))
                e.clear()
                e.update(bus=db, bits=[0, w - 1])
            route(source, home, stem, w, 'data', done)

        ev._efault_rewire = []
        for inst, c in d['cells'].items():
            if c['module'] == 'ot_dp_efault':
                ev._split_efault(ts, bases, inst, c, new, rec, route, d['cells'])
        for inst, c in d['cells'].items():
            if c['module'] == 'ot_dp_efault' or (tn, inst) in getattr(ev, '_efault_done', set()):
                continue
            home = homes[inst]
            cc = copy.deepcopy(c)
            new[home]['cells'][inst] = cc
            rec['cells'][inst] = home
            mod = iface[c['module']]
            for port, entries in cc.get('conns', {}).items():
                if port not in mod.ports:
                    raise SplitError(f'{tn}.{inst}.{port}: unknown module port')
                direction = mod.ports[port][0]
                if direction in ('input', 'in'):
                    for j, e in enumerate(entries):
                        input_entry(e, home, f'{inst}_{port}_{j}')
                elif direction in ('output', 'out'):
                    for e in entries:
                        dest = source_owner(e)
                        if dest is not None and dest != home:
                            raise SplitError(f'{tn}.{inst}.{port}: cross-piece output sink not handled: {e}')
                else:
                    raise SplitError(f'{tn}.{inst}.{port}: unsupported direction {direction}')
        for pf, inst, last in ev._efault_rewire:
            for nm, cc in new[pf]['cells'].items():
                if nm == inst or nm.startswith(inst + '_or'):
                    continue
                for es in cc['conns'].values():
                    for e in es:
                        if e.get('cell') == inst and e.get('port') == 'fault':
                            e['cell'], e['port'] = last, 'q'
        for lb in d.get('leaf_binds', []):
            home = owner(lb['inst'])
            if home is None:
                raise SplitError(f'{tn}: unplaced leaf bind {lb["inst"]}')
            row = copy.deepcopy(lb)
            new[home]['leaf_binds'].append(row)
            for j, e in enumerate(row['drivers']):
                input_entry(e, home, f'leaf_{lb["inst"]}_{lb["port"]}_{j}')
        for bd in d.get('bus_drivers', []):
            home = ts.bp(bd['bus'])
            row = copy.deepcopy(bd)
            new[home]['bus_drivers'].append(row)
            rec['bus_drivers'][bd['bus']] = home
            for j, e in enumerate(row['drivers']):
                input_entry(e, home, f'bus_{bd["bus"]}_{j}')
        for rw in d.get('rewired', []):
            home = owner(rw['sink']['inst'])
            if home is None or source_owner(rw['driver']) not in (None, home):
                raise SplitError(f'{tn}: cross-piece rewired sink not handled: {rw}')
            new[home]['rewired'].append(copy.deepcopy(rw))
        for i, nm in enumerate(ts.tnames):
            TT[nm] = new[i]
        ev.rep['plan_cells'][tn] = rec
    return out
