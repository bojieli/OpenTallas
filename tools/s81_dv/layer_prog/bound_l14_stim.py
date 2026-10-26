#!/usr/bin/env python3
"""Bound-port stimulus / expectation spec of a strict-bound S81 carve (TOK-DS 10-26, L14 path carve).

Inputs (all read-only):
  --bound DIR    strict-bind out/ (bind_report.json, bind_latency.json, bind_names.json, rtl/*_bound_top.sv + partitions)
  --carve JSON   carve record (schema opentallas.tok_qw.bound_carve.v1: seeds, inputs, outputs, internal)
  --prog DIR     one compiled layer programme (dv_layer_compile.py out: schedule.json, lowering.json, manifest.json, prog/)
  [--t0 N]       bench cycle of compiled layer cycle 0 (from a measured boot/KS replay). Without it no bench event
                 files are written: the layer->bench offset is not derivable from the programme alone.
  [--ev-dir D]   with --t0: write D/stim/<port>.ev and D/exp/<port>.ev ("<cycle> <hex word incl. epoch>", carve_tb.py)

Output JSON (schema opentallas.tokds.bound_carve_stim.v1):
  sources        sha256 of the bound top, carve, schedule and manifest (stale inputs are detectable)
  price          the compiled schedule's priced layer (schedule.json price: dv_layer_price facts) + scheduler span
  timebase       cycles are compiled LAYER cycles (layer 0 = KS + 5, dv_cut_replay.host_boot_words); bench = layer + t0
  inputs[port]   class CLOCK | RESET | LOOPBACK_FT | DERIVABLE | IDLE_BY_SCHEDULE | MISSING, with lane, src/dst
                 partitions, original producer pins (bind_latency source_bits), hop chain outside the carve and its
                 station count, and for DERIVABLE the words [{edge, port_edge, word_hex}] (port_edge = the edge after
                 which the carve input port carries the word: producer pin edge + source out flop + outside FT stations)
                 MISSING always names why (no producer value is invented; masks/plan-only events are not values)
  outputs[port]  class CLOCK_RESET | DERIVABLE (expected words from compiled producer-pin events) | UNSPECIFIED
  prog_load_map  per compiled programme file: delivery mechanism, original consumer instance(s) (compiler names)
                 -> bound partition.leaf (bind_names.json) -> partition module, in_carve
  counts         per class

Matching rule (exact only): a compiled boundary event is a producer value for a lane bit only when the event's
(inst, port) equals the original producer pin (path, port) of that bit, or the event is a dir-in event at the
destination pin of a compiled link whose source pin is that producer pin (source edge = landed - link age_edges).
Event words must cover every bit of the lane (mask all ones on those bits). Anything else is MISSING.
IDLE_BY_SCHEDULE is claimed only when every producer instance is one the programme lowers completely (every op whose
insts name it is LOWERED) and the programme has no event on it. A port the compiler does not model is MISSING.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

OFFDIE = ('phy_', 'lk_')          # modelled off-chip PHY / die-link partitions (owner: only these may be modelled)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Bound:
    def __init__(self, d):
        d = Path(d)
        rep = json.loads((d / 'bind_report.json').read_text())
        if rep.get('n_errors') or rep.get('errors') or rep.get('type_splits'):
            raise ValueError('bound carve stimulus requires a strict bind with 0 errors and no type splits')
        if (rep.get('proof') or {}).get('tied'):
            raise ValueError('bound carve stimulus requires 0 tied bits')
        tops = sorted((d / 'rtl').glob('*_bound_top.sv'))
        if len(tops) != 1:
            raise ValueError('need exactly one emitted bound top')
        self.dir, self.top = d, tops[0]
        self.buses = {b['lane']: b for b in json.loads((d / 'bind_latency.json').read_text())['buses']}
        names = json.loads((d / 'bind_names.json').read_text())
        self.by_orig = {}
        for leaf, orig in names.items():
            self.by_orig.setdefault(orig, []).append(leaf)
        text = self.top.read_text()
        self.module = {}
        for m in re.finditer(r'^\s*(s81p_\S+)\s+(?:#\(.*\)\s+)?(\S+)\s+\($', text, re.M):
            self.module[m.group(2)] = m.group(1)
        self.nets = {}
        for m in re.finditer(r'^\s*wire\s+\[(\d+):0\]\s+(\S+);\s*//\s*lane\s+(\S+)', text, re.M):
            self.nets.setdefault(m.group(3), []).append(m.group(2))
        self._st = {}

    def parse_net(self, net):
        """x_<drv>_<port>_<rcv> with drv/rcv bound instance names (longest unique split)."""
        body = net[2:]
        for drv in sorted(self.module, key=len, reverse=True):
            if body.startswith(drv + '_'):
                rest = body[len(drv) + 1:]
                for rcv in sorted(self.module, key=len, reverse=True):
                    if rest.endswith('_' + rcv):
                        return drv, rest[:-len(rcv) - 1], rcv
        return None

    def stations(self, inst, port):
        """ot_dp_st stations on an ft output (port comment 'ft ftN: K station(s)'); source out = u_bout flop."""
        mod = self.module[inst]
        if mod not in self._st:
            t = (self.dir / 'rtl' / (mod + '.sv')).read_text()
            st = {m.group(1): int(m.group(2)) for m in re.finditer(r'output\s+wire\s+\[\d+:0\]\s+(\w+),?\s*//\s*ft \w+: (\d+) station', t)}
            st.update({m.group(1): 1 for m in re.finditer(r'ot_dp_st\s+#\(\.W\(\d+\)\)\s+u_bout_(\w+)\s', t)})
            self._st[mod] = st
        if port not in self._st[mod]:
            raise ValueError(f'no station count for {inst}.{port} ({mod})')
        return self._st[mod][port]

    def chain(self, lane):
        """ordered hops [(drv, port, rcv, net)] of a lane from its source partition."""
        hops = {}
        for net in self.nets.get(lane, []):
            p = self.parse_net(net)
            if p:
                hops.setdefault(p[0], []).append((*p, net))
        b = self.buses[lane]
        out, cur, seen = [], b['src'], set()
        while cur in hops and cur not in seen:
            seen.add(cur)
            if len(hops[cur]) != 1:
                return None           # branching lane (replicas): not a single chain
            h = hops[cur][0]
            out.append(h)
            cur = h[2]
        return out if out and out[-1][2] == b['dst'] else None


class Programme:
    def __init__(self, d):
        d = Path(d)
        self.dir = d
        self.s = json.loads((d / 'schedule.json').read_text())
        self.low = json.loads((d / 'lowering.json').read_text())
        self.by_pin = {}
        for e in self.s.get('events', []):
            for p in (e.get('ports') or [e['port']]):
                self.by_pin.setdefault((e['inst'], p, e['dir']), []).append(e)
        self.insts = {e['inst'].split('.')[0] for e in self.s.get('events', [])}
        self.links = self.s.get('links') or {}
        # per instance: statuses of every op that names it
        self.inst_status = {}
        for op in self.low.get('ops', []):
            for i in op.get('insts') or []:
                self.inst_status.setdefault(i.split()[0], set()).add(op.get('status'))

    def pin_events(self, path, port):
        """producer-pin values: dir out events at the pin, or dir in events at a link destination fed by it."""
        ev = [(e, 0) for e in self.by_pin.get((path, port, 'out'), [])]
        for name, L in self.links.items():
            if [path, port] in [list(x) for x in L.get('src') or []]:
                for di, dp in L.get('dst') or []:
                    ev += [(e, L['age_edges']) for e in self.by_pin.get((di, dp, 'in'), [])]
        return ev


def pin_value(e, port, widths):
    """the word of one pin inside a (possibly multi-pin, LSB-first) event; None when not fully specified."""
    ports = e.get('ports') or [e['port']]
    if any(p not in widths for p in ports) or not e.get('words'):
        return None
    lo = 0
    for p in ports:
        if p == port:
            break
        lo += widths[p]
    w = widths[port]
    total = sum(widths[p] for p in ports)
    res = []
    for edge, val, mask in e['words']:
        m = int(mask, 16)
        if m.bit_length() > total:
            return None
        if (m >> lo) & ((1 << w) - 1) != (1 << w) - 1:
            return None               # masked bits are assertions, not producer values
        res.append((int(edge), (int(val, 16) >> lo) & ((1 << w) - 1)))
    return res


def classify(bound, prog, carve):
    inside = set(carve['seeds'])
    widths = {}
    for b in bound.buses.values():
        for d in b['source_bits']:
            if d[0] == 'leaf':
                k = (d[1], d[2])
                widths[k] = max(widths.get(k, 0), d[3] + 1)
    out_by_lane = {}
    for port, v in carve['outputs'].items():
        if v.get('lane'):
            out_by_lane.setdefault(v['lane'], []).append(port)

    def lane_words(b, outside_stations):
        """per-edge projected word of a lane from exact producer-pin events, or (None, reason)."""
        pins = sorted({(d[1], d[2]) for d in b['source_bits'] if d[0] == 'leaf'})
        if any(d[0] != 'leaf' for d in b['source_bits']):
            return None, 'forwarded source bits need a landed forward trace'
        per_pin = {}
        for path, port in pins:
            evs = prog.pin_events(path, port)
            if not evs:
                return None, f'no compiled event at producer pin {path}.{port}'
            vals = {}
            for e, age in evs:
                if e.get('plan_only'):
                    return None, f'plan-only event at {path}.{port} ({e.get("tag")}): no encoded payload'
                eports = e.get('ports') or [e['port']]
                if age:   # dir-in event at a link sink: only a single-pin sink word maps to the source pin
                    if len(eports) != 1:
                        return None, f'multi-pin sink event {e.get("tag")} at {e["inst"]}.{e["port"]}: source pin split unknown'
                    pw, sel = {eports[0]: widths.get((path, port))}, eports[0]
                else:
                    pw, sel = {p: widths.get((e['inst'], p)) for p in eports}, port
                pv = pin_value(e, sel, {k: v for k, v in pw.items() if v})
                if pv is None:
                    return None, f'event {e.get("tag")} at {e["inst"]}.{e["port"]} does not fully specify {path}.{port}'
                for edge, val in pv:
                    vals[edge - age] = val
            per_pin[(path, port)] = vals
        edges = sorted(set().union(*[set(v) for v in per_pin.values()]))
        if any(set(v) != set(edges) for v in per_pin.values()):
            return None, 'producer pins of one lane have events on different edges (other pins unknown on those edges)'
        words = []
        W = b['width']
        for edge in edges:
            w = 0
            for i, d in enumerate(b['source_bits']):
                w |= ((per_pin[(d[1], d[2])][edge] >> d[3]) & 1) << i
            w |= 1 << W                  # epoch: delivered (released) reset level of the source partition
            words.append(dict(edge=edge, port_edge=edge + outside_stations, word_hex=format(w, 'x')))
        return words, None

    def producers_status(b):
        tops = sorted({d[1].split('.')[0] for d in b['source_bits'] if d[0] == 'leaf'})
        return tops, [t for t in tops if t in prog.insts], {t: sorted(prog.inst_status.get(t, [])) for t in tops}

    inputs = {}
    for port, v in carve['inputs'].items():
        rec = dict(width=v['width'], lane=v.get('lane'), readers=v.get('readers'))
        if not v.get('lane'):
            rec['class'] = 'CLOCK' if port.startswith('clk') else 'RESET'
            rec['source'] = 'bench clock' if port.startswith('clk') else 'reset wavefront output of an outside partition (bind_reset.json release)'
            inputs[port] = rec
            continue
        b = bound.buses[v['lane']]
        rec.update(src=b['src'], dst=b['dst'], bound_stages=b['bound_stages'], data_width=b['width'],
                   producers=sorted({f'{d[1]}.{d[2]}' for d in b['source_bits'] if d[0] == 'leaf'}))
        if b['src'] in inside:
            rec['class'] = 'LOOPBACK_FT'
            rec['source'] = 'carve-internal producer relayed through outside feed-through partitions; drive from the carve output ' + ', '.join(out_by_lane.get(v['lane'], ['(none)']))
            inputs[port] = rec
            continue
        ch = bound.chain(v['lane'])
        drv = None
        st = None
        if ch:
            k = [i for i, h in enumerate(ch) if h[3] == port]
            if k:
                hops = ch[:k[0] + 1]
                rec['hops_outside'] = [f'{h[0]}.{h[1]}' for h in hops]
                try:
                    st = sum(bound.stations(h[0], h[1]) for h in hops)
                    rec['stations_to_port'] = st
                except ValueError as e:
                    rec['stations_error'] = str(e)
        if b['src'].startswith(OFFDIE):
            rec['offdie'] = True
        tops, modelled, status = producers_status(b)
        words, why = lane_words(b, st if st is not None else 0)
        if words is not None and st is None:
            words, why = None, 'producer words exact but the hop chain/stations to this carve port are unresolved'
        if words is not None:
            rec['class'] = 'DERIVABLE'
            rec['words'] = words
        elif not modelled and tops and all(status[t] and set(status[t]) == {'LOWERED'} for t in tops):
            rec['class'] = 'IDLE_BY_SCHEDULE'
        else:
            rec['class'] = 'MISSING'
            if not modelled:
                why = ('off-die ' if rec.get('offdie') else '') + 'producer instance(s) ' + ', '.join(tops) + \
                      ' not modelled by the compiled programme (no boundary events' + \
                      (', lowering ' + json.dumps(status) if any(status.values()) else '') + ')'
            rec['reason'] = why
        inputs[port] = rec

    outputs = {}
    for port, v in carve['outputs'].items():
        rec = dict(width=v['width'], lane=v.get('lane'), drivers=v.get('drivers'))
        if not v.get('lane'):
            rec['class'] = 'CLOCK_RESET'
            outputs[port] = rec
            continue
        b = bound.buses[v['lane']]
        rec.update(src=b['src'], dst=b['dst'], bound_stages=b['bound_stages'])
        ch = bound.chain(v['lane']) or []
        k = [i for i, h in enumerate(ch) if h[3] == port]
        st = None
        if k:
            try:
                st = sum(bound.stations(h[0], h[1]) for h in ch[:k[0] + 1])
            except ValueError as e:
                rec['stations_error'] = str(e)
        words, why = lane_words(b, st or 0)
        if words is not None and st is not None:
            rec['class'] = 'DERIVABLE'
            rec['expected'] = words
        else:
            rec['class'] = 'UNSPECIFIED'
            rec['reason'] = why or 'hop chain/stations to this carve port unresolved'
        outputs[port] = rec
    return inputs, outputs


# compiled programme files: (glob, delivery, original consumer instances); dv_layer_compile.py docstring
PROG_KINDS = [
    ('prog/*host_boot.memh', 'HOST_STREAM: 515-b host words on the seqhost host lane f_host, one per 5 edges (dv_cut_replay.host_boot_words); '
     'carries CSR 0x11 length, 0x10 calendar, 0x13 CTL templates, 0x14 gunit rows', ['u_seqhost']),
    ('prog/**/host_boot.memh', None, ['u_seqhost']),
    ('prog/calendar.json', 'IN_HOST_STREAM (CSR 0x10 rows of host_boot.memh)', ['u_seqhost']),
    ('prog/ctl_templates.json', 'IN_HOST_STREAM (CSR 0x13 of host_boot.memh)', ['u_seqhost']),
    ('prog/gunit_rows.json', 'IN_HOST_STREAM (CSR 0x14 -> seqhost cw_v/cw_a/cw_d beats)', ['u_gunit']),
    ('prog/svc_jobs.json', 'SVC_JOBS (engine 4 rows of the calendar; jobs reach svc_rs via seqhost s_j / s_hw_*)', ['u_rsv_05', 'u_rsv_11']),
    ('prog/frame_cfg7/*.json', 'FRAME_CFG (frame programme placement record; memh banks only when lowered)', None),
    ('prog/gu/*.json', 'GUNIT_PLAN (record; delivered by the host stream)', ['u_gunit']),
    ('prog/bk/*.json', 'BK_PLAN (record)', ['u_bk_sel']),
    ('prog/xs/**/*', 'XS_STREAM (slice xs calendars / stream images)', None),
]


def load_map(bound, prog, carve):
    inside = set(carve['seeds'])
    seen, rows = set(), []
    for pat, delivery, consumers in PROG_KINDS:
        for f in sorted(prog.dir.glob(pat)):
            if f.is_dir() or f in seen:
                continue
            seen.add(f)
            rel = str(f.relative_to(prog.dir))
            cons = consumers
            if cons is None and 'frame_cfg7' in rel:
                cons = [f.stem]
            if cons is None and '/xs/' in '/' + rel:
                # xs op record (or the record next to an image directory) names its frames / slice
                rec_p = f if f.suffix == '.json' else f.parent.parent / (f.parent.name + '.json')
                if not rec_p.exists():
                    rec_p = f.parent / 'manifest.json'
                try:
                    r = json.loads(rec_p.read_text())
                    fr = r.get('frames')
                    if isinstance(fr, str):
                        fr = re.findall(r"'frame': '([^']+)'", fr)
                    elif isinstance(fr, list):
                        fr = [x['frame'] if isinstance(x, dict) else x for x in fr]
                    cons = fr or ([r['slice']] if r.get('slice') else None)
                except (ValueError, OSError, KeyError, TypeError):
                    cons = None
            row = dict(file=rel, sha256=sha(f), delivery=delivery or PROG_KINDS[0][1])
            if cons is None:
                row['status'] = 'UNMAPPED: consumer instance not recorded in the file name'
                rows.append(row)
                continue
            if f.suffix == '.json' and 'frame_cfg7' in rel:
                try:
                    j = json.loads(f.read_text())
                    row['compiled_status'] = j.get('status')
                except ValueError:
                    pass
            bl = []
            for c in cons:
                leaves = [k for o, ks in bound.by_orig.items() if o == c or o.startswith(c + '.') for k in ks]
                parts = sorted({k.split('.')[0] for k in leaves})
                bl.append(dict(original=c, bound_leaves=sorted(leaves)[:8], n_leaves=len(leaves),
                               partitions=[dict(partition=p, module=bound.module.get(p), in_carve=p in inside) for p in parts]))
            row['consumers'] = bl
            flags = [p['in_carve'] for x in bl for p in x['partitions']]
            if not all(x['n_leaves'] for x in bl):
                row['status'] = 'CONSUMER_NOT_IN_BOUND_TOP'
            elif all(flags):
                row['status'] = 'MAPPED_IN_CARVE'
            elif any(flags):
                row['status'] = 'MAPPED_PARTLY_OUTSIDE_CARVE'
            else:
                row['status'] = 'MAPPED_OUTSIDE_CARVE'
            rows.append(row)
    return rows


def rom_images(bound, carve):
    """simulation ROM macros inside the carve: bound leaf, original path, the INSTANCE image name the emitted
    partition passes (ot_rom_* reads +OT_ROM_DIR/<INSTANCE>.viamap.hex only when INSTANCE is non-empty)."""
    names = {k: o for o, ks in bound.by_orig.items() for k in ks}
    rows, mods = [], {}
    for part in sorted(set(carve['seeds'])):
        mod = bound.module.get(part)
        if mod is None:
            continue
        if mod not in mods:
            t = (bound.dir / 'rtl' / (mod + '.sv')).read_text()
            mods[mod] = re.findall(r'(ot_rom_\w+)\s+#\((.*?)\)\s+(\w+)\s*\(', t)
        for master, params, leaf in mods[mod]:
            m = re.search(r'\.INSTANCE\("([^"]*)"\)', params)
            rows.append(dict(partition=part, module=mod, leaf=leaf, master=master,
                             original=names.get(part + '.' + leaf), instance_param=m.group(1) if m else None))
    empty = sum(1 for r in rows if not r['instance_param'])
    return dict(n=len(rows), empty_instance=empty,
                status=('BLOCKED: emitted INSTANCE("") on every carve ROM macro -> no image is read in simulation '
                        '(bind emit must carry the elaborated INSTANCE string)') if rows and empty == len(rows)
                else ('PARTIAL' if empty else 'OK'), macros=rows)


def build(bound_dir, carve_p, prog_dir, t0=None):
    bound, prog = Bound(bound_dir), Programme(prog_dir)
    carve = json.loads(Path(carve_p).read_text())
    top_sha = sha(bound.top)
    if carve.get('top_sha256') and carve['top_sha256'] != top_sha:
        raise ValueError('carve was cut from a different bound top')
    inputs, outputs = classify(bound, prog, carve)
    counts = {}
    for side, d in (('inputs', inputs), ('outputs', outputs)):
        c = {}
        for v in d.values():
            c[v['class']] = c.get(v['class'], 0) + 1
        counts[side] = c
    ops = prog.s.get('ops') or []
    span = (max(o['end'] for o in ops if o.get('critical') is not False) - min(o['start'] for o in ops if o.get('critical'))) if any(o.get('critical') for o in ops) else None
    lmap = load_map(bound, prog, carve)
    return dict(schema='opentallas.tokds.bound_carve_stim.v1',
                scope='BOUND-PORT STIMULUS/EXPECTATION SPEC ONLY; not a token pass; words only where exact producer events exist',
                sources=dict(bound_top=str(bound.top), bound_top_sha256=top_sha, carve=str(carve_p), carve_sha256=sha(carve_p),
                             schedule_sha256=sha(prog.dir / 'schedule.json'), manifest_sha256=sha(prog.dir / 'manifest.json')
                             if (prog.dir / 'manifest.json').exists() else None, layer=prog.s.get('layer'),
                             timing_contract=(prog.s.get('timing_contract') or {}).get('schema')),
                price=dict(prog.s.get('price') or {}, critical_ops_span=span),
                timebase=dict(unit='compiled layer cycle (layer 0 = KS + 5)', t0=t0,
                              t0_status='GIVEN' if t0 is not None else 'UNRESOLVED: needs the measured boot/KS phase of a bound replay'),
                counts=counts, inputs=inputs, outputs=outputs, prog_load_map=lmap,
                prog_load_counts={s: sum(1 for r in lmap if r['status'] == s) for s in sorted({r['status'] for r in lmap})},
                rom_images=rom_images(bound, carve))


def write_ev(spec, d, t0):
    d = Path(d)
    for side, key, sub in (('inputs', 'words', 'stim'), ('outputs', 'expected', 'exp')):
        (d / sub).mkdir(parents=True, exist_ok=True)
        for port, v in spec[side].items():
            if v.get('class') != 'DERIVABLE':
                continue
            lines = [f"{w['port_edge'] + 1 + t0} {w['word_hex']}" for w in v[key] if w['port_edge'] + 1 + t0 >= 0]
            (d / sub / f'{port}.ev').write_text('\n'.join(lines) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--bound', required=True)
    ap.add_argument('--carve', required=True)
    ap.add_argument('--prog', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--t0', type=int)
    ap.add_argument('--ev-dir')
    a = ap.parse_args(argv)
    spec = build(a.bound, a.carve, a.prog, a.t0)
    Path(a.out).write_text(json.dumps(spec, indent=1) + '\n')
    if a.ev_dir:
        if a.t0 is None:
            raise SystemExit('--ev-dir needs --t0 (bench cycle of layer cycle 0)')
        write_ev(spec, a.ev_dir, a.t0)
    print(json.dumps(dict(counts=spec['counts'], prog_load=spec['prog_load_counts'], price=spec['price'],
                          rom=dict(n=spec['rom_images']['n'], empty_instance=spec['rom_images']['empty_instance']))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
