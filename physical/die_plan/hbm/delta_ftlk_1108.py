"""HBM plan event FTLK-1108: FT transit types get the hold-safe hop lockup and the negedge reset relay.

CLASS (DIE-HBM-92 11-08, measured on routed vsN1/vsN2/q_mca/q_spb1): every non-port FF hold miss is a zero-logic
FT station hop u_ft_<bus>_s<k> -> s<k+1> (or an internal reset relay u_rrl_a -> u_rrl_b) whose two flops hang on
different kit grid tap ports.  The plan tap window is a flat 160 ps (launch source -160, capture 0, no CRPR
across ports), so a short hop fails hold by up to ~100 ps.  Existing opt-in plan forms (TYPE-SAFE-1 11-06,
CLK FORM #7 11-03; gen_rtl.ft_hop_lockup / reset_tree relay_lockup) give each hop ~T/2 hold margin by
construction with 0 added cycles: clock.ft_hop_lockup {types}.  v2 (11-08 05:3x): reset.relay_lockup negedge is NOT
used: on the q_spb1 pilot its half-cycle budget (T/2 - 160 ps) failed TT setup -84.84 ps on a full ~377-um relay hop
(u_rrl_28 -> u_rrl_30); the reset relay hops get their own form (latch at the hop midpoint, next event).
The flat 160 window stays (no narrower SDC).  Only the listed types change; no type block, pin, outline or
cycle changes.  Absent keys are created; existing lists are extended (sorted, unique)."""
import argparse
import copy
import hashlib
import json
import sys

EVENT = 'FTLK-1108'
TYPES = ['q_spb1', 'vsN1', 'vsN2']
RELAY_TYPES = []  # v2 11-08 05:3x: negedge relay FAILED setup on the q_spb1 pilot (T/2 - 160 for a full ~377-um hop)


def apply(plan, types=TYPES, relay_types=RELAY_TYPES):
    out = copy.deepcopy(plan)
    known = set(out['partition_types'])
    miss = [t for t in types if t not in known]
    if miss:
        raise ValueError(f'{EVENT}: types not in plan: {miss}')
    lk = out['clock'].get('ft_hop_lockup')
    if lk and lk.get('all'):
        raise ValueError(f'{EVENT}: plan already uses ft_hop_lockup all/except; edit it explicitly')
    lk = dict(lk or {})
    lk['types'] = sorted(set(lk.get('types', [])) | set(types))
    out['clock']['ft_hop_lockup'] = lk
    if relay_types:
        rl = dict(out['reset'].get('relay_lockup') or {'form': 'negedge', 'types': []})
        if rl.get('form') != 'negedge':
            raise ValueError(f'{EVENT}: existing relay_lockup form {rl.get("form")!r} is not negedge')
        rl['types'] = sorted(set(rl.get('types', [])) | set(relay_types))
        out['reset']['relay_lockup'] = rl
    return out


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan'); ap.add_argument('--out', required=True); ap.add_argument('--receipt', required=True)
    ap.add_argument('--types', nargs='*', default=TYPES)
    ap.add_argument('--relay-types', nargs='*', default=RELAY_TYPES)
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    new = apply(raw, a.types, a.relay_types)
    blocks_same = all(sha(raw['partition_types'][t]) == sha(new['partition_types'][t]) for t in raw['partition_types'])
    with open(a.out, 'w') as f:
        json.dump(new, f, indent=1); f.write('\n')
    json.dump(dict(event=EVENT, plan_in=a.plan, sha_in=sha(raw), sha_out=sha(new), types=a.types,
                   ft_hop_lockup=new['clock']['ft_hop_lockup'], relay_lockup=new['reset'].get('relay_lockup'),
                   type_blocks_unchanged=blocks_same, pin_cycles_added=0), open(a.receipt, 'w'), indent=1)
    print(f'{EVENT}: types {a.types}; type blocks unchanged: {blocks_same}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
