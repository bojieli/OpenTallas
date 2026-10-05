"""Bind executed finite/exceptional phase RF, banks and shared producer versions.

Branches are separate scenarios. Oversized source warp shapes do not silently
gain more partitions; wave control and protected ingress remain required.
"""
from collections import Counter
import gzip,hashlib,json,subprocess
from pathlib import Path
from w13_index_resource_calendar import demand,schedule


def phase_resources(phases, finite_count):
    latest={};summaries=[];errors=[];external=Counter();totals=Counter()
    for index,phase in enumerate(phases):
        if index==finite_count:latest={}
        branch='finite' if index<finite_count else 'exceptional'
        events=phase['events'];words={};bank_no_broadcast=0;bank_broadcast_floor=0;broadcast_fanout=0
        mapped_count=0;bindings=0
        for e in events:
            mapped=e.get('source_mapped_shared_accesses')
            if e['opcode'] not in ('LOAD','STORE'):continue
            if mapped is None:continue
            mapped_count+=1
            bywarp={}
            for v in mapped:
                if v['bytes']!=4 or type(v['address']) is not int or v['address']%4 or not 0<=v['address']<65536:
                    errors.append('word_address_outside_contract:'+e['id']);continue
                key=(v['warp'],v['lane'])
                if key in bywarp:errors.append('duplicate_source_lane_address:'+e['id'])
                bywarp[key]=v['address']
            expected={(a['warp'],lane) for a in e['active_lanes'] for lane in a['lanes']}
            if set(bywarp)!=expected:errors.append('source_active_lane_address_coverage:'+e['id'])
            for a in e['active_lanes']:
                if not a['lanes']:continue
                addresses=[bywarp[a['warp'],lane] for lane in a['lanes'] if (a['warp'],lane) in bywarp]
                words[e['id'],a['warp']]=[x//4 for x in addresses]
                bank_no_broadcast+=max(Counter((x//4)%32 for x in addresses).values(),default=0)
                bank_broadcast_floor+=max(Counter((x//4)%32 for x in set(addresses)).values(),default=0)
                broadcast_fanout+=len(addresses)-len(set(addresses))
            declared={(b['consumer_warp'],b['consumer_lane']):b for b in e.get('crossphase_shared_producer_bindings',[])}
            for key,address in bywarp.items():
                if e['opcode']=='STORE':latest[address]=e['id'];continue
                b=declared.get(key)
                if b:
                    # Scale producers first name an RF result; only the actual
                    # mandatory STORE bridge publishes shared memory.
                    producer=b.get('mandatory_scale_STORE_bridge_event',b['producer_event'])
                    if latest.get(address)!=producer:
                        errors.append('shared_producer_version_or_address_mismatch:'+e['id'])
                    bindings+=1
                elif address not in latest:external[branch]+=1
        result=schedule(events,{},words)
        d=demand(events);warps={a['warp'] for e in events for a in e['active_lanes'] if a['lanes']}
        totals[branch,'RF_read_bits']+=sum(d['active_RF_read_bits_by_opcode'].values())
        totals[branch,'RF_write_bits']+=sum(d['active_RF_logical_write_bits_by_opcode'].values())
        totals[branch,'shared_warp_instructions']+=sum(d['shared_warp_instructions_by_opcode'].values())
        summaries.append({'phase':phase['kernel'],'branch_scenario':branch,'source_shape':phase['shape'],
            'source_event_count':len(events),'source_warp_count':len(warps),
            'minimum_contiguous_resident_waves_capacity_only':max(warps,default=-1)//32+1,
            'single_wave_residency_aperture':max(warps,default=-1)<32,
            'demand':d,'shared_events_with_source_word_map':mapped_count,
            'shared_events_total':sum(e['opcode'] in ('LOAD','STORE') for e in events),
            'no_broadcast_shared_bank_service_cycles':bank_no_broadcast,
            'hypothetical_broadcast_bank_floor_cycles':bank_broadcast_floor,
            'broadcast_extra_lane_fanouts_requiring_provider':broadcast_fanout,
            'crossphase_source_STORE_bindings_checked':bindings,
            'source_RF_contract':result['source_RF_contract'],'source_residency_pin':result['source_residency_pin'],
            'source_RF_allocation_summary':result['source_RF_allocation_summary'],
            'calendar_blockers':result['issues'],'candidate_cycles':result['candidate_cycles']})
    return {'phases':summaries,'shared_producer_audit_issues':sorted(set(errors)),
        'unbound_external_first_read_lane_words':dict(external),
        'separate_branch_resource_totals':{branch:{k:totals[branch,k] for k in ('RF_read_bits','RF_write_bits','shared_warp_instructions')} for branch in ('finite','exceptional')},
        'broadcast_provider_qualified':False,'branch_selection_and_phase_lease_calendar':None,
        'whole_program_cycles':None,'hardware_admission':False}


def build(evidence_git='024bf9f8f',version='r2'):
    base='results/rtl/deepseek_hbm_complete_20261001/'
    proofraw=subprocess.check_output(['git','show',evidence_git+':'+base+'index-source-service-plan-proof-'+version+'.json']);proof=json.loads(proofraw)
    artifact='index-source-service-phases-'+version+'.json.gz'
    raw=subprocess.check_output(['git','show',evidence_git+':'+base+artifact])
    assert hashlib.sha256(raw).hexdigest()==proof['artifacts'][artifact]['sha256']
    for p,sha in proof['source_pins'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',proof['source_commit']+':'+p])).hexdigest()==sha
    d=json.loads(gzip.decompress(raw));out=phase_resources(d['phases'],d['finite_phase_count'])
    wavepath=base+'index-source-queryguard-waves-r1.json'
    waveraw=subprocess.check_output(['git','show','879e75887:'+wavepath]);waves=json.loads(waveraw)
    for p,sha in waves['source_pins'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',waves['source_commit']+':'+p])).hexdigest()==sha
    assert [w['wave_base_global_warp'] for w in waves['waves']]==[0,32,64,96]
    assert [g for w in waves['waves'] for g in w['global_warps']]==list(range(128))
    out['query_guard_wave_contract']={'git':'879e75887','path':wavepath,'sha256':hashlib.sha256(waveraw).hexdigest(),
        'verified_source_pins':waves['source_pins'],'ordinary_address_warp_ops':waves['address_warp_ops_allwaves'],
        'waves':waves['waves'],'physical_opcode_II_RF_import_launch_barrier_cycles':None,
        'control_ops_are_additional_to_executed_phase_demand':True}
    out.update(schema='w13.index-allphase-source-resource-join.v2',source_git=proof['source_commit'],evidence_git=evidence_git,
        verified_source_pins=proof['source_pins'],phase_manifest_sha256=hashlib.sha256(raw).hexdigest(),
        source_fixture=d['fixture'],source_event_count=sum(len(p['events']) for p in d['phases']),
        historical_442us_budget_verdict='FAIL_CURRENT_LOWERING_BUDGET',checkpoint_reads=0,
        preserved_historical_fixture={'evidence_git':'a4d69239c','receipt':'allphase_resource_join_r1.json','scope':'all-ones RF/event counts not transferable to diverse r2'})
    return out


if __name__=='__main__':
    import sys
    Path(sys.argv[1]).write_text(json.dumps(build(),separators=(',',':'))+'\n')
