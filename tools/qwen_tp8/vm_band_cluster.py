#!/usr/bin/env python3
"""Full VM band composition: all 32 columns and all 64 pad-row bays.

Generate the structural RTL and independent production bench before source
views and die-assigned root-station pins exist. This is deliberately NOT a
route submission: root gathering, control distribution and final pin alignment
must be appended when the die publishes those contracts.
"""
import collections
import hashlib
import json
import re
from pathlib import Path
from vm_bay_cluster import MOD, VIEW, WID

ROOT = Path(__file__).resolve().parents[2]
P = 'rtl/qwen_sys/vm_plane_20261013'


def main():
    files = ['results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json',
             'results/arch/qwen_tp8_1012/vm_bay_tiles_claude.json']
    plan, packing = [json.loads((ROOT / f).read_text()) for f in files]
    bays = {b['n']: b for b in plan['x_relay_bays']}
    pads = {n: b for n, b in bays.items() if b.get('padrow')}
    columns = [c for c in plan['children'] if c['n'].startswith('vm_xcol_')]
    assert len(pads) == 64 and len(columns) == 32
    x0, y0 = 13284.0, 18131.04
    width, height = 4838.4, 386.64
    slotfile = ROOT/'results/arch/qwen_tp8_1012/vm_band_slot_assignment_codex.json'
    physical_slots = json.loads(slotfile.read_text())['physical_slots'] if slotfile.exists() else {}
    bitfile = ROOT/'results/arch/qwen_tp8_1012/vm_band_bit_assignment_codex.json'
    physical_bits = json.loads(bitfile.read_text())['physical_bits'] if bitfile.exists() else {}
    finefile = ROOT/'results/arch/qwen_tp8_1012/vm_band_fine_assignment_codex.json'
    fine = json.loads(finefile.read_text())['physical_offsets'] if finefile.exists() else {}
    orderfile = ROOT/'results/arch/qwen_tp8_1012/vm_band_bit_order_codex.json'
    orders = json.loads(orderfile.read_text())['physical_bit_permutations'] if orderfile.exists() else {}
    tilemap, children, clocks = {}, [], []
    for bn, b in pads.items():
        for t in packing['bay_tiles'].get(bn, []):
            i = len(children)
            v = dict(t, inst=f'u_t{i}', clock=f'ck_t{i}', enable=f'me_t{i}')
            tilemap[bn, t['slot']] = v
            clocks.append(v['clock'])
            delta = fine.get(f'{bn}:{t["slot"]}', [0,0])
            children.append(dict(inst=v['inst'], view=VIEW[t['kind']],
                at=[round(b['x']-x0+physical_slots.get(f'{bn}:{t["slot"]}',t['slot'])*21.6+delta[0], 4), round(b['y']-y0+delta[1], 4)],
                outline_um=[17.28, 97.2], orient='R0', bay=bn, slot=t['slot'],
                fine_offset=delta,
                physical_slot=physical_slots.get(f'{bn}:{t["slot"]}',t['slot'])))
    assert len(tilemap) == 270
    ni = collections.Counter()
    segments, assignments, ordered_wires = [], [], []
    used = collections.defaultdict(set)
    # Immutable port order matches the region generator, but joins use lane+visit.
    for lane, unordered in packing['lane_chain'].items():
        chain = sorted(unordered, key=lambda v: v['visit'])
        assert [v['visit'] for v in chain] == list(range(len(chain)))
        indices = [i for i, v in enumerate(chain) if v['bay'] in pads]
        assert indices and indices == list(range(indices[0], len(chain))), lane
        start = indices[0]
        source, pl = lane.split('>')
        region, bank, fifo = map(int, re.fullmatch(r'vm_g(\d+)_b(\d+)_xf(\d+)', source).groups())
        col = int(pl[1:])
        face = 's' if region < 4 else 'n'
        pin = [f'd_{face}', 8*ni[face]]
        ni[face] += 1
        prev = f'{pin[0]}[{pin[1]} +: 8]'
        initial = prev
        stages = []
        for visit in chain[start:]:
            for stage in visit['tiles']:
                stage = dict(stage)
                placement_id = f'{lane}|{visit["visit"]}|{stage["slot"]}|{stage["bit0"]}'
                stage['bit0'] = physical_bits.get(placement_id, stage['bit0'])
                order = orders.get(placement_id,list(range(8)))
                assert sorted(order)==list(range(8))
                key = visit['bay'], stage['slot']
                t = tilemap[key]
                bits = set(range(stage['bit0'], stage['bit0']+8))
                assert not bits & used[key], (lane, key, stage['bit0'])
                used[key].update(bits)
                if order==list(range(8)):
                    assignments.append(f'    assign d_{t["inst"]}[{stage["bit0"]} +: 8] = {prev};')
                    prev = f'q_{t["inst"]}[{stage["bit0"]} +: 8]'
                else:
                    logical=f'ordered_{len(segments)}_{len(stages)}'
                    ordered_wires.append(f'    wire [7:0] {logical} = {prev};')
                    for bit in range(8):assignments.append(f'    assign d_{t["inst"]}[{stage["bit0"]+order[bit]}] = {logical}[{bit}];')
                    prev='{'+','.join(f'q_{t["inst"]}[{stage["bit0"]+order[bit]}]' for bit in reversed(range(8)))+'}'
                stages.append(dict(bay=visit['bay'], visit=visit['visit'], placement_id=placement_id, bit_permutation=order, **stage))
        dest = [f'col{col}_d_'+('lo' if face == 's' else 'hi'), (region % 4*8+bank)*16+fifo*8]
        target = f'{dest[0]}[{dest[1]} +: 8]'
        # Mutation changes an actual boundary-to-column lane, before the column.
        assignments.append(f'    assign {target} = '+
            (f'(MUT == 1) ? {initial} : {prev};' if not segments else f'{prev};'))
        segments.append(dict(lane=lane, input=pin, output=dest,
            predecessor=chain[start-1]['bay'] if start else source,
            first_visit=start, path=stages, stages=sum(s['stages'] for s in stages)))
    assert len(segments) == 4096 and ni == {'s': 2048, 'n': 2048}
    ports = [('input', ck, '1') for ck in clocks]
    ports += [('input', t['enable'], '1') for t in tilemap.values()]
    ports += [('input', f'd_{f}', str(ni[f]*8)) for f in 'sn']
    ctrl = [('c_a','10'),('c_nv','10'),('c_v','1'),('c_d','14'),('c_j','4'),
            ('c_sp','4'),('o_v','1'),('o_sp','4'),('phase','PHW'),('epoch','16'),('sel_v','1')]
    for col in range(32):
        ports += [('input',f'ck_c{col}','1'),('input',f'me_c{col}','1')]
        ports += [('input', f'c{col}_{n}', w) for n,w in ctrl]
    ports += [('output','q','4096'),('output','q_phase','32*PHW'),
              ('output','q_epoch','512'),('output','q_v','32')]
    top = 'ot_qfd_vm_band'
    v = ['// GENERATED: full band, provisional local column outputs; root gather pending.',
         '// Enables are individual entries for the existing two-level me delivery.',
         f'module {top} #(parameter integer SMAX=9, PHW=SMAX-7, MUT=0) (',
         ',\n'.join('    '+d+' wire '+('' if w=='1' else f'[{w}-1:0] ')+n for d,n,w in ports), ');']
    for t in tilemap.values():
        w = WID[t['kind']]
        v += [f'    wire [{w-1}:0] d_{t["inst"]}, q_{t["inst"]};',
              '`ifndef OT_QFD_VM_HARD',
              f'    {MOD[t["kind"]]} #(.W({w}), .MEREG(1)) {t["inst"]}',
              '`else', f'    {MOD[t["kind"]]} {t["inst"]}', '`endif',
              f'      (.clk({t["clock"]}), .me_e({t["enable"]}), .d(d_{t["inst"]}), .q(q_{t["inst"]}));']
    for col, c in enumerate(columns):
        assert c['n'] == f'vm_xcol_{col}'
        v += [f'    wire [511:0] col{col}_d_lo, col{col}_d_hi;',
              '`ifndef OT_QFD_VM_HARD',
              f'    ot_qfd_vm_xcol_roots #(.NRB(64), .SMAX(SMAX), .MUT((MUT==2)?2:0)) u_c{col}',
              '`else', f'    ot_qfd_vm_xcol_roots u_c{col}', '`endif',
              f'      (.clk(ck_c{col}), .me_e(me_c{col}), .d_lo(col{col}_d_lo), .d_hi(col{col}_d_hi),',
              '       '+', '.join(f'.{n}(c{col}_{n})' for n,w in ctrl)+',',
              f'       .q(q[{col*128} +: 128]), .q_phase(q_phase[{col}*PHW +: PHW]),',
              f'       .q_epoch(q_epoch[{col*16} +: 16]), .q_v(q_v[{col}]));']
        children.append(dict(inst=f'u_c{col}', view=None, expected_master='ot_qfd_vm_xcol_roots',
            at=[round(c['x']-x0,4), round(c['y']-y0,4)], outline_um=[c['w'],c['h']], orient=c['orient']))
    v += ordered_wires + assignments
    for key, t in tilemap.items():
        for b in range(WID[t['kind']]):
            if b not in used[key]: v.append(f"    assign d_{t['inst']}[{b}] = 1'b0;")
    v.append('endmodule')
    out = ROOT / P / 'band'
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{top}.sv').write_text('\n'.join(v)+'\n')
    # Every lane reference is a behavioural shift chain, independent of tile mapping.
    tb = ['`timescale 1ns/1ps', 'module tb_qfd_vm_band;',
          'parameter integer SMAX=9, MUT=0, SEED=1, CYCLES=4000;',
          'localparam integer PHW=SMAX-7, NX=1<<SMAX;',
          'reg clk=0; always #5 clk=~clk; reg me=0, me_prev=0;',
          'reg [16383:0] d_s=0,d_n=0;',
          'reg [9:0] c_a=0,c_nv=1008;reg c_v=0,o_v=0,sel_v=0;',
          'reg [13:0] c_d=0;reg [3:0] c_j=0,c_sp=7,o_sp=7;',
          'reg [PHW-1:0] phase=0; reg [15:0] epoch=0;',
          'wire [4095:0] q;wire [32*PHW-1:0] q_phase;wire [511:0] q_epoch;wire [31:0] q_v;',
          'wire [32767:0] ref_inputs;',
          'ot_qfd_vm_band #(.SMAX(SMAX),.MUT(MUT)) dut (']
    binds = [f'.{ck}(clk)' for ck in clocks]+[f'.{t["enable"]}(me)' for t in tilemap.values()]
    binds += ['.d_s(d_s)', '.d_n(d_n)']
    for col in range(32):
        binds += [f'.ck_c{col}(clk)', f'.me_c{col}(me)']
        binds += [f'.c{col}_{n}({n})' for n,w in ctrl]
    binds += [f'.{n}({n})' for n in ('q','q_phase','q_epoch','q_v')]
    tb += [',\n'.join('    '+b for b in binds), ');',
           'integer cyc,w,r,k,errors=0,checks=0,lane_checks=0,stalls=0,valids=0;',
           'integer root_changes[0:1023];reg [4095:0] lastq=0;reg [(1<<PHW)-1:0] phase_seen=0;',
           'integer idx[0:127]; reg [3:0] split=0;',
           'reg [PHW-1:0] ph1=0,ph2=0,ph3=0;reg [15:0] ep1=0,ep2=0,ep3=0;',
           'reg v1=0,v2=0,v3=0;',
           'reg [31:0] rng;',
           'function automatic [31:0] rnd(input integer dummy); begin rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);rnd=rng;end endfunction',
           'always @(posedge clk) begin me_prev<=me; if(me_prev) begin',
           'if(o_v)split<=o_sp; ph1<=phase;ph2<=ph1;ph3<=ph2;ep1<=epoch;ep2<=ep1;ep3<=ep2;',
           'v1<=sel_v;v2<=v1;v3<=v2;',
           'for(k=0;k<128;k=k+1)idx[k]<=((32*phase+k/4)*4+k%4) % (1<<split);',
           'end end']
    for i,s in enumerate(segments):
        d=s['stages']; inp=f'{s["input"][0]}[{s["input"][1]} +: 8]'
        col=int(s['output'][0].split('_')[0][3:]);off=s['output'][1]+(512 if s['output'][0].endswith('hi') else 0)
        tb += [f'reg [{d*8-1}:0] delay{i}=0;',
               f'always @(posedge clk) if(me_prev) delay{i}<='+
               (f'{{delay{i}[{d*8-9}:0],{inp}}};' if d>1 else inp+';'),
               f'assign ref_inputs[{col*1024+off} +: 8]=delay{i}[{d*8-8} +: 8];',
               f'always @(posedge clk) begin #1;if(cyc>40)begin lane_checks=lane_checks+1;',
               f'if(dut.{s["output"][0]}[{s["output"][1]} +: 8] !== delay{i}[{d*8-8} +: 8]) errors=errors+1;end end']
    for col in range(32):
        tb += [f'wire [1007:0] bv{col};wire [NX-1:0] line{col};reg [127:0] expected2_{col}=0,expected3_{col}=0;',
               f'ot_qfd_vm_xplane_t #(.NRB(64)) ref_p{col}(.clk(clk),.me_e(me),.d(ref_inputs[{col*1024} +: 1024]),.c_a(c_a),.c_nv(c_nv),.q(bv{col}));',
               f'ot_qfd_vm_xline_t #(.NRB(64),.SMAX(SMAX),.SELECT_ONLY(1)) ref_l{col}(.clk(clk),.me_e(me),.d(bv{col}),.c_v(c_v),.c_d(c_d),.c_j(c_j),.c_sp(c_sp),.o_v(o_v),.o_sp(o_sp),.q(),.line_data(line{col}));',
               f'integer k{col};always @(posedge clk) if(me_prev) begin for(k{col}=0;k{col}<128;k{col}=k{col}+1) expected2_{col}[k{col}]<=line{col}[idx[k{col}]];expected3_{col}<=expected2_{col};end',
               f'always @(posedge clk) begin #1;if(cyc>40)begin checks=checks+1;if(q_v[{col}]!==v3 || (v3 && (q[{col*128} +:128]!==expected3_{col} || q_phase[{col}*PHW+:PHW]!==ph3 || q_epoch[{col*16}+:16]!==ep3)))errors=errors+1;end end']
    tb += ['initial begin rng=32\'h87654321^SEED;for(w=0;w<1024;w=w+1)root_changes[w]=0;',
           'for(cyc=0;cyc<CYCLES;cyc=cyc+1)begin @(negedge clk);me=(rnd(0)%4)!=0;if(!me)stalls=stalls+1;',
           'for(w=0;w<512;w=w+1)begin d_s[32*w+:32]=rnd(0);d_n[32*w+:32]=rnd(0);end',
           'c_a=rnd(0);c_nv=1008;c_v=(rnd(0)%2)==0;c_d=1<<(rnd(0)%14);c_j=rnd(0)%9;c_sp=7+rnd(0)%(SMAX-6);o_sp=c_sp;o_v=(rnd(0)%8)==0;phase=rnd(0);epoch=rnd(0);sel_v=(rnd(0)%3)!=0;',
           '@(posedge clk);#2;if(q_v==32\'hffffffff)begin valids=valids+1;phase_seen[q_phase[PHW-1:0]]=1;for(w=0;w<1024;w=w+1)if(q[4*w+:4]!==lastq[4*w+:4])root_changes[w]=root_changes[w]+1;end lastq=q;end',
           'for(w=0;w<1024;w=w+1)if(root_changes[w]<16)errors=errors+1;if(phase_seen!=={(1<<PHW){1\'b1}})errors=errors+1;',
           'if(errors || checks!=(CYCLES-41)*32 || lane_checks!=(CYCLES-41)*4096 || stalls<CYCLES/8 || valids<CYCLES/3)begin $display("FAIL fullband SMAX=%0d MUT=%0d errors=%0d checks=%0d lane_checks=%0d",SMAX,MUT,errors,checks,lane_checks);$fatal(1,"FAIL");end',
           '$display("PASS fullband SMAX=%0d MUT=%0d columns=32 roots=32 payload=4096 lane_checks=%0d checks=%0d valids=%0d stalls=%0d",SMAX,MUT,lane_checks,checks,valids,stalls);$finish;end endmodule']
    (out/'tb_qfd_vm_band.sv').write_text('\n'.join(tb)+'\n')
    rec=dict(schema='opentallas.qwen.vm-band.v1', status='COMPOSITION_ONLY_UNROUTED',
        origin_um=[x0,y0],outline_um=[width,height],columns=32,pad_bays=64,
        occupied_pad_slots=270,total_pad_slots=384,spare_pad_slots=114,
        child_clock_entries=len(children),clock_form='entries; no parent tree; phi-R_i',
        lane_enable_delivery='per-child entry; existing two-level me tree not yet placed',
        source_payload_bits=4096,source_tags_per_column='phase + epoch16 + valid',
        child_count=len(children),children=children,segments=segments,
        sources={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
        inputs={f'd_{f}':ni[f]*8 for f in 'sn'},
        stage_bits=sum(s['stages']*8 for s in segments),
        production_shape=dict(NRB=64,SMAX_native=9,phases_native=4,SMAX_fallback=11,phases_fallback=16),
        open_requirements=['die-assigned32rootstation output pins','full4096bit gathering and aligned tags',
                          'control and enable distribution','closed xcol_roots view slot fit',
                          'all-bit real-pin hop audit and combined cut model','M7local PG and phase-alignedM8/M9',
                          'fullband CTS/GRT/DRT and wholeVM end-to-end composition'])
    (ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json').write_text(json.dumps(rec,indent=1)+'\n')
    print({k:rec[k] for k in ('columns','pad_bays','occupied_pad_slots','spare_pad_slots','child_count','stage_bits')})


if __name__ == '__main__':
    main()
