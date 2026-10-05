#!/usr/bin/env python3
"""Source-bound demand of actual relocated SU commands; no memory/RTL launches."""
import collections,gzip,hashlib,json,math,subprocess
from pathlib import Path
import hdc_isa_v41 as I
PIN='4080bb5fd'
PREFIX='results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2'
ROOT=Path(__file__).resolve().parents[1]
def obj(path):return subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT)
def clog(x):return max(0,(max(1,x)-1).bit_length())
def ranges(values):
    out=[]
    for v in sorted(values):
        if out and out[-1][1]==v:out[-1][1]+=1
        else:out.append([v,v+1])
    return out

def batches(f,n=1024,m=256):
    """Mirror vec S1/S2 slots and live lane row/column positions."""
    ni,no=f['su_nin'],f['su_nout']
    if f['su_d_nin'] or f['su_d_nout']:raise ValueError('dynamic dimensions must be resolved explicitly')
    half=f['b_half'];red=f['red']!=I.RED_NONE
    ok=(f['a_ind']==0 and f['dst']!=I.DST_KVT and
        (ni%2==0 or not(half or f['qm'] in (I.QM_ALT_NP,I.QM_ALT_PN))) and
        f['a_so']==ni*f['a_si'] and f['b_so']==(ni//2 if half else ni)*f['b_si'] and
        (f['c_pair'] or f['c_so']==ni*f['c_si']) and
        f['d_so']==(ni//2 if half else ni)*f['d_si'] and
        (f['dst']==I.DST_NONE or f['o_so']==ni*f['o_si']))
    flat=(not red or f['red_whole'] or f['red_tree']) and ok
    wnf=(f['red_whole'] or f['red_tree']) and red and not ok and no>1
    scalar=f['sfu'] in (I.SFU_RSQRT,I.SFU_SQRT,I.SFU_SPSQRT,I.SFU_EGATE)
    sf=f['sfu'] in (I.SFU_EXP,I.SFU_SIGM,I.SFU_SILU) or f['m1'] in (I.M1_DIVB,I.M1_DIVIMM)
    width=1 if scalar else m if sf else n
    sni=ni*no if flat else ni
    ls=min((sni&-sni).bit_length()-1 if wnf else clog(max(sni,8 if red else 1)),clog(width))
    slot=1<<ls;packed=not wnf and sni<=slot
    pow2=f['r_so']>0 and f['r_so']&(f['r_so']-1)==0
    nslot=width//slot if packed and (not red or pow2) else 1
    if flat:
        for start in range(0,ni*no,slot):yield [(0,i) for i in range(start,min(start+slot,ni*no))]
    else:
        for row in range(0,no,nslot):
            for inner in range(0,ni,slot):
                yield [(o,i) for o in range(row,min(row+nslot,no)) for i in range(inner,min(inner+slot,ni))]

def demand(f,bindings):
    axes={b['operand']:b for b in bindings};unique={a:set() for a in axes};allunique=set();hist=collections.Counter()
    peak=0;service=0;logicaluses=0;peakbank=0;containerpeak=0;bursts=0
    for coords in batches(f):
        readset=set();uses=0
        for axis,b in axes.items():
            for o,i in coords:
                ii=i//2 if axis in 'bd' and f['b_half'] else i
                address=f[axis+'_base']+o*f[axis+'_so']+ii*f[axis+'_si']
                if b['kind']=='checkpoint_CROM' and not b['tensor_base']<=address<b['tensor_end']:raise ValueError('demand outside actual tensor')
                unique[axis].add(address);readset.add(address);uses+=1
        # Scalar logical service reads each distinct word once per burst;
        # same-address fanout/buffering is a priced, UNIMPLEMENTED requirement.
        mapped={a for axis,b in axes.items() if b['kind']=='checkpoint_CROM' for a in unique[axis]}
        # Use only this burst's addresses, never invent placement for generated products.
        mapped &= readset
        bank=collections.Counter(a//3//4096 for a in mapped)
        peakbank=max(peakbank,max(bank.values(),default=0));containerpeak=max(containerpeak,len({a//3 for a in readset}))
        peak=max(peak,len(readset));service+=len(readset);logicaluses+=uses;allunique.update(readset)
        hist[len(readset)]+=1;bursts+=1
    return {'operand_demands':[dict(operand=a,kind=b['kind'],tensor=b.get('tensor'),base=f[a+'_base'],
            outer_stride=f[a+'_so'],inner_stride=f[a+'_si'],half_inner=bool(a in 'bd' and f['b_half']),
            logical_uses=f['su_nin']*f['su_nout'],unique_words=len(unique[a]),unique_address_ranges=ranges(unique[a]),
            reuse_factor=(f['su_nin']*f['su_nout'])/len(unique[a]) if unique[a] else 0) for a,b in axes.items()],
        'vector_elements':f['su_nin']*f['su_nout'],'nin':f['su_nin'],'nout':f['su_nout'],
        'pred':f['pred'],'emit_bursts':bursts,'logical_lane_uses':logicaluses,
        'unique_words_per_command':len(allunique),'peak_unique_words_per_emit':peak,
        'peak_containers_per_emit':containerpeak if all(b['kind']=='checkpoint_CROM' for b in axes.values()) else None,
        'peak_same_bank_unique_words_per_emit':peakbank if all(b['kind']=='checkpoint_CROM' for b in axes.values()) else None,
        'unique_words_per_emit_histogram':dict(hist),'one_port_cycles_within_emit_dedup':service,
        'ideal_command_prefetch_cycles':len(allunique),'command_prefetch_buffer_bits':len(allunique)*64,
        'lane_use_boundary_bits_per_command':logicaluses*32,
        'peak_unique_response_boundary_bits':peak*64,'peak_useful_coefficient_bits':peak*32,
        'required_values_per_serial_emit_cycle':peak,'equivalent_values_per_fast_cycle_at_continuous_serial_emit':peak*3/4,
        'service_ns_at_1p2GHz':service/1.2,'ideal_prefetch_ns_at_1p2GHz':len(allunique)/1.2}

def build():
    raw=obj(PREFIX+'.json');audit=json.loads(raw);ranks=[]
    for rank in audit['ranks']:
        data=gzip.decompress(obj(PREFIX+f".rank{rank['rank']}.templates.bin.gz"))
        assert hashlib.sha256(data).hexdigest()==rank['encoded_template_sha256']
        records=[];offset=0
        stages=rank['stages']+[dict(layer='head',instruction_count=7,bindings=rank['head_bindings'],unbound=[])]
        for stage in stages:
            grouped=collections.defaultdict(list)
            for b in stage['bindings']:
                if b['kind']=='checkpoint_CROM':grouped[b['instruction']].append(b)
            for b in stage['unbound']:
                grouped[b['instruction']].append(dict(b,kind='unbound_generated',tensor=f"L{stage['layer']}.engram.q_times_k"))
            for pc,bs in grouped.items():
                globalpc=offset+pc;f=I.decode(int.from_bytes(data[globalpc*256:(globalpc+1)*256],'little'),full_shape=True)
                d=demand(f,bs);records.append(dict(layer=stage['layer'],instruction=pc,global_instruction=globalpc,**d))
            offset+=stage['instruction_count']
        assert offset==4778
        ranks.append({'rank':rank['rank'],'bound_operands':sum(len([b for b in r['operand_demands'] if b['kind']=='checkpoint_CROM']) for r in records),
            'records':records,'summary':{'commands':len(records),'per_command_unique_prefetch_cycles':sum(r['ideal_command_prefetch_cycles'] for r in records),
                'per_emit_dedup_service_cycles':sum(r['one_port_cycles_within_emit_dedup'] for r in records),
                'peak_unique_values_per_emit':max(r['peak_unique_words_per_emit'] for r in records),
                'total_coefficient_lane_uses':sum(r['logical_lane_uses'] for r in records),
                'service_ns_at_1p2GHz':sum(r['one_port_cycles_within_emit_dedup'] for r in records)/1.2,
                'bound_service_cycles':sum(sum(o['unique_words'] for o in r['operand_demands'] if o['kind']=='checkpoint_CROM') for r in records),
                'unbound_generated_service_cycles':sum(sum(o['unique_words'] for o in r['operand_demands'] if o['kind']=='unbound_generated') for r in records)}})
    return {'schema':'opentallas.w11.actual-CROM-demand.v1','source':{'commit':PIN,'path':PREFIX+'.json','sha256':hashlib.sha256(raw).hexdigest()},
        'geometry':{'SUN':1024,'SUM':256,'serial_GHz':0.9,'fast_GHz':1.2,'scalar_issue_per_fast_cycle':1},'ranks':ranks,
        'scope':'Static source-bound coefficient demand at command execution, not dynamic token timing. Predicated commands tabulated even if skipped. Generated Engram coefficients use symbolic command-local addresses, not physical binding. RoPE held-cache excluded.',
        'pricing_rules':['729 bound operand descriptors are not729reads; each lane coefficient use is enumerated',
            'Dedup requires explicit capture/broadcast buffer andfanout; current service implementation NULL',
            'Per-command prefetch assumes a full command coefficient buffer; no cross-command reuse credit',
            'All commands serialized sum is CROM service demand, not additive token slowdown; subtract overlapped existing compute only with phase calendar',
            '2capture/select cycle candidate pipeline and CDC/backpressure/route latency excluded; actual composed token unknown'],
        'physical_gate':{'bank_mux_and_route':None,'broadcast_ports_and_capture_buffers':None,'replicas_and_copies':None,'CDC':None,'phase_calendar':None},
        'hardware_admission':False,'checkpoint_reads':0,'jobs_launched':0,'gain_credit':0}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();r=build()
 if a.out.exists():raise ValueError('refuse overwrite evidence')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(gzip.compress(json.dumps(r,sort_keys=True).encode(),mtime=0))
 print(json.dumps([{'rank':x['rank'],**x['summary']} for x in r['ranks']]))
