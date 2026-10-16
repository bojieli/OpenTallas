#!/usr/bin/env python3
"""Generate A2 internally controlled full shared53/32bank/512bit witness; --run needs admission."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/s81_vm_area_1417'
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
SOURCES = ['tools/s81_vm/area_a2_controlled.sv', 'tools/s81_vm/area_id_native.sv',
           'tools/s81_vm/area_id_native_join.sv', 'tools/s81_vm/area_a2_hardmasters.sv', 'tools/s81_vm/area_a2_controlled_gate.py']

BENCH = r'''`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;
 reg [52:0] v=0;reg [741:0] row=0;
 reg [847:0] mask=0;reg [423:0] tag=0;reg [27135:0] data=0;

 wire [127:0] ov;wire [1791:0] ore;wire [1023:0] ot;
 wire [511:0] om;wire [16383:0] od;wire [15:0] fault;
 s81_a2_controlled dut(
 .ck_header(ck),.ck_payload({4{ck}}),.ck_control({16{ck}}),
 .ck_meta({16{ck}}),.ck_fault({16{ck}}),.ck_data({128{ck}}),
 .rst_header_n(rst),.rst_payload_n({4{rst}}),.rst_control_n({16{rst}}),
 .rst_meta_n({16{rst}}),.rst_fault_n({16{rst}}),.rst_data_n({128{rst}}),
 .i_v(v),.i_row(row),.i_tag(tag),.i_mask(mask),.i_data(data),
 .o_slice_v(ov),.o_slice_row(ore),.o_slice_tag(ot),.o_mask(om),.o_data(od),.o_fault(fault));
 reg [31:0] ev[0:511];
 reg [447:0] er[0:511];reg [511:0] em[0:511];
 reg [255:0] et[0:511];reg [16383:0] ed[0:511];
 integer sourcecycle[0:511][0:31];integer sourcelane[0:511][0:31];
 integer cycle,src,bank,ln,t,n,sl,ps,pbank,mode,checked=0,active=0;
 reg [13:0] r;reg [127:0] word;reg [511:0] fullword;reg [15:0] fullmask;
 task tick;begin @(posedge ck);#1;end endtask
 initial begin
  mode=0;if($value$plusargs("mode=%d",mode))begin end
  if(mode!=0 && mode!=4)$fatal(1,"unsupported mode");
  for(t=0;t<512;t=t+1)begin
   ev[t]=0;er[t]=0;em[t]=0;et[t]=0;ed[t]=0;
  end
  repeat(7)tick();@(negedge ck);rst=1;repeat(7)tick();
  for(cycle=0;cycle<220;cycle=cycle+1)begin
   @(negedge ck);v=0;row=0;mask=0;tag=0;data=0;
   if(cycle<180 && (cycle%9==0 ||mode==4))begin
    for(n=0;n<(mode==4?32:53);n=n+1)begin
     src=mode==4?(n+cycle)%53:n;
     bank=mode==4?n:(n/3+cycle/9)%32;ln=0;
     // Expected lane is the ascending-source prefix, independent of DUT IDs.
     for(ps=0;ps<src;ps=ps+1)begin
      pbank=row[14*ps+:5]^{row[14*ps+5+:3],2'b00};
      if(v[ps] && pbank==bank)ln=ln+1;
     end
     r=((cycle/9)%16)*32+bank;
     r[4:0]=bank^{r[7:5],2'b00};
     fullword=0;fullmask=0;
     for(sl=0;sl<4;sl=sl+1)begin
      word={32'(src),32'(cycle),32'(sl),32'hcafe0000+32'(src+sl*256)};
      fullword[sl*128+:128]=word;
      fullmask[sl*4+:4]=((src+sl)%15)+1;
     end
     v[src]=1;row[14*src+:14]=r;
     mask[16*src+:16]=fullmask;tag[8*src+:8]=cycle+src;
     data[512*src+:512]=fullword;
     t=cycle+6+ln;
     ev[t][bank]=1;er[t][14*bank+:14]=r;em[t][16*bank+:16]=fullmask;
     et[t][8*bank+:8]=cycle+src;ed[t][512*bank+:512]=fullword;
     sourcecycle[t][bank]=cycle;sourcelane[t][bank]=ln;
     active=active+1;
    end
   end
   tick();
   for(sl=0;sl<4;sl=sl+1)begin
    if(ov[32*sl+:32]!==ev[cycle])$fatal(1,"FULL32_VALID cycle%0d slice%0d",cycle,sl);
    for(bank=0;bank<32;bank=bank+1)if(ev[cycle][bank])begin
     if(ore[(32*sl+bank)*14+:14]!==er[cycle][14*bank+:14] ||
        ot[(32*sl+bank)*8+:8]!==et[cycle][8*bank+:8])
       $fatal(1,"FULL32_META cycle%0d bank%0d slice%0d",cycle,bank,sl);
    end
   end
   for(bank=0;bank<32;bank=bank+1)if(ev[cycle][bank])begin
    if(od[bank*512+:512]!==ed[cycle][bank*512+:512] ||
       om[bank*16+:16]!==em[cycle][bank*16+:16])
      $fatal(1,"FULL32_PAYLOAD cycle%0d bank%0d",cycle,bank);
    $display("OBS_FULL %0d %0d %0d %0d %0d %0d %0d %0128h",cycle,
      sourcecycle[cycle][bank],bank,sourcelane[cycle][bank],
      ore[bank*14+:14],ot[bank*8+:8],om[bank*16+:16],od[bank*512+:512]);
    checked=checked+1;
   end
   if(fault!==0)$fatal(1,"FULL32_FAULT cycle%0d",cycle);
  end
  if(checked!=active)$fatal(1,"FULL32_LOST %0d/%0d",checked,active);
  @(negedge ck);rst=0;repeat(7)tick();
  if(fault!==0 || ov!==0)$fatal(1,"FULL32_RESET");
  $display("PASS full_shared53 banks32 width512 quarters16 roots181 mode%0d records%0d first_age6 II1",mode,checked);
  $finish;
 end
endmodule
'''


def check_lock():
    if json.loads(LOCK.read_text())['owner'] not in ('claude','codex'):
        raise RuntimeError('coordinator ownership changed')


def write(path, value):
    check_lock()
    path.write_text(value)


def run(command, logfile):
    check_lock()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    check_lock()
    write(logfile, result.stdout + result.stderr)
    return result


UNIT = r'''`timescale 1ns/1ps
module unit_tb;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;reg [52:0] v=(53'b1<<0)|(53'b1<<5)|(53'b1<<52);reg [423:0] bank=0;
 wire [2:0] epoch;wire [52:0] unusedv;wire [741:0] unusedrow;wire [423:0] unusedtag;
 wire [167:0] ids;wire [7:0] dv;wire [15:0] ds;wire fault;
 s81_a2_w0_header header(ck,rst,v,742'b0,424'b0,unusedv,unusedrow,unusedtag,epoch);
 s81_a2_controller_b0 control(ck,rst,v,bank,epoch,{4{epoch}},ids,dv,ds,fault);
 reg stripe_override=1;
 wire [847:0] stripe_input;wire [127:0] stripe_data;wire [7:0] stripe_v;wire stripe_fault;
 genvar s;generate for(s=0;s<53;s=s+1)begin:stripe_source
  assign stripe_input[16*s+:16]=16'ha000+s;
 end endgenerate
 s81_a2_stripe_data16 stripe(ck,rst,stripe_input,
  stripe_override?168'h74:ids,stripe_override?8'h01:dv,ds,stripe_v,stripe_data,stripe_fault);
 task tick;begin @(posedge ck);#1;end endtask
 integer e;
 initial begin
  repeat(7)tick();
  if(fault!==0 || ids!==0 || dv!==0 ||stripe_v!==0 ||stripe_fault!==0)$fatal(1,"UNIT_HELD_RESET");
  @(negedge ck);rst=1;
  repeat(3)begin tick();if(ids!==0 ||dv!==0 ||fault!==0 ||stripe_v!==0 ||stripe_fault!==0)$fatal(1,"UNIT_PREARM_STALE");end
  @(negedge ck);v=0;stripe_override=0;repeat(7)tick();
  if(fault!==0)$fatal(1,"UNIT_EPOCH_PHASE");
  @(negedge ck);v=(53'b1<<0)|(53'b1<<5)|(53'b1<<52);
  tick();
  @(negedge ck);v=0;
  for(e=1;e<=8;e=e+1)begin
   tick();
   if(e==2 && (ids[6:0]!==7'h40 || ids[13:7]!==7'h45 || ids[20:14]!==7'h74 || ids[167:21]!==0))
    $fatal(1,"UNIT_ID_PREFIX");
   if(e>=4 && e<=6)begin
    if(dv!==1 || ds[1:0]!==e-4)$fatal(1,"UNIT_DRAIN_PHASE edge%0d",e);
   end else if(dv!==0)$fatal(1,"UNIT_EARLY_DRAIN edge%0d",e);
   if(fault!==0)$fatal(1,"UNIT_UNEXPECTED_FAULT edge%0d",e);
   if(stripe_fault!==0)$fatal(1,"UNIT_STRIPE_FAULT edge%0d",e);
   if(e>=6)begin
    if(stripe_v!==1 ||stripe_data[15:0]!==(e==6?16'ha000:e==7?16'ha005:16'ha034))
     $fatal(1,"UNIT_STRIPE_AGE6 edge%0d",e);
   end else if(stripe_v!==0)$fatal(1,"UNIT_STRIPE_EARLY");
  end
  @(negedge ck);v=(53'b1<<0)|(53'b1<<1)|(53'b1<<5)|(53'b1<<52);
  tick();@(negedge ck);v=0;repeat(8)tick();
  if(fault!==1)$fatal(1,"UNIT_MISSING_OVERFLOW_FAULT");
  @(negedge ck);rst=0;v=(53'b1<<0)|(53'b1<<5)|(53'b1<<52);stripe_override=1;
  repeat(7)tick();if(ids!==0 ||dv!==0 ||fault!==0)$fatal(1,"UNIT_RESTART_HELD");
  @(negedge ck);rst=1;
  repeat(3)begin tick();if(ids!==0 ||dv!==0 ||fault!==0 ||stripe_v!==0 ||stripe_fault!==0)$fatal(1,"UNIT_RESTART_PREARM");end
  @(negedge ck);v=0;stripe_override=0;
  repeat(8)begin tick();if(ids!==0 ||dv!==0 ||fault!==0 ||stripe_v!==0 ||stripe_fault!==0)$fatal(1,"UNIT_RESTART_STALE");end
  $display("PASS A2 controller source0/5/52 prefix IDsP2 drainsP4/P5/P6 native_reset phase overflow");$finish;
 end
endmodule
'''


def unit_gate():
    records=[]
    with tempfile.TemporaryDirectory(prefix='s81-a2-unit-') as temporary:
        bench=Path(temporary)/'unit.sv'
        write(bench,UNIT)
        for variant,define in [('gold',None),('wrong_id','S81_A2_MUT_ID'),
                               ('drain_phase','S81_A2_MUT_DRAIN'),
                               ('held_reset','S81_A2_MUT_HELD_RESET'),('epoch','S81_A2_MUT_EPOCH')]:
            executable=str(Path(temporary)/(variant+'.vvp'))
            command=['iverilog','-g2012','-s','unit_tb','-o',executable]
            if define:command.append('-D'+define)
            build=run(command+SOURCES[:4]+[str(bench)],OUT/f'a2_controlled_pinplain_unit_{variant}_compile.log')
            if build.returncode:raise RuntimeError(build.stdout+build.stderr)
            result=run(['vvp',executable],OUT/f'a2_controlled_pinplain_unit_{variant}.log')
            passed=result.returncode==0 and 'PASS A2 controller' in result.stdout
            rejected=result.returncode!=0 and 'UNIT_' in result.stdout
            if not (passed if variant=='gold' else rejected):
                raise RuntimeError(f'unit {variant}: {result.stdout}{result.stderr}')
            records.append(dict(variant=variant,returncode=result.returncode,stdout=result.stdout,
                                exact_pass=passed,mutant_rejected=rejected))
    proof=dict(status='PASS_ISOLATED_A2_CONTROLLER_UNIT_ONLY_NOT_FULL32_OR_PHYSICAL',
               source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES},
               bench_sha256=hashlib.sha256(UNIT.encode()).hexdigest(),
               scope='actual controller+one actual native W0header+one actual native W16 stripe; four payload epochs tied to header only in unit bench',
               prefix_source='NP64 sat3 and p_lane block copied from git3f077f3a1 with plain-pin arm qualification added dsfd_vm_static_wcontrol.sv',
               records=records)
    write(OUT/'a2_controlled_pinplain_unit_proof.json',json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(status=proof['status'],mutants_rejected=4)))


def syntax_gate():
    # Elaborate only the generated scoreboard against an empty interface stub.
    # This catches bench name errors before the admitted full-shape compile.
    source=(ROOT/SOURCES[0]).read_text()
    start=source.index('module s81_a2_controlled(')
    stub=source[start:source.index(');',start)+2]+'\nendmodule\n'
    with tempfile.TemporaryDirectory(prefix='s81-a2-bench-syntax-')as temporary:
        path=Path(temporary)
        write(path/'stub.sv',stub);write(path/'bench.sv',BENCH)
        result=run(['iverilog','-g2012','-s','tb','-o',str(path/'sim'),str(path/'stub.sv'),str(path/'bench.sv')],
                   OUT/'a2_controlled_pinplain_syntax.log')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    write(OUT/'a2_controlled_pinplain_syntax.json',json.dumps(dict(
        status='PASS_GENERATED_BENCH_NAME_AND_SYNTAX_CHECK_ONLY',
        method='generated scoreboard compiled against empty exact-interface top stub; no hardware correctness claim',
        bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest()),indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-only', action='store_true')
    parser.add_argument('--run', action='store_true', help='build/run only inside parent-admitted resource job')
    parser.add_argument('--unit', action='store_true', help='small controller-only Icarus gate')
    args = parser.parse_args()
    check_lock()
    OUT.mkdir(parents=True, exist_ok=True)
    bench = OUT / 'a2_controlled_pinplain_bench.sv'
    write(bench, BENCH)
    plan = dict(status='GENERATED_NOT_RUN', source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES},
                bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),
                topology=dict(shared_global_sources=53, logical_banks=32, output_width=512,
                              native_quarters=16, real_fault_join_per_quarter=True, independent_clock_roots=181, actual_W0_roots=5, internal_controller_ID_and_drain=True),
                clock_scope='all181 clock/reset pins tied only in functional bench',
                expected_records=dict(mode0_all_three_lanes=1060, mode4_sustained_II1=5760),
                flags=dict(actual_SRAM_read_join_run=False, native_physical_qualified=False,
                           full_programme_trace=False, full_token_claim=False))
    write(OUT/'a2_controlled_pinplain_plan.json', json.dumps(plan, indent=2)+'\n')
    syntax_gate()
    if args.unit:
        unit_gate()
    if not args.run:
        print(json.dumps(dict(status='GENERATED_NOT_RUN', bench=str(bench))))
        return
    records=[]
    with tempfile.TemporaryDirectory(prefix='s81-a2-controlled-') as temporary:
        for variant, define in [('gold', None), ('wrong_id', 'S81_A2_MUT_ID'), ('drain_phase', 'S81_A2_MUT_DRAIN'), ('held_reset', 'S81_A2_MUT_HELD_RESET'), ('epoch', 'S81_A2_MUT_EPOCH')]:
            executable=str(Path(temporary)/(variant+'.vvp'))
            command=['iverilog','-g2012','-s','tb','-o',executable]
            if define:
                command.append('-D'+define)
            build=run(command+SOURCES[:4]+[str(bench)],OUT/f'a2_controlled_{variant}_compile.log')
            if build.returncode:
                raise RuntimeError(build.stdout+build.stderr)
            for mode in ((0,4) if variant=='gold' else (0,)):
                result=run(['vvp',executable,f'+mode={mode}'],OUT/f'a2_controlled_{variant}_mode{mode}.log')
                passed=result.returncode==0 and 'PASS full_shared53' in result.stdout
                rejected=result.returncode!=0 and 'FATAL:' in result.stdout
                if not (passed if variant=='gold' else rejected):
                    raise RuntimeError(f'{variant}/{mode}: {result.stdout[-2000:]}{result.stderr}')
                observed=[]
                occupied=set()
                for line in result.stdout.splitlines():
                    if not line.startswith('OBS_FULL '):
                        continue
                    fields=line.split()
                    edge,sourceedge,bank,lane,row,tag,mask=map(int,fields[1:8])
                    if edge!=sourceedge+6+lane:
                        raise AssertionError('component latency mismatch')
                    raw=edge+6
                    if (raw,bank) in occupied:
                        raise AssertionError('raw write bank port collision')
                    occupied.add((raw,bank))
                    observed.append(dict(source_edge=sourceedge,output_edge=edge,bank=bank,lane=lane,
                                         row=row,tag=tag,mask=mask,data_hex=fields[8],
                                         analytical_raw_write=raw,analytical_commit=edge+8))
                if variant=='gold' and len(observed)!=(1060 if mode==0 else 5760):
                    raise AssertionError('wrong full32 observed count')
                records.append(dict(variant=variant,mode=mode,returncode=result.returncode,
                                    exact_pass=passed,mutant_rejected=rejected,
                                    observed_records=len(observed),records=observed,
                                    stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest()))
    proof=dict(plan,status='PASS_ISOLATED_A2_CONTROLLED_SHARED53_FULL32_512BIT_NOT_PHYSICALLY_QUALIFIED',runs=records,
               observed_scope='one common53source interface concurrently drives all32logicalbanks and four128bit slices',
               analytical_scope='rawwrite=observedoutput+6 and commit=observedoutput+8 are declared backend arithmetic, not SRAM/commit observations')
    write(OUT/'a2_controlled_pinplain_proof.json',json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(status=proof['status'],gold_records=6820,mutants_rejected=4)))


if __name__=='__main__':
    main()
