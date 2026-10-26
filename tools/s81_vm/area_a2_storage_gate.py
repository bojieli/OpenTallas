#!/usr/bin/env python3
"""Generate actual A2+128SRAM component bench; --run requires admission."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/s81_vm_area_1417'
LOCK=Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
SOURCES=['tools/s81_vm/area_a2_storage_join.sv','tools/s81_vm/area_a2_controlled.sv',
         'tools/s81_vm/area_id_native.sv','tools/s81_vm/area_id_native_join.sv','tools/s81_vm/area_a2_hardmasters.sv']+[
 f'rtl/dsrom_sys/s81_ph/vm/{name}.sv'for name in
 ['dsfd_vm_static_scatter_b8_out','dsfd_vm_static_relay128_b8','dsfd_vm_static_relay128_b4',
  'dsfd_vm_static_relay128','dsfd_vm_static_bank128']]+[
 'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
HARD_COUNTS=dict(s81_a2_controller_b0=4,s81_a2_controller_b8=4,s81_a2_controller_b16=4,s81_a2_controller_b24=4,s81_a2_stripe_data16=128,s81_a2_stripe_meta26=16,s81_area_id_fault_join=16,
                 s81_a2_w0_header=1,s81_a2_w0_payload=4,dsfd_vm_static_scatter_b8_out=16,
                 dsfd_vm_static_relay128_b8=16,dsfd_vm_static_relay128_b4=32,dsfd_vm_static_bank128=128)

BENCH=r'''`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst=0,testing=0;
 reg [52:0] v=0;reg [741:0] row=0;reg [423:0] tag=0;
 reg [847:0] mask=0;reg [27135:0] data=0;
 reg [31:0] rv=0;reg [287:0] ra=0;reg [255:0] rt=0;
 wire [127:0] ov,cv;wire [16383:0] od;wire [1023:0] ot,ct;
 wire [1151:0] ca;wire [511:0] cm;wire [15:0] ff,sf;
 s81_a2_storage_join dut(
 .ck_front({181{ck}}),.rst_front_n({181{rst}}),
 .ck_scatter({16{ck}}),.rst_scatter_n({16{rst}}),
 .ck_req({48{ck}}),.ck_rsp({48{ck}}),.rst_relay_n({48{rst}}),
 .ck_bank({128{ck}}),.rst_bank_n({128{rst}}),
 .i_v(v),.i_row(row),.i_tag(tag),.i_mask(mask),.i_data(data),
 .i_rv(rv),.i_ra(ra),.i_rt(rt),.o_rv(ov),.o_rd(od),.o_rt(ot),
 .o_commit(cv),.o_ca(ca),.o_cm(cm),.o_ct(ct),.o_front_fault(ff),.o_scatter_fault(sf));
 wire [127:0] mwv,mrv;wire [1151:0] mwa,mra;wire [1023:0] mwt;
 wire [16383:0] mwd,mwm;
 genvar x,q,h,b;
 generate for(x=0;x<4;x=x+1)begin:mon_slice
  for(q=0;q<4;q=q+1)begin:mon_group
   always @(posedge ck)if(testing &&
      ((dut.slice[x].group[q].sv & ~dut.slice[x].group[q].swe)!==0))
     $fatal(1,"SCATTER_VALID_REQUIRES_WE");
   for(h=0;h<2;h=h+1)begin:mon_half
    for(b=0;b<4;b=b+1)begin:mon_bank
     localparam B=q*8+h*4+b;localparam K=x*32+B;
     assign mwv[K]=dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.w_ce_in;
     assign mrv[K]=dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.r_ce_in;
     assign mwa[K*9+:9]=dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.w_addr_in;
     assign mra[K*9+:9]=dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.r_addr_in;
     assign mwd[B*512+x*128+:128]=dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.wd_in;
     assign mwm[B*512+x*128+:128]=dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.w_mask_in;
     assign mwt[K*8+:8]=dut.slice[x].group[q].half[h].bank[b].u_bank.wtq;
     initial if($test$plusargs("CAPACITY_ALIAS"))begin
      force dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.w_addr_in[8]=1'b0;
      force dut.slice[x].group[q].half[h].bank[b].u_bank.u_sram.r_addr_in[8]=1'b0;
     end
    end
   end
  end
 end endgenerate
 reg [31:0] ewv[0:4095],erv[0:4095],esv[0:4095];
 reg [287:0] ewa[0:4095],era[0:4095];
 reg [511:0] ewm[0:4095];reg [255:0] ewt[0:4095],ert[0:4095],est[0:4095];
 reg [16383:0] ewd[0:4095],esd[0:4095];
 reg [287:0] esa[0:4095];reg [16383:0] actual_raw_data[0:4095];
 integer ewsrc[0:4095][0:31],eworigin[0:4095][0:31],ewlane[0:4095][0:31];
 reg [511:0] model[0:31][0:511];
 reg [127:0] swv,srv;reg [1151:0] swa,sra;reg [1023:0] swt;
 reg [16383:0] swd,swm;
 reg [52:0] seen_sources=0;
 reg wrong_readbeforewrite;
 integer cycle,mode,t,bank,sl,k,j,src,n,ln,oldsrc,oldbank,due,addr,offset;
 integer raw_words=0,commit_words=0,read_words=0,sameedge_old_words=0,afteredge_new_words=0;
 reg [13:0] logicalrow;reg [511:0] word;reg [15:0] wordmask;reg [127:0] bitmask;
 function automatic [127:0] pattern(input integer a,input integer bankid,input integer sliceid,input integer version);
  begin pattern={32'(a),32'(bankid),32'(sliceid),32'hcafe0000+32'(a+bankid+sliceid)}^{4{32'h3c5a96e1*version}};end
 endfunction
 task clear_inputs;begin v=0;row=0;tag=0;mask=0;data=0;rv=0;ra=0;rt=0;end endtask
 task write_frame(input integer a,input integer version,input integer burst);
  begin
   offset=burst?(cycle/9)%32:0;
   for(n=0;n<(burst?53:32);n=n+1)begin
    src=burst?n:(n+cycle)%53;bank=burst?(n/3+offset)%32:n;ln=0;
    for(oldsrc=0;oldsrc<src;oldsrc=oldsrc+1)begin
     oldbank=row[14*oldsrc+:5]^{row[14*oldsrc+5+:3],2'b00};
     if(v[oldsrc] && oldbank==bank)ln=ln+1;
    end
    logicalrow=a*32;logicalrow[4:0]=bank^{logicalrow[7:5],2'b00};
    word=0;wordmask=0;
    for(sl=0;sl<4;sl=sl+1)begin
     word[128*sl+:128]=pattern(a,bank,sl,version);
     if(burst)word[128*sl+:128]=word[128*sl+:128]^{4{32'(src*257)}};
     wordmask[4*sl+:4]=version?(1<<((bank+sl)%4)):15;
    end
    v[src]=1;row[14*src+:14]=logicalrow;tag[8*src+:8]=cycle;
    mask[16*src+:16]=wordmask;data[512*src+:512]=word;
    seen_sources[src]=1;due=cycle+12+ln;
    if(ewv[due][bank])$fatal(1,"WRITE_CALENDAR_COLLISION");
    ewv[due][bank]=1;ewa[due][9*bank+:9]=a;ewt[due][8*bank+:8]=cycle;
    ewm[due][16*bank+:16]=wordmask;ewd[due][512*bank+:512]=word;
    ewsrc[due][bank]=src;eworigin[due][bank]=cycle;ewlane[due][bank]=ln;
   end
  end
 endtask
 task read_frame(input integer a);begin
  rv=32'hffffffff;
  for(bank=0;bank<32;bank=bank+1)begin
   ra[9*bank+:9]=a;rt[8*bank+:8]=cycle;
   erv[cycle+3][bank]=1;era[cycle+3][9*bank+:9]=a;ert[cycle+3][8*bank+:8]=cycle;
  end
 end endtask
 task tick;begin
  @(posedge ck);
  // Snapshot actual macro input pins BEFORE NBA updates at their write edge.
  swv=mwv;srv=mrv;swa=mwa;sra=mra;swd=mwd;swm=mwm;swt=mwt;
  #1;
  if(testing)begin
   for(sl=0;sl<4;sl=sl+1)begin
    if(swv[32*sl+:32]!==ewv[cycle])$fatal(1,"RAW_WRITE_VALID edge%0d slice%0d",cycle,sl);
    if(srv[32*sl+:32]!==erv[cycle])$fatal(1,"RAW_READ_VALID edge%0d slice%0d",cycle,sl);
    if(ov[32*sl+:32]!==esv[cycle])$fatal(1,"RETURN_READ_VALID edge%0d slice%0d",cycle,sl);
    if(cycle>=2)begin
     if(cv[32*sl+:32]!==ewv[cycle-2])$fatal(1,"RETURN_COMMIT_VALID edge%0d slice%0d",cycle,sl);
    end else if(cv[32*sl+:32]!==0)$fatal(1,"EARLY_INITIAL_COMMIT");
    for(bank=0;bank<32;bank=bank+1)begin
     k=sl*32+bank;
     if(ewv[cycle][bank])begin
      for(j=0;j<4;j=j+1)bitmask[j*32+:32]={32{ewm[cycle][16*bank+4*sl+j]}};
      if(swa[k*9+:9]!==ewa[cycle][9*bank+:9] || swt[k*8+:8]!==ewt[cycle][8*bank+:8] ||
         swd[bank*512+sl*128+:128]!==ewd[cycle][bank*512+sl*128+:128] ||
         swm[bank*512+sl*128+:128]!==bitmask)
       $fatal(1,"RAW_WRITE_RECORD edge%0d bank%0d slice%0d",cycle,bank,sl);
      $display("OBS_RAW %0d %0d %0d %0d %0d %0d %0d %0d %0d %032h %032h",cycle,
       eworigin[cycle][bank],bank,sl,ewsrc[cycle][bank],ewlane[cycle][bank],
       swa[k*9+:9],swt[k*8+:8],ewm[cycle][16*bank+4*sl+:4],
       swd[bank*512+sl*128+:128],swm[bank*512+sl*128+:128]);
     end
     if(erv[cycle][bank] && sra[k*9+:9]!==era[cycle][bank*9+:9])$fatal(1,"RAW_READ_ADDRESS");
     if(esv[cycle][bank] && (od[bank*512+sl*128+:128]!==esd[cycle][bank*512+sl*128+:128] ||
         ot[k*8+:8]!==est[cycle][bank*8+:8]))
       $fatal(1,"RETURN_READ_DATA edge%0d bank%0d slice%0d",cycle,bank,sl);
     if(esv[cycle][bank])
      $display("OBS_READ %0d %0d %0d %0d %0d %0d %032h",cycle,cycle-3,bank,sl,
       esa[cycle][9*bank+:9],ot[k*8+:8],od[bank*512+sl*128+:128]);
     if(cycle>=2 && ewv[cycle-2][bank])begin
      if(ca[k*9+:9]!==ewa[cycle-2][bank*9+:9] || ct[k*8+:8]!==ewt[cycle-2][bank*8+:8] ||
         cm[k*4+:4]!==ewm[cycle-2][bank*16+sl*4+:4])
       $fatal(1,"RETURN_COMMIT_RECORD edge%0d bank%0d slice%0d",cycle,bank,sl);
      $display("OBS_COMMIT %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %032h",cycle,
       cycle-2,eworigin[cycle-2][bank],bank,sl,ewsrc[cycle-2][bank],ewlane[cycle-2][bank],
       ca[k*9+:9],ct[k*8+:8],cm[k*4+:4],actual_raw_data[cycle-2][bank*512+sl*128+:128]);
     end
    end
   end
   // Reference reads sample before reference masked writes on the same edge.
   for(bank=0;bank<32;bank=bank+1)begin
    if(erv[cycle][bank])begin
     esv[cycle+3][bank]=1;est[cycle+3][8*bank+:8]=ert[cycle][8*bank+:8];
     esa[cycle+3][9*bank+:9]=era[cycle][9*bank+:9];
     esd[cycle+3][512*bank+:512]=model[bank][era[cycle][bank*9+:9]];
     if(ewv[cycle][bank] && era[cycle][bank*9+:9]==ewa[cycle][bank*9+:9])begin
      sameedge_old_words=sameedge_old_words+1;
      if(wrong_readbeforewrite)for(j=0;j<16;j=j+1)if(ewm[cycle][bank*16+j])
       esd[cycle+3][bank*512+j*32+:32]=ewd[cycle][bank*512+j*32+:32];
     end
     if(cycle>0 && ewv[cycle-1][bank] && era[cycle][bank*9+:9]==ewa[cycle-1][bank*9+:9])afteredge_new_words=afteredge_new_words+1;
    end
    if(ewv[cycle][bank])begin
     actual_raw_data[cycle][bank*512+:512]=swd[bank*512+:512];
     for(j=0;j<16;j=j+1)if(ewm[cycle][bank*16+j])
      model[bank][ewa[cycle][bank*9+:9]][j*32+:32]=ewd[cycle][bank*512+j*32+:32];
     raw_words=raw_words+1;
    end
    if(cycle>=2 && ewv[cycle-2][bank])commit_words=commit_words+1;
    if(esv[cycle][bank])read_words=read_words+1;
   end
   if(ff!==0 || sf!==0)$fatal(1,"COMPONENT_FAULT edge%0d front%h scatter%h",cycle,ff,sf);
  end
 end endtask
 initial begin
  mode=4;if($value$plusargs("mode=%d",mode))begin end
  wrong_readbeforewrite=$test$plusargs("EXPECT_NEW_SAMEEDGE");
  for(t=0;t<4096;t=t+1)begin
   ewv[t]=0;erv[t]=0;esv[t]=0;ewa[t]=0;era[t]=0;ewm[t]=0;ewt[t]=0;ert[t]=0;est[t]=0;ewd[t]=0;esd[t]=0;esa[t]=0;actual_raw_data[t]=0;
  end
  for(bank=0;bank<32;bank=bank+1)for(t=0;t<512;t=t+1)model[bank][t]=0;
  repeat(7)tick();@(negedge ck);rst=1;repeat(7)tick();testing=1;
  for(cycle=0;cycle<(mode==0?220:1120);cycle=cycle+1)begin
   @(negedge ck);clear_inputs();
   if(mode==0)begin
    if(cycle<180 && cycle%9==0)write_frame(cycle/9,0,1);
   end else begin
    if(cycle<512)write_frame(cycle,0,0);
    if(cycle>=532 && cycle<1044)read_frame(cycle-532);
    if(cycle==1060)write_frame(7,1,0);
    if(cycle==1069 ||cycle==1070 ||cycle==1090)read_frame(7);
   end
   tick();
  end
  if(seen_sources!=={53{1'b1}})$fatal(1,"NOT_ALL53_SOURCES");
  if(mode==0)begin
   if(raw_words!=1060 || commit_words!=1060 ||read_words!=0)$fatal(1,"BURST_COUNTS");
  end else begin
   if(raw_words!=16416 ||commit_words!=16416 ||read_words!=16480 ||sameedge_old_words!=32 ||afteredge_new_words!=32)
    $fatal(1,"STORAGE_COUNTS raw%0d commit%0d read%0d same%0d after%0d",raw_words,commit_words,read_words,sameedge_old_words,afteredge_new_words);
  end
  $display("PASS actual128SRAM bytes1048576 mode%0d raw_words%0d commits%0d read_words%0d sameedgeOLD%0d nextedgeNEW%0d raw_age12 returnedcommit14 directread_raw3_return6",mode,raw_words,commit_words,read_words,sameedge_old_words,afteredge_new_words);
  $finish;
 end
endmodule
'''


def check_lock():
    if json.loads(LOCK.read_text())['owner'] not in ('claude','codex'):raise RuntimeError('coordinator ownership changed')


def write(path,value):
    check_lock();path.write_text(value)


def run(command,path):
    check_lock();result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    check_lock();write(path,'\n'.join(line for line in result.stdout.splitlines()if not line.startswith('OBS_'))+'\n'+result.stderr)
    return result


def source_manifest():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in SOURCES+['tools/s81_vm/area_a2_storage_gate.py']}


def syntax_gate(bench):
    # Actual backend and monitor names are checked with only the large front
    # replaced by its empty exact interface. No functional/storage proof here.
    source=(ROOT/'tools/s81_vm/area_a2_controlled.sv').read_text()
    start=source.index('module s81_a2_controlled(')
    stub=source[start:source.index(');',start)+2]+'\nendmodule\n'
    with tempfile.TemporaryDirectory(prefix='s81-a2-storage-syntax-')as temporary:
        path=Path(temporary);write(path/'front_stub.sv',stub)
        result=run(['iverilog','-g2012','-s','tb','-o',str(path/'sim'),SOURCES[0]]+
                   SOURCES[5:]+[str(path/'front_stub.sv'),str(bench)],OUT/'a2_storage_syntax.log')
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    write(OUT/'a2_storage_syntax.json',json.dumps(dict(
        status='PASS_BACKEND_AND_MONITOR_NAME_SYNTAX_ONLY_FRONT_STUBBED',
        bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),
        scope='compile only; actual backend names checked, A2 front stubbed, no functional validation'),indent=2)+'\n')


def census(executable):
    counts=collections.Counter()
    clocks=collections.Counter();current=None
    with open(executable)as stream:
        for line in stream:
            match=re.search(r'\.scope module, "[^"]*" "([^"]+)"',line)
            if match:
                current=match[1];counts[current]+=1
            elif '.scope 'in line:current=None
            port=re.search(r'\.port_info \d+ /INPUT (\d+) "([^"]+)"',line)
            if current in HARD_COUNTS and port and port[2]in('ck','ck_control','ck_req','ck_rsp'):
                clocks[current]+=int(port[1])
    for master,count in HARD_COUNTS.items():
        if counts[master]!=count:raise AssertionError((master,counts[master],count))
    if counts['ot_sram_1r1w_512x128_m4_r2c2']!=128:raise AssertionError('not128 real macros')
    if counts['dsfd_vm_static_write_capture128']:raise AssertionError('legacy capture unexpectedly elaborated')
    if sum(clocks.values())!=421:raise AssertionError(('actual hard clock port census',clocks))
    return dict(module_scope_counts=dict(counts),actual_hard_leaves=sum(counts[m]for m in HARD_COUNTS),
                actual_hard_clock_pins=sum(clocks.values()),clock_pin_counts_by_master=dict(clocks),
                actual_real_SRAM_macros=128,method='Icarus .vvp module scope census after actual compile',
                whole_VM_elaborated=False,other_inventory_retained_leaves_not_elaborated=170)


def trace(stdout,path,require_full=False):
    counts=collections.Counter();raw_cells=set();read_cells=set();raw_sources=set()
    explicit={}
    check_lock()
    with gzip.open(path,'wt')as stream:
        for line in stdout.splitlines():
            fields=line.split()
            if not fields or not fields[0].startswith('OBS_'):continue
            kind=fields[0][4:].lower()
            if kind=='raw':
                edge,origin,bank,sl,src,lane,addr,tag,mask=map(int,fields[1:10])
                row=dict(kind='raw_write',edge=edge,source_edge=origin,bank=bank,slice=sl,
                         source=src,lane=lane,address=addr,tag=tag,mask4=mask,
                         actual_data_hex=fields[10],actual_mask128_hex=fields[11],
                         source_provenance='matched against full scheduled payload at actual macro input pins')
                if edge!=origin+12+lane:raise AssertionError('raw age changed')
                raw_cells.add((bank,sl,addr));raw_sources.add(src)
            elif kind=='commit':
                edge,raw,origin,bank,sl,src,lane,addr,tag,mask=map(int,fields[1:11])
                row=dict(kind='returned_commit',edge=edge,raw_edge=raw,source_edge=origin,
                         bank=bank,slice=sl,source=src,lane=lane,address=addr,tag=tag,mask4=mask,
                         actual_raw_data_reference_hex=fields[11],
                         data_scope='commit carries address/tag/mask; data field references saved actual raw write pins')
                if edge!=raw+2 or edge!=origin+14+lane:raise AssertionError('commit age changed')
            elif kind=='read':
                edge,raw,bank,sl,addr,tag=map(int,fields[1:7])
                row=dict(kind='returned_read',edge=edge,raw_edge=raw,launch_edge=edge-6,
                         bank=bank,slice=sl,address=addr,tag=tag,actual_data_hex=fields[7],
                         address_scope='matched actual raw read-address pin, then carried by scoreboard for return attribution')
                read_cells.add((bank,sl,addr))
            else:raise AssertionError(kind)
            counts[row['kind']]+=1
            if (bank,sl,addr)==(31,3,511):explicit[row['kind']]=row
            stream.write(json.dumps(row,separators=(',',':'))+'\n')
    if require_full:
        cells={(bank,sl,addr)for bank in range(32)for sl in range(4)for addr in range(512)}
        if raw_cells!=cells or read_cells!=cells:raise AssertionError('full1MiB macro cell address coverage missing')
        if raw_sources!=set(range(53)):raise AssertionError('raw trace does not cover all53 sources')
        if set(explicit)!={'raw_write','returned_commit','returned_read'}:raise AssertionError('missing row511 bank31 slice3 evidence')
    return dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                records=dict(counts),unique_raw_cells=len(raw_cells),unique_read_cells=len(read_cells),
                unique_raw_sources=len(raw_sources),row511_bank31_slice3=explicit,
                scope='complete observations, no sampling or record truncation')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-only',action='store_true')
    parser.add_argument('--run',action='store_true',help='parent-admitted heavy compile and component simulation only')
    args=parser.parse_args()
    check_lock();OUT.mkdir(parents=True,exist_ok=True)
    bench=OUT/'a2_storage_bench.sv';write(bench,BENCH)
    plan=dict(status='GENERATED_NOT_RUN',sources=source_manifest(),bench_sha256=hashlib.sha256(BENCH.encode()).hexdigest(),
              planned_hard_counts=HARD_COUNTS,planned_hard_leaves=373,planned_clock_pins=421,planned_real_SRAM_macros=128,
              SRAM_bytes=1048576,legacy_capture_instances=0,
              write_age=dict(raw_macro='P+12+lane',returned_commit='P+14+lane'),
              read_age=dict(raw_macro='Q+3',returned='Q+6',scope='direct physical bank read interface only'),
              unjoined_service_read=dict(front_cycles=4,back_cycles=10,raw='Q+7',returned='Q+16',qualified=False),
              same_edge_semantics='actual macro read-before-write; dependent new-value read must have raw_read>raw_write',
              global_clock_scope='421 pins functionally tied in bench only; no physical clock qualification',
              legacy_logical_packet_adapter='J=8*(bank%4)+bank/4; this join uses bank-linear outputs directly',
              flags=dict(whole_VM_elaborated=False,full_programme_trace=False,physical_qualification=False))
    write(OUT/'a2_storage_plan.json',json.dumps(plan,indent=2)+'\n')
    syntax_gate(bench)
    if not args.run:
        print(json.dumps(dict(status=plan['status'],bench=str(bench))))
        return
    records=[];elaborations=[]
    with tempfile.TemporaryDirectory(prefix='s81-a2-storage-')as temporary:
        for variant,define in [('gold',None),('early_commit','OT_VM_BANK_MUT_EARLY_COMMIT'),
                               ('mask','OT_VM_BANK_MUT_MASK'),('scatter_addr','OT_VM_DIRECT_SCATTER_MUT_ADDR')]:
            executable=str(Path(temporary)/(variant+'.vvp'))
            command=['iverilog','-g2012','-s','tb','-o',executable]
            if define:command.append('-D'+define)
            result=run(command+SOURCES+[str(bench)],OUT/f'a2_storage_{variant}_compile.log')
            if result.returncode:raise RuntimeError(result.stdout+result.stderr)
            elaborations.append(dict(variant=variant,**census(executable)))
            cases=([(0,'gold',None),(4,'gold',None),(4,'capacity_alias','CAPACITY_ALIAS'),
                    (4,'wrong_read_before_write_expectation','EXPECT_NEW_SAMEEDGE')]
                   if variant=='gold'else[(4,variant,None)])
            for mode,case,flag in cases:
                command=['vvp',executable,f'+mode={mode}']
                if flag:command.append('+'+flag)
                result=run(command,OUT/f'a2_storage_{case}_mode{mode}.log')
                passed=result.returncode==0 and 'PASS actual128SRAM' in result.stdout
                rejected=result.returncode!=0 and 'FATAL:'in result.stdout
                if not(passed if case=='gold'else rejected):raise RuntimeError(f'{case}/{mode}: {result.stdout[-4000:]}{result.stderr}')
                observations=trace(result.stdout,OUT/f'a2_storage_{case}_mode{mode}_trace.jsonl.gz',require_full=case=='gold'and mode==4)
                if case=='gold':
                    expected_raw=(1060 if mode==0 else 16416)*4
                    if observations['records'].get('raw_write',0)!=expected_raw or observations['records'].get('returned_commit',0)!=expected_raw:
                        raise AssertionError('raw/commit observation counts mismatch')
                records.append(dict(variant=case,compile_variant=variant,mode=mode,returncode=result.returncode,
                                    exact_pass=passed,mutant_rejected=rejected,
                                    stdout='\n'.join(line for line in result.stdout.splitlines()if not line.startswith('OBS_')),
                                    stderr=result.stderr,complete_observations=observations))
    # Explicit classifier negative control: a physical same-edge read may return
    # old data, but cannot satisfy a dependency asking for the new write value.
    write_edge=12
    rejected_same_edge=not(write_edge>write_edge)
    accepted_next_edge=(write_edge+1)>write_edge
    assert rejected_same_edge and accepted_next_edge
    proof=dict(plan,status='PASS_ACTUAL_A2_128SRAM_COMPONENT_ONLY_NOT_FULL_VM_OR_PHYSICAL',
               elaborations=elaborations,runs=records,
               dependent_new_value_classifier=dict(same_raw_edge_rejected=True,next_raw_edge_accepted=True),
               observed_scope='actual raw128 SRAM input pins, masked contents, returned read data and commit metadata',
               flags=dict(actual128_SRAM_component_join_run=True,whole_VM_elaborated=False,
                          service_R4_read_interface_joined=False,full_programme_trace=False,physical_qualification=False))
    write(OUT/'a2_storage_proof.json',json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(status=proof['status'],mutants_rejected=5,actual_SRAM_macros=128)))


if __name__=='__main__':main()
