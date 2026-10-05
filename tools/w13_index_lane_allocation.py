"""Lane-aware finite RF allocation of retained executed manifests, no timing credit."""
import hashlib,json,subprocess
from collections import Counter
from pathlib import Path
PATH='results/rtl/deepseek_hbm_complete_20261001/index-exceptional-executed-manifest-r1.json'


def allocate(events):
    issues=[];intervals={};latest={};defined={};maxwarp=0
    for index,e in enumerate(events):
        eid=e['id'];active={(x['warp'],l) for x in e['active_lanes'] for l in x['lanes']}
        ports=Counter();destports=Counter()
        for o in e['operand_register_bindings']:
            warp,lane,source_lane=o['warp'],o['lane'],o['source_lane'];maxwarp=max(maxwarp,warp)
            if (warp,lane) not in active or not 0<=source_lane<32:issues.append('inactive_or_invalid_operand_lane')
            key=(o['register'],warp,source_lane)
            if latest.get(key)!=(o['producer_event'],o['result_id']):issues.append('stale_lane_version:'+eid)
            if o['producer_event'] not in e['dependencies']:issues.append('missing_lane_producer_dependency:'+eid)
            ports[warp,lane]+=1
            symbol=o['register'];span=intervals.setdefault(symbol,[index,index]);span[1]=index
        for r in e['result_register_bindings']:
            warp,lane=r['warp'],r['lane'];maxwarp=max(maxwarp,warp)
            if (warp,lane) not in active:issues.append('masked_write_outside_active_lane')
            key=(r['register'],warp,lane);latest[key]=(eid,r['result_id']);defined[r['result_id']]=(warp,lane,index)
            destports[warp,lane]+=1
            span=intervals.setdefault(r['register'],[index,index]);span[1]=max(span[1],index)
        if any(n>2 for n in ports.values()) or any(n>1 for n in destports.values()):issues.append('lane_2R1W_aperture')
    live={};free=set(range(32));mapping={};peak=0
    for index,e in enumerate(events):
        for symbol in list(live):
            if intervals[symbol][1]<index:free.add(live.pop(symbol))
        needed={o['register'] for o in e['operand_register_bindings']}|{r['register'] for r in e['result_register_bindings']}
        for symbol in sorted(needed):
            if symbol not in live:
                if not free:issues.append('32registers_exceeded');continue
                reg=min(free);free.remove(reg);live[symbol]=reg;mapping[symbol]=reg
        peak=max(peak,len(live))
    # Mapping per symbol is stable for its complete conservative interval;
    # no lane-dependent physical register mux or free phi is introduced.
    out=[]
    for e in events:
        operands=[dict(o,physical_register=mapping.get(o['register']),RF_read_copy=o['operand_index']) for o in e['operand_register_bindings']]
        results=[dict(r,physical_register=mapping.get(r['register']),physical_write_copies=[0,1]) for r in e['result_register_bindings']]
        out.append({'id':e['id'],'opcode':e['opcode'],'active_lanes':e['active_lanes'],'dependencies':e['dependencies'],
            'operand_register_bindings':operands,'result_register_bindings':results,
            'candidate_residency':[{'source_warp':w,'partition':w//8,'warp_slot':w%8} for w in sorted({x['warp'] for x in e['active_lanes']})],
            'RF_read_tick':None,'RF_writeback_tick':None,'shared_service_tick':None})
    if maxwarp>=32:issues.append('32residentwarps_exceeded')
    return {'issues':sorted(set(issues)),'peak_conservative_registers_per_lane':peak,'resident_source_warps':maxwarp+1,
      'symbol_lifetimes_instruction_ordinals':intervals,'symbol_physical_register_candidate':mapping,'events':out,
      'allocation_scope':'executed kernel isolated, ordinal live intervals; no latency/residency/other clients or full64tile proof',
      'physical_timing_admitted':False}


def build():
    b=subprocess.check_output(['git','show','0dac17bf9:'+PATH]);d=json.loads(b)
    groups=d['executed_producer']['executed_ordinary_events']
    for p,sha in d['source_sha256'].items():
        if hashlib.sha256(subprocess.check_output(['git','show',d['source_commit']+':'+p])).hexdigest()!=sha:raise ValueError('source pin mismatch '+p)
    return {'schema':'w13.index-lane-allocation.v1','manifest_pin':{'git':'0dac17bf9','path':PATH,'sha256':hashlib.sha256(b).hexdigest()},
      'verified_source_pins':d['source_sha256'],'kernels':{name:allocate(e) for name,e in groups.items()},
      'real_producer_rows':1,'full64tile_actual_operand_manifest':None,'existing_finite_replay_real_rows':2,
      'no_row_replication_as_actual_full64':True,'checkpoint_reads':0,'all_domain_score_lowering':None,
      'phase_leases':None,'descriptor_publication_physical_ACK':None,'common36client_ACK_CDC_drain':None,
      'unknown_opcode_latencies':None,'SS_FF':None,'hardware_launch':False,'physical_admission':False,'rate_credit':0}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(build(),separators=(',',':'))+'\n')
