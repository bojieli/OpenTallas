"""Source-executed lane resource calendar; supplied model contracts, never STA.

Unknown opcode II/latency or shared addresses stop scheduling. Immediates do
not consume RF ports. Shared repeated addresses get no free multicast credit.
Each warp preserves executed order through retirement, including branches.
"""
from collections import Counter, defaultdict
import ast
from functools import lru_cache
import gzip
import hashlib
import json
import subprocess
from pathlib import Path
from w13_index_ssa_allocation import color
from w13_index_lane_allocation import allocate


@lru_cache(maxsize=1)
def _pinned_RF_source():
    path='tools/w19_gpu_simd_contract.py';rev='922a6b673'
    return subprocess.check_output(['git','show',rev+':'+path])


def pinned_RF_contract():
    # Cache immutable committed bytes, never a caller-mutable authority dict.
    path='tools/w19_gpu_simd_contract.py';rev='922a6b673';raw=_pinned_RF_source()
    tree=ast.parse(raw)
    nodes=[n.value for n in ast.walk(tree) if isinstance(n,ast.keyword) and n.arg=='register_file']
    if len(nodes)!=1 or not isinstance(nodes[0],ast.Call):raise ValueError('ambiguous RF source contract')
    values={k.arg:ast.literal_eval(k.value) for k in nodes[0].keywords}
    assert (values['read_ports_bank'],values['write_ports_bank'],values['word_bits'],values['banks'])==(2,1,32,128)
    assert values['read_latency_candidate']==2
    values['source_pin']={'git':rev,'path':path,'sha256':hashlib.sha256(raw).hexdigest()}
    return values


def demand(events):
    ops=Counter();reads=Counter();writes=Counter();shared=Counter()
    for e in events:
        warps={a['warp'] for a in e['active_lanes'] if a['lanes']}
        ops[e['opcode']]+=len(warps)
        reads[e['opcode']]+=len(e['operand_register_bindings'])*32
        writes[e['opcode']]+=len(e['result_register_bindings'])*32
        if e['opcode'] in ('LOAD','STORE'):shared[e['opcode']]+=len(warps)
    return {'executed_warp_issues_by_opcode':dict(ops),
            'active_RF_read_bits_by_opcode':dict(reads),
            'active_RF_logical_write_bits_by_opcode':dict(writes),
            'active_RF_physical_two_copy_write_bits':2*sum(writes.values()),
            'shared_warp_instructions_by_opcode':dict(shared),
            'immediates_are_not_RF_reads':True}


def schedule(events, opcode_contract, memory_words, rf_contract='pinned', residency='allocator'):
    """One SM, source allocator residency, exact versions; conservative schedule.

    Contract entries require core latency (excluding two-cycle RF import) and
    initiation interval. memory_words[(event_id,warp)] lists actual service
    word addresses, one per active lane: no broadcast/coalescing assumption.
    """
    allocation=color(events);errors=list(allocation['issues']);portledger=[]
    allocation_summary={k:allocation[k] for k in ('allocated_version_registers','reserved_address_loop_registers','total_per_lane_registers')}
    placement={}
    for e in allocate(events)['events']:
        for r in e['candidate_residency']:
            placement[r['source_warp']]={'partition':r['partition'],'warp_slot':r['warp_slot']}
    residency_pin={'git':'bea9714b1','path':'tools/w13_index_lane_allocation.py'}
    pinned_source=subprocess.check_output(['git','show',residency_pin['git']+':'+residency_pin['path']])
    residency_pin['sha256']=hashlib.sha256(pinned_source).hexdigest()
    if hashlib.sha256(Path(__file__).with_name('w13_index_lane_allocation.py').read_bytes()).hexdigest()!=residency_pin['sha256']:
        errors.append('allocator_residency_source_drift')
    if residency!='allocator' and residency!=placement:
        errors.append('residency_layout_unknown_or_not_allocator_bound')
    pinned=pinned_RF_contract()
    rf=pinned if rf_contract=='pinned' else rf_contract
    if not isinstance(rf,dict) or rf!=pinned:
        errors.append('RF_port_or_import_contract_unknown_or_not_source_bound')
        rf=None
    for e in events:
        reads=Counter((o['warp'],o['lane']) for o in e['operand_register_bindings'])
        writes=Counter((o['warp'],o['lane']) for o in e['result_register_bindings'])
        maxreads=max(reads.values(),default=0);maxwrites=max(writes.values(),default=0)
        portledger.append({'source_event':e['id'],'max_register_reads_per_active_lane':maxreads,
                           'max_result_words_per_active_lane':maxwrites})
        # Independent calendar-entry guard: allocator changes cannot silently
        # remove the strict source-defined opcode 2R1W aperture.
        if rf and (maxreads>rf['read_ports_bank'] or maxwrites>rf['write_ports_bank']):
            errors.append('calendar_lane_2R1W_aperture:'+e['id'])
        c=opcode_contract.get(e['opcode'],{})
        if any(type(c.get(k)) is not int or c[k]<1 for k in ('core_latency','II')):
            errors.append('opcode_contract_missing:'+e['opcode'])
        for a in e['active_lanes']:
            if not a['lanes']:continue
            if not 0<=a['warp']<32:errors.append('resident_warp_limit')
            if e['opcode'] in ('LOAD','STORE'):
                words=memory_words.get((e['id'],a['warp']))
                if not isinstance(words,list) or len(words)!=len(a['lanes']):
                    errors.append('shared_address_binding_missing:'+e['id']);continue
                if any(type(w) is not int or not 0<=w<16384 for w in words):
                    errors.append('shared_address_outside_64KiB:'+e['id'])
    if errors:return {'issues':sorted(set(errors)),'calendar':None,'candidate_cycles':None,'demand':demand(events),
                      'source_RF_contract':rf,'source_lane_port_ledger':portledger,
                      'source_RF_allocation_summary':allocation_summary,
                      'source_residency':placement,'source_residency_pin':residency_pin}
    warp_ready=defaultdict(int);partition_ready=defaultdict(int)
    results={};rfwrites=set();rfreads=set();shared_ready=0;calendar=[]
    for e in events:
        c=opcode_contract[e['opcode']]
        for a in e['active_lanes']:
            warp=a['warp'];lanes=a['lanes']
            if not lanes:continue
            part=placement[warp]['partition']
            operands=[o for o in e['operand_register_bindings'] if o['warp']==warp]
            dests=[r for r in e['result_register_bindings'] if r['warp']==warp]
            # Producer visibility is per lane/result identity, including SHFL.
            ready=max([warp_ready[warp],partition_ready[part]]+
                      [results[o['result_id']] for o in operands])
            import_cycles=rf['read_latency_candidate'] if operands else 0
            words=memory_words.get((e['id'],warp),[])
            bankcounts=Counter(w%32 for w in words)
            bankcycles=max(bankcounts.values(),default=0)
            start=ready
            while True:
                issue=start+import_cycles
                service=max(issue,shared_ready) if words else None
                finish=(service+bankcycles+c['core_latency']) if words else issue+c['core_latency']
                if (operands and any((part,t) in rfreads for t in range(start,issue))) or (dests and (part,finish) in rfwrites):
                    start+=1;continue
                break
            if operands:
                for t in range(start,issue):rfreads.add((part,t))
            if dests:rfwrites.add((part,finish))
            for r in dests:results[r['result_id']]=finish
            warp_ready[warp]=finish
            partition_ready[part]=issue+c['II']
            # Serialize until visibility; never let a later shared read observe
            # a STORE merely accepted for bank service but not retired.
            if words:shared_ready=finish
            calendar.append({'source_event':e['id'],'opcode':e['opcode'],'warp':warp,'partition':part,
                'warp_slot':placement[warp]['warp_slot'],
                'active_lanes':lanes,'RF_read_cycle':start if operands else None,'issue_cycle':issue,
                'writeback_or_retirement_cycle':finish,'RF_read_bits':32*len(operands),
                'RF_logical_write_bits':32*len(dests),'RF_physical_write_copies':2 if dests else 0,
                'shared_service_first_cycle':service,'shared_bank_service_cycles':bankcycles,
                'shared_word_addresses':words,'source_operand_result_ids':[o['result_id'] for o in operands],
                'result_ids':[r['result_id'] for r in dests]})
    return {'issues':[],'calendar':calendar,'candidate_cycles':max(warp_ready.values(),default=0),
            'source_RF_contract':rf,'source_lane_port_ledger':portledger,
            'source_RF_allocation_summary':allocation_summary,
            'source_residency':placement,'source_residency_pin':residency_pin,
            'demand':demand(events),'scope':'conservative selected executed branch path only; source order per warp through retirement',
            'model_contract_only':True,'physical_admission':False}


def build():
    path='results/rtl/deepseek_hbm_complete_20261001/index-finite-fused-executed-ssa-r1.json.gz'
    raw=subprocess.check_output(['git','show','7c091e32d:'+path]);d=json.loads(gzip.decompress(raw))
    for p,sha in d['source_pins'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',d['source_commit']+':'+p])).hexdigest()==sha
    events=d['events'];result=schedule(events,{}, {})
    result.update(schema='w13.source-lane-resource-calendar.v1',
        source_manifest={'git':'7c091e32d','path':path,'sha256':hashlib.sha256(raw).hexdigest()},
        verified_source_pins=d['source_pins'],source_fixture=d['fixture'],
        required_phases=['query producer/version publication','cache authority validation','query guard/decoder',
            'key producer/descriptor WRvisible ACK/read lease','key guard/decoder','finite shader',
            'exceptional continuation','ABI/gather/result publication','consumer retirement/credit/epoch drain'],
        full_phase_calendars=None,provider_ACK_CDC_calendar=None,clock_qualification=None,
        hardware_launch=False,whole_token_cycles=None,historical_442us_budget_verdict='FAIL_CURRENT_LOWERING_BUDGET',
        software_authority_scan_bytes_per_finite_invocation=33280,
        software_authority_source='cb6959c24',checkpoint_reads=0)
    return result


if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(build(),separators=(',',':'))+'\n')
