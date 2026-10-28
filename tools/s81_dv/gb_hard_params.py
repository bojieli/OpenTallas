#!/usr/bin/env python3
"""Restore the kit-stripped hardened parameter sets of hard children in a functional (simulation) copy of an as-built
GB partition source (TOK-ALL-16, 10-27).

The physical kit strips #() from hard children; the hardened set is recorded in the manifest's hard_params json
(<partition>_hard_params.json, masters{}), and bind_elab bakes it into port-only stubs for extraction.  A FUNCTIONAL
copy that instantiates the real RTL must carry the same set, else the child elaborates at its defaults.  Measured
failure (TOK-ALL-15 run2): ot_s81_cfg7_seq at default PQ 0 / LAYOUT 0 / PINREG 0 read the il7 (LAYOUT 1) cfg image
linearly, never loaded the class-valid word 8, act stayed 0 and go_e never rose.

Every inserted value must equal BOTH the hard_params record and the canonical reference call (same module, same
instance name); existing values must agree; ports and every other parameter stay byte-identical.  0 cycles: this
restores the signed view's own parameters, it does not change hardware.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from qxpq_go_boundary import _group, _named


def calls(text, masters):
    pat = re.compile(r'(?m)^[ \t]*(' + '|'.join(sorted(map(re.escape, masters), key=len, reverse=True)) + r')\b(?!\w)')
    for m in pat.finditer(text):
        pos = m.end()
        while text[pos].isspace():
            pos += 1
        p0 = p1 = None
        if text[pos] == '#':
            p0 = text.index('(', pos); p1 = _group(text, p0); pos = p1
        n = re.match(r'\s*(\w+)\s*\(', text[pos:])
        if not n:
            raise ValueError('unsupported instance syntax at ' + m.group(1))
        c0 = pos + n.end() - 1; c1 = _group(text, c0)
        yield dict(module=m.group(1), name=n.group(1), p0=p0, p1=p1, insert=m.end(),
                   params={k: v[2] for k, v in (_named(text[p0 + 1:p1 - 1]) if p0 is not None else {}).items()},
                   ports=text[c0:c1])


def restore(actual, reference, hard):
    masters = {k: {p: str(v) for p, v in d.items()} for k, d in hard['masters'].items() if d}
    refs = {}
    for c in calls(reference, masters):
        refs.setdefault((c['module'], c['name']), []).append(c['params'])
    edits, rows = [], []
    for c in calls(actual, masters):
        key = (c['module'], c['name'])
        want = masters[c['module']]
        if key not in refs:
            raise ValueError('actual hard call absent from canonical reference: %s' % (key,))
        for rp in refs[key]:
            for p, v in want.items():
                if rp.get(p) != v:
                    raise ValueError('canonical %s %s=%s != hard_params %s' % (key, p, rp.get(p), v))
        for p, v in c['params'].items():
            if p in want and v != want[p]:
                raise ValueError('actual %s %s=%s disagrees with hard_params %s' % (key, p, v, want[p]))
        add = [(p, v) for p, v in want.items() if p not in c['params']]
        s = ', '.join('.%s(%s)' % pv for pv in add)
        if add:
            if c['p1'] is None:
                edits.append((c['insert'], ' #(' + s + ')'))
            else:
                edits.append((c['p1'] - 1, (', ' if c['params'] else '') + s))
        rows.append(dict(module=c['module'], instance=c['name'], restored=dict(add), kept=c['params'],
                         ports_sha256=hashlib.sha256(c['ports'].encode()).hexdigest()))
    if not rows:
        raise ValueError('no hard calls with a recorded parameter set')
    for pos, s in sorted(edits, reverse=True):
        actual = actual[:pos] + s + actual[pos:]
    after = list(calls(actual, masters))
    if len(after) != len(rows):
        raise ValueError('call count changed')
    for r, a in zip(rows, after):
        if hashlib.sha256(a['ports'].encode()).hexdigest() != r['ports_sha256']:
            raise ValueError('port change')
        if {k: v for k, v in a['params'].items() if k not in r['restored']} != r['kept']:
            raise ValueError('non-restored parameter change')
        if any(a['params'].get(p) != v for p, v in masters[a['module']].items()):
            raise ValueError('restore incomplete')
    sites = {}
    for r in rows:
        sites[r['module']] = sites.get(r['module'], 0) + 1
    return actual, dict(schema='opentallas.gb_hard_params.v1', calls=rows, restored_calls=len(edits), sites=sites,
                        added_cycles=0, hardware_changed=False, native_provider_qualified=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--actual', type=Path, required=True)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--hard-params', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    hard = json.loads(a.hard_params.read_text())
    text, receipt = restore(a.actual.read_text(), a.reference.read_text(), hard)
    receipt['source_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (a.actual, a.reference, a.hard_params)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text)
    receipt['out_sha256'] = hashlib.sha256(a.out.read_bytes()).hexdigest()
    a.out.with_suffix('.hard_params.json').write_text(json.dumps(receipt, indent=1) + '\n')
    print(json.dumps({k: receipt[k] for k in ('restored_calls', 'sites')}))


if __name__ == '__main__':
    main()
