"""Read-only probe: S58 pricing basis (dsrom_fit/price_options.py), dumps per-stage occupancy and critical-path windows."""
import sys, json, math, copy, collections
WT='/home/ubuntu/dsrom-stage-balance-20261003'
sys.path.insert(0, WT+'/tools')
import uarch_model as u
S=int(sys.argv[1]); ctx=int(sys.argv[2])
cap=json.load(open(WT+'/results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json'))
rows={r['stages']:r for r in cap['all_stage_capacity_rows']}
b=rows[S]['BF16_pairs_per_die'] if S in rows else math.ceil(41*1024/S)
saved=copy.deepcopy(u.PRESETS['proposal']); u.PRESETS['proposal']['bf16_stripe_macros']=2*b
G={}
orig_occ=u._cons_occupancy; orig_win=u._cons_windows
def occ(g,plan):
    G.setdefault('occ',[]).append((g,plan)); return orig_occ(g,plan)
u._cons_occupancy=occ
with u._cons_ctx(ctx):
    p=u.cons_v41_rom(S,8,36,bf16='columns',clock_hz=u.PRODUCT_CLOCK_HZ,field_concurrency=u.FIELD_CONCURRENCY,
      added_latency=dict(u.SOFTPLUS_FIX,**u.W11_STREAM_SS,**u.PLUS_LAT),dyn_scale=u.PRODUCT_DYN_SCALE,
      slow_domain=(.9e9,'w18'),elem_stages=8,ss_wire=True,serial=u.PRODUCT_SERIAL,die=u.DIE_SHRUNK_INTERIM,vmh=u.VMC_FUSED,hub_block=u.PRODUCT_HUB)
    g,plan=G['occ'][0]
    # per-stage per-node issue
    per=collections.defaultdict(lambda: collections.defaultdict(float))
    for name,nd in g.nodes.items():
        if nd['kind'] in ('collective','hop'): continue
        s0=u._cons_stage_of(name,nd,plan)
        parts=([(s,f) for s,f in plan['frac'][nd['layer']]] if s0!='head' and name.endswith(u.A.EXPERT_NODES) else [(s0,1.0)])
        for s,f in parts:
            tail=name.split('.',1)[1] if name.startswith(('L','E')) and '.' in name else name
            per[str(s)][('field:' if nd.get('_uarch') else 'hub:')+tail]+=nd['issue']*f
    win,T=orig_win(g,plan)
    # critical path per node per stage
    sink=[n for n in g.nodes if n.endswith('token.return')][0]
    cp=collections.defaultdict(lambda: collections.defaultdict(float))
    for n in g.path(sink):
        s=u._cons_stage_of(n,g.nodes[n],plan); tail=n.split('.',1)[1] if n.startswith(('L','E')) and '.' in n else n
        cp[str(s)][tail]+=sum(g.contrib[n].values())
    layers={str(s):[] for s in range(S)}
    for L,parts in plan['frac'].items():
        for s,f in parts: layers[str(s)].append([L,round(f,4)])
    out=dict(S=S,ctx=ctx,keep={k:p[k] for k in ('ar_tokens_s_b1','mtp_tokens_s_b1','ar_saturated_tokens_s','mtp_saturated_tokens_s','busiest_stage','busiest_stage_us','stage_hops','pipeline_hops_us','critical_path_top_us','cooling','layer_dies','dies')},
      T_us=T*1e6, start=plan['start'], layers=layers,
      occ_us={k:{kk:v*1e6 for kk,v in sorted(d.items(),key=lambda x:-x[1])} for k,d in per.items()},
      win_us={str(k):v*1e6 for k,v in win.items()},
      cp_us={k:{kk:v*1e6 for kk,v in sorted(d.items(),key=lambda x:-x[1])} for k,d in cp.items()})
json.dump(out,open(f'/tmp/claude-review-20261003/stagebal/probe_S{S}_{ctx}.json','w'),indent=1)
print(json.dumps(out['keep'])[:800]); print('T_us',T*1e6)
