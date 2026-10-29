#!/usr/bin/env python3
"""TOK-HBM-4 (opt-in, read-only): bound-latency file for tools/hbm_next/four_role_calendar.py from a die plan.

Composes the FUSED tree legs from plan station registers only (legs_exclude_tree_nodes: true; tree-node edges come from
the measured tnode segments), one rule per leg, every number with provenance:
  down_r = root internal 'bus:n4x_dn_<r>_o' regs + lane N4D_<r> cycles + hub 'bus:n4x_dn_i' regs + hub mu_tree down regs
  up_r   = hub mu_tree up regs + hub 'bus:n4x_up_o' regs + lane N4U_<r> cycles + root 'bus:n4x_up_<r>_i' regs
  hub mu_tree regs follow the critical (max down+up) leaf path below u_mu_fused_n4 (same walk as hub_tree_pads()).
Legs the plan does not carry (per-role delivered resets, host leaf -> provider -> root ingress, root -> provider status)
are left out and listed in 'missing' (the calendar then fails closed); a plan event that adds them as reset/latency
tables is read from plan['reset']['delivery'] / plan['latency']['fused_legs'] {leg: {cycles, source}} if present.
Opt-in --side <side.json> (TOK-HBM-5): DIE-HBM plan side data (schema opentallas.hbm.c25b_side.v1) for the same plan
(plan_sha256 must match, else fail closed): reset_legs.<k>.release_cycle (int) and provider_legs.<k>.cycles (int) fill
legs the plan itself does not carry; plan tables win; a side leg without an int value stays missing.
Usage: bound_from_plan.py <die_plan.json> <plan_commit_40hex|''> <rtl_constants.json> <out.json> [--side <side.json>]
"""
import hashlib, json, sys

ROLES = {'NW': 'q_hub_nw', 'NE': 'q_hub_ne'}
OTHER = ['reset_SW', 'reset_SE', 'reset_NW', 'reset_NE', 'reset_root', 'host_to_provider', 'provider_to_root',
         'root_to_provider']


def tree_path(stations, top='u_mu_fused_n4'):
    up, dn, kids = {}, {}, {}
    for s in stations:
        if not s['conn'].startswith('mu_tree:'): continue
        a, b = s['conn'].split(':', 1)[1].split('|'); inst, port = a.rsplit('.', 1); n = len(s['regs_um'])
        if port == 'uo': up[(inst, b)] = n
        else: dn[(b, inst)] = n; kids.setdefault(inst, {})[port] = b

    def walk(x):                                   # -> (down, up) on the max round-trip path
        if x not in kids: return 0, 0
        best = None
        for p in ('da', 'db'):
            c = kids[x][p]; d, u = walk(c); d += dn[(c, x)]; u += up[(c, x)]
            if best is None or d + u > sum(best): best = (d, u)
        return best
    return walk(top), len(up) + len(dn)


def _int(x): return isinstance(x, int) and not isinstance(x, bool)


def clock_qualified_cycles(leg):
    """Opt-in physical clock term: unknown CA cycles keep the leg incomplete."""
    if not isinstance(leg, dict) or not _int(leg.get('cycles')):
        return None
    cycles = leg['cycles']
    if leg.get('clock_extra_required'):
        extra = leg.get('clock_extra_cycles')
        if extra is None:
            return None
        if not _int(extra) or extra < 0:
            raise SystemExit('FAIL_CLOSED clock_extra_cycles must be a known nonnegative integer')
        cycles += extra
    return cycles


def side_legs(side, side_name, plan_sha):
    if side.get('plan_sha256') != plan_sha:
        raise SystemExit(f"FAIL_CLOSED side {side_name} plan_sha256 {side.get('plan_sha256')} != plan {plan_sha}")
    out, tag = {}, f'side {side_name} (plan {plan_sha[:8]})'
    for k, v in side.get('reset_legs', {}).items():
        if _int(v.get('release_cycle')):
            out[k] = dict(cycles=v['release_cycle'], source=f"{tag} reset_legs.{k}.release_cycle; {v.get('release_basis', '')}")
    for k, v in side.get('provider_legs', {}).items():
        cycles = clock_qualified_cycles(v)
        if cycles is not None:
            clock = f" clock_extra={v['clock_extra_cycles']}" if v.get('clock_extra_required') else ''
            out[k] = dict(cycles=cycles, source=f"{tag} provider_legs.{k} {v.get('form', '')} {v.get('status', '')}{clock}".strip())
    return out


def build(plan, plan_commit, rtl, side_extra=None):
    st = lambda pt: plan['partition_types'][pt]['internal_stations']
    regs = lambda pt, conn: [len(s['regs_um']) for s in st(pt) if s['conn'] == conn]
    lat = plan['latency']['lanes']; legs, missing = {}, []
    for r, hub in ROLES.items():
        (td, tu), nlegs = tree_path(st(hub))
        parts = {'dn': (regs('root', f'bus:n4x_dn_{r.lower()}_o'), lat.get(f'N4D_{r}', {}).get('cycles'), regs(hub, 'bus:n4x_dn_i')),
                 'up': (regs('root', f'bus:n4x_up_{r.lower()}_i'), lat.get(f'N4U_{r}', {}).get('cycles'), regs(hub, 'bus:n4x_up_o'))}
        for d, (rootr, lane, hubr) in parts.items():
            leg = ('down_' if d == 'dn' else 'up_') + r
            if len(rootr) != 1 or len(hubr) != 1 or not isinstance(lane, int):
                missing.append(f'{leg}: root/lane/hub n4x station not unique in plan (root {rootr} lane {lane} hub {hubr})'); continue
            tree = td if d == 'dn' else tu
            legs[leg] = dict(cycles=rootr[0] + lane + hubr[0] + tree,
                             source=f'plan root bus:n4x_{d}_{r.lower()} {rootr[0]} + lane N4{"D" if d == "dn" else "U"}_{r} {lane} + '
                                    f'{hub} bus:n4x_{d}_{"i" if d == "dn" else "o"} {hubr[0]} + {hub} mu_tree {d} {tree} '
                                    f'(critical leaf path, {nlegs} legs; tree-node edges excluded)')
    extra = dict(side_extra or {})
    extra.update(plan.get('reset', {}).get('delivery', {})); extra.update(plan.get('latency', {}).get('fused_legs', {}))
    for k in OTHER:
        v = extra.get(k)
        cycles = clock_qualified_cycles(v)
        if cycles is not None and v.get('source'): legs[k] = dict(v, cycles=cycles)
        else: missing.append(f"{k}: not in plan{' or side' if side_extra is not None else ''} (needs plan reset.delivery / latency.fused_legs)")
    return legs, missing


def main(argv):
    argv = list(argv); sidef = None
    if '--side' in argv:
        i = argv.index('--side'); sidef = argv[i + 1]; del argv[i:i + 2]
    pf, commit, rtlf, out = argv[1:5]
    raw = open(pf, 'rb').read(); plan = json.loads(raw); rtl = json.load(open(rtlf)); psha = hashlib.sha256(raw).hexdigest()
    sx = side_legs(json.load(open(sidef)), sidef, psha) if sidef else None
    legs, missing = build(plan, commit, rtl, sx)
    rep = dict(source_plan_commit=commit, plan_sha256=psha, legs_exclude_tree_nodes=True, side=sidef,
               legs=legs, rtl=rtl, missing=missing,
               note='GENERATED by tools/hbm_next/bound_from_plan.py (TOK-HBM-4); legs = plan station/lane registers only')
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps({k: v['cycles'] for k, v in legs.items()}), 'missing', len(missing))
    return 0 if not missing else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
