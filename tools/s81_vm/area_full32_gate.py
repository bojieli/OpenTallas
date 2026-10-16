#!/usr/bin/env python3
"""Generate full shared53/32bank/512bit native witness; --run needs admission."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/arch/s81_vm_area_1417'
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
SOURCES = ['tools/s81_vm/area_id_native.sv', 'tools/s81_vm/area_id_native_join.sv',
           'tools/s81_vm/area_full32_gate.py']

BENCH = r'''`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;
 reg [52:0] v=0;reg [741:0] row=0;reg [105:0] lane=0;
 reg [847:0] mask=0;reg [423:0] tag=0;reg [27135:0] data=0;
 reg [31:0] dv=0;reg [63:0] ds=0;
 wire [127:0] ov;wire [1791:0] ore;wire [1023:0] ot;
 wire [511:0] om;wire [16383:0] od;wire [15:0] fault;
 genvar q,x,s,b;
 generate for(q=0;q<4;q=q+1)begin:bankquarter
  for(x=0;x<4;x=x+1)begin:slice
   wire [6783:0] di;wire [211:0] mi;
   wire [7:0] vo;wire [111:0] ro;wire [31:0] mo;
   wire [63:0] to;wire [1023:0] dout;
   for(s=0;s<53;s=s+1)begin:source
    assign di[128*s+:128]=data[512*s+128*x+:128];
    assign mi[4*s+:4]=mask[16*s+4*x+:4];
   end
   s81_area_id_native_quarter #(.BASE(q*8)) dut(
    .ck_sel(ck),.ck_meta(ck),.ck_data({8{ck}}),.ck_fault(ck),
    .rst_sel_n(rst),.rst_meta_n(rst),.rst_data_n({8{rst}}),.rst_fault_n(rst),
    .i_v(v),.i_row(row),.i_lane(lane),.i_mask(mi),.i_tag(tag),.i_data(di),
    .i_drain_v(dv[q*8+:8]),.i_drain_slot(ds[q*16+:16]),
    .o_v(vo),.o_row(ro),.o_mask(mo),.o_tag(to),.o_data(dout),.fault(fault[q*4+x]));
   for(b=0;b<8;b=b+1)begin:bank
    assign ov[x*32+q*8+b]=vo[b];
    assign ore[(x*32+q*8+b)*14+:14]=ro[b*14+:14];
    assign ot[(x*32+q*8+b)*8+:8]=to[b*8+:8];
    assign om[(q*8+b)*16+x*4+:4]=mo[b*4+:4];
    assign od[(q*8+b)*512+x*128+:128]=dout[b*128+:128];
   end
  end
 end endgenerate
 reg [31:0] ev[0:511],drainv[0:511];
 reg [63:0] drains[0:511];
 reg [447:0] er[0:511];reg [511:0] em[0:511];
 reg [255:0] et[0:511];reg [16383:0] ed[0:511];
 integer sourcecycle[0:511][0:31];integer sourcelane[0:511][0:31];
 integer cycle,src,bank,ln,t,n,sl,mode,checked=0,active=0;
 reg [13:0] r;reg [127:0] word;reg [511:0] fullword;reg [15:0] fullmask;
 task tick;begin @(posedge ck);#1;end endtask
 initial begin
  mode=0;if($value$plusargs("mode=%d",mode))begin end
  if(mode!=0 && mode!=4)$fatal(1,"unsupported mode");
  for(t=0;t<512;t=t+1)begin
   ev[t]=0;er[t]=0;em[t]=0;et[t]=0;ed[t]=0;drainv[t]=0;drains[t]=0;
  end
  repeat(7)tick();@(negedge ck);rst=1;repeat(7)tick();
  for(cycle=0;cycle<220;cycle=cycle+1)begin
   @(negedge ck);v=0;row=0;mask=0;tag=0;data=0;lane=0;
   if(cycle<180 && (cycle%9==0 ||mode==4))begin
    for(n=0;n<(mode==4?32:53);n=n+1)begin
     src=mode==4?(n+cycle)%53:n;
     bank=mode==4?n:(n/3+cycle/9)%32;ln=mode==4?0:n%3;
     r=((cycle/9)%16)*32+bank;
     r[4:0]=bank^{r[7:5],2'b00};
     fullword=0;fullmask=0;
     for(sl=0;sl<4;sl=sl+1)begin
      word={32'(src),32'(cycle),32'(sl),32'hcafe0000+32'(src+sl*256)};
      fullword[sl*128+:128]=word;
      fullmask[sl*4+:4]=((src+sl)%15)+1;
     end
     v[src]=1;row[14*src+:14]=r;lane[2*src+:2]=ln;
     mask[16*src+:16]=fullmask;tag[8*src+:8]=cycle+src;
     data[512*src+:512]=fullword;
     t=cycle+5+ln;
     ev[t][bank]=1;er[t][14*bank+:14]=r;em[t][16*bank+:16]=fullmask;
     et[t][8*bank+:8]=cycle+src;ed[t][512*bank+:512]=fullword;
     sourcecycle[t][bank]=cycle;sourcelane[t][bank]=ln;
     if(drainv[cycle+4+ln][bank])$fatal(1,"drain calendar collision");
     drainv[cycle+4+ln][bank]=1;drains[cycle+4+ln][2*bank+:2]=ln;
     active=active+1;
    end
   end
   dv=drainv[cycle];ds=drains[cycle];
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
  $display("PASS full_shared53 banks32 width512 quarters16 roots176 mode%0d records%0d first_age5 II1",mode,checked);
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-only', action='store_true')
    parser.add_argument('--run', action='store_true', help='build/run only inside parent-admitted resource job')
    args = parser.parse_args()
    check_lock()
    OUT.mkdir(parents=True, exist_ok=True)
    bench = OUT / 'full32_bench.sv'
    write(bench, BENCH)
    plan = dict(status='GENERATED_NOT_RUN', source_sha256={name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES},
                bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),
                topology=dict(shared_global_sources=53, logical_banks=32, output_width=512,
                              native_quarters=16, real_fault_join_per_quarter=True, independent_clock_roots=176),
                clock_scope='all176 clock/reset pins tied only in functional bench',
                expected_records=dict(mode0_all_three_lanes=1060, mode4_sustained_II1=5760),
                flags=dict(actual_SRAM_read_join_run=False, native_physical_qualified=False,
                           full_programme_trace=False, full_token_claim=False))
    write(OUT/'full32_plan.json', json.dumps(plan, indent=2)+'\n')
    if not args.run:
        print(json.dumps(dict(status='GENERATED_NOT_RUN', bench=str(bench))))
        return
    records=[]
    with tempfile.TemporaryDirectory(prefix='s81-full32-') as temporary:
        for variant, define in [('gold', None), ('selector', 'S81_AREA_MUT_SELECTOR'), ('data', 'S81_AREA_MUT_DATA')]:
            executable=str(Path(temporary)/(variant+'.vvp'))
            command=['iverilog','-g2012','-s','tb','-o',executable]
            if define:
                command.append('-D'+define)
            build=run(command+SOURCES[:2]+[str(bench)],OUT/f'full32_{variant}_compile.log')
            if build.returncode:
                raise RuntimeError(build.stdout+build.stderr)
            for mode in ((0,4) if variant=='gold' else (0,)):
                result=run(['vvp',executable,f'+mode={mode}'],OUT/f'full32_{variant}_mode{mode}.log')
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
                    if edge!=sourceedge+5+lane:
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
    proof=dict(plan,status='PASS_ISOLATED_SHARED53_FULL32_512BIT_NATIVE_RTL_NOT_PHYSICALLY_QUALIFIED',runs=records,
               observed_scope='one common53source interface concurrently drives all32logicalbanks and four128bit slices',
               analytical_scope='rawwrite=observedoutput+6 and commit=observedoutput+8 are declared backend arithmetic, not SRAM/commit observations')
    write(OUT/'full32_proof.json',json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(status=proof['status'],gold_records=6820,mutants_rejected=2)))


if __name__=='__main__':
    main()
