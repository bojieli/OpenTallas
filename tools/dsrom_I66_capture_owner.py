#!/usr/bin/env python3
"""Constructive read-owner protocol, before physical register placement.
No field ready, source edit, payload arithmetic or geometry invented.
"""
import argparse,hashlib,json,math
from pathlib import Path
import dsrom_I66_capture_timing as T
ROOT=T.ROOT;OUT=ROOT/'results/uarch/dsrom_I66_capture_owner_20261002'
# Proposed software ABI: current04bb fields, explicitly separate from root69.
CONTEXT=[('stage',6),('rank',2),('expert',9),('phase',10),('key_word',32),('generation',32),('user',32),('xversion',32),('pc',14)]
def identity(ctx):
    if set(ctx)!=set(n for n,w in CONTEXT):raise ValueError('context missing/extra')
    for n,w in CONTEXT:
        if type(ctx[n])!=int or not 0<=ctx[n]<(1<<w):raise ValueError('context width')
    return tuple(ctx[n] for n,w in CONTEXT)

class Owner:
    """One frozen phase lease; read acceptance reserves a sink seat.
    Credits are explicit supplied capacity, never chosen by this model.
    Abstract returns may reorder, but delivery remains source-provider rows0..575.
    """
    def __init__(self,ctx,rows,credits):
        if type(credits)!=int or not 1<=credits<=576:raise ValueError('finite read credits')
        self.ctx=identity(ctx);self.rows=rows;self.capacity=credits
        self.captured={};self.issued={};self.returned={};self.visible=set()
        self.next_issue=0;self.next_delivery=0;self.terminal=False;self.lease=True;self.last_issue=None
        self.arrival_edges={};self.last_consume=None;self.delivery_ack=False
    def capture(self,row,root,raw):
        if not self.lease or self.terminal or row in self.captured or self.rows.get(row)!=root:raise ValueError('capture identity')
        # opaque69bits, no rounding/mode changes
        if type(raw)!=int or not 0<=raw<1<<69:raise ValueError('record69 width')
        self.captured[row]=raw
    def source_terminal(self,idle):
        if not idle or len(self.captured)!=576:raise ValueError('source debt')
        self.terminal=True
    def issue(self,row,ctx,edge,physical_shard):
        if identity(ctx)!=self.ctx or not self.lease or not self.terminal:raise ValueError('owner/source admission')
        if row!=self.next_issue or row not in self.captured:raise ValueError('ordered read admission')
        if physical_shard!=self.rows[row]//64:raise ValueError('physical shard route ownership')
        if self.last_issue is not None and edge<=self.last_issue:raise ValueError('one scalar acceptance/edge')
        if len(self.issued)>=self.capacity:return False # scalar-only backpressure
        self.issued[row]=edge;self.next_issue+=1;self.last_issue=edge;return True
    def arrive(self,row,ctx,raw,edge,physical_shard):
        if identity(ctx)!=self.ctx or row not in self.issued or row in self.returned:raise ValueError('stale/unowned/duplicate return')
        if physical_shard!=self.rows[row]//64:raise ValueError('physical return owner')
        if edge<=self.issued[row] or raw!=self.captured[row]:raise ValueError('response clock/data identity')
        # This seat was irrevocably reserved at issue, even if sink refuses.
        self.returned[row]=raw;self.arrival_edges[row]=edge
    def consume(self,ready,edge):
        row=self.next_delivery
        if not ready or row not in self.returned:return None
        if edge<=self.arrival_edges[row] or (self.last_consume is not None and edge<=self.last_consume):
            raise ValueError('registered return/one consumer acceptance per edge')
        self.last_consume=edge
        value=self.returned.pop(row);self.issued.pop(row);self.next_delivery+=1
        return row,value
    def mark_visible(self,row,ctx):
        if identity(ctx)!=self.ctx or row>=self.next_delivery or row in self.visible:raise ValueError('home visibility identity')
        self.visible.add(row)
    def packet_ack(self,ctx,edge,crc_checked,sequence_checked):
        # Actual RX ACK follows its final out_fire; it is not row visibility.
        if identity(ctx)!=self.ctx or self.delivery_ack or self.next_delivery!=576 or not crc_checked or not sequence_checked:
            raise ValueError('unowned/early/duplicate delivery ACK')
        if edge<=self.last_consume:raise ValueError('ACK must follow last accepted delivery')
        self.delivery_ack=True
    def release(self,source_fenced,wire_delivery_fenced,provenance):
        if not self.delivery_ack or not all((source_fenced,wire_delivery_fenced,provenance)) or self.issued or self.returned or len(self.visible)!=576:raise ValueError('causal rearm fence')
        self.lease=False

def source_formatter(record,descriptor):
    """Direct transcription of unchanged source rows block, no new rounding.
    Source r_bf16 is supplied by the field, never recomputed from r_fp32 here.
    Legal-adapter contract rejects original truncation/VM alias conditions.
    """
    for name,width in [('row',16),('pos',3),('fp32',32),('bf16',16),('error',1)]:
        if type(record[name])!=int or not 0<=record[name]<(1<<width):raise ValueError('raw field width')
    fmt=descriptor['fmt'];split=descriptor['rsplit']
    if fmt not in (0,1,2):raise ValueError('invalid format')
    address=descriptor['obase']+record['row']+record['pos']*descriptor['ops']
    if address<0 or address>=(1<<19):raise ValueError('AW30/VM19 alias or capacity')
    if record['error']:raise ValueError('source error quarantine, no healthy consume')
    fp32=(fmt==1 or (fmt==0 and (descriptor['pw62'] if record['row']<split else descriptor['pw63'])))
    return address,record['fp32'] if fp32 else record['bf16']<<16

def hold_repair():
    lib=T.library()['FF'];facts,_=T.C.facts()
    bmin=min(T.minimum(t) for k,t in lib[T.C.BUF]['tables'] if k.startswith('cell_'))
    result={}
    for name in (T.C.HQ,T.C.ASR):
        early=sum(min(T.minimum(t) for k,t in lib[n]['tables'] if k.startswith('cell_')) for n in (name,T.C.INV,T.C.NAND,T.C.NAND))
        hold=max(max(x for r in t['values'] for x in r) for _,t in lib[name]['hold'])
        n=math.ceil(max(0,hold+25+25-early)/bmin)
        result[name]=dict(paired_same_FF_feedback=True,early_feedback_ps=early,own_destination_hold_ps=hold,BUF_min_ps=bmin,
                         required_allowed_BUF_lower_bound=n,conditional_margin_ps=early+n*bmin-hold-50,
                         position='feedback branch only, before hold NAND; capture branch unchanged',actual_geometry_qualified=False)
    # SourceB991 exactstorage + completecontroller1483, not speculative SRAM.
    count=39744*result[T.C.HQ]['required_allowed_BUF_lower_bound']+1483*result[T.C.ASR]['required_allowed_BUF_lower_bound']
    return dict(typed_paths=result,total_feedback_BUF=count,body_area_um2=count*facts[T.C.BUF]['SS']['area_um2'],
                not_mixed_HQ_launch_ASR_destination=True,forward_paths_need_separate_hold_check=True)

def forward_hold_obligations():
    lib=T.library()['FF']
    def early(n):return min(T.minimum(t) for k,t in lib[n]['tables'] if k.startswith('cell_'))
    def hold(n):return max(max(x for r in t['values'] for x in r) for _,t in lib[n]['hold'])
    paths=[]
    for launch in (T.C.HQ,T.C.ASR):
        for destination in (T.C.HQ,T.C.ASR):
            for gates in (0,2):
                delay=early(launch)+early(T.C.INV)+gates*early(T.C.NAND)
                n=math.ceil(max(0,hold(destination)+50-delay)/early(T.C.BUF))
                paths.append(dict(launch=launch,destination=destination,series_NAND=gates,
                    unbuffered_min_ps=delay,own_destination_hold_ps=hold(destination),
                    required_BUF_minimum=n,conditional_margin_ps=delay+n*early(T.C.BUF)-hold(destination)-50,
                    actual_routes_load_slew_and_clock_correlation_qualified=False))
    return dict(paths=paths,policy_hold_uncertainty_ps=25,capture_skew_ps=25,
        raw_feedback_repair_not_a_forward_path_repair=True,
        pipeline_payload_and_selector_forward_hold_cells_not_inherited_from_feedback=True,
        forward_BUF_state_bits=0,total_added_forward_BUF_cells=None,
        selector_forward_SS_latency_unknown=True)

def geometry_gate(g):
    required=('capture_bank_homes','controller_home','consumer_home','layer_routes','clock_domain_ownership','reset_ingress','accepted_consumer_deadlines')
    missing=[n for n in required if not g.get(n)]
    if missing:raise ValueError('unbound physical/clock/deadline: '+','.join(missing))
    return True

def model():
    import dsrom_I66_capture_join_ledger as L
    plans,depths=T.C.B.allocation()
    trace=T.C.B.local_trace(plans,depths)
    return dict(existing_core_transport_capture_ledger=L.ledger(),observed_source_capture=trace,
                provider_gate=dict(physical_routes=False,registered_selector_positions=False,finite_CDC_provider=False,
                    actual_packet_ACK_enrolled=False,actual_consumer_deadline=False,build_admitted=False),
                minimal_causal_architecture=['reserve all320/256 local capture seats before GO',
                    'freeze one169bit identity lease; dynamicshard1 is route, never owner alias',
                    'register bounded selector copies locally; accepted read reserves sink and route seat',
                    'nonstallable credited local return; final sink holds debt while refused; no field ready',
                    'gather sourceordered rows0..575, preserve original fmt and supplied BF16',
                    'fresh-packet delivery ACK follows actual last RX out_fire; causal home visibility separately required',
                    'release generation only after source, delivery, route, home and provenance fences'],
                remaining_registered_successor='exact home/pin routes -> registered select/control stations -> typed SS/FF forward+feedback screen -> finite3:4CDC/deadline -> contextual gate; no sweep',typed_forward_hold_obligations=forward_hold_obligations(),schema=1,verdict='OWNER_PROTOCOL_DERIVED_PHYSICAL_HOME_JOIN_PENDING',source_changed=False,
                raw_root_bits=69,raw_root_generation_bits=0,rows=576,root_ports=128,
                context_fields=CONTEXT,context_bits=sum(w for n,w in CONTEXT),compound_context_with_route_bits=170,
                proposed_request_bits=sum(w for n,w in CONTEXT)+16+1+1,
                proposed_return_bits=sum(w for n,w in CONTEXT)+69+1+1,
                physical_shard_bits=1,physical_shard_is_route_field_not_global_context=True,
                shard_seats=[320,256],cross_die_scalar_mux_forbidden=True,
                token_valid_separate_from_stored_raw_valid=True,
                issue='reserve return seat and route arrival-slot BEFORE scalar read; never assert ready at field',
                local_selector='registered bit-group copies beside bounded payload lanes; bound group width from allowedcell load/slew and actual bit-cell geometry, not whole69bit select fanout',
                formatter='unchangedsource r_row+r_pos*ops+obase, source fmt/pw62/pw63/rsplit; supplied rawBF16 preserved, no new rounding; healthy delivery requires error0 and AW30/VM19 checked',
                VM_bridge='original512bit full-block read/write; exclusive addressed output lease, mask/assembly/causalvisible provider required, not source ACK substitute',
                CDC_path='native singleclk source does not implement split. Planned streaming gather/VM1.2GHz to serialSU0.9GHz needs explicit owned request/response or committed-visible bridge; no zero-cycle CDC or phase presumed',
                return_flow='nonstallable only after route/sink reservation; all accepted token identity retained; refused final consumer holds its reserved seat',
                retirement='consume rows0..575 and retain frozen generation until source+route+delivery+causal home visibility+provenance fenced',
                ACK_contract='fresh successful source packet delivery ACK after final RX out_fire and CRC/sequence checks; not per-row ACK, not causal VM visibility; source duplicate ACK shortcut still requires separate gate',
                return_edge_contract='registered arrival post-edge cannot be consumed on that same edge; one scalar consumption per consumer edge',
                minimal_credit_rule='For II1 scalar issue: credits cover request+localread+reply+consumerhold+positive captured credit-return path; delivery alone never immediately frees source credit. Exact route/CDC calendar required. No128/512 pool selected.',
                read_credit_capacity=None,positions_selected=False,added_pipeline_state_bits=None,
                state_price_equations=dict(frozen_context_existing_baseline_bits=123,frozen_context_missing_key32_pc14_bits=46,
                    required_extra_frozen_identity_bits=46,context_replication_to_remote_shard_additional_bits=None,
                    extra_frozen_identity_hold_BUF_lower_bound=92,extra_identity_clock_reset_and_PG_not_zero=True,
                    request_stage_bits=187,return_stage_bits=240,selector_copy_bits='registered selector+valid per source-derived physical bit group',sink_seat_bits=240,
                    mandatory_hold_repair=hold_repair()),
                native_clock='one source clk; planned3:4 CDC not implemented',
                physical_streaming_period_ps='2500/3',physical_serial_period_ps='10000/9',
                clock_superperiod_ps='10000/3 (4 streaming,3 serial edges)',CDC_provider=None,CDC_phase=None,
                consumer_first_edge=None,consumer_last_edge=None,missing_deadline_not_zero=True,
                actual_bank_to_consumer_distance_um=None,
                geometry_input_commit='4cc368a46ca8894b102bb34ccd674168571cd282',geometry_previous_input_preserved='1f8e7e65d',region_centre_L1_projection_um=3284.729,
                region_projection_is_not_actual_pin_or_legal_route=True,
                actual_home_enclosure_um=[324,432.81],
                register_positions_pending_actual_routes_not_region_centres=True,
                global_stall_or_read_mux_not_assumed_free=True,
                default1024FAIL_preserved=True,timeout4096_selected=False,RTL_or_build_admitted=False,
                predecessor_rejection='e899350628dcef8ebfa55e7f398cb74d37839337')
def pins():
    ps=[Path(__file__),ROOT/'tools/dsrom_I66_capture_drain_calendar.py',ROOT/'tools/dsrom_I66_capture_join_ledger.py']
    ps+=sorted((OUT/'inputs').glob('*'))
    ps+=[T.C.B.M.S.A/'source_snapshot/pinned/rtl/v41die/ot_v41_spine_w17w10.sv']
    # Include the transitive Python source cone, not private import state.
    import ast
    todo=list(ps);seen=set(ps)
    while todo:
        item=todo.pop()
        if item.suffix!='.py':continue
        for node in ast.walk(ast.parse(item.read_text())):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) else []
            for name in names:
                if not name:continue
                dep=ROOT/'tools'/(name+'.py')
                if dep.is_file() and dep not in seen:seen.add(dep);ps.append(dep);todo.append(dep)
    return {**T.C.B.pins(),**T.pins(),**{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ps}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    m=model();m['source_pins']=pins();raw=(json.dumps(m,indent=2,sort_keys=True)+'\n').encode()
    if a.verify:
        if a.out.read_bytes()!=raw:raise SystemExit('FAIL source-bound owner replay')
        print('PASS byteexact owner contract; physical/deadline gate remains closed')
    else:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(raw)
