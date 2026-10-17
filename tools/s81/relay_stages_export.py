#!/usr/bin/env python3
"""S81 die -> opentallas.die_relay_stages.v1 (ROOT RELAY-SCHEMA 10-16; additive, no placement/routing change).

    relay_stages_export.py --plan-dump WORK/plan.json.gz --plan-id ID [--commit SHA] --out relay_stages.json
    relay_stages_export.py --options GEN.opts --plan-id ID --out relay_stages.json        (rebuilds the model, as
                                                                                          tools/s81/hub_stage_count.py)
    from s81 import relay_stages_export as X; X.export_model(m, plan_id)                   (generator / dump hook)

Every die bus pin pair  origin (inst, port) -> terminal (inst, port)  of the generated die model (m['insts'],
m['buses']), walked through every registered relay / station kind of the die (dsfd_rly i->o, hstn di->dq, stn
di<j>->do<j> and fi<j>->fo<j>, sstn xai/xbi/cci/si -> xa/xb/cc/so, rstg / pqstn i->o): one stage per relay instance,
the same one-cycle-per-relay rule as tools/s81/hub_stage_count.py (whose hub pin-to-pin stages are a subset of this
table).  Clock / reset buses are not data.  plan.json.gz is the c5diag_v15_dump.py plan dump (insts + hops of every
bus with pins on both ends); it carries no clock domain (domain null), the model path carries Inst.domain.
"""
import argparse, gzip, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_relay_stages as DRS  # noqa: E402

RELAY_KINDS = ('rly', 'hstn', 'stn', 'sstn', 'rstg', 'pqstn')
FIXED = {'i': 'o', 'di': 'dq', 'xai': 'xa', 'xbi': 'xb', 'cci': 'cc', 'si': 'so'}
LANE = re.compile(r'^(di|fi)(\d+)$')
SLICE = re.compile(r'^(\w+)\[\d+(?::\d+)?\]$')
CLOCK_PERIOD_PS = 833.333          # stream_1p2 (1.2 GHz)


CONTROL = re.compile(r'^((e|c)\d+|nf)$')    # sstn enable / capture selects (sequencer -> station): terminals


def port_base(p):
    m = SLICE.match(p)
    return m.group(1) if m else p


def thru(_inst, p):
    if p in FIXED:
        return FIXED[p]
    m = LANE.match(p)
    return ('do' if m.group(1) == 'di' else 'fo') + m.group(2) if m else None


def _doc(insts, buses, plan_id, commit, sources, reach=None, kind=''):
    rec, problems = DRS.trace_model(insts, buses, lambda n: insts.get(n, {}).get('kind') in RELAY_KINDS, thru, port_base,
                                    skip_cls=('clock', 'clock_trunk', 'reset', 'constant', 'lkck', 'col_clock', 'col_reset', 'fclk'),
                                    relay_control=lambda _i, p: bool(CONTROL.match(p)))
    if reach is None:
        import die_reach
        reach = die_reach.reach_um('s81')
    return DRS.make_doc('s81', dict(id=plan_id, commit=commit, generator='tools/s81/relay_stages_export.py',
                                    sources=list(sources), kind=kind),
                        CLOCK_PERIOD_PS, reach, rec, coverage='complete', reach_source='results/arch/die_reach_1016.json',
                        problems=problems[:200], problem_count=len(problems),
                        relay_instances=sum(1 for v in insts.values() if v.get('kind') in RELAY_KINDS))


def export_model(m, plan_id, commit=None, sources=(), reach=None):
    insts = {it.name: dict(master=it.master, kind=it.kind, domain=getattr(it, 'domain', None)) for it in m['insts']}
    return _doc(insts, m['buses'], plan_id, commit, sources, reach, 'generator model')


def export_dump(plan_dump, plan_id, commit=None, reach=None):
    d = json.loads(gzip.open(plan_dump).read() if str(plan_dump).endswith('.gz') else Path(plan_dump).read_text())
    insts = {r[0]: dict(master=r[1], kind=r[7], domain=None) for r in d['insts']}
    buses = {}
    for h in d['hops']:            # [bus, cls, bits, drv, dport, load, lport, ...]: one row per (driver, load)
        b = buses.setdefault(h[0], [h[0], h[1], h[2], [(h[3], h[4])]])
        b[3].append((h[5], h[6]))
    return _doc(insts, [tuple(b) for b in buses.values()], plan_id, commit, [str(plan_dump)], reach, 'c5diag plan dump')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--plan-dump'); g.add_argument('--options', type=Path)
    ap.add_argument('--plan-id', required=True); ap.add_argument('--commit'); ap.add_argument('--reach', type=float)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.plan_dump:
        doc = export_dump(a.plan_dump, a.plan_id, a.commit, a.reach)
    else:
        import dsrom_s81_fulldie as F
        args = F.die_options(argparse.ArgumentParser()).parse_args(a.options.read_text().split())
        F.apply_options(args)
        m = F.build()
        F.finalize_r8(m)
        doc = export_model(m, a.plan_id, a.commit, [str(a.options)], a.reach)
    DRS.write(a.out, doc)
    print(f"{a.out}: {doc['bus_count']} buses, max stages {max((b['stages'] for b in doc['buses']), default=0)}, "
          f"relayed {sum(1 for b in doc['buses'] if b['stages'])}, problems {doc['problem_count']}, {doc['digest']}")


if __name__ == '__main__':
    main()
