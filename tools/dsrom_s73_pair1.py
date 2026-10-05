#!/usr/bin/env python3
"""Additive, metadata-only Scenario C ownership model; never executes inference/RTL/P&R."""
import argparse, bisect, collections, copy, gzip, hashlib, json, math, subprocess
from pathlib import Path
import dsrom_full_owner_compiler as C
import dsrom_owner_provider_first as P
import dsrom_full_owner_closure as V

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_s73_pair1_20261003'
PIN = '4a18e3cc0b4c04f75a2e76e4535d9560cdc730c6'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, x):
    b=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
    if p.exists():
        if p.read_bytes()!=b: raise ValueError('Immutable output differs: '+str(p))
    else: p.write_bytes(b)

class RaggedPool(C.Pool):
    """Same ordered source segments and word packing, contiguous real sites, no ROM ECC."""
    def __init__(self, pairs=2682, bf=576, balance_raw=True):
        self.pairs=self.np=pairs; self.bfcount=bf
        self.balance_raw=balance_raw
        self.bounds=[r*pairs//128 for r in range(129)]
        self.bf={i*pairs//bf for i in range(bf)}
        self.byreg={}
        for r in range(128):
            ps=list(range(self.bounds[r],self.bounds[r+1]))
            self.byreg[(r,'q')]=ps
            self.byreg[(r,'bf16')]=[p for p in ps if p in self.bf]
        self.fill=dict.fromkeys(range(pairs),0);self.raw=set();self.phases=0
        self.ecc_bits=0;self.ecc_pairs=[]
    def reserve_ecc(self,bits): pass
    def clone(self):
        x=object.__new__(RaggedPool);x.__dict__=self.__dict__.copy()
        x.fill=self.fill.copy();x.raw=self.raw.copy();x.ecc_pairs=[]
        return x
    def raw_bankset(self,aliases,words_per_bank,banks=8):
        need=math.ceil(banks*math.ceil(words_per_bank/8192)/2)
        free=[p for p in self.fill if p not in self.bf and p not in self.raw and self.fill[p]==0]
        if len(free)<need: raise C.CapacityError('immutable provider '+str(aliases))
        chosen=[]
        for _ in range(need):
            counts=collections.Counter(bisect.bisect_right(self.bounds,p)-1 for p in self.fill if p not in self.raw and p not in chosen)
            chosen.append(min((p for p in free if p not in chosen),key=lambda p:(-counts[bisect.bisect_right(self.bounds,p)-1],p)))
        if not self.balance_raw:chosen=free[:need]
        for p in chosen:self.raw.add(p);self.fill[p]=8192
        return dict(aliases=aliases,banks=banks,words_per_bank=words_per_bank,pairs=chosen,
                    useful_word_bits=256,secded_inline_bits=0,physical_leaf_depth=4096)

def check(m,pool):
    spans=collections.defaultdict(list);coverage=collections.defaultdict(list)
    for si,p,first,n,stride,start,w in m['plans']:
        assert 0<=p<pool.np and start%2==0 and start+n*w<=8192
        assert bisect.bisect_right(pool.bounds,p)-1==first%128
        assert m['format']!='bf16' or p in pool.bf
        coverage[si].extend(first+j*stride for j in range(n))
        spans[p].append((start,start+n*w))
    for si in range(len(m['segments'])):assert sorted(coverage[si])==list(range((m['rows']+1)//2))
    for ss in spans.values():
        ss.sort();assert all(a[1]<=b[0] for a,b in zip(ss,ss[1:]))
    assert sum(n*w*2 for _,_,_,n,_,_,w in m['plans'])==P.matrix_words(m)

def physical_address(m,rank,row,k):
    """No-ECC source coordinate lookup, including canonical-owner references."""
    if not 0<=rank<4 or not 0<=row<m['rows'] or not 0<=k<m['K']:raise ValueError('coordinate bounds')
    owners=m.get('physical_owner_ranks',list(range(4)))
    owner=rank if rank in owners else next(r for r in owners if m['rank_slices'][r]==m['rank_slices'][rank])
    si=next(i for i,(e,n) in enumerate(m['segments']) if e<=k<e+n)
    sr,mb=divmod(row,2)
    run=next(r for r in m['plans'] if r[0]==si and sr>=r[2] and (sr-r[2])%r[4]==0 and (sr-r[2])//r[4]<r[3])
    _,pair,first,n,stride,start,_=run;e,length=m['segments'][si];fmt=m['format']
    unit=k//(128 if fmt=='bf16' else 512);half=(k%512)//256 if fmt=='fp8' else 0
    lane=k%8 if fmt=='bf16' else (k%256)//32
    index=C.S.segment_order(fmt,e,length).index((unit,lane,half))
    word=start+index*n+(sr-first)//stride
    width={'bf16':16,'fp4':4,'fp8':8}[fmt]
    bit=(k%128//8)*16 if fmt=='bf16' else ((k%512//256)*136+(k%32)*4 if fmt=='fp4' else (k%32)*8)
    source=m['rank_slices'][rank]
    assert 0<=word<8192 and bit+width<=274
    return dict(stage=m['stage'],requested_rank=rank,physical_owner_rank=owner,pair=pair,
                physical_macro=4*pair+2*mb+word%2,physical_row=word//2,bit_range=[bit,bit+width],
                source_tensor=m['tensor'],source_row=source['rows'][0]+row,source_col=source['cols'][0]+k,
                ordered_K_range=[e,e+length],ROM_ECC=False,
                owner_result_multicast_required=owner!=rank,conversion=m['conversion'])

def mapping(out,reference_unsplit=False,stages=73,pairs=2682,bf=576):
    headers=C.load_headers(ROOT/'results/uarch/dsrom_fixed4096_owner_compiler_20261002/inputs/tensor_headers.jsonl.gz')
    pools=[RaggedPool(pairs,bf,balance_raw=not reference_unsplit) for _ in range(stages)]
    decls=[C.declarations(headers,L) for L in range(40)]
    providers=[];homes={};covered=set()
    for L,(_,cs,he,_,names) in enumerate(decls):
        home=L*stages//40;homes[L]=home;covered.update(names)
        hw=sum(x['rows']*math.ceil(x['K']/64) for x in he)
        cw=math.ceil(sum(x['elements'] for x in cs)/8)
        for kind,ds,words,banks in [('HE',he,hw,8),('CROM',cs,cw,1)]:
            providers.append(dict(layer=L,stage=home,kind=kind,declarations=ds,
                                  **pools[home].raw_bankset([x['alias'] for x in ds],words,banks)))
    stage=0;failures=[];counts=collections.Counter();layers=collections.defaultdict(set)
    assigned_tensors=set();source_slices=collections.defaultdict(list);intervals=collections.defaultdict(list)
    target=out/'matrix_map.jsonl.gz'
    if target.exists():raise ValueError('Use a fresh attempt directory')
    with target.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as z:
        for L,(groups,*_) in enumerate(decls):
            # Independent output rows may move at complete 128-superrow boundaries;
            # each row retains its entire ordered K tree and source rank slice.
            ordered=[]
            for m in groups[None]:
                mode='bf16' if m['format']=='bf16' else 'q'
                limit=256*min(len(pools[0].byreg[(r,mode)]) for r in range(128))
                if reference_unsplit:limit=m['rows']
                for first in range(0,m['rows'],limit):
                    n=min(limit,m['rows']-first);x=copy.deepcopy(m)
                    if m['rows']>limit:
                        x.update(alias=m['alias']+'.rows'+str(first),original_alias=m['alias'],row_offset=first,rows=n,
                                 output_row_split_delivery_qualified=False)
                        for s in x['rank_slices']:s['rows']=[s['rows'][0]+first,s['rows'][0]+first+n]
                    ordered.append([x])
            ordered += [ms for e,ms in groups.items() if e is not None]
            for ms in ordered:
                while True:
                    trial=pools[stage].clone();planned=[]
                    try:
                        for m in ms:
                            x=trial.matrix(m);x.update(stage=stage,compiled_NP=pairs,ECC=dict(useful_bits=m['ECC']['useful_bits'],secded_bits=0,extra_sidecar_bits=0),ecc_bit_base=None)
                            check(x,trial);planned.append(x)
                    except C.CapacityError as e:
                        if stage<stages-1:stage+=1;continue
                        failures.append(dict(layer=L,aliases=[m['alias'] for m in ms],error=str(e)))
                        planned=[dict(m,stage=None,plans=[],allocation_failure=str(e)) for m in ms]
                    else:pools[stage]=trial
                    break
                for m in planned:
                    counts['declarations']+=1
                    if m['stage'] is not None:
                        counts['placed']+=1;layers[L].add(stage);assigned_tensors.add(m['tensor'])
                        for rank,s in enumerate(m['rank_slices']):source_slices[m['tensor']].append(dict(rank=rank,rows=s['rows'],cols=s['cols']))
                        for _,p,_,n,_,a,w in m['plans']:intervals[(stage,p)].append((a,a+n*w))
                    z.write((json.dumps(m,separators=(',',':'),sort_keys=True)+'\n').encode())
            print(json.dumps(dict(layer=L,last_stage=stage,failed_groups=len(failures))),flush=True)
    for p in providers:
        for pair in p['pairs']:intervals[(p['stage'],pair)].append((0,8192))
    for spans in intervals.values():
        spans.sort();assert all(a[1]<=b[0] for a,b in zip(spans,spans[1:]))
    save(out/'providers.json',providers)
    save(out/'stage_map.json',dict(layer_matrix_stages={k:sorted(v) for k,v in layers.items()},provider_homes=homes,
         region_bounds=pools[0].bounds,BF_site_IDs=sorted(pools[0].bf),rank_dies=[dict(stage=s,rank=r,die_id=4*s+r) for s in range(stages) for r in range(4)],
         scan_layers=[2,8,14,20,24,28,32,36],scan_service_homes={L:homes[L] for L in [2,8,14,20,24,28,32,36]},
         scan_home_is_provisional_not_source_service_binding=True,PHW_required_by_stage=[(p.phases-1).bit_length() for p in pools]))
    # Every released key stays in the accounting, including MTP and vision omitted by decoder-only compilers.
    auxiliary=[h for n,h in headers.items() if n not in covered and n not in ('embed.weight','head.weight','norm.weight')]
    save(out/'auxiliary_obligations.json',dict(tensors=auxiliary,storage_bytes=sum(x['source_storage_bytes'] for x in auxiliary),
         no_omission_credit=True,placement_qualified=False,reason='MTP/vision/aligner source owners require additional priced mapping; decoder mapping cannot prove entire shipped checkpoint'))
    dedicated=V.dedicated_providers(headers)
    for t in dedicated['tables']+dedicated['global_tensors']:t['secded_bits']=0
    save(out/'inventory.json',dict(stages=stages,TP=4,layer_dies=4*stages,head_dies=8,table_dies=36,
         pairs_per_rank_die=pairs,q_only_pairs=pairs-bf,BF_dual_pairs=bf,compiled_pairs_TP4=4*stages*pairs,
         physical_ROM4096_per_layer_die=4*pairs,physical_ROM4096_layer_total=16*stages*pairs,padding_pairs=0,
         macros_per_pair=4,logical_slots_per_pair=2,rows=4096,word_bits=274,ROM_ECC=False,
         occupied_pairs_per_stage=[sum(v>0 for v in p.fill.values()) for p in pools],
         used_logical_words_per_stage=[sum(p.fill.values()) for p in pools],
         dedicated_storage=dedicated,physical_admission=False))
    result=dict(schema='opentallas.dsrom.S73.PAIR1.metadata-map.v1',counts=dict(counts),failures=failures,
         shipped_tensor_count=len(headers),decoder_tensor_count=len(covered),auxiliary_tensor_count=len(auxiliary),
         decoder_matrix_capacity_PASS=not failures,word_overlap_PASS=True,row_and_ordered_K_coverage_PASS=True,
         entire_shipped_checkpoint_exactonce_PASS=False,all_numbers='MODEL_UNVALIDATED',adopted=False,
         no_RTL_PnR_inference=True,W1_RD=4,W1_RD_measured=False,
         blocking=['Auxiliary shipped weights need priced physical owners','Ragged region assignment must join W1 generator','W3 service home and per-die KV demand join','W4 disjoint replacement ledger and rectangles','Actual descriptor PHW/address and golden exactness gates','Loaded SS/FF timing and routing-layer check'])
    save(out/'mapping_verdict.json',result)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--reference-unsplit',action='store_true')
    ap.add_argument('--stages',type=int,default=73);ap.add_argument('--pairs',type=int,default=2682)
    ap.add_argument('--bf',type=int,default=576);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    mapping(a.out,a.reference_unsplit,a.stages,a.pairs,a.bf)
if __name__=='__main__':main()
