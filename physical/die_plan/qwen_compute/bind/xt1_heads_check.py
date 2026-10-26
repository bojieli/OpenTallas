"""BINDER3: R8 head checks on a bound QC top (bind_sinks.json): tap.hw/cid -> xh0..3 landed depth per slice, and the
head -> column go (xh*.n_d / s_d sources) landed depth per sink.  Usage: xt1_heads_check.py BIND_OUT OUT.json"""
import json, re, sys, collections
s = json.load(open(sys.argv[1] + '/bind_sinks.json'))
tap = collections.defaultdict(set)
col = collections.defaultdict(lambda: collections.defaultdict(set))
for k, v in s.items():
    if v[0] != 'pin':
        continue
    m = re.match(r'(dvs_[EW]\d)\.u_core\.u_sub\.u_tap\.(hw|cid)\[', v[1])
    if m and re.search(r'\.u_xh\d\.', k):
        h = re.search(r'u_xh(\d)', k).group(1)
        tap[(m.group(1), m.group(2), 'hc' + h)].add(v[2])
    m = re.match(r'(dvs_[EW]\d)\.u_core\.u_sub\.u_xh(\d)\.(\w+)\[', v[1])
    if m and m.group(3) in ('n_d', 's_d'):
        col[(m.group(1), m.group(3))][re.sub(r'\[\d+\]$', '', k)].add(v[2])
slices = sorted({k[0] for k in tap})
tap_d = {f'{a}.{b}.{c}': sorted(v) for (a, b, c), v in sorted(tap.items())}
tap_all = sorted({x for v in tap.values() for x in v})
col_d = {f'{a}.{b}': sorted({x for v in d.values() for x in v}) for (a, b), d in sorted(col.items())}
out = dict(slices=len(slices), tap_entries=len(tap), tap_depths=tap_all,
           tap_pass=len(slices) == 12 and len(tap) == 12 * 2 * 4 and tap_all == [6],
           column_go={k: sorted({x for v in col_d.values() for x in v if k in ''}) for k in ()},
           n_d=sorted({x for (a, b), d in col.items() if b == 'n_d' for v in d.values() for x in v}),
           s_d=sorted({x for (a, b), d in col.items() if b == 's_d' for v in d.values() for x in v}),
           per_slice_column=col_d, per_tap=tap_d)
out.pop('column_go')
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('slices', 'tap_entries', 'tap_depths', 'tap_pass', 'n_d', 's_d')}))
