"""Replace the wires-only gather aggregate with its source-pinned hard children.

No library or pin is synthesized here. All child masters must already pass the
ordinary view-binding gate, and their LEFs must match the connectivity plan.
"""
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def read_plan(path, root):
    path, root = Path(path), Path(root)
    raw = path.read_bytes()
    plan = json.loads(raw)
    if plan.get('schema') != 'opentallas.s81.gather_flatten.v1' or plan.get('errors'):
        raise ValueError('gather flatten requires a valid wires-only source plan')
    if plan.get('verdict') != 'FLATTEN_PLAN OK' or plan.get('unloaded_child_outputs'):
        raise ValueError('gather flatten plan has unresolved connectivity')
    for key in ('rtl', 'layout', 'strip_plan', 'slot'):
        source = root / plan['sources'][key]
        if hashlib.sha256(source.read_bytes()).hexdigest() != plan['sources'][key + '_sha256']:
            raise ValueError('gather source-plan input changed: ' + str(source))
    plan['_sha256'] = hashlib.sha256(raw).hexdigest()
    return plan


def rewrite_buses(G, buses, parent, plan, names, *, covered=None,
                  require_complete=True, include_internal=True):
    """Expand only incident buses, retaining source bit order and real fanout.

    The plan deliberately omits unused aggregate inputs (e.g. f_vm[511:160]);
    these loads disappear. Every used output must have exactly one real driver.
    Shared child drivers are coalesced, including internal/external fanout.
    """
    untouched, nets = [], {}
    covered = set() if covered is None else covered

    def child(pin):
        inst, port = pin.rsplit('/', 1)
        if inst not in names:
            raise ValueError('gather plan names an absent child: ' + pin)
        base, lo, hi = G.pslice(port)
        return names[inst], f'{base}[{lo}:{hi}]' if lo is not None else base

    def endpoint(inst, spec, bit, width):
        base, lo, hi = G.pslice(spec)
        off = G.psrc(spec)[1] or 0
        if bit < off or bit >= off + (hi-lo+1 if lo is not None else width):
            return []
        index = (lo or 0) + bit - off
        if inst != parent:
            return [(inst, f'{base}[{index}:{index}]')]
        key = f'{base}[{index}]'
        mapping = plan['die_ports'].get(key)
        if mapping is None:
            # Scalar pins are represented without an index in the plan.
            key, mapping = (base, plan['die_ports'].get(base)) if index == 0 else (key, None)
        if mapping is None:
            return []
        covered.add(key)
        return [child(x['pin']) for x in mapping['child_pins']]

    def add(driver, sinks, cls):
        if not sinks:
            return
        rec = nets.setdefault(driver, [cls, []])
        for sink in sinks:
            if sink not in rec[1]:
                rec[1].append(sink)

    for bid, cls, width, eps in buses:
        if all(inst != parent for inst, _ in eps):
            untouched.append((bid, cls, width, eps))
            continue
        for bit in range(width):
            drivers = endpoint(*eps[0], bit, width)
            sinks = [e for ep in eps[1:] for e in endpoint(*ep, bit, width)]
            if len(drivers) != 1:
                raise ValueError(f'gather external output lacks a unique real driver: {bid}[{bit}]')
            add(drivers[0], sinks, cls)
    missing = set(plan['die_ports']) - covered
    if missing and require_complete:
        raise ValueError('gather die is missing actual incident ports: ' + ', '.join(sorted(missing)[:8]))
    for net in plan['nets'] if include_internal else ():
        add(child(net['driver']), [child(s['pin']) for s in net['sinks']], 'gather_internal')
    rewritten = [(f'gather_flat_{i}', cls, 1, [driver] + sinks)
                 for i, (driver, (cls, sinks)) in enumerate(nets.items())]
    return untouched + rewritten


def apply(G, m, path):
    plan = read_plan(path, G.ROOT)
    parent = m['hub']['gather']
    if parent.master != 'dsfd_sp_gather_c' or parent.orient != 'R0':
        raise ValueError('gather flatten requires the actual R0 dsfd_sp_gather_c source aggregate')
    if not G.HOP_FIX:
        raise ValueError('gather flatten requires --hop-fix to plan external hops from actual child pins')
    import die_port_bind as DB
    _, defines, _ = DB.load_manifest(G.ROOT / 'physical/s81_die_rtl/layer1.f')
    if not {'S81PH_GTH_DIE_CLOCKS', 'S81PH_GTH_CONTROL_STRIP'}.issubset({d.split('=')[0] for d in defines}):
        raise ValueError('gather source manifest must expose every actual leaf/relay clock entry')
    views = G.bound_views()
    missing = sorted({v['master'] for v in plan['children'].values()} - set(views))
    if missing:
        raise ValueError('gather flatten requires qualified real child views: ' + ', '.join(missing))
    names, children = {}, []
    for name, rec in plan['children'].items():
        view = views[rec['master']]
        if hashlib.sha256(view['text'].encode()).hexdigest() != rec['lef_sha256']:
            raise ValueError('gather plan LEF differs from bound real view: ' + rec['master'])
        if rec['orient'] != 'R0':
            raise ValueError('gather child orientation is not qualified: ' + name)
        x, y = rec['at_um']
        if x < 0 or y < 0 or x+view['w'] > parent.w+G.SHAVE+1e-6 or y+view['h'] > parent.h+G.SHAVE+1e-6:
            raise ValueError('gather real child escapes actual aggregate reservation: ' + name)
        names[name] = parent.name + '__' + name.replace('.', '__')
        children.append(G.Inst(names[name], rec['master'], parent.x+x, parent.y+y,
                               view['w'], view['h'], 'R0', kind='gather_leaf', region=parent.region))
    for i, a in enumerate(children):
        for b in children[i+1:]:
            if min(a.x+a.w,b.x+b.w)>max(a.x,b.x)+1e-6 and min(a.y+a.h,b.y+b.h)>max(a.y,b.y)+1e-6:
                raise ValueError('gather actual child bodies overlap: ' + a.name + ' / ' + b.name)
    covered = set()
    rewritten = rewrite_buses(G, m['buses'], parent.name, plan, names,
                              covered=covered, require_complete=False)
    m['insts'] = [it for it in m['insts'] if it.name != parent.name] + children
    m['buses'] = rewritten
    m['variant']['gather_flatten'] = dict(plan_sha256=plan['_sha256'], children=len(children),
        clock_entries=plan['counts']['clock_entries'], parent_logic=0,
        status='REAL_CHILD_VIEWS_BOUND; external timing/calendar/geometry qualification still required')
    m['gather_flatten_parent'] = dict(name=parent.name, at_um=[parent.x,parent.y],
                                    outline_um=[parent.w,parent.h], source=plan['sources'])
    # The ordinary clock builder still collects the actual parent's expanded
    # clock/reset ports, then finish() replaces those wire-only endpoints too.
    m['_gather_flatten_work'] = (plan, names, covered)


def finish(G, m):
    plan, names, covered = m.pop('_gather_flatten_work')
    m['buses'] = rewrite_buses(G, m['buses'], m['hub']['gather'].name, plan, names,
                               covered=covered, include_internal=False)
    if any(inst == m['hub']['gather'].name for _,_,_,eps in m['buses'] for inst,_ in eps):
        raise ValueError('gather aggregate endpoint survived flattening')
