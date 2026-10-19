#!/usr/bin/env python3
"""S81-DV price: per-user AR / MTP tok/s of the distributed-vector die vs the current hub die.

Method (same machinery as the ledger, tools/throughput/accepted_cost.py + tools/s81/mtp_ledger_1016.py):
  1. Token-path DAGs results/arch/token_path_20261009/ds_rom{,_mtp}.json; joint longest-path solve with per-node
     deltas (accepted_cost.solve); the MTP wavefront rule of accepted_cost.rom_loss (the slowest verify stage's
     added cycles are paid once more per wave.busy node).
  2. Ledger rows that are hub-implementation costs (VM.*, SU.*, HC.*, CAPT.CD_PINREG) are DROPPED: the units they
     price do not exist in DV.  Every other row (field return tree, cfg7, Engram lookup, MIX4, MTP p2) is KEPT.
  3. DV deltas, each from the node's own recorded composition + the DV plan geometry (dv_plan.py facts):
       hub-in/out:  SU nodes carrying 'hub in 33 / out 23'           -56 + PINREG
       hub-wired:   SU nodes carrying 'BCAST 22 / RET 15'            -37 + PINREG
       hub-slab:    SU 'r8 hub-slab stations' adders (3.333/0.833 ns) removed (-4 / -1)
       norm tree:   full-h RMS norms: hub RW 9 + BW 9 removed, + the mesh exchange of golden-subtree partial roots
                    (worst slice->slice, plan stages); q_lora norm over 4 adjacent slices; kv norm in <= 2 slices
       field wire:  'r8 die wire X cyc over N phases' scaled by DV phase path / DAG basis path (138 cyc)
       attention:   q heads slice -> PHY-side attention: + (DV worst - hub VM->svc) stages on attn.q_rope
       router:      scores slice -> G-unit tree on ffn.top6_order
       h transfer:  HC.H_XFER (246, dropped) replaced by ring-to-edge exit + entry on substage_hop0 / head.hop
     Collectives are left unchanged (conservative: ring end slices sit at the edge links, as far as the hub was).
  4. rate = hop_only(stages) * (1 - (kept ledger % + DV DAG loss %)/100), the mtp_ledger_1016 additive rule.
  5. LANDING (S81-LAND2, lanes/LANDING-CONTRACT.md L4; --land-plan): a forwarded-clock lane costs N stations + 1 ring
     + E handoff + 1 block flop.  The geometric rules above charge st(um) = ceil(um / hop) ~ N + 1 (stations + the
     block flop), so each LANDED link traversal on a priced path adds 1 + E (zero-stage links: no landing, +0).
     Paths are routed on the plan's link graph (blocks = nodes, links = edges weighted stages + 1); each rule takes
     the worst pair the rule's geometry names (same endpoints), and sums 1 + E over its landed links:
       field_phase_wire  per phase: worst slice -> frame (all-gather) + worst frame -> slice (ret)
       norm_tree_full    worst slice -> slice;  norm_tree_q  3 slice columns;  norm_tree_kv  1 slice column
       attn_q_path       worst slice -> its half's q entry (rsv_05 / rsv_11);  router_tree  worst slice -> gunit
       h_xfer_ring       2 x worst slice -> nearest end slice (out and back);  hbm_ctrl_rt  worst hrq + hrd pair
     --half-cycle: half-cycle hops (ck_o = ~ck), each relay station costs T/2: the same paths also credit
     -stations/2, and E comes from the half-cycle pilot's land_plan.json.
  6. HOST PLANE (p4l, S81-DIE7/PRICE; --land-plan): the kit start f_ks {start, user, token, pos} and the kit done t_kd
     {done, next_token} ride the cross-die link's host plane at end slice s_7N and reach dsdv_seq_host over the
     dedicated lanes hf_7N_l0..2 (in) / ht_7N (out).  The hub DAG has no such lane (the kit sat at the link), and no
     rule above routes through seqhost, so the lanes are priced here, one traversal =
        stations (T/2 each with --half-cycle, else T) + 1 block flop [+ 1 + E when landed]
     + the seq_host fixed latencies (tb_dsdv_seq_host: f_ks capture -> issuer +3, command register +1, V command ->
       vo pin +7 = 11 in;  issuer KIT -> t_kd pin +3 out).
     Serial classes (scenarios):
       host_token  once per token (per MTP wave): the embed stage's start carries the sampled token (in) and the
                   head stage's done carries next_token (out) -> + in on 'embed', + out on 'head.argmax_merge'.
       host_stage  sensitivity only: every stage's start waits for its f_ks AFTER the h message has landed (+ in on
                   every substage_hop / head.hop).  The built protocol hides it: the upstream kit emits its done
                   before the hop op completes (dsfd_stage_seq_c8 KDX 7: the hop is the kit's hidden hand-off), so the
                   downstream f_ks travels beside the 40,976-B h message (652 serialization cycles) and lands first.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from throughput import accepted_cost as ac          # noqa: E402

TP = ROOT / 'results/arch/token_path_20261009'
LEDGER = ROOT / 'results/arch/accepted_cost_ledger_1013.json'
HOP = 1004 + 171 / 84
# KP4 FEC in the stage hop (S81-SMHKP4 / NATIVE-REF 10-18): HOP's board channel is 251 cycles = 209 ns
# (configs/hardware/technology.json links.rom_board_serdes hop_latency_s: channel 200 ns incl. RS(544,514) encode +
# decode ~80-100 ns, + CDC 4 ns + digital endpoint).  The on-die RTL decoder ot_s81_kp4_dec (claude/smhkp4-1018:
# flow pin_regs +1 in / +1 out) is 68 cycles p_d -> q_d (was 66; RTL 60 + tile pin registers) = 56.7 ns at 833.3 ps,
# inside the channel's FEC share, so HOP (and every price here) is unchanged by the +2; kp4_check() keeps it so.
T_PS = 833.333
KP4_DEC_HW_CYCLES = 68
KP4_FEC_SHARE_NS = (80.0, 100.0)     # encode + decode share of the 200 ns channel (technology.json note)


def kp4_check(dec_cycles=KP4_DEC_HW_CYCLES):
    """the RTL KP4 decode latency (ns) and whether it fits the FEC share the hop price assumes"""
    ns = dec_cycles * T_PS / 1000.0
    return dict(kp4_dec_cycles=dec_cycles, kp4_dec_ns=round(ns, 1), fec_share_ns=KP4_FEC_SHARE_NS,
                within_hop_price=ns <= KP4_FEC_SHARE_NS[0])
ANCHOR = {'ar': (1447.7, 1.0), 'mtp': (4238.4, 4.159)}
DROP = re.compile(r'^(VM|SU|HC)\.|^CAPT\.CD_PINREG$')
BASIS_PHASE = 138.0          # results/rtl/dsrom_field_reprice_r8_20261006 f183.60: farthest-frame round trip
HUB_VM_TO_SVC_STAGES = 50    # c26l sp_vm centre -> svc_SW centre ~20 mm at 405 um
# measured (tb_s81dv_xfin16, results/rtl/s81_dv_1016): last partial -> rstd 234 cycles with the sequenced dataflow finish
# vs 171 with the parallel tree the hub's price already contains -> +63 on every full-h norm (rstd precedes the matvec:
# norm-after-matvec is AGENTS level 6, excluded, so this latency is on the critical path)
FINISH_SEQ_EXTRA = 234 - 171
LEAF_PARTIAL_EXTRA = (112 + 4 + 5) - 100
LEAF_SCALE_EXTRA = (59 + 4 * 4 + 4) - 76
# RTL-BUILD-S81 (owner 0dv 10-18): mix4_half deleted; the Engram mix is the in-slice op ENG (ve beat sub-leaf + xfin ENG
# + ot_s81sl_eg scalar finish; results/arch/s81_dv_1016/p4j/engram_mix_verdict.json build_plan.cycle_estimate).  With
# --eng-slice the eng.* chain nodes are REPLACED (absolute, not a hub delta) by the slice-op terms; ESTIMATES except
# ve reduce 129 / add 44 (measured tb_s81sl_ve) until the slice composition bench measures them:
#   eng.hh   = ve reduce 129 (meas.) + partial -> xfin DL 4 + collector 5           = 138
#   eng.dot  = 0: dd = csum((h*w)*k) is summed in the same ve reduce pass as hh / kk
#   eng.gate = exchange 111 + finish 270 + scalar chain 175 + gate -> leaves 8      = 564 (est.)
#   eng.add  = ve add 44 (meas.) + write-back 11                                    = 55
ENG_SLICE_EST = {'eng.hh': 138.0, 'eng.dot': 0.0, 'eng.gate': 564.0, 'eng.add': 55.0}
ENG_SLICE = False


def hop_only(stages):
    add = (stages - 81) * HOP / 1200
    return {wl: t * 1e6 / (t * 1e6 / a + add) for wl, (a, t) in ANCHOR.items()}


def dv_deltas(doc, g, pinreg=8, su_scale=0.0, basis_scale=1.0, hbm_rt=False, host=()):
    """per-node delta (cycles) and a per-rule audit"""
    st = lambda um: math.ceil(um / g['hop_um'])
    xchg = g['scalar_exchange_stages']
    rules = {}
    d = {}

    def add(nid, rule, v):
        d[nid] = d.get(nid, 0.0) + v
        r = rules.setdefault(rule, dict(nodes=0, cycles=0.0))
        r['nodes'] += 1; r['cycles'] += v
    r_phase = g['phase_path_stages'] / (BASIS_PHASE * basis_scale)
    LR = (g.get('landing') or {}).get('rule_cycles')
    for n in doc['nodes']:
        note = n.get('src', {}).get('note', '') or ''
        op, nid, cls = n.get('op', ''), n['id'], n.get('cls')
        if ENG_SLICE and op in ENG_SLICE_EST:
            add(nid, 'eng_slice_est', ENG_SLICE_EST[op] - n['cycles'])
            continue
        if cls == 'su':
            if 'hub in 33 / out 23' in note:
                add(nid, 'hub_in_out', -56 + pinreg)
            if 'BCAST 22 / RET 15' in note:
                add(nid, 'hub_wired', -37 + pinreg)
            k = note.count('hub-slab stations 3.333 ns')
            if k:
                add(nid, 'hub_slab', -4 * k)
            k = note.count('hub-slab stations 0.833 ns')
            if k:
                add(nid, 'hub_slab', -1 * k)
            if op in ('attn.quant', 'ffn.norm.scale', 'eng.gate') or op.endswith('hc.sumsq'):
                add(nid, 'norm_tree_full', -18 + xchg)
                add(nid, 'norm_finish_seq', FINISH_SEQ_EXTRA)
                # S81-SLICE measured beat leaf (10-17, real vp+vn+vq RTL, bit-exact): go -> beat partial 112 + DL 4 +
                # collector 5 = 121 vs the hub's sumsq 100; rstd -> XQ complete at the ring stop 59 + 4*4 (last leaf)
                # + DL 4 = 79 vs the hub's scale 76.  hc_post (63 leaf vs 641 hub) NOT credited until slice-level.
                add(nid, 'leaf_measured', LEAF_PARTIAL_EXTRA + LEAF_SCALE_EXTRA)
            elif op == 'attn.q_quant':
                add(nid, 'norm_tree_q', -18 + st(3 * g['cluster_pitch_um']))
            elif op == 'attn.kv_rope_qdq':
                add(nid, 'norm_tree_kv', -18 + st(g['cluster_pitch_um']))
            if su_scale:
                add(nid, 'su_contingency', su_scale * n['cycles'])
        m = re.search(r'r8 die wire (\d+(?:\.\d+)?) cyc over (\d+) phase', note)
        if m and cls == 'field':
            add(nid, 'field_phase_wire', float(m.group(1)) * (r_phase - 1.0))
            if LR:
                add(nid, 'land_field_phase', int(m.group(2)) * LR['field_phase'])
        if LR and cls == 'su':
            if op in ('attn.quant', 'ffn.norm.scale', 'eng.gate') or op.endswith('hc.sumsq'):
                add(nid, 'land_norm_tree_full', LR['norm_tree_full'])
            elif op == 'attn.q_quant':
                add(nid, 'land_norm_tree_q', LR['norm_tree_q'])
            elif op == 'attn.kv_rope_qdq':
                add(nid, 'land_norm_tree_kv', LR['norm_tree_kv'])
        if LR and op == 'attn.q_rope':
            add(nid, 'land_attn_q_path', LR['attn_q_path'])
            if hbm_rt and g.get('hbm_rt_stages'):
                add(nid, 'land_hbm_ctrl_rt', LR['hbm_ctrl_rt'])
        if LR and op == 'ffn.top6_order':
            add(nid, 'land_router_tree', LR['router_tree'])
        if LR and re.search(r'(substage_hop\d+|head\.hop)$', nid):
            add(nid, 'land_h_xfer_ring', LR['h_xfer_ring'])
        if op == 'attn.q_rope':
            add(nid, 'attn_q_path', st(g['worst_slice_to_attention_um']) - HUB_VM_TO_SVC_STAGES)
        if hbm_rt and op == 'attn.q_rope' and g.get('hbm_rt_stages'):
            # p4g sensitivity: the farthest regional HBM controller's rq + rd stations, charged once per attention
            # pass as if the KV read were NOT issued ahead (static schedule normally prefetches it)
            add(nid, 'hbm_ctrl_rt', g['hbm_rt_stages'])
        if op == 'ffn.top6_order':
            add(nid, 'router_tree', st(g['worst_slice_to_gunit_um']))
        if g.get('slice_leaves'):
            # p4: the slice is a cluster of `slice_leaves` leaves (one 64-lane beat each), ring stop + xfin in the
            # middle leaf; registered leaf-to-leaf hops: lm = middle <-> outer leaf, ld = outer <-> outer
            lh = g['leaf_um'][1]
            lm = st((g['slice_leaves'] - 1) / 2 * lh); ld = st((g['slice_leaves'] - 1) * lh)
            if m and cls == 'field':
                add(nid, 'intra_slice_leaf', int(m.group(2)) * (ld + 2 * lm))   # return to owner + x to/from ring stop
            if cls == 'su' and op in ('attn.quant', 'ffn.norm.scale', 'attn.q_quant', 'attn.kv_rope_qdq', 'eng.gate'):
                add(nid, 'intra_slice_leaf', 2 * lm)                            # partial to xfin leaf, rstd back
        if g.get('tier_w'):
            # p4c per-column tier exchange vs p4b end-column ring: the N tier needs the S tier's 40 beats; p4b moves
            # them over 2 x 1,104-b end links (~20 cycles of serialization each), p4c over 8 x tier_w-bit links
            # (5 x 1,104 / tier_w cycles per column); + up to 2 registered unit ring stops (+4) on the crossing
            cross = 5 * 1104 / g['tier_w'] - 20 + 4
            if m and cls == 'field':
                add(nid, 'tier_cross', int(m.group(2)) * max(0.0, cross))
            if cls == 'su' and op in ('attn.quant', 'ffn.norm.scale', 'eng.gate'):
                add(nid, 'tier_cross', 4 + math.ceil(173 / g['tier_w']) - 1)   # partial flit + unit stops
        if re.search(r'(substage_hop\d+|head\.hop)$', nid):
            add(nid, 'h_xfer_ring', 2 * st(g['worst_slice_to_edge_um']))
        HP = g.get('host_plane')
        if HP and 'token' in host and op == 'embed':
            add(nid, 'host_token_in', HP['in_cycles'])
        if HP and 'token' in host and op == 'head.argmax_merge':
            add(nid, 'host_token_out', HP['out_cycles'])
        if HP and 'stage' in host and re.search(r'(substage_hop\d+|head\.hop)$', nid):
            add(nid, 'host_stage_in', HP['in_cycles'])
    return d, rules


def host_terms(plan, land, half=False, landed=True):
    """one traversal of the host plane in / out (worst lane), cycles (module docstring item 6)"""
    E = {l['link']: (l.get('K') or l['E']) for l in land['links']}   # S81-LBGAP/G8: the landing latency is K + 1
    lanes = {l['i'].replace('-', '_'): l['s'] for l in plan['links'] if l['i'].startswith(('hf_', 'ht_'))}
    if not lanes:
        return None
    one = lambda nm: (lanes[nm] / 2 if half else lanes[nm]) + 1 + ((1 + E[nm]) if landed else 0)
    fin = max((nm for nm in lanes if nm.startswith('hf_')), key=one)
    fout = max((nm for nm in lanes if nm.startswith('ht_')), key=one)
    SEQ_IN, SEQ_OUT = 3 + 1 + 7, 3
    return dict(landed=landed, half_cycle=half, in_link=fin, in_stations=lanes[fin], in_E=E[fin],
                out_link=fout, out_stations=lanes[fout], out_E=E[fout], seq_in=SEQ_IN, seq_out=SEQ_OUT,
                in_cycles=one(fin) + SEQ_IN, out_cycles=one(fout) + SEQ_OUT,
                in_landing_cycles=(1 + E[fin]) if landed else 0, out_landing_cycles=(1 + E[fout]) if landed else 0)


def land_terms(plan, land, half=False):
    """per rule: added cycles per traversal (+ sum(1 + E) over landed links, - stations / 2 if half) and the path"""
    import collections, heapq
    B = plan['blocks']
    E = {l['link']: (l.get('K') or l['E']) for l in land['links']}   # S81-LBGAP/G8: the landing latency is K + 1
    G = collections.defaultdict(dict)
    for l in plan['links']:
        a, b = B[l['e'][0][0]]['name'], B[l['e'][1][0]]['name']
        nm = l['i'].replace('-', '_')
        if l['s'] > 0 and nm not in E:
            raise SystemExit(f'dv_price: landed link {nm} has no E in the land plan')
        x = (1 + E[nm]) if l['s'] > 0 else 0
        if b not in G[a] or G[a][b][0] > l['s'] + 1:
            G[a][b] = (l['s'] + 1, x, l['s'], nm)
    memo = {}

    def sp(src):
        if src not in memo:
            d = {src: (0, 0, 0, ())}
            q = [(0, src)]
            while q:
                w, u = heapq.heappop(q)
                if d[u][0] < w:
                    continue
                for v, (ww, xx, ss, nm) in G[u].items():
                    if v not in d or d[v][0] > w + ww:
                        d[v] = (w + ww, d[u][1] + xx, d[u][2] + ss, d[u][3] + (nm,))
                        heapq.heappush(q, (w + ww, v))
            memo[src] = d
        return memo[src]

    def worst(pairs):
        best = None
        for a, b in pairs:
            r = sp(a).get(b)
            if r is None:
                continue
            key = (r[0], r[1])
            if best is None or key > best[0]:
                best = (key, dict(src=a, dst=b, edges=r[0], landing=r[1], stations=r[2], links=list(r[3])))
        return best[1]

    def nearest(a, targets):
        return min(((sp(a)[t][0], t) for t in targets if t in sp(a)))[1]
    sl = [b['name'] for b in B if b['kind'] == 'slice']
    fr = [b['name'] for b in B if b['kind'] == 'frame']
    ends = [n for n in ('s_0S', 's_0N', 's_7S', 's_7N') if n in sl]
    entry = [n for n in ('rsv_05', 'rsv_11') if any(x['name'] == n for x in B)]
    col = lambda n: int(n[2])
    paths = dict(
        ag=worst((s_, f) for s_ in sl for f in fr),
        ret=worst((f, nearest(f, sl)) for f in fr),
        ss=worst((a, b) for a in sl for b in sl if a != b),
        q3=worst((a, b) for a in sl for b in sl if a[-1] == b[-1] and abs(col(a) - col(b)) == 3),
        kv1=worst((a, b) for a in sl for b in sl if a[-1] == b[-1] and abs(col(a) - col(b)) == 1),
        attn=worst((s_, nearest(s_, entry)) for s_ in sl),
        gunit=worst((s_, 'gunit') for s_ in sl),
        edge_out=worst((s_, nearest(s_, ends)) for s_ in sl if s_ not in ends),
        edge_back=worst((nearest(s_, ends), s_) for s_ in sl if s_ not in ends))
    hb = {}
    for l in plan['links']:
        if l['i'].startswith(('hrq_', 'hrd_')) and l['s'] > 0:
            k = l['i'][4:]
            r = hb.setdefault(k, dict(landing=0, stations=0, links=[]))
            r['landing'] += 1 + E[l['i']]; r['stations'] += l['s']; r['links'].append(l['i'])
    if hb:
        paths['hbm'] = max(hb.values(), key=lambda r: (r['stations'], r['landing']))
    cyc = lambda r: r['landing'] - (r['stations'] / 2 if half else 0.0)
    for r in paths.values():
        r['added_cycles'] = cyc(r)
    rule = dict(field_phase=cyc(paths['ag']) + cyc(paths['ret']), norm_tree_full=cyc(paths['ss']),
                norm_tree_q=cyc(paths['q3']), norm_tree_kv=cyc(paths['kv1']), attn_q_path=cyc(paths['attn']),
                router_tree=cyc(paths['gunit']), h_xfer_ring=cyc(paths['edge_out']) + cyc(paths['edge_back']),
                hbm_ctrl_rt=cyc(paths['hbm']) if 'hbm' in paths else 0.0)
    return dict(half_cycle=half, rule_cycles=rule, paths=paths, E_hist=land.get('summary', {}).get('E_hist'))


def solve_with_wave(doc, delta):
    nodes, edges = doc['nodes'], doc['edges']
    base, _ = ac.solve(nodes, edges)
    delta = dict(delta)
    wave = [n['id'] for n in nodes if n.get('op') == 'wave.busy']
    if wave:
        stages = [x for x in doc.get('groups', []) if x.get('kind') in ('stage', 'layer', 'embed')]
        worst = max(stages, key=lambda x: x['cycles'])['id']
        wadd = sum(delta.get(n['id'], 0.0) for n in nodes if n.get('group') == worst)
        for i in wave:
            delta[i] = delta.get(i, 0.0) + wadd
    new, _ = ac.solve(nodes, edges, delta)
    return base, new


def ledger_split(path=LEDGER, drop=None):
    drop = drop if drop is not None else DROP
    led = json.loads(Path(path).read_text())
    kept, dropped = {'ar': 0.0, 'mtp': 0.0}, {'ar': 0.0, 'mtp': 0.0}
    rows = []
    for r in led['rows']:
        # superseded = a retired hub-design row (accepted_cost.py supersede): it is in the current hub-die baseline
        # (dropped side), never in the DV kept total.  S81.DV_* rows are this tool's own DV terms (landing, ...):
        # dv_price computes them, so counting the ledger copy too would charge them twice.
        if r['design'] != 's81' or r.get('status') not in ('accepted', 'proposed', 'superseded'):
            continue
        if r['group'].startswith('S81.DV_'):
            continue
        is_drop = r['status'] == 'superseded' or bool(drop.search(r['group']))
        tgt = dropped if is_drop else kept

        for wl in ('ar', 'mtp'):
            tgt[wl] += (r.get('per_workload', {}).get(wl) or {}).get('e2e_loss_pct', 0.0) or 0.0
        rows.append(dict(group=r['group'], status=r['status'], dropped=is_drop,
                         ar=(r.get('per_workload', {}).get('ar') or {}).get('e2e_loss_pct'),
                         mtp=(r.get('per_workload', {}).get('mtp') or {}).get('e2e_loss_pct')))
    return kept, dropped, rows


def price(g, stages=89, pinreg=8, su_scale=0.0, frames=128, drop=None, basis_scale=1.0, hbm_rt=False, host=()):
    kept, dropped, rows = ledger_split(drop=drop if drop is not None else DROP)
    st_eff = stages * 128 / frames if frames != 128 else stages
    ho = hop_only(89)
    ho_dv = hop_only(math.ceil(st_eff))
    out = dict(stages=stages, dv_stages=math.ceil(st_eff), frames=frames, pinreg=pinreg, su_contingency=su_scale,
               ledger_kept_pct=kept, ledger_dropped_pct=dropped, workloads={})
    for wl, name in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')):
        doc = json.loads((TP / f'{name}.json').read_text())
        delta, rules = dv_deltas(doc, g, pinreg, su_scale, basis_scale, hbm_rt, host)
        base, new = solve_with_wave(doc, delta)
        dv_loss = ac.loss_pct(base, new)
        cur = ho[wl] * (1 - (kept[wl] + dropped[wl]) / 100)
        dv = ho_dv[wl] * (1 - (kept[wl] + dv_loss) / 100)
        out['workloads'][wl] = dict(base_cycles=round(base, 1), dv_cycles=round(new, 1), dv_dag_loss_pct=round(dv_loss, 3),
                                    hop_only=round(ho[wl], 1), current_tok_s=round(cur, 1), dv_tok_s=round(dv, 1),
                                    change_vs_current_pct=round(100 * (dv / cur - 1), 2),
                                    rules={k: dict(nodes=v['nodes'], cycles=round(v['cycles'], 1)) for k, v in rules.items()})
    out['ledger_rows'] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True, help='dv_plan.py plan.json (facts)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--land-plan', default=None, help='dv_land_pilot land_plan.json: price N + 2 + E per landed lane')
    ap.add_argument('--half-cycle', action='store_true', help='half-cycle hops (stations cost T/2); use the half-cycle land plan')
    ap.add_argument('--eng-slice', action='store_true', help='0dv: Engram mix = slice op ENG (ENG_SLICE_EST replaces the eng.* chain; MIX4.* ledger rows dropped: the units are deleted)')
    a = ap.parse_args()
    global ENG_SLICE, DROP
    if a.eng_slice:
        ENG_SLICE = True
        DROP = re.compile(DROP.pattern + r'|^MIX4\.')
    plan = json.loads(Path(a.plan).read_text())
    f = plan['facts']
    B = {b['name']: b for b in plan['blocks']}
    cen = lambda b: (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
    sl = [b for b in plan['blocks'] if b['kind'] == 'slice']
    man = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    g = dict(f, hop_um=f.get('hop_um', 405.0),
             worst_slice_to_gunit_um=max(man(cen(s), cen(B['gunit'])) for s in sl),
             # p4i: coll_edge deleted -> the cross-die link endpoints are the 4 end slices (dsdv_slice_lep)
             worst_slice_to_edge_um=max(min(man(cen(s), cen(B[c])) for c in (('coll_WS', 'coll_WN', 'coll_ES', 'coll_EN')
                                        if 'coll_WS' in B else ('s_0S', 's_0N', 's_7S', 's_7N'))) for s in sl))
    hl = {l['i']: l['s'] for l in plan['links'] if l['i'].startswith(('hrq_', 'hrd_'))}
    if hl:
        g['hbm_rt_stages'] = max(hl.get(f'hrq_{k}', 0) + hl.get(f'hrd_{k}', 0) for k in {i[4:] for i in hl})
    # ROM capacity per die scales the stage count (owner-approved lever: fewer ROMs per die, more dies)
    st = math.ceil(89 * f.get('rom_slots_c26l', 1220) / f.get('rom_slots', 1220) - 1e-9)
    g['stages_from_slots'] = st
    if a.land_plan:
        g['landing'] = dict(land_terms(plan, json.loads(Path(a.land_plan).read_text()), a.half_cycle), land_plan=a.land_plan)
    res = dict(schema='opentallas.s81_dv.price.v1', geometry=g, status='COMPOSED_NOT_NATIVE',
               scenarios={
                   'dv_base': price(g, stages=st),
                   'dv_pinreg16': price(g, stages=st, pinreg=16),
                   'dv_su_plus10pct': price(g, stages=st, su_scale=0.10),
                   'dv_su_plus25pct_pinreg16': price(g, stages=st, pinreg=16, su_scale=0.25),
                   'pessimistic_keep_SU_HC_rows': price(g, stages=st, pinreg=16, drop=re.compile(r'^VM\.|^CAPT\.CD_PINREG$')),
                   'pessimistic_plus_su25': price(g, stages=st, pinreg=16, su_scale=0.25, drop=re.compile(r'^VM\.|^CAPT\.CD_PINREG$')),
               })
    # p4g (coordinator 0cw+ (4)): the BF pair sequencer binds ot_s81_cfg7_seq_bfp PINREG=1 (closed, native PASS); its
    # pin-register edges are the ledger row FIELD.CFG7_SEQ_PINREG (+4 lc->go_e on every FIELD matrix job), which
    # every scenario above KEEPS.  'cfg7_pinreg0_binding' prices the old PINREG-0 cfg7_seq_bf binding (row dropped)
    # so the absorbed cost is explicit.
    kept_groups = {r['group'] for r in res['scenarios']['dv_base']['ledger_rows'] if not r['dropped']}
    res['cfg7_binding'] = dict(master='ot_s81_cfg7_seq_bfp', params=dict(LAYOUT=1, PINREG=1),
                               view='s81coll_cfg7_seq_bfp_pr-pr1-ef2866774 (CLOSED TT +244.3 / FF +23.9; native PASS 191.9/137.1/14.4)',
                               ledger_row='FIELD.CFG7_SEQ_PINREG', ledger_row_kept=('FIELD.CFG7_SEQ_PINREG' in kept_groups),
                               edges='lc->a/ce +2, lc->cfg/go_e +4, st +5 vs PINREG 0; charged +4 per FIELD matrix job')
    assert res['cfg7_binding']['ledger_row_kept'], 'cfg7 PINREG ledger row missing'
    res['scenarios']['cfg7_pinreg0_binding'] = price(g, stages=st, drop=re.compile(DROP.pattern + r'|^FIELD\.CFG7_SEQ_PINREG$'))
    if g.get('hbm_rt_stages'):
        res['scenarios']['dv_hbm_rt_unhidden'] = price(g, stages=st, hbm_rt=True)
    if g['hop_um'] < 405:   # reach sensitivity: also price the hub basis on the same hop (today's die degrades too)
        res['scenarios']['dv_base_hub_basis_same_hop'] = price(g, stages=st, basis_scale=405.0 / g['hop_um'])
    if a.land_plan:
        g0 = {k: v for k, v in g.items() if k != 'landing'}
        cmp_ = {}
        for k, kw in (('dv_base', {}), ('dv_hbm_rt_unhidden', dict(hbm_rt=True))):
            if k not in res['scenarios']:
                continue
            b0 = price(g0, stages=st, **kw)['workloads']
            b1 = res['scenarios'][k]['workloads']
            cmp_[k] = {wl: dict(no_landing_tok_s=b0[wl]['dv_tok_s'], landing_tok_s=b1[wl]['dv_tok_s'],
                                change_pct=round(100 * (b1[wl]['dv_tok_s'] / b0[wl]['dv_tok_s'] - 1), 2),
                                landing_cycles={r: v for r, v in b1[wl]['rules'].items() if r.startswith('land_')})
                       for wl in ('ar', 'mtp')}
        res['landing_vs_no_landing'] = cmp_
        land = json.loads(Path(a.land_plan).read_text())
        hp = host_terms(plan, land, a.half_cycle, landed=True)
        if hp:
            hp0 = host_terms(plan, land, a.half_cycle, landed=False)
            g['host_plane'] = hp
            gu = dict(g, host_plane=hp0)                              # host lanes unlanded (geometry only)
            g0h = dict(g0, host_plane=hp0)                            # nothing landed, host lanes geometric
            ref = res['scenarios']['dv_base']['workloads']
            hs = {}
            for k, gg, kw in (('host_token', g, dict(host=('token',))),
                              ('host_token_stage_serial', g, dict(host=('token', 'stage'))),
                              ('host_token_unlanded', gu, dict(host=('token',))),
                              ('no_landing_host_token_unlanded', g0h, dict(host=('token',)))):
                res['scenarios'][k] = price(gg, stages=st, **kw)
                w = res['scenarios'][k]['workloads']
                hs[k] = {wl: dict(tok_s=w[wl]['dv_tok_s'], vs_dv_base_landed_pct=round(100 * (w[wl]['dv_tok_s'] / ref[wl]['dv_tok_s'] - 1), 3),
                                  host_cycles={r: v for r, v in w[wl]['rules'].items() if r.startswith('host_')})
                         for wl in ('ar', 'mtp')}
            res['host_plane'] = dict(terms=hp, terms_unlanded=hp0, scenarios=hs)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    for k, s in res['scenarios'].items():
        w = s['workloads']
        print(f"{k:28s} AR {w['ar']['current_tok_s']:7.1f} -> {w['ar']['dv_tok_s']:7.1f} ({w['ar']['change_vs_current_pct']:+.2f}%)   "
              f"MTP {w['mtp']['current_tok_s']:7.1f} -> {w['mtp']['dv_tok_s']:7.1f} ({w['mtp']['change_vs_current_pct']:+.2f}%)  "
              f"DAG {w['ar']['dv_dag_loss_pct']:+.2f}/{w['mtp']['dv_dag_loss_pct']:+.2f}")
    print(json.dumps(res['scenarios']['dv_base']['workloads']['ar']['rules'], indent=0))
    print(json.dumps(res['scenarios']['dv_base']['workloads']['mtp']['rules'], indent=0))
    print('kept', res['scenarios']['dv_base']['ledger_kept_pct'], 'dropped', res['scenarios']['dv_base']['ledger_dropped_pct'])


if __name__ == '__main__':
    main()
