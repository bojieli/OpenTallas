#!/usr/bin/env python3
"""Refresh adopted Markov clock references and audit placed, connected per-bit arcs.

No routes or coordinates are changed. Legacy ctl is kept as historical evidence
until its static successor publishes a routed view. The TT wire estimate is a
placement screen, not SS/FF die signoff or a proof of obstacle-free routing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81'))
from hier_contract.pinreg_audit import parse_lib, clock_refs, pin_metrics
from v19_pins_1014 import lef_bits

ASSIGNED = Path('physical/s81_die_pins/v19_markov')
RTL = Path('rtl/experimental/dsrom_markov_20261008/ot_s81_markov_k256_native.sv')
OUT = Path('results/arch/markov_clock_refresh_1015/audit.json')


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(write=False):
    layout_path = ROOT / ASSIGNED / 'layout.json'
    layout = json.loads(layout_path.read_text())
    names = ['mul', 'ctl', 'pair', 'fold', 'join'] + [f'chunk{k}' for k in range(8)]
    masters, views, references, mutations = {}, {}, {}, []
    for name in names:
        top = f'ot_s81_markov_{name}_native'
        rec_path = ROOT / ASSIGNED / f'{top}.json'
        rec = json.loads(rec_path.read_text())
        lef = Path(rec['adopted_closed_view'])
        view = lef.parent
        ins_path = view / 'insertion.json'
        ins = json.loads((ROOT / ins_path).read_text())
        wh, pins = lef_bits(str(lef))
        assert list(wh) == rec['outline_um'], (top, 'outline changed')
        current_ports = {p: dict(bits=len(bits), uniform=False, per_bit=[
            [b[0], b[1], b[2] if b[0] in 'NS' else b[3], .192]
            for _, b in sorted(bits.items())]) for p, bits in pins.items()}
        # pc2 removed chunk0's tied-zero sum port; every retained physical pin must match.
        removed = sorted(set(rec['ports']) - set(current_ports))
        assert removed == (['sum'] if name == 'chunk0' and 'sum' in rec['ports'] else []), (top, removed)
        assert not set(current_ports) - set(rec['ports']), (top, 'added ports')
        assert all(rec['ports'][p] == current_ports[p] for p in current_ports), (top, 'pin moved')
        refs = {c: ins[c]['boundary']['mean'] for c in ('ss', 'tt', 'ff')}
        references[name] = refs
        rec['ports'] = current_ports
        rec['phi_R_ps'] = refs
        rec['clock_reference'] = dict(source=str(ins_path), sha256=sha(ins_path),
            basis='measured boundary mean; deliver clock at phi - R, per corner',
            job=ins['base'].split('/closure-loop/')[1].split('/')[0],
            status='legacy controller retained; static successor has no routed view' if name == 'ctl' else 'current pc2 routed arithmetic view')
        metrics = {}
        hashes = {str(p): sha(p) for p in (lef, ins_path)}
        for c in ('tt', 'ff'):
            lib_path = view / f'{top}_{c}.lib'
            lib = parse_lib(ROOT / lib_path)
            metrics[c] = pin_metrics(lib, clock_refs(lib, ins, c))
            hashes[str(lib_path)] = sha(lib_path)
        views[name] = dict(clock_reference=rec['clock_reference'], phi_R_ps=refs,
            boundary_spread_ps={c: round(ins[c]['boundary']['max'] - ins[c]['boundary']['min'], 4) for c in refs},
            geometry_unchanged=True, obsolete_ports_removed=['sum'] if name == 'chunk0' else [], source_sha256=hashes)
        masters[name] = dict(pins=pins, metrics=metrics)
        mutations.append((rec_path, rec))

    def endpoint(inst, port, bit=None):
        name, x, y, _, _ = layout['subslots'][inst]
        pin = port if bit is None else f'{port}[{bit}]'
        p = masters[name]['pins'][port][bit or 0]
        return name, pin, (x + p[2], y + p[3])

    hops = []
    def bus(src, sport, dst, dport, width=1, soff=0, doff=0):
        sm = layout['subslots'][src][0]; dm = layout['subslots'][dst][0]
        for i in range(width):
            sb = i + soff if len(masters[sm]['pins'][sport]) > 1 else None
            db = i + doff if len(masters[dm]['pins'][dport]) > 1 else None
            sn, sp, xy = endpoint(src, sport, sb)
            dn, dp, ab = endpoint(dst, dport, db)
            length = abs(xy[0]-ab[0]) + abs(xy[1]-ab[1])
            o = masters[sn]['metrics']['tt'][sp]['out']
            s = masters[dn]['metrics']['tt'][dp]['inp']
            l = masters[sn]['metrics']['ff'][sp]['lmin']
            h = masters[dn]['metrics']['ff'][dp]['hold']
            assert o is not None and s is not None and l is not None and h is not None, (src, sp, dst, dp, 'missing arc')
            skew = 90 if max(references[sn]['tt'], references[dn]['tt']) <= 300 else 150
            budget = 1000/1.2 - 60 - skew
            # Use each bit's own launch and capture, not a declared reference or bus centroid.
            hops.append(dict(source=f'{src}.{sp}', sink=f'{dst}.{dp}', length_um=round(length, 4),
                launch_tt_ps=round(o, 4), capture_tt_ps=round(s, 4),
                skew_ps=skew, setup_budget_ps=round(budget, 4),
                reach_tt_um=round((budget-o-s)/.76, 4),
                setup_margin_tt_ps=round(budget-o-s-.76*length, 4),
                ff_launch_minus_hold_ps=round(l-h, 4),
                legacy_controller=(sn == 'ctl' or dn == 'ctl')))

    # Exact internal connectivity of the pinned k256 RTL: every data/valid/fault bit.
    # Clock and asynchronous reset distribution require their own die clock/reset proof.
    for lane in range(16):
        mul = f'g_mul[{lane}].u_mul'; c, k = divmod(lane, 8); chunk = f'u_c{c}s{k}'
        bus('u_ctl', 'mul_weight', mul, 'a', 16, 16*lane)
        bus('u_ctl', 'mul_embed', mul, 'b', 16, 16*lane)
        bus('u_ctl', 'mul_fire', mul, 'v')
        bus(mul, 'y', chunk, 'p', 32)
        bus(mul, 'fault', 'u_ctl', 'pf', doff=lane)
        bus(chunk, 'bad', 'u_ctl', 'bad_chunk', doff=lane)
    for c in range(2):
        bus('u_ctl', 'pv_last', f'u_c{c}s0', 'vin')
        for k in range(7):
            bus(f'u_c{c}s{k}', 'y', f'u_c{c}s{k+1}', 'sum', 32)
            bus(f'u_c{c}s{k}', 'vout', f'u_c{c}s{k+1}', 'vin')
    bus('u_c0s7', 'y', 'u_pair', 'a', 32)
    bus('u_c1s7', 'y', 'u_pair', 'b', 32)
    bus('u_c0s7', 'vout', 'u_pair', 'vin')
    tree = ['u_pair'] + [f'g_tree[{k}].u_fold' for k in range(4)] + ['u_join']
    for src, dst in zip(tree, tree[1:]):
        bus(src, 'y', dst, 'x', 32)
        bus(src, 'vout', dst, 'vin')
    for k, src in enumerate(tree[:-1]):
        bus(src, 'bad', 'u_ctl', 'bad_tree', doff=k)
    bus('u_ctl', 'head', 'u_join', 'head', 32)
    bus('u_join', 'y', 'u_ctl', 'jd', 32)
    bus('u_join', 'vout', 'u_ctl', 'jv')
    bus('u_join', 'err', 'u_ctl', 'je', 2)

    layout['phi_R_tt_ps'] = {inst: references[slot[0]]['tt'] for inst, slot in layout['subslots'].items()}
    layout['phi_R_ps'] = {c: {inst: references[slot[0]][c] for inst, slot in layout['subslots'].items()} for c in ('ss', 'tt', 'ff')}
    layout['clock_reference_audit'] = str(OUT)
    layout['clock_reference_rule'] = 'Measured routed insertion.json boundary mean only; clock arrival phi - R per leaf/corner; legacy ctl pending static routed replacement.'
    mutations.append((layout_path, layout))
    arithmetic = [h for h in hops if not h['legacy_controller']]
    result = dict(schema='opentallas.s81.markov.clock_refresh.v1',
        scope='Current arithmetic pc2 views and retained legacy ctl, unchanged placed cluster; TT per-bit Manhattan wire screen only, not die signoff. Static ctl successor is not substituted before routed publication.',
        rtl=str(RTL), rtl_sha256=sha(RTL), views=views,
        placement=dict(outline_um=layout['outline_um'], subslots=layout['subslots'], coordinates_unchanged=True),
        policy=dict(period_ps=1000/1.2, setup_uncertainty_ps=60, same_level_skew_ps=90,
            across_level_skew_ps=150, tt_wire_ps_per_um=.76, physical_hop_limit_um=500,
            hold='FF launch-minus-capture reported per bit; wire minimum-delay/route and hold skew proof remain required',
            routing='Manhattan pin centres are lower bounds; obstacles, channel capacity and detours not certified'),
        summary=dict(hop_bits=len(hops), arithmetic_only_bits=len(arithmetic),
            max_length_um=max(h['length_um'] for h in hops),
            length_over_500_bits=sum(h['length_um']>500 for h in hops),
            tt_setup_negative_bits=sum(h['setup_margin_tt_ps']<0 for h in hops),
            arithmetic_tt_setup_negative_bits=sum(h['setup_margin_tt_ps']<0 for h in arithmetic),
            arithmetic_min_tt_setup_margin_ps=min(h['setup_margin_tt_ps'] for h in arithmetic),
            arithmetic_min_ff_launch_minus_hold_ps=min(h['ff_launch_minus_hold_ps'] for h in arithmetic),
            arithmetic_ff_launch_minus_hold_below_100_bits=sum(h['ff_launch_minus_hold_ps'] < 100 for h in arithmetic),
            legacy_controller_bits=len(hops)-len(arithmetic)),
        hops=hops)
    if write:
        for path, content in mutations:
            path.write_text(json.dumps(content, indent=1)+'\n')
        (ROOT / OUT).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / OUT).write_text(json.dumps(result, indent=1)+'\n')
    print(json.dumps(result['summary'], indent=1))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    run(parser.parse_args().write)
