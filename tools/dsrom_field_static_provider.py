#!/usr/bin/env python3
"""Size and emit literal current stage controls. No arithmetic, key or phase remapping."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(directory):
    d=Path(directory);b=json.loads((d/'binding.json').read_text())
    if b['stage'] not in (37,38) or b['PHW']!=10 or b['SAW']!=14: raise ValueError('unbound stage/geometry')
    if b['descriptor_conflicts'] or not b['only_PHROM_SBASE_changed'] or b['CFG_remapped']:raise ValueError('descriptor/CFG contract')
    for name,h in b['files_sha256'].items():
        if sha(d/name)!=h:raise ValueError('image pin '+name)
    phase=[int(x,16) for x in (d/'spine_phase.hex').read_text().split()]
    stream=[int(x,16) for x in (d/'spine_stream.hex').read_text().split()]
    if len(phase)!=2048 or len(stream)!=16384 or any(x>>64 for x in phase) or any(x>>48 for x in stream):raise ValueError('table geometry')
    for p in b['phases']:
        i=p['phase'];a=p['stream_base'];n=p['stream_words']
        if phase[2*i:2*i+2]!=[int(x,16) if isinstance(x,str) else x for x in p['PHROM_words']]:raise ValueError('phase mapping')
        if a+n>16384 or (phase[2*i]>>30)&65535!=a:raise ValueError('SBASE')
        body=b''.join(x.to_bytes(6,'little') for x in stream[a:a+n])
        if hashlib.sha256(body).hexdigest()!=p['stream_sha256']:raise ValueError('body mismatch')
        if not p['descriptor_stable_for_all_bound_commands']:raise ValueError('mutable descriptor')
    return b,phase,stream


def table_price(words,aw,width):
    nonzero=[x for x in words if x]
    bit_terms=[sum((x>>k)&1 for x in nonzero) for k in range(width)]
    equality_gates=len(nonzero)*(aw-1)
    or_gates=sum(max(0,n-1) for n in bit_terms)
    # Shared address polarities; fanout32 tree on each polarity conservatively.
    fan_nodes=0;n=len(nonzero)
    while n>1:
        n=math.ceil(n/32);fan_nodes+=n
    buffers=2*aw*fan_nodes
    cells=(2*equality_gates+3*or_gates)*.08748+aw*.04374+buffers*.11664
    return dict(address_bits=aw,output_bits=width,logical_depth=len(words),nonzero_entries=len(nonzero),equality_AND2_nodes=equality_gates,output_OR2_nodes=or_gates,buffer4_allowance= buffers,cell_area_screen_um2=cells,max_match_depth=math.ceil(math.log2(aw)),max_output_merge_depth=max((math.ceil(math.log2(n)) if n else 0 for n in bit_terms),default=0),default_zero_explicit=True)


def model(directory):
    b,p,s=load(directory)
    # Packed phase pair is justified by actual pa0={i_ph,0}, pa1={i_ph,1}.
    pairs=[p[2*i]|(p[2*i+1]<<64) for i in range(1024)]
    pp=table_price(pairs,10,128);sp=table_price(s,14,48)
    area=pp['cell_area_screen_um2']+sp['cell_area_screen_um2']
    return {'stage':b['stage'],'phase_count':b['phase_count'],'unique_stream_words':b['unique_stream_words'],'phase_table':pp,'stream_table':sp,
        'provider_realization':'Literal standard-cell constant decoder/OR network synthesized from full-resident images. No hard-macro timing model or fake zero clk-q.',
        'provider_state_bits':0,'provider_clock_sinks':0,'provider_reset_sinks':0,'memory_write_ports':0,'per_actor_programming_cycles':0,
        'phase_read_ports':2,'packed_phase_physical_reads':1,'stream_read_ports':1,'phase_read_bits_per_cycle':128,'stream_read_bits_per_cycle':48,
        'boundary_read_bits_per_cycle':176,'address_bits':24,'read_bytes_per_cycle':22,'added_macs_per_cycle':0,'provider_pipeline_cycles':0,'initiation_interval':1,
        'cell_area_screen_um2':area,'provider_reservation_um2':129.6*86.4,'density_budget':.5,'remaining_cell_budget_um2':129.6*86.4*.5-area,
        'provider_proposed_bbox_um':[15256.08,13476.24,15385.68,13562.64],
        'issuer_reservation_um2':559.872,'issuer_added_bits':47,'combined_new_reservation_um2':129.6*86.4+559.872,
        'ownership':'One immutable provider per selected physical stage/rank die; canonical keys/CFG IDs select existing phase. Dynamic xbase/obase/i_np stay existing GO ports.',
        'ledger':'Gross proposed provider reservation plus issuer charged ONCE; no old capture-space credit. Occupied-cell containment/escape/clock/PG must be reconciled by physical owner.',
        'tracks_required_min':200,'actual_routing_channel_capacity':None,'routing_admitted':False,
        'latency':'Zero logical provider stages is a proposed constant-logic implementation; actual delay is decoder/buffer/wire delay from real launch FF to existing capture FF. If loaded SS/FF misses, source-causal pipeline and its token cycles must be priced before a successor.',
        'clock_period_ns':.833333,'SS_setup_uncertainty_ns':.060,'FF_hold_uncertainty_ns':.025,
        'component_functional_build_admitted':area<=129.6*86.4*.5,'physical_admitted':False,'full_parent_adopted':False,
        'input_sha256':{p.name:sha(p) for p in Path(directory).iterdir() if p.is_file()},'source_assembly_commit':'6ae76fd8e',
        'source_scope':'Full resident stages37/38, all expert alternatives. Not all81 stages or a measured token latency.'}


def emit_module(directory,out):
    b,p,s=load(directory);name=f"ot_v41_stage{b['stage']}_control_rom"
    text=['// Full-resident immutable control inputs only; no expected/golden outputs.',f'module {name}(input wire [9:0] phase, input wire [13:0] stream_addr, output wire [63:0] pq0, pq1, output wire [47:0] sq);','reg [127:0] phase_pair;reg [47:0] stream_word;','assign {pq1,pq0}=phase_pair;assign sq=stream_word;','always @* begin phase_pair=0;case(phase)']
    for i in range(1024):
        word=p[2*i]|(p[2*i+1]<<64)
        if word:text.append(f"10'd{i}:phase_pair=128'h{word:032x};")
    text+=['default:phase_pair=0;endcase end','always @* begin stream_word=0;case(stream_addr)']
    for i,w in enumerate(s):
        if w:text.append(f"14'd{i}:stream_word=48'h{w:012x};")
    text+=['default:stream_word=0;endcase end','endmodule']
    Path(out).write_text('\n'.join(text)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--model',type=Path,required=True);a.add_argument('--rtl',type=Path);n=a.parse_args()
    m=model(n.input);n.model.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    if not m['component_functional_build_admitted']:raise SystemExit('cell budget screen refused')
    if n.rtl:emit_module(n.input,n.rtl)
