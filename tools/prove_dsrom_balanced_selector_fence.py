"""Full compiled selector source algebra plus transport proof, never RTL proof.

Python IEEE comparisons provide independent ranking; source-modeled radix and
balanced networks provide threshold/selection. Synthetic inputs are operands.
Event edges are local normalized proof indices, not an accepted field trace.
"""
from collections import deque
import hashlib
import json
from pathlib import Path
import random
import struct
import uarch_topk_balanced_filter_model as B
import uarch_topk_integer_tree_model as I
import dsrom_selector_physical_join as J

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_balanced_selector_fence_proof_20261002'
SOURCE='results/uarch/topk_finite_source_context_20261002/inputs/c429b2732aea08d9f6fa9ddc850afdbd7b4bd6ea/rtl/chip/ot_coll_topk_merge.sv'
PINS={SOURCE:'e56fefef4d92d0de6faa7a583f9e419bcb9178290a1ef74df34c38aee0b509c6',
      'tools/uarch_topk_balanced_filter_model.py':'7a682b229892ef26c0782fcfdee59100826eeacd73c945c6a2e581fcccc6f2f9',
      'tools/uarch_topk_integer_tree_model.py':'a8cc34e17f0886493431f5267f33fcb923af4bd5d9618da8bdfe74c3c723ce4b'}


def source_pins():
    for path,digest in PINS.items():
        if J.sha((ROOT/path).read_bytes())!=digest: raise ValueError('arithmetic source changed')
    return J.inputs()


def audit_union(model):
    """Check delivered element clone inventory; no selector PG transfer."""
    if model['candidate']!='DS4096-TP4-S58-PAR2-NP2048':raise ValueError('physical scenario changed')
    out={}
    for name,c in model['cases'].items():
        pins=c['clone_translated_CLK_RESET_pin_descriptors'];names=[p['instance'] for p in pins]
        if len(pins)!=8 or len(set(names))!=8 or any('wake' in n.lower() for n in names):
            raise ValueError('clone inventory aliases existing WAKE')
        boxes=[]
        for p in pins:
            if p['master'] not in ('DFFASRHQNx1_ASAP7_75t_R','DFFHQNx1_ASAP7_75t_R'):
                raise ValueError('unexpected clone state master')
            valid=p['master']=='DFFASRHQNx1_ASAP7_75t_R'
            if p['CLK']!='leaf_clk[0]' or p['RESETN']!=('rst_n' if valid else None):
                raise ValueError('clone clock/reset source mismatch')
            x,y=p['origin_DBU']
            if x%54 or y%270 or p['orientation'] not in ('R0','MX'):raise ValueError('clone off source site/row grid')
            w,h=model['physical_master_templates'][p['master']]['size_DBU']
            box=(x,y,x+w,y+h)
            if any(x<b[2] and b[0]<box[2] and y<b[3] and b[1]<box[3] for b in boxes):
                raise ValueError('clone cell overlap')
            boxes.append(box)
        if sum(p['RESETN']=='rst_n' for p in pins)!=4:raise ValueError('reset inventory mismatch')
        for corner,u in c['clock_reset_full_source_union'].items():
            if u['new_leaf0_sinks']-u['existing_leaf0_sinks']!=8:raise ValueError('duplicate/missing new clock sinks')
            if abs(u['composed_leaf0_pin_cap_fF']-u['existing_leaf0_pin_cap_fF']-c['clone_clock_pin_debit_SS_FF_fF'][corner])>1e-8:
                raise ValueError('clock load not composed once')
            if abs(u['composed_reset_pin_cap_fF']-u['existing_reset_pin_cap_fF']-c['clone_reset_pin_debit_SS_FF_fF'][corner])>1e-8:
                raise ValueError('reset load not composed once')
            if u['SETN_constant1_extra_pin_count']!=4:raise ValueError('missing SETN tie provider')
        out[name]=dict(clone_clock_reset_inventory_checked=True,clone_sites_on_source_grid=True,
          owner_PG_rail_projection_terminals=c['source_PG_rail_projection_terminal_count'],
          owner_PG_rail_projection_failures=c['source_PG_rail_projection_failures'],
          selector_station_sites_qualified=False,extracted_clock_reset_or_hold_qualified=False,
          scope='Element clone source inventory/row-grid only; owner PG rail projection is not signal escape or selector PG proof.')
    return out


def key(x):
    if x==0x80000000:x=0
    return (~x)&0xffffffff if x>>31 else x|0x80000000


def nan(x):return (x>>23)&255==255 and (x&0x7fffff)!=0


def threshold(keys,k,mutant=None):
    prefix=0;rr=k;trace=[]
    for shift in (24,16,8,0):
        counts=[0]*256
        for value in keys:
            if value>>(shift+8)==prefix>>(shift+8):counts[(value>>shift)&255]+=1
        if max(counts)>8192 or sum(counts)>8192:raise ValueError('compiled capacity exceeded')
        suffix=I.tree_suffix(counts,14)
        found,bin_,greater=I.tree_choose(counts,suffix,rr,14)
        if not found:raise ValueError('threshold not found')
        prefix|=bin_<<shift;rr-=greater
        trace.append(dict(shift=shift,prefix=prefix,remaining=rr,bin=bin_,greater=greater,counts_sha256=J.sha(struct.pack('<256H',*counts))))
    if mutant=='threshold_off_by_one':prefix=(prefix+1)&0xffffffff
    return prefix,rr,trace


def fixture(runtime,pattern):
    rng=random.Random(20261002+runtime)
    if pattern=='all_tie':return [0x3f800000]*(4*runtime)
    specials=[0x80000000,0,0x3f800000,0xbf800000,0x7f800000,0xff800000,1,0x80000001,0x7f7fffff,0xff7fffff]
    if pattern=='signed_boundaries':return [specials[i%len(specials)] for i in range(4*runtime)]
    if pattern=='random_finite':
        words=[]
        for _ in range(4*runtime):
            w=rng.getrandbits(32)
            if (w>>23)&255==255:w^=1<<23
            words.append(w)
        return words
    raise ValueError('unknown immutable operand pattern')


def compare(runtime,k,pattern,mutant=None):
    if runtime not in (512,2048) or not 1<=k<=4*runtime:raise ValueError('illegal source runtime')
    words=fixture(runtime,pattern);ids=[(i//runtime)*(2*runtime)+i%runtime for i in range(4*runtime)]
    floats=[struct.unpack('!f',struct.pack('!I',w))[0] for w in words]
    ranked=sorted(range(len(words)),key=lambda i:(-floats[i],ids[i]))
    golden=sorted(ids[i] for i in ranked[:k])  # Independent numerical ranking and stable ID output.
    keys=list(map(key,words));t,quota,radix=threshold(keys,k,mutant)
    rows=[]
    for start in range(0,len(words),64):
        if (start//64)%11==5:rows.append(None)  # Valid bubble; no quota consumption.
        chunk=keys[start:start+64]
        rows.append(([int(x>t) for x in chunk],[int(x==t) for x in chunk],ids[start:start+64]))
    outputs,left,trace=B.row_pipeline(rows,quota,14)
    selected=[value for _,row in outputs for value in row]
    if mutant=='reverse_tie':
        selected=[value for row in rows if row for value in B.balanced_row(*row,quota,14)[0]][::-1]
    if selected!=golden:raise AssertionError('SELECTION_DIFF')
    if left!=0:raise AssertionError('QUOTA_DIFF')
    public=B.public_words(outputs,64)
    expected=golden+[0]*((-k)%16)
    if [v for word in public for v in word]!=expected:raise AssertionError('PUBLIC_WORD_DIFF')
    # Source formed-write contract:4 bank addresses, each one16-ID word;
    # done is an operand in the same packet, and never a fabricated ACK.
    native=[];dst=8192;oidx=0
    for group,start in enumerate(range(0,len(public),4)):
        words_=public[start:start+4];nw=len(words_)
        packet=dict(we=(1<<nw)-1,addr=[(dst+oidx+lane)&0x7fff for lane in range(4)],
                    data=words_+[[0]*16]*(4-nw),done=0)
        native.append((1000+group,packet));oidx+=nw
    native.append((native[-1][0]+2,dict(we=0,addr=[0]*4,data=[[0]*16]*4,done=1)))
    expected_events=[(time+127,packet) for time,packet in native]
    returned={time+99:packet for time,packet in native};delay=deque([None]*28);observed=[]
    for cycle in range(native[-1][0]+130):
        packet=delay.popleft();delay.append(returned.get(cycle))
        if packet is not None:observed.append((cycle,packet))
    if mutant=='early_done':observed[-1]=(native[-1][0]+99,native[-1][1])
    if observed!=expected_events:raise AssertionError('FENCE_DIFF')
    writes=[(time,lane,p['addr'][lane],p['data'][lane]) for time,p in observed for lane in range(4) if p['we']&(1<<lane)]
    if [a for _,_,a,_ in writes]!=list(range(dst,dst+len(public))):raise AssertionError('WRITE_ADDRESS_DIFF')
    if [v for _,_,_,word in writes for v in word]!=expected:raise AssertionError('WRITE_DATA_DIFF')
    if observed[-1][0]<=writes[-1][0]:raise AssertionError('DRAIN_DIFF')
    return dict(runtime_n=runtime,k=k,pattern=pattern,candidates=len(words),operand_sha256=J.sha(struct.pack('<'+str(len(words))+'I',*words)),
       threshold=t,quota=quota,radix_trace=radix,filter_rows=len(trace),row_bubbles=len(rows)-len(trace),
       selected_IDs=k,public_VM_words=len(public),selection_sha256=J.sha(struct.pack('<'+str(k)+'I',*golden)),
       actual_model_selected_sha256=J.sha(struct.pack('<'+str(k)+'I',*selected)),
       formed_writes=[list(w) for w in writes],local_normalized_done_edge=observed[-1][0],original_consumer_absolute_deadline=None,
       source_field_or_RTL_execution=False)


def build():
    fixed=source_pins();cases=[]
    for runtime in (512,2048):
        for pattern in ('all_tie','signed_boundaries','random_finite'):
            for k in (1,63,64,65,512,4*runtime):cases.append(compare(runtime,k,pattern))
        if runtime==2048:cases.append(compare(runtime,2048,'signed_boundaries'))
    mutants={}
    for mutant in ('threshold_off_by_one','reverse_tie','early_done'):
        try:compare(2048,512,'all_tie',mutant)
        except AssertionError as e:mutants[mutant]=str(e)
        else:raise AssertionError('mutant escaped')
    plan=fixed['caller_plan']
    return dict(schema='opentallas.fullshape.selector-fence.source-proof.v1',geometry=dict(N=4,NMAX=2048,LDW=4,P=64,PF=64,DIG=8,CB=14),
      immutable_input_only=True,expected_values_assertions_only=True,sourcepins=PINS,cases=cases,mutant_DIFF=mutants,
      service_extra_cycles=142,transport_extra_cycles=plan['additional_cycles_per_call'],ninecall_increment=(142+226)*9,
      RTL_equivalence=False,clock_or_physical_qualification=False,engine_RTL_admitted=False,PR_admitted=False,
      scope='Full compiled geometry source arithmetic, stable tie/order, public ID padding and formed-write fence event algebra. No RTL or field trace. Source-produced timestamps unknown.',
      limitations=['No balanced selector RTL exists in this gate; source model cannot qualify that implementation.',
                   'Actual station legal sites/global clock/reset/PG/signal escapes/extractedRC and full context hold remain required.',
                   'Input IDs are rank-major increasing as required by source contract; no arbitrary unsorted-ID tie contract introduced.'])


if __name__=='__main__':
    out=build();BASE.mkdir(parents=True,exist_ok=True);(BASE/'proof.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(cases=len(out['cases']),mutants=out['mutant_DIFF'],RTL_equivalence=False)))
