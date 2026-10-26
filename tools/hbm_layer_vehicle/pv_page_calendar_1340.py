"""Fixed PV page lifetime at source-client edges; no DUT-dependent waits.

This compiler consumes real runtime input commands and real KV consumer ops.
CP launch/counter alignment and physical bank grants remain explicit binding
obligations; this alone does not qualify the connected programme.
"""
from pathlib import Path
import hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_sm_attention'))
import sm_elem_bench as E
from hbm_layer_vehicle.pv_probability_rows_1340 import ROW_INTERVAL, COMMAND_TO_WRITE

PSTORE_SHA256 = 'c0d9c8ed8c900a5e696f91536469d944937ff2b334acbd2e2223b6d132f3fccd'


def exact_edge(v, name):
    if type(v) is not int or v < 0:
        raise ValueError(f'{name} must be a nonnegative integer source edge')
    return v


def page_calendar(*, page, record, consumer_ops, latencies, input_anchor,
                  copy_ready_edge, pstore_source_path, result_tail_edges=None, downstream_acceptance_edge=None, clear_edge=0):
    """One page: clear -> real runtime writes -> actual KV/PV reads -> retire.

    consumer_ops contains unchanged existing complete SM ops, not sliced partial
    trees. All their global row IDs must belong to this page. No P values are
    read: the existing KV compiler is invoked with an explicit runtime mapping.
    Input anchor is the actual xload command-counter zero in this SM source
    epoch; callers must bind CP counter phase and copy completion, not infer it.
    """
    if hashlib.sha256(Path(pstore_source_path).read_bytes()).hexdigest()!=PSTORE_SHA256:
        raise ValueError('matching selected pstore source required')
    if result_tail_edges is None:
        raise ValueError('explicit result-tail source profile required; exp.end alone is not retirement')
    tail=exact_edge(result_tail_edges,'result_tail_edges')
    if tail<2:
        raise ValueError('historical actual last result is exp.end+2; shorter retirement is unsupported')
    anchor=exact_edge(input_anchor,'input_anchor')
    ready=exact_edge(copy_ready_edge,'copy_ready_edge')
    clear=exact_edge(clear_edge,'clear_edge')
    if page.get('tested_command_interval')!=ROW_INTERVAL:
        raise ValueError('tested256-edge runtime producer spacing required')
    footprints=page['footprints']
    first=exact_edge(page['first_global_probability'],'first_global_probability')
    if any(type(f['row']) is not int or not 0<=f['row']<128 for f in footprints):
        raise ValueError('page-local row must fit actual7-bit pstore address')
    mapping={first+f['row']:f['row'] for f in footprints}
    if not footprints or len(mapping)!=len(footprints) or len(set(mapping.values()))!=len(footprints) or len(footprints)>128:
        raise ValueError('one distinct real128-row page required')
    writes=[]
    for f in footprints:
        cmd=anchor+exact_edge(f['command_slot'],'command_slot')
        write=cmd+COMMAND_TO_WRITE
        if cmd<=ready or clear>=write-1:
            raise ValueError('fixed copy completion/clear must precede producer command/write')
        writes.append(dict(row=f['row'],logical_word=f['logical_word'],command_edge=cmd,write_edge=write))
    if any(b['command_edge']-a['command_edge']!=ROW_INTERVAL for a,b in zip(writes,writes[1:])):
        raise ValueError('runtime producer commands must retain tested spacing')
    next_edge=max(w['write_edge'] for w in writes)+3
    consumers=[]
    for sm,op in consumer_ops:
        if op[1]!='pv' or not set(op[3]).issubset(mapping):
            raise ValueError('complete consumer op must fit current probability page; no silent subtree split')
        addresses={r:mapping[r] for r in op[3]}
        offset=next_edge-8
        cal,exp=E.compile_op(record,op,latencies,True,t0=8,runtime_probability_rows=addresses)
        if cal.xw:raise ValueError('runtime consumer must contain no probability preload')
        reads=[dict(edge=offset+c,row=f['paddr']) for c,f in enumerate(cal.cyc) if f.get('pread')]
        byrow={w['row']:w['write_edge'] for w in writes}
        if any(r['edge']<=byrow[r['row']] for r in reads):
            raise ValueError('consumer reads before real runtime write commit')
        consumers.append(dict(sm=sm,op=op,command_words=[E.cmd_word(**f) for f in cal.cyc],
            command_counter_zero_edge=offset,kv_descriptors=cal.kvd,kv_packets=cal.pkt,preads=reads,model_end_edge=offset+exp['end'],result_tail_edges=tail,retire_edge=offset+exp['end']+tail,
            first_line=offset+exp['first_line'],last_consume=offset+exp['last_consume']))
        next_edge=offset+exp['end']+tail+1
    if not consumers:raise ValueError('actual complete KV/PV consumer ops required')
    last_read=max(r['edge'] for c in consumers for r in c['preads'])
    arithmetic_bound=max(c['retire_edge'] for c in consumers)
    acceptance=None if downstream_acceptance_edge is None else exact_edge(downstream_acceptance_edge,'downstream_acceptance_edge')
    if acceptance is not None and acceptance<arithmetic_bound:
        raise ValueError('downstream acceptance bound precedes arithmetic output bound')
    reuse=None if acceptance is None else max(last_read+3,arithmetic_bound,acceptance)+2
    return dict(status='SOURCE_FIXED_LIFETIME_CP_BANK_AND_CONNECTED_PROOF_OPEN',hardware_executed=False,
        source_sha256=PSTORE_SHA256,page=page['page'],clear_edge=clear,
        clear_command=dict(mode=6,pclear=1),writes=writes,consumers=consumers,
        last_probability_read_edge=last_read,arithmetic_output_candidate_bound=arithmetic_bound,
        downstream_output_acceptance_bound=acceptance,next_page_clear_not_before=reuse,
        page_reuse_qualified=False,fixed_component_observation_not_before=arithmetic_bound+16,
        fixed_source_epoch_edges=arithmetic_bound+16-clear,
        probability_preloads=0,producer_join_qualified=False,
        binding_obligations=['exact CP input/SM counter anchors','real covering-copy completion at copy_ready_edge',
            'source-qualified selected SM/XQL group mapping','actual fixed bank owner calendar and real KV service',
            'downstream result acceptance/VM-write source bound is separate; no next-page clear emitted until supplied',
            'execute producer/copy/loader/consumer with values and all actual fault faces checked'])
