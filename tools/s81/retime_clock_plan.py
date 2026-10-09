#!/usr/bin/env python3
"""Retrospective STA kit with measured clock-plan deltas; preserve original evidence.

The same die netlist, views, SPEF, block insertion offsets, uncertainties and
clock periods are retained. This diagnoses timing under a successor clock plan;
it does not implement the die clock tree or qualify another die configuration.
"""
import argparse
from collections import defaultdict
import gzip
import json
import os
from pathlib import Path
import re


def read_json(p):
    return json.loads((gzip.open(p, 'rt') if p.suffix == '.gz' else p.open()).read())


def prepare(a):
    old, new = read_json(a.old_plan), read_json(a.new_plan)
    if old['die'] != new['die'] or old['source_commit'] != new['source_commit']:
        raise ValueError('clock plans must describe the same source-pinned die')
    if old['sink_insertion'].keys() != new['sink_insertion'].keys():
        raise ValueError('clock-plan sink inventories differ')
    if a.out.exists():
        raise FileExistsError(f'refusing to overwrite {a.out}')
    delta, by_inst = {}, defaultdict(list)
    for pin, v in old['sink_insertion'].items():
        d = [new['sink_insertion'][pin][i] - v[i] for i in range(2)]
        delta[pin] = d + [sum(d) / 2]
        by_inst[pin.split('/')[0]].append(delta[pin])

    def lookup(pin):
        pin = pin.removesuffix('[0]')
        if pin in delta:
            return delta[pin]
        values = by_inst[pin.split('/')[0]]
        if not values or any(v != values[0] for v in values[1:]):
            raise ValueError(f'ambiguous clock alias: {pin}')
        return values[0]

    # Prepare text before creating output: an unbound alias is a terminal error.
    texts, count = {}, {}
    for ci, c in enumerate(('ss', 'ff', 'tt')):
        lat = (a.kit / f'latency_{c}.tcl').read_text()
        n = [0]
        def update(m):
            n[0] += 1
            return f'set_clock_latency {float(m[1]) + lookup(m[2])[ci]:.1f} [get_pins -quiet {{{m[3]}}}]'
        texts[f'latency_{c}.tcl'] = re.sub(
            r'set_clock_latency ([-\d.]+) \[get_pins -quiet \{(([^} ]+)[^}]*)\}\]',
            # group 2 is the whole pin list, group 3 is its first pin.
            lambda m: update((None, m[1], m[3], m[2])), lat)
        count[c] = n[0]
        if not n[0]:
            raise ValueError(f'no clock pin latencies in {c}')
        sta = (a.kit / f'sta_{c}.tcl').read_text()
        sta = re.sub(r'set_clock_latency -source ([-\d.]+) \[get_clocks ck_col_(\d+)\]',
                     lambda m: f'set_clock_latency -source {float(m[1]) + lookup("cf" + m[2] + "/ck")[ci]:.1f} '
                               f'[get_clocks ck_col_{m[2]}]', sta)
        sta = sta.replace('/kit/die.spef', '/run/die_grt.spef').replace('> /kit/', '> /run/')
        texts[f'sta_{c}.tcl'] = sta
    (a.out / 'kit').mkdir(parents=True)
    (a.out / 'sta').mkdir()
    for p in a.kit.iterdir():
        if p.is_file() and p.name not in texts:
            os.link(p, a.out / 'kit' / p.name)
    for name, text in texts.items():
        dest = a.out / ('sta' if name.startswith('sta_') else 'kit') / name
        dest.write_text(text)
    os.link(a.grt / 'die_grt.spef', a.out / 'sta' / 'die_grt.spef')
    (a.out / 'manifest.json').write_text(json.dumps(dict(
        scope=__doc__, original_kit=str(a.kit), original_grt=str(a.grt),
        old_clock_plan=str(a.old_plan), new_clock_plan=str(a.new_plan),
        source_commit=old['source_commit'], latency_pins_updated=count,
        alias_policy='exact clock pin, or all clock pins of instance have identical delta',
        adoption='diagnostic only; die clock implementation and head631 remain unqualified'), indent=2) + '\n')
    print(json.dumps(dict(out=str(a.out), pins=count)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    for k in ('old-plan', 'new-plan', 'kit', 'grt', 'out'):
        ap.add_argument('--' + k, required=True, type=Path)
    prepare(ap.parse_args())
