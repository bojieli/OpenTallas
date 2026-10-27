import json, sys, re, collections
from pathlib import Path
O = Path(sys.argv[1]); W = Path(sys.argv[2])
D = json.load(open(O / 'q2_q3_diff.json'))
ch = D['members_changed']
def d(x): return x['landed'][1] - x['landed'][0]
inbound = [x for x in ch if re.match(r'^(kvs_attn|kvs_ctl)\.d2d__', x['id'])]
emb = [x for x in ch if x['id'].startswith('kvs_emb.') or 'emb' in x['id'].split('<-')[1]]
host = [x for x in ch if x['id'].startswith('host.')]
print('inbound attn/ctl d2d changed:', [(x['id'], x['landed']) for x in inbound])
print('emb changed:', sorted({(x['id'].split('[')[0] + '<-' + x['id'].split('<-')[1], tuple(x['landed'])) for x in emb}))
print('host-sink changed:', len(host))
cls = collections.Counter()
for x in ch:
    s = x['id'].split('.')[0]
    cls[re.sub(r'_(EN|ES|WN|WS|\d+)\b', '', s.split('__')[0])[:24], ] += 1
print('changed sinks by leaf family:', cls.most_common(30))
# lane-class model kv_v39r_price on the folded lane delta (q3 - q2)
J2 = json.load(open(O / 'lat_q2/qwen_kvsys_latency.json'))['lanes']; J3 = json.load(open(O / 'lat_q3/qwen_kvsys_latency.json'))['lanes']
L = [dict(lane=k, src=v['src']['part'] + '.' + v['src']['bus'], dst=v['dst']['part'] + '.' + v['dst']['bus'], width=v['width'],
          delta=J3[k]['cycles'] - v['cycles']) for k, v in J2.items()]
json.dump(dict(lanes=L, note='TOK-QK-6 folded (base + r8_pad) lane cycles hm_r26q3 - hm_r26q2'), open(O / 'lane_delta_folded_q3_vs_q2.json', 'w'), indent=0)
