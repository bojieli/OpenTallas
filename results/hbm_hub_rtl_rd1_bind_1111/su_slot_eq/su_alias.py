"""Name the gold (cached, memory_map'd) g_inj.slot[k] register outputs g_inj.slotK so equiv_make pairs them with the
gate's explicit registers g_inj.slot0..3 (HBM-HUB-RTL-1 11-12)."""
import json, re, sys
d = json.load(open(sys.argv[1])); g = d['modules']['gold']; n = 0
for c, v in g['cells'].items():
    m = re.fullmatch(r'\$memory\\g_inj\.slot\[(\d)\]\$\d+', c)
    if m and v['type'] == '$dff':
        g['netnames']['g_inj.slot' + m.group(1)] = dict(hide_name=0, bits=v['connections']['Q'], attributes={}); n += 1
assert n == 4, n
json.dump(d, open(sys.argv[2], 'w')); print('aliased', n)
