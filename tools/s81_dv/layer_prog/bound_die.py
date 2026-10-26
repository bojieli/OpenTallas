"""Native logical interfaces and exact transport ages from one strict-bound die.

No legacy die.v geometry or link-age table is read. Local unit timing remains a
separate source-qualified contract; this adapter never substitutes historical
seq_host, ring-stop or XRT latency for a missing receipt.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def object_items(path, chunk_size=1 << 20):
    """Stream the flat bind_sinks object without constructing its multi-GB dict."""
    decoder = json.JSONDecoder()
    with Path(path).open() as f:
        buf, at, eof = '', 0, False

        def need():
            nonlocal buf, at, eof
            tail = f.read(chunk_size)
            buf, at = buf[at:] + tail, 0
            eof = not tail

        def token():
            nonlocal at
            while True:
                while at < len(buf) and buf[at].isspace():
                    at += 1
                if at < len(buf):
                    return buf[at]
                if eof:
                    raise ValueError('truncated bind_sinks JSON')
                need()

        def decode():
            nonlocal at
            while True:
                token()
                try:
                    value, end = decoder.raw_decode(buf, at)
                    if end == len(buf) and not eof:
                        need()
                        continue
                    at = end
                    return value
                except json.JSONDecodeError:
                    if eof:
                        raise ValueError('invalid bind_sinks JSON')
                    need()

        if token() != '{':
            raise ValueError('bind_sinks must be an object')
        at += 1
        if token() == '}':
            at += 1
        else:
            while True:
                key = decode()
                if not isinstance(key, str) or token() != ':':
                    raise ValueError('invalid bind_sinks key')
                at += 1
                value = decode()
                yield key, value
                sep = token()
                at += 1
                if sep == '}':
                    break
                if sep != ',':
                    raise ValueError('invalid bind_sinks separator')
        if (buf[at:] + f.read()).strip():
            raise ValueError('trailing data after bind_sinks object')


class BoundDie:
    def __init__(self, bound, inventory, *, sinks=None):
        self.bound = Path(bound)
        self.inventory = json.loads(Path(inventory).read_text()) if not isinstance(inventory, dict) else inventory
        if self.inventory.get('schema') != 'opentallas.s81.bound_inventory.v1':
            raise ValueError('unsupported bound logical-interface inventory')
        report = json.loads((self.bound / 'bind_report.json').read_text())
        if report.get('n_errors') != 0 or report.get('errors') or report.get('type_splits'):
            raise ValueError('BoundDie requires a clean strict bind with no type splits')
        tops = list((self.bound / 'rtl').glob('*_bound_top.sv'))
        if len(tops) != 1:
            raise ValueError('BoundDie needs one emitted die top')
        self.die_sha = file_sha(tops[0])
        if self.inventory.get('source_top_sha256') != self.die_sha:
            raise ValueError('logical inventory belongs to a different bound top')
        if self.inventory.get('source_asbuilt_sha256') != file_sha(self.bound / 'asbuilt.json'):
            raise ValueError('logical inventory belongs to a different elaborated source graph')
        self.units = self.inventory['units']
        self.inst = {name: dict(master=u['master'], params=u.get('params', {}),
                               conns={p: '@' + name + '.' + p for p in u['ports']})
                     for name, u in self.units.items()}
        self.sinks = sinks

    def strap(self, inst, port):
        bits = self.units[inst]['ports'][port]['bits']
        if not bits or any(bit not in ('0', '1') for bit in bits):
            raise ValueError(f'{inst}.{port} is not a literal source strap')
        return sum(int(bit) << i for i, bit in enumerate(bits))

    def slices(self):
        out = {}
        for name, unit in self.units.items():
            if unit['master'].startswith('ot_s81sl_slice'):
                out[name] = dict(master=unit['master'], params=unit.get('params', {}),
                                 sid=self.strap(name, 'sid'), block=name)
        sids = [u['sid'] for u in out.values()]
        if sorted(sids) != list(range(16)):
            raise ValueError('current source needs exactly one slice per SID0..15')
        return out

    def route(self, source, source_port, target, target_port):
        if self.sinks is None:
            wanted = {p for ps in self.inventory['input_pins'].values() for p in ps}
            self.sinks = {key: value for key, value in object_items(self.bound / 'bind_sinks.json') if key in wanted}
        src = self.units[source]['ports'][source_port]
        dst = self.units[target]['ports'][target_port]
        if src['dir'] != 'output' or dst['dir'] != 'input' or len(src['bits']) != len(dst['bits']):
            raise ValueError('transport endpoints need matching output/input word widths')
        ages, drivers, checked, constant = set(), [], 0, []
        for bit, (sn, dn) in enumerate(zip(src['bits'], dst['bits'])):
            if isinstance(sn, str) or isinstance(dn, str):
                if sn != dn or sn not in ('0', '1'):
                    raise ValueError(f'transport bit{bit}: conflicting or unknown constant')
                constant.append(bit)
                continue
            pins = self.inventory['drivers'].get(str(sn), [])
            if len(pins) != 1:
                raise ValueError(f'transport bit{bit}: ambiguous/missing source driver')
            source_pin = pins[0]
            targets = self.inventory['input_pins'].get(str(dn), [])
            if not targets:
                raise ValueError(f'transport bit{bit}: no exact target leaf input')
            for target_pin in targets:
                variants = self.inventory.get('source_variants', {})
                if not variants.get('leaf_rules_applied', False):
                    for rule in variants.get('leaf_rules', []):
                        for pin in (source_pin, target_pin):
                            if re.fullmatch(rule['inst'], pin.rsplit('.', 1)[0]):
                                raise ValueError(f'{pin}: source variant ABI needs explicit projection')
                desc = self.sinks.get(target_pin)
                if not isinstance(desc, list) or len(desc) != 4 or desc[0] != 'pin' or desc[1] != source_pin:
                    raise ValueError(f'transport bit{bit}: {target_pin} does not receive {source_pin}')
                age = desc[2]
                if type(age) is not int or age < 0:
                    raise ValueError(f'transport bit{bit}: missing exact bound age')
                ages.add(age)
                checked += 1
            drivers.append(source_pin)
        if len(ages) != 1:
            raise ValueError(f'transport word has mixed/unmeasured bit ages: {sorted(ages)}')
        return dict(source=source, source_port=source_port, target=target, target_port=target_port,
                    width=len(src['bits']), age_edges=ages.pop(), checked_leaf_inputs=checked,
                    source_pins=drivers, constant_bits=constant, die_sha256=self.die_sha,
                    basis='current bound per-bit source identity and transport stages; no local unit latency')


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bound', required=True, type=Path)
    p.add_argument('--inventory', required=True, type=Path)
    p.add_argument('--routes', required=True, type=Path,
                   help='JSON list of {source,source_port,target,target_port} exact logical endpoints')
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('preserve previous route verdict; select a fresh output')
    die = BoundDie(a.bound, a.inventory)
    routes = []
    for req in json.loads(a.routes.read_text()):
        try:
            routes.append(dict(status='PASS', **die.route(**req)))
        except (KeyError, ValueError) as exc:
            routes.append(dict(status='BLOCKED', request=req, reason=str(exc)))
    rec = dict(schema='opentallas.s81.bound_routes.v1', die_sha256=die.die_sha,
               routes=routes, scope='actual transport only; local unit timing and token remain separate')
    a.out.write_text(json.dumps(rec, indent=1)+'\n')
    print(json.dumps(dict(routes=len(routes), blocked=sum(r['status'] != 'PASS' for r in routes))))
    return any(r['status'] != 'PASS' for r in routes)


if __name__ == '__main__':
    raise SystemExit(main())
