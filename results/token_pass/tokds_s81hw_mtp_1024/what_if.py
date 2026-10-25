"""TOK-DS S81.MTP what-if runner (analysis only; reuses compose_tok_ds + dv_mu_calendar_phys model code, no outputs)."""
import sys, json, importlib.util, re, copy
from pathlib import Path
W = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('ctd', W/'tools/s81_dv/tokfunc/compose_tok_ds.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
BASE = {wl: M.compose(wl, dict(attn='G4', offchip=False, release=False, regrade=False)) for wl in ('ar','mtp')}
class Stop(Exception): pass
def run(name, attn='G4', hop_sw_delta=0, h_msg_scale=1.0, scale=None, x_flat_delta=0):
    K = M.load(M.ROOT / 'tools/s81_dv/dv_mu_calendar_phys.py', 'cal_' + re.sub(r'\W', '_', name))
    K.REL.update(K.REL241); K.REL['attn'] = attn
    K.HOP_SW += hop_sw_delta; K.H_MSG = int(round(K.H_MSG * h_msg_scale)); K.X_FLAT += x_flat_delta
    cap = {}
    o = K.mtp_pipeline_graph
    def spy(model, tl, links, chain_end, hop_head, lead):
        p = o(model, tl, links, chain_end, hop_head, lead); cap.update(model=model, pipe=p); return p
    K.mtp_pipeline_graph = spy
    def stop(*a, **k): raise Stop()
    for nm in ('calendar', 'calendar2', 'calendar3', 'calendar_position_jobs'):
        if hasattr(K, nm): setattr(K, nm, stop)
    def composed(_m='record'):
        r, dags = {}, {}
        for wl in ('ar', 'mtp'):
            x = BASE[wl]; cyc = dict(x['cyc'])
            for i, n in x['dag']['nodes_by_id'].items():
                for pat, f in (scale or {}).items():
                    if re.fullmatch(pat, n.get('op') or ''):
                        cyc[i] = cyc[i] * f
            ex = sum(e['cycles'] for e in x['extra'])
            T = max(sum(cyc[i] for i in x['crit']) + ex, M.C.solve(x['dag'], cyc)[0] + ex)
            r[wl] = dict(T_cycles=T, tok_s=0, pct_measured=0, extra_terms=[dict(slot=e['slot'], kind=e['kind'], cycles=e['cycles']) for e in x['extra']])
            dags[wl] = (x['dag'], cyc)
        return dict(workloads=r), dags
    K.composed = composed
    bl = {}
    try:
        K.build(str(M.MAP241), 'record', True, False, 1)
    except Stop as e:
        tb = e.__traceback__
        while tb:
            if tb.tb_frame.f_code.co_name == 'build': bl = dict(tb.tb_frame.f_locals)
            tb = tb.tb_next
    m, p = cap['model'], cap['pipe']
    f = lambda T: round(1.2e9 * 4.159 / T, 1)
    t6, tp = p['T_mtp_law_6f'], p['step_end'] + p['ar_tail_beyond_head']
    return dict(name=name, T_ar=round(m['T_ar']), ar_tok_s=round(1.2e9 / m['T_ar'], 1), T_6f=round(t6), T_pipe=round(tp),
                T_record=round(m['T_mtp_step']), tok_s_record=f(m['T_mtp_step']), tok_s_6f=f(t6), tok_s_pipe=f(tp),
                chain_end=p['chain_end'], head_ar=m['head_ar'], draft_tail=m['draft_tail'],
                bottleneck=sorted(((s['occ'], s['stage']) for s in m['stages']), reverse=True)[:5],
                wave_phys=round(5 * max(s['occ'] - s['scan'] for s in m['stages'])))
cases = [
    ('record', {}),
    ('G16 attention service (attn.scores/pv node 289/596 vs G4 769/1076)', dict(attn='G16')),
    ('G8 attention service', dict(attn='G8')),
    ('stage-hop message striped over 2 circuits (H_MSG 652->326, HOP -326)', dict(hop_sw_delta=-326, h_msg_scale=0.5)),
    ('stage-hop message in FP8 / 3 circuits (H_MSG 652->217, HOP -435)', dict(hop_sw_delta=-435, h_msg_scale=1/3)),
    ('draft tail halved (draft.* x0.5)', dict(scale={r'draft\..*': 0.5})),
    ('head die lm_head x0.5 (head.lm_head, draft.head)', dict(scale={r'head\.lm_head': 0.5, r'draft\.head': 0.5})),
    ('indexer x0.5 (attn.idx.score/topk_local/topk_final)', dict(scale={r'attn\.idx\.(score|topk_local|topk_final)': 0.5})),
    ('indexer removed from critical path (x0)', dict(scale={r'attn\.idx\.(score|topk_local|topk_final|topk_merge|q_field)': 0.0})),
    ('ROM field matvecs x0.8 (attn.wo_a/wq_b/wo_b/a_proj, ffn.experts_gu/down/router/shared_gu)', dict(scale={r'(attn\.(wo_a|wq_b|wo_b|a_proj)|ffn\.(experts_gu|down|router|shared_gu))': 0.8})),
    ('attn.wo_a x0.5', dict(scale={r'attn\.wo_a': 0.5})),
    ('collectives on-die part x0.5 (allreduce/allgather nodes x0.5)', dict(scale={r'(attn\.(a_allgather|out_allreduce|rows_allgather)|ffn\.(router_allgather|combine_allreduce))': 0.5})),
    ('COMBO A: stripe2 + indexer x0.5 + wo_a x0.75', dict(hop_sw_delta=-326, h_msg_scale=0.5, scale={r'attn\.idx\.(score|topk_local|topk_final)': 0.5, r'attn\.wo_a': 0.75})),
    ('COMBO B: A + collectives x0.75 + G16', dict(attn='G16', hop_sw_delta=-326, h_msg_scale=0.5, scale={r'attn\.idx\.(score|topk_local|topk_final)': 0.5, r'attn\.wo_a': 0.75, r'(attn\.(a_allgather|out_allreduce|rows_allgather)|ffn\.(router_allgather|combine_allreduce))': 0.75})),
    ('COMBO C: B + fields x0.9 (all 8 field ops)', dict(attn='G16', hop_sw_delta=-326, h_msg_scale=0.5, scale={r'attn\.idx\.(score|topk_local|topk_final)': 0.5, r'attn\.wo_a': 0.675, r'(attn\.(wq_b|wo_b|a_proj)|ffn\.(experts_gu|down|router|shared_gu))': 0.9, r'(attn\.(a_allgather|out_allreduce|rows_allgather)|ffn\.(router_allgather|combine_allreduce))': 0.75})),
]
sel = sys.argv[3:] or None
res = []
for nm, kw in cases:
    if sel and not any(s in nm for s in sel): continue
    r = run(nm, **kw); res.append(r)
    print(json.dumps({k: r[k] for k in ('name','T_ar','ar_tok_s','T_6f','T_pipe','tok_s_record','tok_s_pipe','bottleneck','wave_phys')}), flush=True)
json.dump(res, open(sys.argv[2], 'w'))
