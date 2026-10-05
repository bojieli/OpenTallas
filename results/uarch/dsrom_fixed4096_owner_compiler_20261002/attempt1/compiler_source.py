#!/usr/bin/env python3
"""Symbolic fixed4096 NB2/PP1 full-decoder ownership compiler; no payload/builds.

assignment.address(alias,rank,row,k) returns stage, pair, mb, parity, physicalrow,
code/scale bit ranges, and canonical golden subtree identity. Allocation advances
only at whole dense-layer/expert boundaries against ONE supplied candidate.
"""
from __future__ import annotations
import argparse, collections, gzip, hashlib, heapq, json, math, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import hdc_replay_v41 as R
import rtl_v41_fullshape_layer_campaign as LC
import v41_rom_ksplit_bankmap as S
PIN='024e8c519c07aedc74b32511fccfe07d56e91a97'
DEPTH=8192 # logical bank = two physical4096 leaves, NEVER one8192 macro
LEAF_DEPTH=4096
REGIONS=128


def sha(b):return hashlib.sha256(b).hexdigest()
def gitread(p):return subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)
def load_headers(p):
    with gzip.open(p,'rt') as f:return {x['tensor']:x for x in map(json.loads,f)}
def gzrows(p,rows):
    with p.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as z:
        for x in rows:z.write((json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode())
def readrows(p):
    with gzip.open(p,'rt') as f:yield from map(json.loads,f)


def ordered_segments(fmt,K):
    """Power-of-two aligned subtrees; BF16 lane-group tree limitLV5=32groups."""
    quantum=128 if fmt=='bf16' else 256
    max_units=32 if fmt!='fp4' else 64
    units=(K+quantum-1)//quantum;out=[];u=0
    while u<units:
        take=min(max_units,1<<(units-u).bit_length()-1)
        while u%take:take//=2
        # FP4 sibling chunks stay together (a two136-bit word).
        if fmt=='fp4' and take==1:raise ValueError('unaligned singleton FP4 chunk')
        out.append((u*quantum,min(take*quantum,K-u*quantum)));u+=take
    return out


def secded_bits(data):
    r=0
    while (1<<r)<data+r+1:r+=1
    return r+1


class CapacityError(RuntimeError):pass
class Pool:
    def __init__(self,pairs,bf):
        self.pairs=pairs;self.bfcount=bf;self.np=1<<(pairs-1).bit_length()
        self.per=self.np//REGIONS;self.fill={};self.bf=set();self.byreg={}
        active=[];base,extra=divmod(pairs,REGIONS);bb,be=divmod(bf,REGIONS)
        for reg in range(REGIONS):
            ps=list(range(reg*self.per,reg*self.per+base+(reg<extra)));active+=ps
            k=bb+(reg<be);self.bf.update(ps[i*len(ps)//k] for i in range(k))
            self.byreg[(reg,'q')]=[p for p in ps if p not in self.bf]
            self.byreg[(reg,'bf16')]=[p for p in ps if p in self.bf]
        self.fill=dict.fromkeys(active,0);self.raw=set();self.phases=0
    def clone(self):
        x=Pool(self.pairs,self.bfcount);x.fill=self.fill.copy();x.raw=self.raw.copy();x.phases=self.phases;return x
    def matrix(self,m):
        rows=m['rows'];K=m['K'];fmt=m['format'];pieces=ordered_segments(fmt,K)
        plans=[];phase_words=collections.Counter();live=collections.Counter()
        # A complete superrow stays in its modulo return region. Same-range
        # node sharing is limited by actualNSEG/NCH/NCHB, not capacity alone.
        for si,(e0,el) in enumerate(pieces):
            words=S.seg_words(fmt,e0,el);units=min(8,S.seg_units(fmt,e0,el))
            per_pair=min(8,(8 if fmt=='bf16' else 16)//units)
            for reg in range(REGIONS):
                count=max(0,((rows+1)//2-1-reg)//REGIONS+1)
                if not count:continue
                available=self.byreg[(reg,'bf16' if fmt=='bf16' else 'q')]
                while count:
                    n=min(count,per_pair);need=n*words
                    good=[p for p in available if p not in self.raw and live[p]+n<=per_pair and self.fill[p]+(self.fill[p]&1)+need<=DEPTH]
                    if not good:raise CapacityError(f"{m['alias']} reg{reg} fmt{fmt} needs{need}words/{n}nodes")
                    p=min(good,key=lambda p:(phase_words[p],self.fill[p],p));start=self.fill[p]+(self.fill[p]&1)
                    first=reg+(((rows+1)//2-1-reg)//REGIONS+1-count)*REGIONS
                    plans.append([si,p,first,n,REGIONS,start,words]);self.fill[p]=start+need
                    phase_words[p]+=need;live[p]+=n;count-=n
        self.phases+=1
        # Source stream is ascending units, block/round. Conservatively retain
        # LAT8 recurrence; compute exact issue from compressed row-node demand.
        round_load=collections.Counter();required=collections.defaultdict(set)
        for si,p,first,n,stride,start,words in plans:
            e0,el=pieces[si];u0,u1=S.unit_range(fmt,e0,el)
            for q in range(math.ceil((u1-u0)/8)):
                us=range(u0+q*8,min(u1,u0+(q+1)*8))
                round_load[(p,q)]+=n*sum(len(S.unit_halves(fmt,e0,el,u)) for u in us)
                required[q].update(us)
        issue=8*sum(max(8,math.ceil(len(us)/(4 if fmt=='bf16' else 1)),max(v for (p,k),v in round_load.items() if k==q)) for q,us in required.items())
        return {**m,'segments':pieces,'plans':plans,'issue_cycles_LAT8_condition':issue,
                't_read_words_max':max(phase_words.values()),'ordered_superrow_region':True,
                'compute_MACs_per_cycle_per_pair':32 if fmt=='bf16' else (128 if fmt=='fp4' else 64)}
    def raw_bankset(self,aliases,words_per_bank,banks=8):
        # ExistingHE pack_he_fp32: eight256-bit banks, HHW8. Constants use
        # a64-bit word port expanded to FP32, fouraddresses in one256-bit lane.
        slots=banks*math.ceil(words_per_bank/DEPTH);pairs=math.ceil(slots/2)
        free=[p for p in self.fill if p not in self.bf and p not in self.raw and self.fill[p]==0]
        if len(free)<pairs:raise CapacityError(f'rawprovider{aliases}: {pairs}exclusive completepairs')
        chosen=sorted(free)[:pairs]
        for p in chosen:self.raw.add(p);self.fill[p]=DEPTH
        return {'aliases':aliases,'banks':banks,'words_per_bank':words_per_bank,'pairs':chosen,
                'slot_assignment':'bank-major, depth-chunk-major, two logical slots per completepair',
                'useful_word_bits':256,'secded_inline_bits':10,'physical_leaf_depth':4096}


def declarations(headers,L):
    slices=LC.die_slices(L,0,R.SHIPPED,range(384),L in R.ENGRAM)
    groups={None:[]};constants=[];he=[];covered=set()
    for alias,tensor,rr,cc in slices:
        h=headers[tensor];covered.add(tensor)
        if alias.endswith('.scale'):continue # owned with source codes / expansion
        dt=h['dtype'];shape=h['shape'];rows=shape[0];cols=shape[1] if len(shape)>1 else None
        if dt=='I8':cols*=2
        r0,r1=rr or (0,rows);c0,c1=cc or ((0,cols) if cols else (0,1))
        exp=re.match(r'exp(\d+)\.',alias);expert=int(exp[1]) if exp else None
        if alias in ('hc_attn_fn','hc_ffn_fn'):
            he.append({'alias':alias,'tensor':tensor,'rows':rows,'K':cols,'bytes':h['source_storage_bytes']});continue
        ismatrix=(alias in ('wq_a','wkv','wq_b','wo_a','wo_b','gate','indexer.wk','indexer.weights_proj','indexer.wq_b','compressor.wkv','compressor.wgate','engram.wkv') or alias.startswith(('shared.','exp')))
        if not ismatrix:
            constants.append({'alias':alias,'tensor':tensor,'dtype':dt,'elements':math.prod(shape) if rr is None else (r1-r0)*math.prod(shape[1:]),'expanded_bits':32});continue
        fmt='fp4' if dt=='I8' else ('fp8' if dt=='F8_E4M3' and alias!='wo_a' else 'bf16')
        m={'alias':alias,'tensor':tensor,'layer':L,'expert':expert,'format':fmt,'source_dtype':dt,'rows':r1-r0,'K':c1-c0,
           'rank_slices':[],'source_scale_tensor':tensor[:-6]+'scale' if dt in ('I8','F8_E4M3') else None,
           'conversion':'FP8+UE8M0->BF16_RNE' if alias=='wo_a' else 'native',
           'ECC':{'useful_bits':272 if fmt=='fp4' else (264 if fmt=='fp8' else 256),
                  'secded_bits':10,'extra_sidecar_bits':8 if fmt=='fp4' else 0,'current_source_decoder_available':False}}
        for rank in range(4):
            spec=next(x for x in LC.die_slices(L,rank,R.SHIPPED,[],L in R.ENGRAM) if x[0]==alias) if expert is None else next(x for x in LC.die_slices(L,rank,R.SHIPPED,[expert],False) if x[0]==alias)
            m['rank_slices'].append({'rows':list(spec[2] or (0,rows)),'cols':list(spec[3] or (0,cols))})
        if alias=='wo_a':
            for g in range(R.SHIPPED['o_groups']//4):
                part={**m,'alias':f'wo_a.group{g}','rows':R.SHIPPED['o_rank'],
                      'rank_slices':[{'rows':[x['rows'][0]+g*R.SHIPPED['o_rank'],x['rows'][0]+(g+1)*R.SHIPPED['o_rank']],
                                      'cols':x['cols']} for x in m['rank_slices']]}
                groups.setdefault(expert,[]).append(part)
        else:groups.setdefault(expert,[]).append(m)
    # Engramtables remain dedicated storage providers, not free layerfield.
    table=[h for n,h in headers.items() if n.startswith(f'layers.{L}.engram.embed.')]
    covered.update(h['tensor'] for h in table)
    missing=[n for n in headers if n.startswith(f'layers.{L}.') and n not in covered]
    if missing:raise ValueError(f'undeclared layer{L} tensors:{missing}')
    return groups,constants,he,table,covered


class Assignment:
    def __init__(self,records):self.records={(m['layer'],m['alias']):m for m in records}
    def address(self,layer,alias,rank,row,k):
        m=self.records[(layer,alias)];assert 0<=rank<4 and 0<=row<m['rows'] and 0<=k<m['K']
        si=next(i for i,(e0,el) in enumerate(m['segments']) if e0<=k<e0+el)
        superrow,mb=divmod(row,2)
        run=next(r for r in m['plans'] if r[0]==si and superrow>=r[2] and (superrow-r[2])%r[4]==0 and (superrow-r[2])//r[4]<r[3])
        _,pair,first,n,stride,start,words=run;which=(superrow-first)//stride
        e0,el=m['segments'][si];fmt=m['format'];unit=k//(128 if fmt=='bf16' else 512)
        # PP element_order interleaves sameclass superrows within each unit.
        half=(k%512)//256 if fmt=='fp8' else 0
        b=(k%8) if fmt=='bf16' else (k%256)//32
        order=S.segment_order(fmt,e0,el);idx=order.index((unit,b,half))
        a=start+idx*n+which
        slice_=m['rank_slices'][rank];rabs=slice_['rows'][0]+row;kabs=slice_['cols'][0]+k
        payload=(16 if fmt=='bf16' else (4 if fmt=='fp4' else 8))
        bit=(k%128//8)*16 if fmt=='bf16' else ((k%512//256)*136+(k%32)*4 if fmt=='fp4' else (k%32)*8)
        return {'stage':m['stage'],'rank':rank,'pair':pair,'mb':mb,'parity':a%2,'physical_row':a//2,
            'bit_range':[bit,bit+payload],'tensor':m['tensor'],'tensor_row':rabs,'tensor_col':kabs,
            'scale_tensor':m['source_scale_tensor'],'scale_index':[rabs if fmt=='fp4' else rabs//32,kabs//32] if m['source_scale_tensor'] else None,
            'segment':si,'ordered_K_range':[e0,e0+el],'return_region':superrow%REGIONS,
            'converted_BF16':m['conversion']!='native','ECC_sidecar_required':m['ECC']['extra_sidecar_bits']>0}


def phase_cfg(m,pair):
    """Emit actual25word element config for one allocated phase/pair (NB2PP1)."""
    runs=[r for r in m['plans'] if r[1]==pair];cfg=[0]*25
    if not runs:return cfg
    assert len({r[0] for r in runs})==1 # allocator places disjoint subtrees on differentpairs
    si=runs[0][0];e0,el=m['segments'][si];u0,u1=S.unit_range(m['format'],e0,el)
    rows=[]
    for _,_,first,n,stride,start,words in runs:
        rows.extend(first+j*stride for j in range(n))
    assert len(rows)<=8 and len(runs)==1
    start=runs[0][5];words=runs[0][6]
    for slot,row in enumerate(rows):
        lo=e0<=u0*512;hi=u1*512-256<e0+el
        cfg[slot]=(2*row|(si<<16)|(len(m['segments'])<<21)|((m['format']=='fp4')<<26)|(int(lo)<<27)|(int(hi)<<28)|((start+slot*words)<<29)|((m['format']=='bf16')<<42))
        cfg[17+slot]=2*row+1 if 2*row+1<m['rows'] else 0x8000
    cfg[8]=1|(u0<<1)|((u1-u0)<<9)|((len(rows)-1)<<19)|((m['format']=='bf16')<<22)
    cfg[16]=(math.ceil((u1-u0)/8)-1)|(start<<6)
    return cfg


def check_matrix(m):
    expected=(m['rows']+1)//2
    coverage=collections.defaultdict(list);intervals=collections.defaultdict(list)
    for si,p,first,n,stride,start,w in m['plans']:
        if p<0 or start%2 or start+n*w>DEPTH:raise ValueError('invalid physical4096 address span')
        e0,el=m['segments'][si]
        if w!=S.seg_words(m['format'],e0,el):raise ValueError('wordcapacity mismatch')
        if any((first+j*stride)%REGIONS!=p//(m['compiled_NP']//REGIONS) for j in range(n)):raise ValueError('returnregion owner mismatch')
        coverage[si].extend(first+j*stride for j in range(n));intervals[p].append((start,start+n*w))
    for si in range(len(m['segments'])):
        if sorted(coverage[si])!=list(range(expected)):raise ValueError('omitted/duplicated rowtree')
    ends=[e+el for e,el in m['segments']];starts=[e for e,el in m['segments']]
    if starts[0]!=0 or ends[-1]!=m['K'] or ends[:-1]!=starts[1:]:raise ValueError('Kcoverage')
    for e,el in m['segments']:
        quantum=128 if m['format']=='bf16' else 256;units=math.ceil(el/quantum)
        if units&(units-1) or e//quantum%units:raise ValueError('golden subtree alignment')
    return True


def key_for(L,alias):
    e=re.match(r'exp(\d+)\.(w[123])$',alias)
    if e:return (L<<24)|({'w1':1,'w3':2,'w2':3}[e[2]]<<21)|(int(e[1])<<12)
    order=['wq_a','wkv','wq_b','wo_b','gate','wo_a','shared.w1','shared.w3','shared.w2','indexer.wq_b','indexer.wk','indexer.weights_proj','compressor.wkv','compressor.wgate','engram.wkv']
    basealias=alias.split('.group')[0];base=(L<<24)|(order.index(basealias)<<16)
    if '.group' in alias:base+=int(alias.split('group')[1])*65536
    return base


def bind_program(L,ops,consts):
    """Original exact emitter stays failclosed. Successfully emittedPCs bind to owner APIs."""
    lay=R.ShapeLayout(R.SHIPPED,tp_exact=True,rope_storage='hbm_cache',layer=L)
    q={'wq_a':'wq_a','wkv':'wkv','wq_b':'wq_b','wo_b':'wo_b','indexer.wq_b':'iwq_b','engram.wkv':'ewkv'}
    me={'gate':'gate','wo_a':'wo_a','indexer.wk':'iwk','indexer.weights_proj':'iwp','compressor.wkv':'cwkv'}
    for a,m in ops.items():
        basealias=a.split('.group')[0]
        if basealias in q:lay.qmat[(L,q[basealias])]['base']=key_for(L,basealias)
        elif basealias in me:lay.mat[(L,me[basealias])]['base']=key_for(L,basealias)
        elif a.startswith('shared.'):
            lay.qmat[(L,'shared',a.split('.')[1])]['base']=key_for(L,a)
        elif a.startswith('exp0.'):
            part=a.split('.')[1];lay.qmat[(L,'exp',0,part)]['base']=key_for(L,a);lay.qmat[(L,'exp_stride',part)]=4096
    old=R.I.SU_LANES;R.I.SU_LANES=256
    try:
        try:program=R.ShapeBuilder(lay).build([L],False,False)
        except ValueError as e:
            return {'layer':L,'status':'FAIL_ORIGINAL_EXACT_TP_EMITTER_UNSUPPORTED','error':str(e),
                    'symbolic_ownership_opcodes':[{'alias':a,'key':key_for(L,a),'stage':m['stage'],'rows':m['rows'],'K':m['K']} for a,m in ops.items()],
                    'order':'Source phase declarations + dense then ascending expertIDs capacityorder; not a substitute for an exact unsupported ISA sequence'}
    finally:R.I.SU_LANES=old
    bykey={(m['format']=='bf16',key_for(L,a)):(a,m) for a,m in ops.items()}
    bound=[]
    for pc,f in enumerate(program):
        u=f.get('unit');entry={'pc':pc,'instruction':{k:v for k,v in f.items() if not k.startswith('_')},'tag':f.get('_tag')}
        if u==R.I.UNIT_QE and not f.get('qe_mode',0):
            key=f['qe_wbase']
            if f.get('qe_ind'):
                allbound=all(f'exp{e}.{part}' in ops for e in range(384) for part in ('w1','w3','w2'))
                entry['owner_lookup']={'API':'Assignment.address','layer':L,'expert_ID_from_VM':f['qe_ibase'],'expert_stride':f['qe_istride'],'all384_IDs_bound':allbound,'selected_order_preserved':True,'family_base':key}
            elif (False,key) in bykey:
                a,m=bykey[(False,key)];entry['weight_owner']={'alias':a,'stage':m['stage'],'compiled_NP':m['compiled_NP']}
        elif u==R.I.UNIT_ME and f.get('me_wsrc',0)==0:
            key=f.get('me_wbase',0)
            if (True,key) in bykey:
                a,m=bykey[(True,key)];entry['weight_owner']={'alias':a,'stage':m['stage'],'compiled_NP':m['compiled_NP']}
        bound.append(entry)
    return {'layer':L,'status':'PASS_SYMBOLIC_SOURCE_EMITTED_PC_OWNER_BINDING','program':bound,
            'physical_dispatch_implemented':False,'runtime_exactness_credit':False}


def compile_model(headers,candidate,out):
    counts=candidate['single_candidate_counts'];budget=counts['complete_pairs_per_die'];bf=counts['BF_pairs_per_die_reservation'];nstages=counts['stages']
    assert candidate['candidate_id']=='DS4096-TP4-S58-PAIR1' and counts['TP']==4
    pools=[Pool(budget,bf) for _ in range(nstages)];stage=0;failures=[];stats=[];layer_ops={};covered=set();rawproviders=[]
    def records():
        nonlocal stage
        for L in range(40):
            groups,constants,he,tables,names=declarations(headers,L);covered.update(names);layer_ops[L]={}
            for expert,ms in groups.items():
                while True:
                    trial=pools[stage].clone();planned=[];raw=[]
                    try:
                        if expert is None:
                            hw=sum(x['rows']*math.ceil(x['K']/64) for x in he)
                            if hw:raw.append({'stage':stage,'layer':L,'kind':'HE','declarations':he,**trial.raw_bankset([x['alias'] for x in he],hw)})
                            elements=sum(c['elements'] for c in constants)
                            if elements:raw.append({'stage':stage,'layer':L,'kind':'CROM','declarations':constants,**trial.raw_bankset([c['alias'] for c in constants],math.ceil(elements/8),1)})
                        for m in ms:
                            part=trial.matrix(m);part.update(stage=stage,compiled_NP=trial.np,key=key_for(L,m['alias']))
                            check_matrix(part);planned.append(part)
                    except CapacityError as e:
                        if stage+1<nstages:stage+=1;continue
                        failures.append({'layer':L,'expert':expert,'stage':stage,'error':str(e),'whole_group_unallocated':True})
                        # Preserve unplaced declarations, do not invent extra candidate dies.
                        for m in ms:yield {**m,'stage':None,'plans':[],'allocation_failure':str(e)}
                        break
                    pools[stage]=trial;rawproviders.extend(raw)
                    for m in planned:
                        layer_ops[L][m['alias']]=m
                        yield m
                    break
            if tables:rawproviders.append({'layer':L,'kind':'ENGRAM_TABLES','dedicated_table_die_count':counts['table_dies'],
                 'source_tensors':tables,'storage_bits':sum(h['source_storage_bytes']*8 for h in tables),
                 'physical4096_leaves':math.ceil(sum(h['source_storage_bytes']*8 for h in tables)/(4096*274)),
                 'complete_pair_equivalents':math.ceil(sum(h['source_storage_bytes']*8 for h in tables)/(4*4096*274)),
                 'storage_only_compute_not_instantiated':True,'table_die_physical_fit_credit':False})
            print(f'allocated layer{L} stage{stage} failures{len(failures)}',flush=True)
    gzrows(out/'assignments.jsonl.gz',records())
    # ECC is an explicit finite storage debit. Existing source has no decoder.
    ecc_by_stage=collections.Counter()
    for m in readrows(out/'assignments.jsonl.gz'):
        if m['stage'] is not None and m['format']=='fp4':
            ecc_by_stage[m['stage']]+=sum(n*w*2*8 for si,p,first,n,stride,start,w in m['plans'])
    for s,pool in enumerate(pools):
        need=math.ceil(ecc_by_stage[s]/(4*4096*274));empty=[p for p,f in pool.fill.items() if not f and p not in pool.bf]
        if len(empty)<need:failures.append({'stage':s,'error':'ECC sidecar cannot fit in remaining exclusive completeq pairs','required':need,'available':len(empty)})
        else:
            ps=sorted(empty)[:need]
            for p in ps:pool.raw.add(p);pool.fill[p]=DEPTH
            rawproviders.append({'stage':s,'kind':'ECC_FP4_SIDECAR','bits':ecc_by_stage[s],'pairs':ps,'read_bits_per_active_pair_cycle':16,'current_source_decoder_available':False})
        NP=pool.np;bits=8386*(2*NP-128)+2146304
        used=sum(v>0 for v in pool.fill.values());phw=max(1,(pool.phases-1).bit_length())
        stats.append({'stage':s,'compiled_NP':NP,'R':REGIONS,'NBF_shape':bf,'active_capacity_pairs':budget,'actually_used_pairs':used,
            'physical_ROMs_instantiated':4*budget,'physical_ROMs_in_compiled_declarations':4*NP,
            'padding_pairs':NP-budget,'logical_words_reserved_per_row_macro':sum(pool.fill.values()),
            'physical_gross_capacity_bits':4*budget*4096*274,'return_declared_bits':bits,'conditional_return_FF_50pct_mm2':bits*.37908/.5/1e6,
            'root_public_ports':REGIONS,'root_public_bits_per_cycle':REGIONS*69,'return_reduction_credit_qualified':False,
            'phase_count':pool.phases,'required_PHW':phw,'source_PHW6_fits':pool.phases<=64,
            'pair_cfg_bits_if_required_PHW':budget*25*48*(1<<phw),'phase_key_bits_if_required_PHW':32*(1<<phw),
            'keys_scanned_combinationally':1<<phw,'new_PHW_fanout_clock_ports_context_not_qualified':True})
    programs=[]
    for L in range(40):programs.append(bind_program(L,layer_ops[L],[]))
    gzrows(out/'stage_program_binding.jsonl.gz',programs)
    # Global text providers preserve full modelcapacity; multimodal/MTP inactive profile separately explicit.
    globals_=[headers[n] for n in ['embed.weight','head.weight','norm.weight']]
    for h in globals_:
        bits=h['source_storage_bytes']*8
        rawproviders.append({'kind':'HEAD_GLOBAL','tensor':h['tensor'],'shape':h['shape'],'source_bits':bits,
            'head_dies':counts['head_dies'],'fixed4096_complete_pairs':math.ceil(bits/(4*4096*274)),
            'physical_address_recipe':'linear nativeBF16 bitstream ->274-bit logicalword ->NB2slot ->parity/a>>1; exact head/embedding port binding gate separate',
            'declared_head_capacity_only_not_runtime_qualification':True})
        covered.add(h['tensor'])
    extra=sorted(set(headers)-covered)
    if any(n.startswith('layers.') for n in extra):raise ValueError('active layer tensor omitted')
    gzrows(out/'provider_assignment.jsonl.gz',rawproviders)
    sourcepaths=['tools/hdc_replay_v41.py','tools/rtl_v41_fullshape_layer_campaign.py','tools/v41_fullshape_weight_layout.py','tools/rtl_v41_rom_array.py','tools/v41_die_images_w17w10.py','rtl/v41rom/ot_v41_rom_elem_w10.sv','rtl/v41die/ot_v41_rom_adapt.sv']
    report={'schema':'opentallas.fullmodel.owner_compiler.v1','source_commit':PIN,'candidate_id':candidate['candidate_id'],
        'source_sha256':{p:sha(gitread(p)) for p in sourcepaths},'layers':40,'expert_IDs_per_layer':384,'ranks_per_stage':4,
        'candidate_stages':nstages,'allocation_failures':failures,'capacity_verdict':'PASS' if not failures else 'FAIL_OVERCAPACITY',
        'stage_stats':stats,'active_source_tensors_covered':len(covered),'inactive_checkpoint_tensors':extra,
        'inactive_profile':'Vision/aligner/image special tokens/MTP are outside the shipped40layer textdecoder profile; preserved, not dropped fromcheckpoint.',
        'program_bindings':collections.Counter(p['status'] for p in programs),
        'current_source_PHW6_verdict':'PASS' if all(s['source_PHW6_fits'] for s in stats) else 'FAIL_REQUIRED_SOURCE_PARAMETER_PLUMBING_AND_CONTEXT_MODEL',
        'ECC_verdict':'FINITE_SEPARATE_DEBIT_REQUIRED_DECODER_AND_LATENCY_CONTRACT_UNQUALIFIED',
        'assignment_API':'Assignment.address(layer,alias,rank,localrow,localK)',
        'golden_order':'Whole dense bundles/expertIDs partitioned monotonically; every superrow stays in its root region. K subtrees power-of-two aligned, ordered by originalK. Runtime selectedexpert order never sorted by stage.',
        'unpartitionable_grains':['NB2superrow+alignedK subtree+source rowroot','whole expert ID for stagepartition','whole dense layer bundle inclHE/constants for stagepartition'],
        'RTL_builds':0,'checkpoint_payload_reads':0,'physical_or_fulltoken_admission':False}
    (out/'model.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--headers',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);x=compile_model(load_headers(a.headers),json.loads(a.candidate.read_text()),a.out)
    print(json.dumps({'capacity':x['capacity_verdict'],'failures':len(x['allocation_failures']),'programs':x['program_bindings']}))
