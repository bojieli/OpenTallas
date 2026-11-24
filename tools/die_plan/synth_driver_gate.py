#!/usr/bin/env python3
"""Kit synthesis driver gate (KITSYN-UNDRIVEN-FATAL, COORD 11-23 22:4x).

A kit whose yosys log reports a wire that is used but has no driver is synthesising a broken netlist
(QC tt_ctlm rs1: 447 output bits aliased to undriven nets; the probe numbers were read on it).  Yosys only warns, so
this gate turns every such warning into a hard FAIL and lists the nets.

Exceptions are explicit and recorded: <kit>/undriven_exceptions.json
  {"exceptions": [{"net": "<name or fnmatch pattern>", "kind": "tied"|"dead", "plan": "<plan/bind that declares it>",
                   "reason": "<why>"}]}
Only nets the plan declares tied or dead may be listed; an entry without kind in {tied, dead} or without plan is itself
a FAIL.  Waived nets are written to the report so the exception stays on record.

usage: synth_driver_gate.py KIT [--log LOG ...] [--out report.json]
exit 0 = PASS, 1 = FAIL (undriven nets or bad exception file), 2 = NOT RUN (no synthesis log).
"""
import argparse
import fnmatch
import glob
import json
import re
import sys
from pathlib import Path

# yosys `check`: "Warning: Wire top.\w_core_cmd [12] is used but has no driver."  (also seen: "is undriven")
WARN = re.compile(r'Warning:\s*Wire\s+(?P<net>.+?)\s+is\s+(?:used\s+but\s+has\s+no\s+driver|undriven)\b', re.I)
KINDS = ('tied', 'dead')


def norm(net):
    """'top.\\w_core_cmd [12]' -> ('top.w_core_cmd[12]', 'w_core_cmd[12]')"""
    n = re.sub(r'\s+(?=\[)', '', net.replace('\\', '').strip())
    return n, (n.split('.', 1)[1] if '.' in n else n)


def scan(text):
    """-> sorted unique normalised net names of every no-driver warning in a yosys log"""
    return sorted({norm(m.group('net'))[0] for m in WARN.finditer(text)})


def load_exceptions(path):
    """-> (entries, errors)"""
    p = Path(path)
    if not p.exists():
        return [], []
    try:
        ex = json.loads(p.read_text()).get('exceptions', [])
    except (ValueError, AttributeError) as e:
        return [], [f'{p.name}: unreadable ({e})']
    ok, errs = [], []
    for i, e in enumerate(ex):
        if not isinstance(e, dict) or not e.get('net') or e.get('kind') not in KINDS or not e.get('plan'):
            errs.append(f'{p.name}[{i}]: needs net, kind in {KINDS} and plan: {e!r}')
        else:
            ok.append(e)
    return ok, errs


def waived_by(net, exceptions):
    short = norm(net)[1]
    for e in exceptions:
        if fnmatch.fnmatchcase(net, e['net']) or fnmatch.fnmatchcase(short, e['net']):
            return e
    return None


def gate(logs, exceptions, exc_errors=()):
    nets = {}
    for lg in logs:
        for n in scan(Path(lg).read_text(errors='replace')):
            nets.setdefault(n, []).append(str(lg))
    bad, waived = [], []
    for n in sorted(nets):
        e = waived_by(n, exceptions)
        if e:
            waived.append(dict(net=n, exception=e))
        else:
            bad.append(n)
    ok = not bad and not exc_errors
    return dict(verdict='PASS' if ok else 'FAIL', undriven=bad, n_undriven=len(bad), waived=waived,
                exception_errors=list(exc_errors), logs=[str(x) for x in logs])


def find_logs(kit):
    k = str(kit)
    return sorted(glob.glob(k + '/run/logs/*/*/*/1_2_yosys.log') + glob.glob(k + '/run/logs/*/*/1_2_yosys.log'))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('kit', type=Path)
    ap.add_argument('--log', action='append', default=[])
    ap.add_argument('--out', type=Path)
    a = ap.parse_args(argv)
    logs = a.log or find_logs(a.kit)
    if not logs or not all(Path(x).exists() for x in logs):
        print('SYNTH_DRIVER_GATE NOT RUN: no 1_2_yosys.log under', a.kit)
        return 2
    ex, errs = load_exceptions(a.kit / 'undriven_exceptions.json')
    rep = gate(logs, ex, errs)
    if a.out:
        a.out.write_text(json.dumps(rep, indent=1) + '\n')
    print(f"SYNTH_DRIVER_GATE {rep['verdict']}: {rep['n_undriven']} undriven net(s), {len(rep['waived'])} waived")
    for n in rep['undriven'][:200]:
        print('  NO DRIVER', n)
    if rep['n_undriven'] > 200:
        print(f"  ... {rep['n_undriven'] - 200} more (see report)")
    for e in rep['exception_errors']:
        print('  BAD EXCEPTION', e)
    return 0 if rep['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
