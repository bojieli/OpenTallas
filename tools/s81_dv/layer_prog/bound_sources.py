"""Exact original-source bit projection onto current bound partition buses.

This maps qualified producer words or traces. It does not manufacture missing
producer values or qualify a whole token by itself.
"""
import json
from pathlib import Path


class BoundSources:
    def __init__(self, root):
        self.root = Path(root)
        report = json.loads((self.root / 'bind_report.json').read_text())
        if report.get('n_errors') != 0 or report.get('errors'):
            raise ValueError('current bound source projection requires zero strict binding errors: ' + str(report.get('n_errors')) + '; ' + str((report.get('errors') or ['no error detail'])[0])[:300])
        if report.get('type_splits'):
            raise ValueError('current bound source projection refuses unresolved partition type splits')
        tops = list((self.root / 'rtl').glob('*_bound_top.sv'))
        if len(tops) != 1:
            raise ValueError('current bound source projection needs one complete emitted top')
        self.top = tops[0]
        latency = json.loads((self.root / 'bind_latency.json').read_text())
        self.buses = {}
        for bus in latency['buses']:
            lane = bus['lane']
            if lane in self.buses:
                raise ValueError('ambiguous physical lane: ' + lane)
            if bus.get('source_bit_order') != 'lsb_first':
                raise ValueError('exact LSB-first source map absent for ' + str(lane))
            if len(bus.get('source_bits', [])) != bus['width']:
                raise ValueError('exact source bit map absent for ' + lane)
            self.buses[lane] = bus

    def _bits(self, lane, values):
        bus = self.buses[lane]
        out = []
        for desc in bus['source_bits']:
            if desc[0] == 'leaf':
                _, path, port, bit = desc
                pin = path + '.' + port
                if pin not in values or not isinstance(values[pin], int) or values[pin] < 0:
                    raise ValueError('missing actual producer value: ' + pin)
                if not isinstance(bit, int) or bit < 0:
                    raise ValueError('invalid original producer bit')
                out.append((values[pin] >> bit) & 1)
            elif desc[0] == 'forward':
                _, previous, bit = desc
                if previous not in self.buses:
                    raise ValueError('forwarded source lane absent: ' + previous)
                # A forwarded value has already crossed its preceding lane.
                # Require its actual trace at this source edge; reusing the
                # original producer word would erase that transport age.
                trace = values.get('@' + previous)
                if not isinstance(trace, int) or trace < 0:
                    raise ValueError('missing landed forward trace: ' + previous)
                if not isinstance(bit, int) or bit < 0 or bit >= self.buses[previous]['width']:
                    raise ValueError('forwarded source bit out of range')
                out.append((trace >> bit) & 1)
            else:
                raise ValueError('unsupported bound source descriptor')
        return out

    def project(self, lane, values, source_cycle):
        """Return physical source bus word and landing date; source dates stay real."""
        bus = self.buses[lane]
        if not isinstance(source_cycle, (int, float)):
            raise ValueError('actual producer edge missing')
        bits = self._bits(lane, values)
        return dict(lane=lane, source_partition=bus['src'], source_port=bus['bus_out'],
                    sink_partition=bus['dst'], sink_port=bus['bus_in'],
                    width=bus['width'], word=sum(b << i for i, b in enumerate(bits)),
                    source_cycle=source_cycle, landed_cycle=source_cycle + bus['bound_stages'])


    def project_trace(self, lane, trace, program=None):
        """Project every observed producer edge; gaps and stale source traces fail."""
        import hashlib
        if trace.get('bound_top_sha256') != hashlib.sha256(self.top.read_bytes()).hexdigest():
            raise ValueError('producer trace is not from this current bound top')
        samples = trace.get('samples') or []
        if not samples:
            raise ValueError('actual producer trace is empty')
        profile = None
        if program and program.get('eng_profile'):
            from layer_prog.eng_schedule import load_profile, validate_landed_start
            profile = load_profile(program['eng_profile']['manifest'])
            if profile['profile_sha256'] != program['eng_profile'].get('profile_sha256'):
                raise ValueError('programme E5 source profile changed')
        starts = [i for i, d in enumerate(self.buses[lane]['source_bits'])
                  if d == ['leaf', 'u_seqhost', 'engram_f_ks', 52]]
        if profile and self.buses[lane]['src'] == 'seqhost' and self.buses[lane]['dst'] == 'eng' and len(starts) != 1:
            raise ValueError('selected E5 trace does not map the actual producer START bit')
        previous, out = None, []
        for sample in samples:
            cycle = sample.get('cycle')
            if not isinstance(cycle, int) or (previous is not None and cycle != previous + 1):
                raise ValueError('producer trace must include every consecutive source edge')
            word = self.project(lane, sample.get('values') or {}, cycle)
            if profile and starts and (word['word'] >> starts[0]) & 1:
                word['eng_entry_phase'] = validate_landed_start(profile, program.get('eng_readiness') or {}, word['landed_cycle'])
            word['word_hex'] = format(word['word'], 'x')
            out.append(word)
            previous = cycle
        return dict(scope='OBSERVED_PRODUCER_PROJECTION_ONLY; bound RTL token still required',
                    bound_top_sha256=trace['bound_top_sha256'], lane=lane, samples=out)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bound', required=True)
    ap.add_argument('--lane', required=True)
    inputs = ap.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--trace', help='observed complete source-edge trace JSON from this current bound top')
    inputs.add_argument('--values', help='JSON actual producer pin values; @lane names landed forward traces')
    ap.add_argument('--source-cycle', type=float)
    ap.add_argument('--program', help='compiled schedule.json; selected E5 readiness is checked at actual landed START')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    try:
        bound = BoundSources(a.bound)
        if a.trace:
            program = json.loads(Path(a.program).read_text()) if a.program else None
            projection = bound.project_trace(a.lane, json.loads(Path(a.trace).read_text()), program)
        else:
            if a.source_cycle is None or a.program:
                raise ValueError('single values need --source-cycle; programme readiness requires --trace')
            projection = bound.project(a.lane, json.loads(Path(a.values).read_text()), a.source_cycle)
    except (ValueError, KeyError, OSError) as e:
        print(json.dumps(dict(status='BLOCKED', reason=str(e))))
        return 2
    if 'word' in projection:
        projection['word_hex'] = format(projection['word'], 'x')
    projection['scope'] = 'PRODUCER_WORD_PROJECTION_ONLY; not a bound RTL token PASS'
    text = json.dumps(projection, indent=1) + '\n'
    if a.out:
        Path(a.out).write_text(text)
    print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
