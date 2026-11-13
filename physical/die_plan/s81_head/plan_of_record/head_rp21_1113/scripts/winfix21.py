"""HEAD-97 rp21x: per-port tap windows re-derived from the ROUTED die clock gate on rp21x (HEAD-CLKGATE-1 recipe, intel1
head-97-clk it3 kitwin.json, plan 802d132f): for every type with a port whose need + 10 exceeds its window (hd_tile, hd_lep0N,
hd_spn_end), per_port = min(per_type, max(need + 10, 10)) on all its ports (rp20a winfix rule); other types untouched.
The kitwin plan may differ from SRC only inside hd_host_e (internal macro move after the gate ran; its tap ports unchanged)."""
import json, sys, hashlib, collections
src, base, kitwin, out = sys.argv[1:5]
d = json.loads(open(src, 'rb').read(), object_pairs_hook=collections.OrderedDict)
braw = open(base, 'rb').read(); b = json.loads(braw)
kw = json.load(open(kitwin))
assert kw['plan_sha256'] == hashlib.sha256(braw).hexdigest(), 'kitwin is not for the base plan'
diff = [k for k in d if k != 'partition_types' and d[k] != b.get(k)] + [t for t in d['partition_types'] if d['partition_types'][t] != b['partition_types'].get(t)]
assert set(diff) <= {'hd_host_e'}, diff
tw = d['clock']['tap_window']; ptype = tw.get('per_type_ps', {}); W0 = tw.get('window_ps', 10)
rep = {}
for t, need in sorted(kw['per_port_ps'].items()):
    cur = tw.get('per_port_ps', {}).get(t, {})
    extra = set(filter(None, __import__('os').environ.get('WF_EXTRA', '').split(',')))   # types re-derived on purpose (e.g. hd_spn: windows 36-70 vs need <= 9 -> rp20 GRT hold structural)
    if t not in extra and not any(n > cur.get(p, ptype.get(t, W0)) for p, n in need.items()):
        continue
    cap = ptype.get(t, 208)
    new = collections.OrderedDict()
    for p in list(cur) + sorted(set(need) - set(cur), key=lambda x: (len(x), x)):
        n = need.get(p)
        new[p] = float(min(cap, max(n + 10, 10))) if n is not None else cur[p]
    rep[t] = dict(ports=len(new), raised=sum(1 for p in new if new[p] > cur.get(p, ptype.get(t, W0))),
                  lowered=sum(1 for p in new if new[p] < cur.get(p, ptype.get(t, W0))), need_max=max(need.values()),
                  old_max=max(cur.values()) if cur else None, new_max=max(new.values()))
    tw.setdefault('per_port_ps', {})[t] = new
tw['per_port_note'] = (tw.get('per_port_note') or '') + (" | HEAD-97 rp21x 11-13: " + ", ".join(sorted(rep)) +
    " per_port_ps = min(per_type, max(need + 10, 10)) from the ROUTED die clock gate on rp21x 802d132f (it3 kitwin.json)")
s = json.dumps(d, indent=1) + '\n'
open(out, 'w').write(s)
print(json.dumps(rep)); print('sha256', hashlib.sha256(s.encode()).hexdigest())
