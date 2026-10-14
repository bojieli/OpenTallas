import json,collections,re,sys,pickle
rows=json.load(open(sys.argv[1]))
m=pickle.load(open(sys.argv[2],'rb')); I=m['insts']
def grp(b):
    n=b['bus']
    rules=[('LINK chain (coll<->lk_ep)',r'^lk_lk_'),('TKM stream (coll<->tkm)',r'^tkm|^hb_tkm|coll_tkm'),
     ('SU<->VM8 spine slice',r'^hb_(su_\w+_vm|vm_su_)'),('VM8 x-load (vms->vm8)',r'^vxl_'),('VM8 x-trunk (vm8->SM)',r'^xt_|^xl_|^xh_'),
     ('VM ring (vms<->vms)',r'^vring_'),('COLL bcast star (coll->vms)',r'^vcb_'),('ring clients (vms<->cmdproc/quant/hc_eng)',r'^vrc_'),
     ('lane group (vms->SU/SFU/HC)',r'^hgi_lg'),('SU<->SU peer',r'^hb_su_\w\w_su_'),('SU<->COLL',r'^hb_su_\w+_coll|^hb_coll_su'),
     ('cmdproc fan-out',r'_cmd|^ct_|^cd_|^ctl'),('IDX (grid/selector/hgi_idx)',r'^idx_|^ks|^hgi_idx|^isel|^is_'),
     ('DMA loader',r'^lw_|^lq_|^lr_|^ld_|^hgi_vmw|^dma'),('HC map',r'^vmap|^hc'),('SM result/weight',r'^rt_|^rh_|^wl_|^wq|^lk_ep|^res'),
     ('KV/attn',r'^kv|^at_|^aq|^ap|^ao')]
    for g,p in rules:
        if re.search(p,n): return g
    return 'other:'+b['fam']
G=collections.defaultdict(lambda: dict(hub=0,hot=0,bits=0,xbits=0,n=0,ex=collections.Counter()))
H=sum(r['hub_bitmm'] for r in rows); T=sum(r['hot_bitmm'] for r in rows)
for r in rows:
    g=G[grp(r)]; g['hub']+=r['hub_bitmm']; g['hot']+=r['hot_bitmm']; g['bits']+=r['bits']; g['n']+=1
    if len(r['quads'])>1: g['xbits']+=r['bits']
    if r['hub_bitmm']>0: g['ex'][r['bus']]+=r['hub_bitmm']
out=[]
for k,g in sorted(G.items(),key=lambda t:-t[1]['hub']):
    out.append(dict(group=k,buses=g['n'],bits=g['bits'],xquad_bits=g['xbits'],hub_share=round(g['hub']/H,4),hot_share=round(g['hot']/T,4),top=[b for b,_ in g['ex'].most_common(4)]))
    if g['hub']/H>0.002: print(f"{k:44s} n={g['n']:4d} bits={g['bits']:7d} xq={g['xbits']:7d} hub={g['hub']/H*100:5.1f}% hot={g['hot']/T*100:5.1f}%  {[b for b,_ in g['ex'].most_common(3)]}")
json.dump(out,open(sys.argv[3],'w'),indent=1)
