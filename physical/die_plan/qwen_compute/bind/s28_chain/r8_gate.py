#!/usr/bin/env python3
"""QC-S28-BIND r8 gate: which bind errors may be cleared by ONE land_r8_derive from the current bus_groups.

R8_STALE                       the landing table itself is stale against the bound bus_groups.
PARAM_REGEN ... would need a pad  coll_regen / qc_fabric_transport read r_d / nb_od of the R8 landings; with a stale
                               table the region-0 value is not the latest, so this clears only after the derive.
                               (DIE-QC-100 11-13: deadlock when r8 is withheld on it.)
Every other error blocks the derive. After the single derive the chain rebinds strict; a remaining R8-class error
then fails the chain (no second derive).

usage: r8_gate.py BIND_REPORT.json   -> prints "r8_class N other M", lists the others, exit 0 if M == 0 else 1
"""
import json
import sys


def r8_class(err):
    s = str(err)
    if 'R8_STALE' in s:
        return True
    return 'PARAM_REGEN' in s and 'would need a pad' in s


def split(errors):
    r8 = [e for e in errors if r8_class(e)]
    other = [e for e in errors if not r8_class(e)]
    return r8, other


def main(argv):
    errs = json.load(open(argv[1]))['errors']
    r8, other = split(errs)
    print(f'r8_class {len(r8)} other {len(other)}')
    for e in other[:20]:
        print('  ', str(e)[:300])
    return 0 if not other else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
