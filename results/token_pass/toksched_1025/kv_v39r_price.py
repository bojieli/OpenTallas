#!/usr/bin/env python3
"""TOK-SCHED 10-25 (c): price the KV plan v3.9r lane-cycle table (PATH-KV-REBASE claude/path-kv-rebase-1025@3832299dfb,
839 lanes vs main lat_v39pd) and KV LAT_L663 on the Qwen ROM token path (ledger design qwen_rom).

No KV static calendar on main consumes per-lane plan cycles (the KV die schedule is hardened RTL parameters: d2d landed
bundles, ECTLK RESPONSE_LAT, PV_W port equalisation, kvs_attn programme).  So this is a lane-class model, the same form
KV-405 used for v3.9 ("d2d<->kvs_attn round trip ~+44 cyc/layer"):
  per attention request (36 a token, node L<k>.attn_kv):  d2d rx bundle sys_c -> hub_C (max delta, one landed bundle)
                                                          + kvs_attn tx bundle hub_C -> sys_c (max delta)
  per token (node embed, the embedding row fetch):        d2d rx bundle + hub_Wi -> hub_Wo px hop + the WORST PC
                                                          broadcast chain hub_Wo -> pc_*_7 .. pc_*_0 (est / tep / tok,
                                                          parallel chains, max) + emb tx slot sys_c -> hub_Wi
                                                          + row tx hub_Wi -> sys_c (serial sum: upper bound)
  interior attention lanes (vport/slg, pv rows/pvw, ahub/astk, hroot/hsl, acal fan): NOT priced -- they are padded to
  hardened equalisation budgets; their bound if every family were serial once per request is reported as the bracket.
  L663 hub_Wi.o_host_fdi -> io_W3.i_host_fdi (host FDI, 1044 b): the host link carries boot / admission / host IO; the
  token path DAG has no host node (embedding -> 36 layers -> LM head on die) -> 0 token cycles.

    kv_v39r_price.py <lane_cycle_delta_vs_main.json> <out.json>
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from throughput import accepted_cost as ac  # noqa: E402

src, out = sys.argv[1:3]
L = json.loads(Path(src).read_text())['lanes']


def sel(rx_src, rx_dst):
    return [l for l in L if re.search(rx_src, l['src']) and re.search(rx_dst, l['dst'])]


def mx(ls):
    return max((l['delta'] for l in ls), default=0)


rx_bundle = sel(r'^sys_c\.o_dNd_kv_', r'^hub_C\.i_dNd_kv_')                  # d2d rx landed bundle (q / ctl / kvn)
attn_tx = sel(r'^hub_C\.o_kvs_attn_attn__tx', r'^sys_c\.')                     # attention result tx bundle
emb_slot = sel(r'^sys_c\.o_dNd_kv_emb_tx_slot', r'^hub_Wi\.')
emb_hop = sel(r'^hub_Wi\.o_kvs_emb_px_tep_d1', r'^hub_Wo\.')
emb_rowtx = sel(r'^hub_Wi\.o_kvs_emb_rowtx__', r'^sys_c\.')
chains = defaultdict(int)
for l in L:
    m = re.search(r'(embgw_est|kvs_emb_px_tep|kvs_emb_px_tok)', l['src'])
    q = re.search(r'pc_(EN|ES|WN|WS)_\d', l['dst'])
    if m and q and re.search(r'^(hub_[EW]o|pc_)', l['src']):
        chains[(m.group(1), q.group(1))] += l['delta']
per_layer = mx(rx_bundle) + mx(attn_tx)
worst_chain = max(chains.values(), default=0)
per_token_embed = mx(rx_bundle) + mx(emb_hop) + worst_chain + mx(emb_slot) + mx(emb_rowtx)

fam_rx = [('vport_slg', r'(vport|slg|vq|vreq|in0_|rsp)'), ('pv_rows', r'(pvw|pvr|_pv|row|kv_rd|kvrd)'),
          ('ahub_astk', r'(ahub|astk|_am|_ap)'), ('seq_hroot_hsl', r'(seq|hroot|hsl|hslice|fan|xs)'),
          ('acal', r'acal')]
OFF = r'(fault|flt|health|boot|cfg|obs|dbg|rst|reset|scan|stat|host)'
interior = {}
for n, rx in fam_rx:
    ls = [l for l in L if re.search(rx, l['src'] + ' ' + l['dst']) and not re.search(OFF, l['src'] + l['dst'])
          and l not in rx_bundle + attn_tx]
    interior[n] = dict(lanes=len(ls), max_delta=mx(ls))
interior_serial_per_layer = sum(v['max_delta'] for v in interior.values())

doc = json.loads((ac.TP / 'qwen_rom.json').read_text())
nodes, edges = doc['nodes'], doc['edges']
base, _ = ac.solve(nodes, edges)


def price(per_attn, per_embed):
    delta = {n['id']: per_attn for n in nodes if re.fullmatch(r'L\d+\.attn_kv', n['id'])}
    delta['embed'] = per_embed
    new, _ = ac.solve(nodes, edges, delta)
    return dict(base_cycles=round(base, 1), cycles=round(new, 1), added_cycles=round(new - base, 1),
                tok_s_before=round(1.2e9 / base, 1), tok_s_after=round(1.2e9 / new, 1), e2e_loss_pct=round(ac.loss_pct(base, new), 3))


l663 = [l for l in L if l['lane'] == 'L663']
res = dict(
    schema='opentallas.toksched.kv_v39r_price.v1',
    source='claude/path-kv-rebase-1025@3832299dfb results/arch/kv_plan_0719/rebase1025/lane_cycle_delta_vs_main.json '
           '(839 lanes, lat_v39r vs main 183f0b03b9 lat_v39pd)',
    model='lane-class model on the token-path DAG results/arch/token_path_20261009/qwen_rom.json (accepted_cost.solve); '
          'clock 1.2 GHz as the DAG record',
    per_attention_request=dict(d2d_rx_bundle_max=mx(rx_bundle), d2d_rx_lanes=[l['lane'] for l in rx_bundle],
                               kvs_attn_tx_max=mx(attn_tx), kvs_attn_tx_lanes=[l['lane'] for l in attn_tx],
                               cycles=per_layer, requests_per_token=36),
    per_token_embed=dict(d2d_rx=mx(rx_bundle), px_hop=mx(emb_hop), worst_pc_chain=worst_chain,
                         chains={f'{a}:{b}': v for (a, b), v in sorted(chains.items())}, emb_tx_slot=mx(emb_slot),
                         row_tx=mx(emb_rowtx), cycles=per_token_embed, basis='serial sum, upper bound'),
    L663=dict(rebased_lane=l663, main_plan='34 -> 42 (claude/path-kv-obst-1025 a9faecc2ab, head-macro station fix)',
              token_cycles=0, basis='host FDI (hub_Wi -> io_W3): boot / admission / host IO lane; no host node on the '
                                    'token path DAG; the decode loop (embed -> 36 layers -> LM head) never waits on it'),
    interior_unpriced=dict(families=interior, serial_bound_per_layer=interior_serial_per_layer,
                           basis='hardened equalisation budgets (PV_W, ECTLK RESPONSE_LAT, landed bundles) absorb these '
                                 'only while the new lane cycles stay inside the budget; not checked here'),
    priced=dict(ar=price(per_layer, per_token_embed)),
    bracket_upper=dict(ar=price(per_layer + interior_serial_per_layer, per_token_embed)),
)
Path(out).write_text(json.dumps(res, indent=1) + '\n')
print(json.dumps({k: res[k] for k in ('per_attention_request', 'per_token_embed', 'priced', 'bracket_upper')}, indent=1))
print('interior', json.dumps(res['interior_unpriced']['families']))
