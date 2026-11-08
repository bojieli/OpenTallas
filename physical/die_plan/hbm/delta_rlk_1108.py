"""HBM plan event RLK-1108: FT transit types get the hop lockup LATCH on every internal reset relay hop.

CLASS (DIE-HBM-92 11-08, measured on routed vsN1/vsN2/q_mca/q_spb1): after FTLK-1108 (ft station hops), the rest of
the non-port FF hold misses are internal reset relay hops u_rrl_a -> u_rrl_b on different kit grid tap ports (flat
160-ps tap window, no CRPR across ports): vsN1 ~-63, vsN2 -95.31, q_spb1 u_rrl19 -> u_rrl23 -56.27, q_mca -48.71.
The negedge relay (CLK FORM #7) failed setup on the q_spb1 pilot (T/2 - 160 for a full 377-um hop, TT -84.84).
FIX: reset.relay_lockup {"form": "latch", types} (tools/die_plan/reset_tree.py RLK-1108): relays stay posedge, one
transparent-low ot_dp_lk per internal hop, clocked from the launch relay's tap and FIRM at the hop midpoint: ~T/2
extra hold, setup = half hop after the falling edge (or the whole hop within T - 160 with borrowing).  0 PIN CYCLES,
reset depth K and release cycle unchanged, no type block / pin / outline change.  Applied on top of FTLK-1108 v2.
Absent key is created; an existing latch list is extended (sorted, unique); an existing negedge list is refused."""
import argparse
import copy
import hashlib
import json
import sys

EVENT = 'RLK-1108'
TYPES = ['q_mca', 'q_spb1', 'vsN1', 'vsN2']


def apply(plan, types=TYPES):
    out = copy.deepcopy(plan)
    miss = [t for t in types if t not in out['partition_types']]
    if miss:
        raise ValueError(f'{EVENT}: types not in plan: {miss}')
    rl = dict(out['reset'].get('relay_lockup') or {'form': 'latch', 'types': []})
    if rl.get('form') != 'latch':
        raise ValueError(f'{EVENT}: existing relay_lockup form {rl.get("form")!r} is not latch (one form per plan)')
    if out['reset'].get('relay_driver') or out['reset'].get('start') not in (None, 'none'):
        raise ValueError(f'{EVENT}: relay_lockup excludes relay_driver / START broadcast plans')
    rl['types'] = sorted(set(rl.get('types', [])) | set(types))
    rl.setdefault('note', 'RLK-1108 DIE-HBM-92-RLK: hop lockup latch on internal reset relay hops (0 cycles)')
    out['reset']['relay_lockup'] = rl
    return out


def sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan'); ap.add_argument('--out', required=True); ap.add_argument('--receipt', required=True)
    ap.add_argument('--types', nargs='*', default=TYPES)
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    new = apply(raw, a.types)
    blocks_same = all(sha(raw['partition_types'][t]) == sha(new['partition_types'][t]) for t in raw['partition_types'])
    with open(a.out, 'w') as f:
        json.dump(new, f, indent=1); f.write('\n')
    json.dump(dict(event=EVENT, plan_in=a.plan, sha_in=sha(raw), sha_out=sha(new), types=a.types,
                   relay_lockup=new['reset']['relay_lockup'], ft_hop_lockup=new['clock'].get('ft_hop_lockup'),
                   type_blocks_unchanged=blocks_same, pin_cycles_added=0), open(a.receipt, 'w'), indent=1)
    print(f'{EVENT}: types {a.types}; type blocks unchanged: {blocks_same}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
