"""Executed lane SSA interference coloring; preserves uniform operand registers."""
from collections import defaultdict
import gzip,hashlib,json,subprocess
from pathlib import Path
from w13_index_lane_allocation import allocate
PATH='results/rtl/deepseek_hbm_complete_20261001/index-blas-production-candidate-r1.json.gz'


def color(events,reserved=8):
    errors=[e for e in allocate(events)['issues'] if e!='32registers_exceeded']
    defs={};parent={};intervals={};uses=[]
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    for i,e in enumerate(events):
        for r in e['result_register_bindings']:
            group=(e['id'],r['register']);find(group)
            defs[r['result_id']]=(group,r['warp'],r['lane'],2*i+1)
            intervals[r['result_id']]=[2*i+1,2*i+1]
    for i,e in enumerate(events):
        operands=defaultdict(list)
        for o in e['operand_register_bindings']:
            definition=defs.get(o['result_id'])
            if definition is None:errors.append('unbound_phase_input_version');continue
            group,warp,lane,start=definition
            if warp!=o['warp'] or lane!=o['source_lane']:errors.append('source_lane_definition_mismatch')
            intervals[o['result_id']][1]=max(intervals[o['result_id']][1],2*i)
            operands[o['operand_index']].append(group);uses.append((i,o['result_id']))
        # One opcode operand register index for all owning lanes/warps, including
        # phi-like reaching versions. No lane-dependent free selector.
        for groups in operands.values():
            for group in groups[1:]:union(groups[0],group)
    roots={find(g) for g in parent};edges={g:set() for g in roots};lane_intervals=defaultdict(list)
    for result,(group,warp,lane,start) in defs.items():lane_intervals[warp,lane].append((intervals[result][0],intervals[result][1],find(group),result))
    for spans in lane_intervals.values():
        spans.sort();active=[]
        for start,end,group,result in spans:
            active=[x for x in active if x[0]>=start]
            for stop,other,old in active:
                if other!=group:edges[group].add(other);edges[other].add(group)
                elif old!=result:errors.append('uniform_register_union_overlapping_versions')
            active.append((end,group,result))
    assigned={};limit=32-reserved
    for g in sorted(roots,key=lambda x:(-len(edges[x]),x)):
        forbidden={assigned[n] for n in edges[g] if n in assigned};available=set(range(limit))-forbidden
        if not available:errors.append('SSA_coloring_exceeds_register_budget');continue
        assigned[g]=min(available)
    out=[]
    for e in events:
        operands=[dict(o,physical_register=assigned.get(find(defs[o['result_id']][0]))) for o in e['operand_register_bindings'] if o['result_id'] in defs]
        results=[dict(r,physical_register=assigned.get(find(defs[r['result_id']][0])),write_copies=[0,1]) for r in e['result_register_bindings']]
        out.append({'id':e['id'],'opcode':e['opcode'],'operand_register_bindings':operands,'result_register_bindings':results,'active_lanes':e['active_lanes'],'RF_read_tick':None,'RF_writeback_tick':None})
    occupied=max(assigned.values(),default=-1)+1
    return {'issues':sorted(set(errors)),'allocated_version_registers':occupied,'reserved_address_loop_registers':reserved,
      'total_per_lane_registers':occupied+reserved,'events':out,'source_result_live_intervals':intervals,
      'allocation_group_colors':[{'group':list(g),'register':r,'interferes_with':[list(x) for x in sorted(edges[g])]} for g,r in sorted(assigned.items())],
      'uniform_operand_register_constraints':'all active lanes use same physical operand register; no free phi/mux',
      'scope':'selected executed trace only; ordinal liveness not actual latency or full64tile schedule','actual_timing':None,'physical_admission':False}


def build():
    b=subprocess.check_output(['git','show','efdfcb483:'+PATH]);d=json.loads(gzip.decompress(b))
    for p,sha in d['source_sha256'].items():
        if hashlib.sha256(subprocess.check_output(['git','show',d['source_commit']+':'+p])).hexdigest()!=sha:raise ValueError('source pin')
    a=color(d['selected_first_key_block_executed_virtual_SSA'],d['RF_address_loop_regs'])
    return {'schema':'w13.index-selected-lane-SSA-allocation.v1','source_pin':{'git':'efdfcb483','path':PATH,'sha256':hashlib.sha256(b).hexdigest()},
      'verified_source_sha256':d['source_sha256'],'allocation':a,'whole64_SSA_expanded':False,
      'full_score_other_phases_and_liveout_leases':None,'new_sanitize_exception_buffers_addresses':None,
      'whole64_shared_metrics':d['executed_whole64_metrics'],'old63488fit_admitted':False,
      'actual_production_provider_ACK_CDC':None,'SS_FF':None,'checkpoint_reads':0,'physical_admission':False,'hardware_launch':False,'rate_credit':0}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(build(),separators=(',',':'))+'\n')
