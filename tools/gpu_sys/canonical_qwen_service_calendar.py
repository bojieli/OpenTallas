"""Calibratable canonical1737 source-worker service calendar, no arithmetic.

The unchanged870 runtime serializes PC issue through retirement and each RPC.
Native LOOP demand comes from pinned metadata-only counting functions. Unknown
launch/RF/ACK/CDC/retirement prices remain symbolic; a partial priced subtotal
is never a token latency. Peirce owns the KV528 commit interval consumed here.
"""
import argparse
import ast
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/uarch/qwen_hbm_native_service_calendar_20261003'
PROGRAM='results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'
SOURCE='results/uarch/c0_pc40_payload_lease_20261003/inputs/h3_qwen_bounded_native.py'
SOURCE_SHA='282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b'
KV_MODEL_SHA='759eb1a0149ff29c012fc18ef2cbc4833bc2bf76ad99afbe2a6d048c96a0f364'
KV_OWNER_COMMIT='1b8c58185ad586a05f4ba03603ea5032f5cf4bc8'
PROGRAM_SHA='ab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354'
FAST=Fraction(2500,3)
SERIAL=Fraction(10000,9)
NATIVE_PHASES=('launch','RF_operand_capture','execute','W4_write_ACK',
               'W6_result_capture','reverse_retirement','forward_route_CDC','reverse_route_CDC')


def need(ok,message):
    if not ok:raise ValueError(message)


def canonical(obj):return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def verify_W2_runtime(raw,kv_model):
    measured=kv_model['measured_service']
    need(sha(raw)==measured['runtime_sha256'],'Peirce/current measured W2 runtime pin')
    text=raw.decode()
    segment=text.split('CASE_PASS full16_oldcredit_no_bypass_outoforder')[0].split('PORT_EVENT fenced_rearm_accept cycle88')[1]
    accepts=[int(v) for v in re.findall(r'PORT_EVENT request_accept cycle(\d+) tag00000000[0-9a-f] gen1 we0',segment)]
    need(len(accepts)==16 and accepts==measured['actual16_request_accept_edges']
         and all(b-a==19 for a,b in zip(accepts,accepts[1:])),'actual sixteen same-client accepts proveII19')
    return accepts


def counting_functions(raw):
    need(sha(raw)==SOURCE_SHA,'original870 counting/control source pin')
    names={'code_sector_count','interleaved_BF16_windows','tiled_counts','tiled_kernel_calls'}
    tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    need({n.name for n in nodes}==names,'all original metadata counters')
    namespace=dict(math=math,Counter=Counter)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'original870-metadata-counts','exec'),namespace)
    return namespace


def source_demands(native,position,counters):
    p=native['source_program']
    need(type(position) is int and 0<=position<p['context_capacity'],'source position aperture')
    rows=[]
    for op,src in zip(native['operations'],p['instructions']):
        need(op['pc']==src['id'] and op['opcode']==src['opcode'],'source PC/operation alignment')
        need(op['loop_program']['row_step']==128 and op['loop_program']['norm_leaf']==8
             and op['loop_program']['code_K_window']==32,'original fixed LOOP/tile phases')
        calls=counters['tiled_kernel_calls'](src,p,position)
        primitives=Counter();units=Counter();recipes=[]
        for kernel,repetitions in calls.items():
            code=native['microcode'][kernel];abi=native['tile_kernel_ABI'][kernel]['steps']
            need(len(code)==len(abi),'ordered recipe/ABI steps')
            steps=[]
            for index,(node,contract) in enumerate(zip(code,abi)):
                need(node['op']==contract['op'],'literal native ordered instruction')
                bits=contract['write']['bits_per_element']
                for sub,opcode in enumerate(contract['native_steps']):
                    # NEG has three32-bit operations; never treat it as one.
                    width=32 if node['op']=='NEG' else bits
                    key=f'{opcode}/bits{width}'
                    units[key]+=repetitions;primitives[opcode]+=repetitions
                    steps.append(dict(step=index,substep=sub,service=key,source_node=node,
                                      source_contract=contract))
            recipes.append(dict(template=kernel,repetitions=repetitions,ordered_steps='native_recipes/'+kernel))
        if position==p['context_capacity']-1:
            need(dict(primitives)==op['calendar_export']['physical_primitives']['native_primitive_commands'],
                 'original full-context primitive census')
        rows.append(dict(pc=op['pc'],family=op['opcode'],dependencies=op['dependencies'],
                         loop=op['loop_program'],native_units=dict(units),recipes=recipes,
                         source_counts=counters['tiled_counts'](src,p,position)['logical_counts']))
    return rows


def same_client_calendar(requests,*,same_client_II=19,different_client_II=10):
    """Actual mapped accepts: II is max recurrence, never a per-request RTT.

    This helper consumes actual mapped physical PC/client and supplied positive
    end-to-end phase prices. It does not infer routes from rank/address/shape.
    Dependencies wait for physical reverse, not merely an early response.
    """
    need(same_client_II==19 and different_client_II==10,'selected W2 II contract unchanged')
    pc_last={};client_last={};done=[];out=[]
    for i,r in enumerate(requests):
        pc,client=r['physical_PC'],r['client']
        need(type(pc) is int and 0<=pc<128 and type(client) is int and 0<=client<6,'actual W2 route')
        for k in ('offer_edge','request_edges','backend_edges','capture_edges','reverse_edges'):
            need(type(r[k]) is int and r[k]>=(0 if k=='offer_edge' else 1),'positive actual phase '+k)
        deps=r.get('depends_on',[])
        need(all(type(d) is int and 0<=d<i for d in deps),'previous actual reverse dependencies')
        offer=max([r['offer_edge']]+[done[d] for d in deps])
        accept=max(offer+r['request_edges'],pc_last.get(pc,-10)+10,client_last.get((pc,client),-19)+19)
        capture=accept+r['backend_edges']+r['capture_edges']
        reverse=capture+r['reverse_edges']
        pc_last[pc]=accept;client_last[pc,client]=accept;done.append(reverse)
        out.append(dict(index=i,physical_PC=pc,client=client,offer_edge=offer,
                        accept_edge=accept,capture_edge=capture,reverse_edge=reverse))
    return out


class Prices:
    """Each phase is unknown or a positive, source/evidence-bound duration."""
    def __init__(self,profile=None):
        self.profile={} if profile is None else profile
        self.services=self.profile.get('services',{})
        self.used=set()

    def duration(self,key):
        self.used.add(key)
        row=self.services.get(key)
        if row is None or row.get('edges') is None:return None
        need(row.get('domain') in ('streaming','serial'),'actual enrolled clock domain '+key)
        edges=row['edges']
        need(type(edges) is int and edges>=0,'integer edge price '+key)
        if edges==0:
            need(key.endswith('route_CDC') and row.get('same_clock_source_sha256') in self.profile.get('verified_same_clock_source_sha256',[]),
                 'zero only for source-proven same-clock boundary '+key)
        else:
            need(bool(row.get('source')) and row.get('scope') in ('measured','source_minimum','conditional'),
                 'explicit phase evidence/scope '+key)
        period=FAST if row['domain']=='streaming' else SERIAL
        # Clock/uncertainty are fixed; a slow service needs latency stages, not a relaxed headline clock.
        need(Fraction(row.get('period_ps',period))==period,'unchanged domain period '+key)
        return edges*period


class Interval:
    def __init__(self):self.priced=Fraction(0);self.floor=Fraction(0);self.missing=Counter();self.terms=[]
    def charge(self,key,count,prices,*,minimum_ps=0):
        if count==0:return
        need(type(count) is int and count>0,'positive source service demand')
        value=prices.duration(key);minimum=Fraction(minimum_ps)
        if value is None:
            self.missing[key]+=count;self.floor+=minimum*count
        else:
            need(value>=minimum,'price cannot undercut source interval '+key)
            self.priced+=value*count;self.floor+=value*count
        self.terms.append(dict(service=key,count=count,duration_ps=None if value is None else str(value),
                               source_minimum_ps=str(minimum) if minimum else None))
    def merge(self,other):
        self.priced+=other.priced;self.floor+=other.floor;self.missing.update(other.missing)
    def record(self):
        return dict(duration_ps=None if self.missing else str(self.priced),
                    bound_subtotal_ps=str(self.priced),known_constraints_floor_ps=str(self.floor),
                    unresolved=dict(self.missing),terms=self.terms)


def kv_demand(family,p,position):
    """Exact original BoundKVStorage RPC demand, not bulk-byte substitution.

    Its read checks bitmap once per addressed byte. The current real server
    caches sectors only inside one payload RPC; there is no cross-RPC cache.
    These costs cannot be hidden behind the already-finished FP8 writer.
    """
    c=p['config'];T=position+1;payload=2*(c['num_key_value_heads']//2)*c['head_dim']
    windows=2*(c['num_key_value_heads']//2)*((c['head_dim']+127)//128)
    counts=Counter()
    if family=='KV_WRITE':
        counts.update({'kv_state_read/1':1,'kv_state_write/8':1,'kv_begin':1,'kv_stage_write/64':payload//64})
    elif family=='KV_FENCE':
        counts.update({'kv_commit':1,'kv_state_read/1':1,'kv_state_write/1':1,
                       'kv_state_write/16':1,'kv_publish':1})
    elif family=='KV_READ':
        counts.update({'kv_state_read/1':T+payload*T,'kv_state_read/16':1+windows*T,
                       'kv_state_write/16':1,'kv_acquire':1,'kv_payload_read/128':windows*T})
    elif family in ('SCORES','PV'):
        counts.update({'kv_state_read/16':1,'kv_state_write/16':1,'kv_consumer_done':1})
        if family=='PV':counts['kv_reader_release']=1
    return counts


def compose(native,position,kv_model,profile=None,*,raw_source):
    need(sha(canonical(native))==PROGRAM_SHA,'complete canonical1737 program identity')
    need(len(native['operations'])==1737 and [o['pc'] for o in native['operations']]==list(range(1737)),
         'complete source1737 PCs')
    need(kv_model['schema']=='QWEN_ACTUAL_KV_SERIALIZED_CRITICAL_PATH_V1','Peirce exact commit provider')
    need(kv_model['measured_service']['same_client_request_II']==19,'actual W2 measuredII19')
    writers=[o['pc'] for o in native['operations'] if o['opcode']=='KV_WRITE']
    fences=[o['pc'] for o in native['operations'] if o['opcode']=='KV_FENCE']
    need(writers==kv_model['KV_write_PCs'] and len(writers)==72,'Peirce/source72writer join')
    need(fences==[w+1 for w in writers],'actual commit lives at KV_FENCE after staging')
    commit_floor=Fraction(kv_model['scenarios']['zero_external_protocol_floor']['exposed_commit_ps'])
    # This is only a retained local protocol constraint. Missing backend,
    # routes, CDC, refresh, launch and drain keep the composed latency unknown.
    counts=source_demands(native,position,counting_functions(raw_source))
    prices=Prices(profile);total=Interval();rows=[];native_counts=Counter();kv_counts=Counter()
    prefix_known=Fraction(0);prefix_complete=True
    startup=Interval();startup.charge('startup_reset_release',1,prices)
    startup.charge('source_token_position_publication',1,prices)
    total.merge(startup);prefix_known=startup.priced;prefix_complete=not startup.missing
    for row in counts:
        interval=Interval();pc=row['pc'];family=row['family']
        interval.charge('PC_launch',1,prices)
        # RPC counts for page traffic are not the old huge conservative word
        # budgets, or guessed shape/32SM homes. Real source trace must calibrate
        # this PC interval. It excludes native scratch and all KV/state RPCs.
        interval.charge(f'PC{pc}/source_delivery',1,prices)
        interval.charge(f'PC{pc}/fixed_LOOP_tile_control',1,prices)
        for service,n in row['native_units'].items():
            native_counts[service]+=n
            for phase in NATIVE_PHASES:interval.charge(f'native/{service}/{phase}',n,prices)
        kv=kv_demand(family,native['source_program'],position)
        for service,n in kv.items():
            kv_counts[service]+=n
            interval.charge(service,n,prices,minimum_ps=commit_floor if service=='kv_commit' else 0)
        interval.charge(f'PC{pc}/result_publication',1,prices)
        interval.charge(f'PC{pc}/source_retirement',1,prices)
        start=str(prefix_known) if prefix_complete else None
        prefix_known+=interval.priced;prefix_complete=prefix_complete and not interval.missing
        total.merge(interval)
        rows.append(dict(pc=pc,family=family,depends_on=list(sorted(set(row['dependencies']+([pc-1] if pc else [])))),
                         start_ps=start,end_ps=str(prefix_known) if prefix_complete else None,
                         calendar=interval.record(),native_units=row['native_units'],kv_RPCs=dict(kv),
                         loop=row['loop'],recipes=row['recipes'],source_counts=row['source_counts']))
    need(sum(kv_counts[k] for k in ('kv_commit',))==72,'once-only72fence commits')
    need(kv_counts['kv_consumer_done']==144 and kv_counts['kv_reader_release']==72,'fullSCORES/PV reader lifecycle')
    return dict(schema='QWEN_CANONICAL_NATIVE_SERVICE_CALENDAR_R1',program_sha256=PROGRAM_SHA,
        original_runtime='870c5fe581b768df28dd2998b2d0aecc24510c23',position=position,
        worker_policy='actual original serialPC+retirement, one synchronous delivery sequence; no speculative32SM parallelism',
        period_ps=dict(streaming=str(FAST),serial=str(SERIAL)),setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        startup=startup.record(),operations=rows,total=total.record(),
        native_recipes={k:dict(source_nodes=native['microcode'][k],ABI=native['tile_kernel_ABI'][k]) for k in native['microcode']},
        actual_token_latency_ps=None,single_user_tokens_s=None,physical_qualified=False,
        KV_state_RPC_reads=kv_counts['kv_state_read/1']+kv_counts['kv_state_read/16'],
        KV_state_RPC_writes=sum(v for k,v in kv_counts.items() if k.startswith('kv_state_write/')),
        KV_source_byte_checks_not_coalesced=True,
        conditional_source_calendar_ps=None if total.missing else str(total.priced),
        native_service_demands=dict(native_counts),KV_RPC_demands=dict(kv_counts),
        finite_resources=dict(RF_vectors_per_worker=32,shared_reserved_bytes=17408,
                              synchronous_RPCs=1,KV_writer_slots=1,KV_stage_bytes=1024,
                              W2_clients_per_PC=6,W2_tags_per_PC=16,KV_reader_drains=72),
        W2=dict(same_client_II_measured=19,different_client_II_source=10,
                application='mapped max recurrence, not RTT or added19; Peirce commit owns its528request recurrence',
                commit_floor_already_contains_II=True,endpoint_RTT_route_refresh_CDC_not_measured=True),
        joins=dict(KV_commit=kv_model['schema'],KV_write_PCs=writers,KV_commit_PCs=fences,
            W4='existing ACK_ID1 actual provider plus matched current owner55; unknown fullstep ACK duration cannot be one-edge proxy',
            W6='actual result/consumer/reverse/allcopy retention; PC40 fragment19 is NOT every opcode cost',
            native_consumer='SCORES/PV fulloperator finish and credit_return only, never each primitive',
            drain='actual max eight retained cohort returns; never sum unrelated endpoints or use idle',
            once_only='no historical bandwidth headline added; no oldKVread debit removed; no Peirce528 reimplementation; no grossauthority544 addition'),
        calibration=dict(required_services=sorted(prices.used),
            source_delivery='perPC actual source page/immutable/home traffic excluding native scratch and KV/state',
            native_phases=list(NATIVE_PHASES),unknown_is_zero=False,
            fixed_LOOP_tile_control='actual outer controller phases once perPC, excluding already charged primitive RPC launch; unbound until sourcehandler joins',
            kv_commit='Peirce complete source-bound interval inclusive physical request/capture/reverse. Replace localfloor once; never floor+RTT sum',
            service_total_convention='launch/capture/ACK/retirement and ordered route/CDC stages are separate, no overlapping gross branch sums; calibrate observed intervals only',
            physical_admission='not granted by source minimum, hypothetical positive profile, or complete metadata calendar'))


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--position',type=int,required=True)
    a.add_argument('--kv-model',type=Path,default=BASE/'inputs/kv_commit_model.json')
    a.add_argument('--prices',type=Path)
    a.add_argument('--out',type=Path,required=True)
    a.add_argument('--verify',action='store_true')
    args=a.parse_args()
    native=read(ROOT/PROGRAM);source=(ROOT/SOURCE).read_bytes();kv=read(args.kv_model)
    need(sha(args.kv_model.read_bytes())==KV_MODEL_SHA,'frozen Peirce KV interval input; migration requires explicit source join')
    runtime=ROOT/'results/rtl/w2_fullnc6_functional_20261003/r7_reset_quarantine_pass/runtime.log'
    measured=verify_W2_runtime(runtime.read_bytes(),kv)
    profile=read(args.prices) if args.prices else None
    if profile:
        verified=[]
        for name,want in profile.get('source_pins',{}).items():
            need(sha((ROOT/name).read_bytes())==want,'calibration source pin '+name)
            verified.append(want)
        need(set(profile.get('verified_same_clock_source_sha256',[]))<=set(verified),'same-clock proof must be source-pinned')
    result=compose(native,args.position,kv,profile,raw_source=source)
    result['W2']['verified_actual16_request_accept_edges']=measured
    result['KV_peer_input_origin']=dict(owner='Peirce',commit=KV_OWNER_COMMIT,sha256=KV_MODEL_SHA,
        nested_source_pins_scope='retained historical peer provenance; only top-level source_pins are current replay dependencies')
    paths=[ROOT/PROGRAM,ROOT/SOURCE,args.kv_model,Path(__file__),ROOT/'tools/h4_qwen_released_provider_delivery.py',
           ROOT/'tools/h4_qwen_released_kv_delivery.py',ROOT/'tools/gpu_sys/canonical_qwen_kv_ports.py',
           ROOT/'tools/gpu_sys/canonical_qwen_rf_ports.py',ROOT/'tools/gpu_sys/canonical_qwen_transport.py',
           ROOT/'results/rtl/w2_fullnc6_functional_20261003/r7_reset_quarantine_pass/runtime.log',
           ROOT/'results/uarch/h4_hbm_pc40_physical_ack_r3_20261003/model.json',
           ROOT/'results/uarch/qwen_native_consumer_drain_20261003/model.json']
    if args.prices:paths.append(args.prices)
    result['source_pins']={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p.read_bytes()) for p in paths}
    raw=canonical(result)
    if str(args.out).endswith('.gz'):raw=gzip.compress(raw,mtime=0)
    if args.verify:need(args.out.read_bytes()==raw,'cold calendar equality')
    else:
        need(not args.out.exists(),'preserve previous calendar; select a fresh output')
        args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(raw)
    print(json.dumps(dict(PCs=len(result['operations']),position=args.position,
        actual_token_latency_ps=None,conditional_source_calendar_ps=result['conditional_source_calendar_ps'],
        unresolved_services=len(result['total']['unresolved']),native_calls=sum(result['native_service_demands'].values()),
        KV_RPCs=result['KV_RPC_demands'],known_constraints_floor_ps=result['total']['known_constraints_floor_ps'])))

if __name__=='__main__':main()
