#!/usr/bin/env python3
"""Qwen compute die -> opentallas.die_relay_stages.v1 (ROOT RELAY-SCHEMA 10-16; additive, no placement change).

    relay_stages_export.py --relay-dump OT_RELAY_DUMP.json --plan-id ID [--commit SHA] --out relay_stages.json
    from qwen_split import relay_stages_export as X; X.export_model(m, plan_id)       (generator hook, see below)

The relay planner (tools/qwen_rom_fulldie_b3r2.py _relays) replaces a long bus bid by relay frames
(kind 'relay', ports a -> b, paired a_d -> b_d with the ready b_r -> a_r) and records r21_stage_of[bid] = n + 1
(EDGES).  This schema counts RELAY FLOPS: stages = n = r21_stage_of - 1.
  * model path: walks m['insts'] / m['buses'] after the relay plan (exact: what the netlist contains);
  * dump path: the OT_RELAY_DUMP plans [{bid, cl, bits, eps, n}] (eps = the original endpoints, n = frames).
RELAY_SKIP classes (clock/reset trees, tap, CDC / PHY / FDI boundaries: elastic, not static on-die buses) are left out.
Generator hook: tools/qwen_rom_fulldie_b3r2.py writes $OT_DIE_RELAY_STAGES_OUT after the relay plan when that env is set.
"""
import argparse, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_relay_stages as DRS  # noqa: E402

RELAY_SKIP = ('clock_trunk', 'reset', 'tap', 'kv_land', 'cdc_core', 'hbm_cdc', 'phy_dfi', 'coll_fdi', 'clock', 'constant')
THRU = {'a': 'b', 'a_d': 'b_d', 'b_r': 'a_r'}
SLICE = re.compile(r'^(\w+)\[\d+(?::\d+)?\]$')
CLOCK_PERIOD_PS = 833.333          # stream_1p2


def port_base(p):
    m = SLICE.match(p)
    return m.group(1) if m else p


def _make(rec, problems, plan_id, commit, sources, kind, reach=None, design='qwen_compute', skip_cls=RELAY_SKIP, **extra):
    if reach is None:
        import die_reach
        reach = die_reach.reach_um(design)
    return DRS.make_doc(design, dict(id=plan_id, commit=commit, generator='tools/qwen_split/relay_stages_export.py',
                                     sources=list(sources), kind=kind),
                        CLOCK_PERIOD_PS, reach, rec, coverage='complete', reach_source='results/arch/die_reach_1016.json',
                        skipped_classes=sorted(skip_cls), problems=problems[:200], problem_count=len(problems), **extra)


def export_model(m, plan_id, commit=None, sources=(), reach=None, design='qwen_compute', skip_cls=RELAY_SKIP):
    insts = {it.name: dict(master=it.master, kind=it.kind, domain=getattr(it, 'domain', None)) for it in m['insts']}
    rec, problems = DRS.trace_model(insts, m['buses'], lambda n: insts.get(n, {}).get('kind') == 'relay',
                                    lambda _i, p: THRU.get(p), port_base, skip_cls=tuple(skip_cls),
                                    relay_control=lambda _i, p: p in ('ck', 'rs', 'fck_a'))
    return _make(rec, problems, plan_id, commit, sources, 'generator model (after the relay plan)', reach, design, skip_cls,
                 relay_instances=sum(1 for v in insts.values() if v['kind'] == 'relay'))


def export_dump(dump, plan_id, commit=None, reach=None):
    d = json.loads(Path(dump).read_text())
    rec, problems = [], []
    seen = set()
    for p in d['plans']:
        if p['cl'] in RELAY_SKIP:
            continue
        eps = p['eps']
        if len(eps) != 2:
            problems.append(f"{p['bid']}: {len(eps)} endpoints (p2p expected)"); continue
        (si, sp), (di, dp) = eps
        bid = DRS.bus_id(si, port_base(sp), di, port_base(dp))
        if bid in seen:
            problems.append(f'{bid}: duplicate pin pair (bid {p["bid"]})'); continue
        seen.add(bid)
        rec.append(dict(id=bid, src=dict(inst=si, port=port_base(sp)), dst=dict(inst=di, port=port_base(dp)),
                        width=int(p['bits']), stages=int(p['n']), domain=None, eq_age_group=None, bid=p['bid']))
    return _make(rec, problems, plan_id, commit, [str(dump)], 'OT_RELAY_DUMP plans', reach)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--relay-dump', required=True); ap.add_argument('--plan-id', required=True)
    ap.add_argument('--commit'); ap.add_argument('--reach', type=float); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    doc = export_dump(a.relay_dump, a.plan_id, a.commit, a.reach)
    DRS.write(a.out, doc)
    print(f"{a.out}: {doc['bus_count']} buses, max stages {max((b['stages'] for b in doc['buses']), default=0)}, "
          f"problems {doc['problem_count']}, {doc['digest']}")


if __name__ == '__main__':
    main()
