#!/usr/bin/env python3
"""Source-bound selected RMW/shared design and causal cache admission refusal.
Opaque bit movement only. No numerical oracle, engine RTL or physical timing.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_selected_cache_rmw_20261002'
PIN='cf8549d90285c47724396cfc9f18a8eecee5d6d67d220fe3d3629589c76fd3d5'
COMMAND_PIN='abfb89202dec727b3e11b885790093d59a178225191866ee756358345627b5e9'

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def inputs():
    b=(BASE/'input_manifest.json').read_bytes()
    if sha(b)!=PIN:raise ValueError('exact manifest pin')
    out={}
    for r in json.loads(b)['inputs']:
        p=(BASE/r['archive']).resolve()
        if not p.is_relative_to(BASE.resolve()):raise ValueError('archive origin')
        b=p.read_bytes()
        if sha(b)!=r['sha256'] or len(b)!=r['bytes']:raise ValueError('exact source pin')
        out[p.name]=json.loads(gzip.decompress(b)) if p.name.endswith('.json.gz') else json.loads(b) if p.name.endswith('.json') else b.decode()
    return out

def compile_selected(s=None):
    s=inputs() if s is None else s;calendar=s['H1_PC0.json.gz'];lookup={(p['die'],p['SM'],p['sequence']):p for p in calendar['packets']};rmw=[]
    for p in calendar['packets']:
        if p['role']!='partial_vector_RMW_read':continue
        a=lookup[p['die'],p['SM'],p['sequence']+1];b=lookup[p['die'],p['SM'],p['sequence']+2]
        keys=('source_owner','parent_publication_owner','provider_reference','version','RF_slot','physical_mirror_byte_addresses','active_words')
        if a['role']!='both_mirror_write' or b['role']!='actual_publication_readback' or any(p[k]!=a[k] or p[k]!=b[k] for k in keys):raise ValueError('exact RMW read/write/readback owner span')
        if not 0<p['active_words']<128 or p['physical_mirror_byte_addresses'][1]-p['physical_mirror_byte_addresses'][0]!=262144:raise ValueError('partial vector/mirror extent')
        rmw.append(dict(id=f"PC0.d{p['die']}.s{p['SM']}.q{p['sequence']}",kind='RF_partial_RMW',PC=0,die=p['die'],SM=p['SM'],
            generation=p['generation'],owner=p['source_owner'],outer_owner=p['parent_publication_owner'],provider_reference=p['provider_reference'],
            version=p['version'],RF_slot=p['RF_slot'],mirror_byte_addresses=p['physical_mirror_byte_addresses'],active_words=p['active_words'],
            vector_bytes=512,pair_response_bytes=1024,write_both_copy_bytes=1024,version_retire_PC=p['source_version_lease_retire_PC'],
            child_sequence=[p['sequence'],a['sequence'],b['sequence']],
            source_local_edges=8,proposed_merge_register_edges=1,conditional_local_reference_edges=9,
            merge_semantics='prefix active_words opaque U32 lanes replace; retain all other captured copy0 bytes, including exceptional FP bit patterns',
            parent_owner_hold='read ACK, merge, two-copy write ACK, readback, consumer, reverse; local idle never releases parent'))
    if len(rmw)!=288:raise ValueError('complete actual PC0 partial RMW inventory')
    x=s['shared_execution.json.gz'];calls=x['control_movement_calls'];journals={j['journal_id']:j['events']for j in x['control_disk_journal_events']}
    bindings=s['shared64.json.gz'];commands=bindings['calls']['10:0:0']['commands'];shared=[]
    if len(commands)!=len(calls)*8 or len(commands)!=9216:raise ValueError('complete directed source shared64 count')
    for i,call in enumerate(calls):
        owner=call['owner'];binding=call['binding'];events=journals[call['journal_id']][call['journal_start']:call['journal_end']]
        requests=[e for e in events if e['event']=='request_accept']
        if len(requests)!=16 or [e['identity']['sector'] for e in requests]!=[(binding['logical_base']+32*k)//32 for k in range(16)]:raise ValueError('actual ordered sector32 source spans')
        if binding['logical_base']!=16777216+owner['SM']*65536+binding['shared_tile_offset']:raise ValueError('actual shared address translation')
        for beat,c in enumerate(commands[i*8:i*8+8]):
            address=binding['shared_tile_offset']+beat*64
            if (c['die'],c['SM'],c['generation'],c['lease'],c['scratch_byte_address'])!=(owner['rank'],owner['SM'],owner['generation'],binding['lease'],address):raise ValueError('shared64 exact owner/lease/address')
            if address%64 or not 0<=address<=65536-64 or c['source_operand']['typed_bytes']!=64:raise ValueError('finite aligned source shared64 extent')
            if c['actual_journal_span']!=[call['journal_id'],call['journal_start'],call['journal_end']]:raise ValueError('source child journal identity')
            kind='shared_write64' if call['source_reference']['operand']=='dst' else 'shared_read64'
            if c['kind']!=kind:raise ValueError('source shared read/write kind')
            edges=s['H1_edges.json']['service_edges']['shared_write' if kind=='shared_write64' else 'shared_read']
            # Reject the old explicit1/1/1 as physical bounds; preserve its ledger identity only.
            shared.append(dict(id=f'PC10.directed.c{i}.beat{beat}',kind=kind,PC=10,die=c['die'],SM=c['SM'],generation=c['generation'],
                outer_owner=owner,lease=c['lease'],provider_reference=c['provider_reference'],physical_byte_address=16777216+c['SM']*65536+address,
                source_tile_lease=c['lease'],scratch_byte_address=address,scratch_row=address//64,macro_banks=[0,1],SRAM_bytes_each=32,payload_bytes=64,
                source_operand=c['source_operand'],actual_journal_span=c['actual_journal_span'],
                sector_children=[e['identity'] for e in requests[beat*2:beat*2+2]],existing_interval_id=c['existing_interval_id'],
                local_reference_edges=edges,backend_physical_bound=None,outer_consumer_bound=None,outer_reverse_bound=None))
    return dict(schema='HBM_SELECTED_RMW_SHARED_SERVICE_COMMANDS_V1',RMW=rmw,shared64=shared,
        scope='actual96 PC0 partial RF publications plus retained directed PC10 rank0 shared software spans',
        shared_production_calls_closed=0,whole_operator=False,whole_token_latency_ns=None,hardware_admitted=False)

class SelectedEndpoint:
    """Bounded software endpoint design over ONLY emitted source commands.

    One parent service owner per (die,SM), preserved across children. The parent
    provider must supply a live lease receipt before issue. Local ACK, child
    reverse and parent consumer/reverse are deliberately distinct.
    No fairness or installed physical ownership is implemented or credited.
    """
    def __init__(self,commands):
        if sha(canonical(commands))!=COMMAND_PIN:raise ValueError('exact selected command source pin')
        commands=json.loads(canonical(commands))
        self.commands={x['id']:x for x in commands['RMW']+commands['shared64']};self.live={};self.completed=set()
        self.groups={}
        for c in self.commands.values():
            g=self.group(c);self.groups.setdefault(g,[]).append(c['id'])
    @staticmethod
    def group(c):
        return c['id'] if c['kind']=='RF_partial_RMW' else (c['PC'],c['die'],c['SM'],c['generation'],c['outer_owner']['tile'])
    def acquire(self,command_id,*,lease,owner_receipt):
        c=self.commands[command_id];key=(c['die'],c['SM'])
        expected=dict(generation=c['generation'],die=c['die'],SM=c['SM'],provider_reference=c['provider_reference'],lease=lease,live=True,outer_owner=c['outer_owner'])
        if type(lease)is not int or not 0<lease<2**64 or owner_receipt!=expected:raise ValueError('explicit matching live parent lease receipt')
        if command_id in self.completed:raise ValueError('parent credit retained or replay')
        group=self.group(c)
        if key in self.live:
            x=self.live[key]
            if x['phase']!='NEXT_CHILD' or x['group']!=group or x['lease']!=lease or x['remaining'][0]!=command_id:raise ValueError('parent credit retained or ordered child mismatch')
            x.update(command=c,phase='SHARED_ISSUE');return
        if self.groups[group][0]!=command_id:raise ValueError('outer owner first child required')
        self.live[key]=dict(command=c,lease=lease,group=group,remaining=list(self.groups[group]),phase='READ_ISSUE' if c['kind']=='RF_partial_RMW' else 'SHARED_ISSUE',old=None,merged=None,child=None)
    def event(self,command_id,*,lease,event,payload=None,copy0=False,copy1=False):
        c=self.commands[command_id];key=(c['die'],c['SM']);x=self.live.get(key)
        if x is None or x['command']['id']!=command_id or x['lease']!=lease:raise ValueError('stale child/parent lease')
        phase=x['phase'];result=None
        if event=='read_child_accept' and phase=='READ_ISSUE':x.update(phase='READ_ACK',child='RF_read_pair')
        elif event=='read_ACK_consume' and phase=='READ_ACK':
            if type(payload)is not bytes or len(payload)!=1024:raise ValueError('actual paired RF read ACK payload')
            if payload[:512]!=payload[512:]:raise ValueError('full-vector merge requires identical old mirror tails; initialization/ownership proof missing')
            x.update(old=payload[:512],phase='READ_REVERSE')
        elif event=='read_child_reverse' and phase=='READ_REVERSE':x.update(phase='MERGE',child=None)
        elif event=='merge_register' and phase=='MERGE':
            n=c['active_words']*4
            if type(payload)is not bytes or len(payload)!=n:raise ValueError('exact source active opaque U32 words')
            result=payload+x['old'][n:];x.update(old=None,merged=result,phase='WRITE_ISSUE')
        elif event=='write_child_accept' and phase=='WRITE_ISSUE':x.update(phase='WRITE_ACK',child='RF_write_both')
        elif event=='write_ACK_consume' and phase=='WRITE_ACK':
            if copy0 is not True or copy1 is not True:raise ValueError('both physical copy write observations with common ACK')
            x['phase']='WRITE_REVERSE'
        elif event=='write_child_reverse' and phase=='WRITE_REVERSE':x.update(phase='READBACK_ISSUE',child=None)
        elif event=='readback_child_accept' and phase=='READBACK_ISSUE':x.update(phase='READBACK_ACK',child='RF_readback_pair')
        elif event=='readback_ACK_consume' and phase=='READBACK_ACK':
            if type(payload)is not bytes or payload!=x['merged']*2:raise ValueError('actual both-copy publication readback bits')
            x['phase']='READBACK_REVERSE'
        elif event=='readback_child_reverse' and phase=='READBACK_REVERSE':x.update(phase='CONSUMER',child=None)
        elif event=='shared_child_accept' and phase=='SHARED_ISSUE':
            if c['kind']=='shared_write64':
                if type(payload)is not bytes or len(payload)!=64:raise ValueError('exact64B shared write data')
                result=payload
            x.update(phase='SHARED_ACK',child='shared64')
        elif event=='shared_ACK_consume' and phase=='SHARED_ACK':
            if c['kind']=='shared_read64' and (type(payload)is not bytes or len(payload)!=64):raise ValueError('actual64B read capture')
            if c['kind']=='shared_read64':result=payload
            x['phase']='SHARED_REVERSE'
        elif event=='shared_child_reverse' and phase=='SHARED_REVERSE':
            x['remaining'].pop(0);x.update(phase='NEXT_CHILD' if x['remaining'] else 'CONSUMER',child=None)
        elif event=='parent_consumer_accept' and phase=='CONSUMER':x['phase']='PARENT_REVERSE'
        elif event=='parent_reverse_lease_grant' and phase=='PARENT_REVERSE':
            if x['child']is not None:raise ValueError('child obligation retained')
            del self.live[key];self.completed.update(self.groups[x['group']])
        else:raise ValueError('out-of-order child/readACK/consumer/reverse handshake')
        return result
    def cache_accept(self,*args,**kw):
        raise ValueError('FAIL_CACHE_SOURCE_BINDING: no emitted generic-cache request/home/owner directory; no atomic bank grant')


def build(commands,s):
    # Reuse existing V1 analytical area assumptions, not measured standard-cell PPA.
    if 'gate_area_range=[.1,.3];dff=.2916;util=.5' not in s['V1_model.py']:raise ValueError('source area assumption pin')
    bits=4096+7+9+4+10+8 #opaque vector, prefix, RFslot, FSM, shared row and child counter
    gates=4096*3+128*7*4+128*2 #mux decomposition, prefix comparators, mask fanout
    footprint=[(bits*.2916+gates*a)/.5 for a in (.1,.3)]
    parent=s['parent.json.gz'];counts=Counter(c['kind']for c in commands['shared64'])
    if 'input wire [31:0] rf_owner_grant,shared_owner_grant' not in s['context.sv']:raise ValueError('actual source ownership gate')
    return dict(schema='HBM_SELECTED_CACHE_RMW_SERVICE_DESIGN_V1',status='FAIL_COMPOSED_SOURCE_ADMISSION',
        source_context_owner_ports=['rf_owner_grant[31:0]','shared_owner_grant[31:0]'],
        local_service_design_scope='source-bound opaque endpoint and child/parent state design; actual outer ownership gate implementation unbound',
        integer_or_FP_MACs_per_cycle=0,arithmetic_rounding_points_added=0,
        actual_generic_cache_ingress_connected=False,actual_generic_cache_command_inventory=None,actual_cache_contender_upper=None,
        cache_refusal='emitted H1/PC0 and directed shared commands do not contain cache clients; SM context exports RF/shared ownership grants but no connected generic cache bank-credit source',
        RMW=dict(commands=288,per_SM_credit=1,opaque_vector_storage_bits=4096,total_incremental_state_bits=bits,
            register_area_um2_per_bit_ASSUMED=.2916,gate_area_um2_range_ASSUMED=[.1,.3],placement_utilization_ASSUMED=.5,
            gate_equivalents=gates,incremental_footprint_um2_per_SM_range=footprint,replicas_per_die=32,
            proposed_merge_edges=1,SS_FF_merge_verified=False,source_RF_local_edges_per_command=8,
            local_reference_edge_delta=288,old_RF_RMW_charge_replaced_not_added=True,incremental_I64_RMW_charge=0,
            port_bytes=dict(RF_pair_capture=1024,merge_prefix_max=508,vector_write_each_copy=512),
            reused_RF_boundary_payload_bits=dict(read=8192,write=4096),additional_wide_external_memory_ports=0,
            new_local_mux_connections_bits=4096*3,mask_fanout=128*32,source_bound_distributed_logic_slots=None,
            parent_owner_identity_storage_reused_only_if_source_gate_bound=True,
            software_replay_history_is_not_hardware_state=True,
            full_vector_old_mirror_identity_required=True,source_padded_tail_initialization_proof=None,
            software_mirror_bit_checks_are_not_installed_comparator_credit=True,
            local_routing_tracks_required=None,merged_payload_type='opaque U32 bits; NaN/Inf/zero unchanged',
            owner_hold='read child ACK+reverse, merge, both-copy write ACK+reverse, readback ACK+reverse, parent consumer+reverse'),
        shared64=dict(commands=len(commands['shared64']),counts=dict(counts),bytes=len(commands['shared64'])*64,
            aligned_rows=[0,1023],actual_max_row=max(c['scratch_row']for c in commands['shared64']),
            physical_banks_per_SM=2,bank_bytes=32,shared_capacity_per_SM=65536,per_SM_child_credit=1,
            max_children_per_retained_outer_tile=144,parent_child_counter_bits=8,
            read_local_source_edges=3,write_local_source_edges=2,physical_ns=None,
            proposed_local_serial_reference_edges=sum(c['local_reference_edges']for c in commands['shared64']),
            whole_group_parent_reverse_must_wait_for_every_child=True,production_calls_closed=0,
            rejected_historical_external_edge_defaults=[1,1,1],extra_C0_V1_I64_provider_charge=0),
        composed_area_upper_only={name:dict(source_parent_occupied_mm2=d['full_selected_occupied_mm2'],
            with_RMW_upper_mm2=d['full_selected_occupied_mm2']+32*footprint[-1]/1e6,die_mm2=d['die_mm2'],
            slot_and_track_admission=False) for name,d in parent['models'].items()},
        conditional_bound=None,missing_causal_dependencies=['actual cache ingress/home directory and same atomic L2 bank ownership',
            'actual whole-program contender overlap and finite grants from Dewey emitted DAG',
            'live parent lease receipt/child ACK/consumer/reverse endpoint bounds',
            'source-bound distributed RMW slots/control fanout cut capacity and SS merge stage',
            'old RF mirror/tail initialization proof for full-vector versus sector-RMW equivalence',
            'current production shared64 spans; retained directed control call is not production'],
        whole_operator=False,whole_token_latency_ns=None,engine_build_allowed=False,hardware_admitted=False,
        fairness_hardware_credit=False,installed_owner=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    s=inputs();c=compile_selected(s);files={'commands.json.gz':gzip.compress(canonical(c),mtime=0),'model.json':canonical(build(c,s))+b'\n'}
    for name,b in files.items():
        path=a.out/name
        if a.verify:
            if path.read_bytes()!=b:raise ValueError('byte-exact replay '+name)
        else:
            a.out.mkdir(parents=True,exist_ok=True)
            if path.exists() and path.read_bytes()!=b:raise ValueError('historical evidence overwrite refused')
            path.write_bytes(b)
    print('PASS selected source design replay; causal cache/whole-service admission FAIL')
if __name__=='__main__':main()
