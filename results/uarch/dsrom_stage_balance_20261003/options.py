"""Read-only pricing of stage-imbalance fix options on the S58 basis (dsrom_fit/price_options.py settings).
Surgery is applied to the priced graph BEFORE uarch_model._cons_adjust re-times it (both the AR graph and the MTP
verify graph).  Usage: options.py <ctx> <variant>   variant: base | chase | cpW[:layers][:ns] | chase+cpW...
cpW: index scan of the listed layers (default 20) split over W dies instead of the TP-4 group (context parallel over
keys, position-order concatenation into one tselect_final -> exact); ns = extra crossing latency on the merge."""
import sys, json, math, copy, collections
WT='/home/ubuntu/dsrom-stage-balance-20261003'; sys.path.insert(0, WT+'/tools')
import uarch_model as u, decode_critical_path as D
S=58; ctx=int(sys.argv[1]); variant=sys.argv[2]
cap=json.load(open(WT+'/results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json'))
b={r['stages']:r for r in cap['all_stage_capacity_rows']}[S]['BF16_pairs_per_die']
u.PRESETS['proposal']['bf16_stripe_macros']=2*b
clk=u.PRODUCT_CLOCK_HZ; cyc=1/clk
chase='chase' in variant; W=4; layers=[20]; ns=0.0
for part in variant.split('+'):
    if part.startswith('cp'):
        f=part[2:].split(':'); W=int(f[0])
        if len(f)>1 and f[1]: layers=[int(x) for x in f[1].split(',')]
        if len(f)>2: ns=float(f[2])
def surgery(g):
    for n,nd in g.nodes.items():
        L=nd.get('layer')
        if chase and n.endswith(('.idx.topk_local','.cand.topk_local')):
            nd['stream']=True
        if W!=4 and L in layers:
            k=4/W
            if n.endswith(('.idx.score','.idx.topk_local','.cand.topk_local')):
                nd['issue']*=k
            elif n.endswith('.idx.topk_final'):
                kk=512; nd['depth']=(math.ceil(W*kk/64)+D.tselect_latency(W*kk))*cyc
            elif n.endswith('.cand.final'):
                kk=2048; nd['depth']=(math.ceil(W*kk/64)+D.tselect_latency(W*kk))*cyc
            elif n.endswith(('.idx.topk_merge','.cand.merge')):
                nd['depth']+=ns*1e-9
orig=u._cons_adjust; GS=[]
def adj(g,P,*a,**kw):
    surgery(g); v=orig(g,P,*a,**kw); GS.append((P,g)); return v
u._cons_adjust=adj
orig_cool=u._cons_cooling; COOL={}
def cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, tot):
    lt={k:v for k,v in tot.items() if k!='head'}
    COOL['layer_only']=orig_cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, lt)
    bal={k:sum(lt.values())/len(lt) for k in lt}
    ps_bal={k:sum(pair_s.values())/len(lt) for k in lt}
    COOL['balanced']=orig_cool(die_static, die_static_ungated, cats, ps_bal, pp, dyn_scale, sat, S_, bal)
    return orig_cool(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S_, tot)
u._cons_cooling=cool
orig_occ=u._cons_occupancy; PL=[]
def occ(g,plan):
    PL.append(plan); return orig_occ(g,plan)
u._cons_occupancy=occ
with u._cons_ctx(ctx):
    p=u.cons_v41_rom(S,8,36,bf16='columns',clock_hz=clk,field_concurrency=u.FIELD_CONCURRENCY,
      added_latency=dict(u.SOFTPLUS_FIX,**u.W11_STREAM_SS,**u.PLUS_LAT),dyn_scale=u.PRODUCT_DYN_SCALE,
      slow_domain=(.9e9,'w18'),elem_stages=8,ss_wire=True,serial=u.PRODUCT_SERIAL,die=u.DIE_SHRUNK_INTERIM,vmh=u.VMC_FUSED,hub_block=u.PRODUCT_HUB)
g=GS[0][1]; plan=PL[0]
o=orig_occ(g,plan); tot={str(s):(v['field']+v['hub'])*1e6 for s,v in o.items()}
lay=[v for k,v in tot.items() if k!='head']
# per-layer blocks: non-expert (indivisible, on the start stage) and expert (divisible) per-die issue, us
blk=collections.defaultdict(lambda: dict(nonexp=0.0, exp=0.0, scan=0.0))
res=collections.defaultdict(lambda: collections.defaultdict(float))   # per-stage per-resource issue
for n,nd in g.nodes.items():
    if nd['kind'] in ('collective','hop'): continue
    L=nd['layer']; s0=u._cons_stage_of(n,nd,plan)
    isexp=s0!='head' and n.endswith(u.A.EXPERT_NODES)
    key='head' if s0=='head' else L
    blk[key]['exp' if isexp else 'nonexp']+=nd['issue']*1e6
    if n.endswith(('.idx.score','.idx.topk_local','.cand.topk_local')): blk[key]['scan']+=nd['issue']*1e6
    r=('field' if nd.get('_uarch') else 'idx_hbm' if n.endswith('idx.score') else 'tselect' if nd['kind']=='select' else 'attn' if nd['kind']=='kvscan' else nd['kind'])
    parts=[(s,f) for s,f in plan['frac'][L]] if isexp else [(s0,1.0)]
    for s,f in parts: res[str(s)][r]+=nd['issue']*f*1e6
out=dict(variant=variant,ctx=ctx,W=W,layers=layers,extra_merge_ns=ns,
  ar_us=1e6/p['ar_tokens_s_b1'],ar_tok_s=p['ar_tokens_s_b1'],mtp_tok_s=p['mtp_tokens_s_b1'],
  ar_sat=p['ar_saturated_tokens_s'],mtp_sat=p['mtp_saturated_tokens_s'],busiest_stage=p['busiest_stage'],busiest_us=p['busiest_stage_us'],
  layer_stage_max_us=max(lay),layer_stage_mean_us=sum(lay)/len(lay),layer_stage_std_us=(sum((x-sum(lay)/len(lay))**2 for x in lay)/len(lay))**.5,
  stage_occ_us=tot, stage_resource_us={k:dict(v) for k,v in res.items()}, layer_blocks_us={str(k):v for k,v in blk.items()},
  cooling=p['cooling'],cooling_layer_stages=COOL['layer_only'],cooling_balanced=COOL['balanced'],cp_top=p['critical_path_top_us'],pipeline_hops_us=p['pipeline_hops_us'],stage_hops=p['stage_hops'])
fn=f"/tmp/claude-review-20261003/stagebal/opt_{variant.replace(':','_').replace(',','-')}_{ctx}.json"
json.dump(out,open(fn,'w'),indent=1)
print(json.dumps({k:(round(v,3) if isinstance(v,float) else v) for k,v in out.items() if k not in('stage_occ_us','stage_resource_us','layer_blocks_us','cooling','cp_top')}),'hot_w_model',p['cooling']['layer_die_busiest_w_saturated'],'hot_layer',COOL['layer_only']['busiest_stage'],COOL['layer_only']['layer_die_busiest_w_saturated'],'balanced',COOL['balanced']['layer_die_busiest_w_saturated'],'mean',COOL['layer_only']['layer_die_mean_w_saturated'])
