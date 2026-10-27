import json, sys, collections, re
O = sys.argv[1]
J = {k: json.load(open(f'{O}/lat_{k}/qwen_kvsys_latency.json')) for k in ('q2', 'q3')}
Lm = {k: json.load(open(f'{O}/lat_{k}/qwen_kvsys_r8_landing.json')) for k in ('q2', 'q3')}
a, b = J['q2']['lanes'], J['q3']['lanes']
print('lane keys sample', list(a.items())[0])
base = {l: b[l]['base'] - a[l]['base'] for l in a if b[l]['base'] != a[l]['base']}
fold = {l: b[l]['cycles'] - a[l]['cycles'] for l in a if b[l]['cycles'] != a[l]['cycles']}
print('base: lanes', len(base), 'sum', sum(base.values()), collections.Counter(base.values()))
print('folded: lanes', len(fold), 'sum', sum(fold.values()), collections.Counter(fold.values()))
ma = {m['id']: m for m in Lm['q2']['members']}; mb = {m['id']: m for m in Lm['q3']['members']}
assert ma.keys() == mb.keys()
ch = [dict(id=i, lane=ma[i]['lane'], sink_part=ma[i]['sink_part'], src_part=ma[i]['src_part'], landed=[ma[i]['landed'], mb[i]['landed']],
           bound=[ma[i]['bound'], mb[i]['bound']], pad=[ma[i]['pad'], mb[i]['pad']]) for i in ma if ma[i]['landed'] != mb[i]['landed']]
print('members landed changed', len(ch), collections.Counter(x['landed'][1] - x['landed'][0] for x in ch))
def grp(rx):
    s = [x for x in ch if re.search(rx, x['id'])]
    return dict(n=len(s), max=max((x['landed'][1] - x['landed'][0] for x in s), default=0), ids=[x['id'] for x in s][:6])
G = dict(attn_tx=grp(r'^d2d_kv\.att_tx_'), d2d_rx=grp(r'kvs_attn\.d2d__rx_payload|d2d__srx|<-d2d_kv\.'), pv=grp(r'^pvw?_|\bpv'),
         vport=grp(r'vport|slg'), ahub_astk=grp(r'ahub|astk'), hroot_seq=grp(r'hroot|seq'), acal=grp(r'acal'), emb=grp(r'emb'))
for k, v in G.items(): print(k, v)
# all attention-tx members (unchanged ones too)
tx = [(i, ma[i]['landed'], mb[i]['landed']) for i in ma if i.startswith('d2d_kv.att_tx_')]
print('att_tx members', tx)
json.dump(dict(base_lane_delta=base, folded_lane_delta=fold, members_changed=ch, groups=G, att_tx=tx), open(f'{O}/q2_q3_diff.json', 'w'), indent=1)
