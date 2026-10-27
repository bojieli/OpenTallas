"""KV-CORE-SLICE-1: price the KVHR face pin-register recut per core from the measured face_guard.json (kits on
intel2:/srv/opentallas-scratch2/claude/cores-kits/kvhr/kits). Class -> structural fix -> cycle cost:
  output 'shared' (port Q also drives internal loads) -> private output Q copy (KVHR mechanism 929a037e3, proven host_qm) : 0 cyc, +1 FF/bit
  input fanout ('N loads on X')                         -> landing pin register                                        : +1 cyc on that input bus
  reset/control input fanout (name has rst)             -> regional reset net (12.2a), exempt from pin-register rule      : 0 cyc
  'unregistered' output (comb gate drives port)         -> output pin register                                           : +1 cyc on that output bus
  'feedthrough' (port->port buffer)                     -> in-core ft register (12.1d pushdown)                          : +1 cyc on that bus
  'dropped' (no load, register removed)                 -> plan pin drop (declared dead input, COORD 10-25)              : 0 cyc
A bus = pin name without [index]; cycles are per bus (all bits of a bus move together)."""
import json, re, sys, glob, collections, os
root = sys.argv[1]; out = {}
for d in sorted(glob.glob(root + '/qkd_hr_*')):
    core = os.path.basename(d).split('__')[0]
    fg = json.load(open(d + '/face_guard.json')) if os.path.exists(d + '/face_guard.json') else None
    if fg is None:
        out[core] = dict(status='NO face_guard (stopped earlier)'); continue
    buses = collections.defaultdict(lambda: collections.Counter())
    for cls, rows in fg['fails'].items():
        for r in rows:
            pin = r.split(':')[0].strip(); bus = re.sub(r'\[\d+\]$', '', pin)
            if cls == 'shared':
                k = 'in_fanout' if re.match(r'^\d+ loads on', r.split(': ', 1)[1]) else 'out_shared'
                if k == 'in_fanout' and re.search(r'rst', bus): k = 'reset_ctl'
            else:
                k = cls
            buses[bus][k] += 1
    cyc_cls = {'in_fanout', 'unregistered', 'feedthrough'}
    plus1 = sorted(b for b, c in buses.items() if any(c[k] for k in cyc_cls))
    tot = collections.Counter()
    for c in buses.values(): tot.update(c)
    out[core] = dict(checked=fg['checked'], ok=fg['ok'], fail_counts=fg['fail_counts'], bits_by_fix=dict(tot),
                     private_q_ff=tot['out_shared'], pin_drops=tot['dropped'],
                     plus1_buses=len(plus1), plus1_bits=sum(tot[k] for k in cyc_cls), plus1_bus_list=plus1,
                     zero_cycle=len(plus1) == 0, listed_complete=sum(len(v) for v in fg['fails'].values()) == sum(fg['fail_counts'].values()))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
for k, v in out.items():
    print(k, {x: v.get(x) for x in ('fail_counts', 'bits_by_fix', 'plus1_buses', 'zero_cycle', 'listed_complete')}, v.get('plus1_bus_list', [])[:8], v.get('status', ''))
