`timescale 1ns/1ps
`default_nettype none
// Valid-schedule differential replay against exact fb9122ac6. The reference
// has only module names changed. After malformed requests, compare fault,
// read enable and output suppression; post-fault fill status is unspecified.
module tb_hbm_dma_load_fill_overlap;
 reg clk=0,rst_n=0;always #1 clk=~clk;
 reg bv=0,bb=0,start=0,sb=0,lv=0;reg[15:0]bep=0,sep=0,base=0;
 reg[61:0]cmd=0;reg[1:0]fv=0,fb=0;reg[11:0]fs=0;
 reg[31:0]fe=0;reg[511:0]fd=0;
 wire[1:0]f0,f1,pb,ft,bz,ov;wire[1:0]ready[0:1],destq[0:1];
 wire[2:0]destb[0:1];wire[280:0]raw[0:1],load[0:1];
 ot_hbm_svc_vmdel_lane_load_static #(.NPC(2)) u_candidate(.clk(clk),.rst_n(rst_n),.bank_id(3'd3),
 .begin_v_i(bv),.begin_bank_i(bb),.begin_epoch_i(bep),
 .start_i(start),.start_bank_i(sb),.start_epoch_i(sep),.start_base_sector_i(base),
 .fill_v_i(fv),.fill_bank_i(fb),.fill_slot_i(fs),.fill_epoch_i(fe),.fill_data_i(fd),
 .full0_all({8{f0[0]}}),.full1_all({8{f1[0]}}),.pcbad_all({8{pb[0]}}),
 .full0(f0[0]),.full1(f1[0]),.pcbad(pb[0]),.block_ready(ready[0]),.busy(bz[0]),.fault(ft[0]),.dq(raw[0]),
 .load_v_i(lv),.load_cmd_i(cmd),.load_dest_bank(destb[0]),.load_dest_q(destq[0]),.load_dq(load[0]),.load_out_v(ov[0]));
 baseline_ot_hbm_svc_vmdel_lane_load_static #(.NPC(2)) u_reference(.clk(clk),.rst_n(rst_n),.bank_id(3'd3),
 .begin_v_i(bv),.begin_bank_i(bb),.begin_epoch_i(bep),
 .start_i(start),.start_bank_i(sb),.start_epoch_i(sep),.start_base_sector_i(base),
 .fill_v_i(fv),.fill_bank_i(fb),.fill_slot_i(fs),.fill_epoch_i(fe),.fill_data_i(fd),
 .full0_all({8{f0[1]}}),.full1_all({8{f1[1]}}),.pcbad_all({8{pb[1]}}),
 .full0(f0[1]),.full1(f1[1]),.pcbad(pb[1]),.block_ready(ready[1]),.busy(bz[1]),.fault(ft[1]),.dq(raw[1]),
 .load_v_i(lv),.load_cmd_i(cmd),.load_dest_bank(destb[1]),.load_dest_q(destq[1]),.load_dq(load[1]),.load_out_v(ov[1]));
 function automatic[255:0]data(input integer bank,input integer epoch,input integer group_id,input integer slot);
  for(integer j=0;j<32;j=j+1)data[j*8+:8]=8'(j+17*slot+91*group_id+13*bank+epoch);
 endfunction
 function automatic[2:0]fmt(input integer k);
  case(k%6)0:fmt=0;1:fmt=1;2:fmt=2;3:fmt=4;4:fmt=5;default:fmt=6;endcase
 endfunction
 integer errors=0,nload=0,nraw=0,reads=0,compared=0;
 reg valid_mode=1;
 always @(posedge clk)begin
  if(rst_n)reads=reads+integer'(u_candidate.pc[0].u_payload.r_ce_in)+integer'(u_candidate.pc[1].u_payload.r_ce_in);
  #0.1;
  if(rst_n)begin
   if(valid_mode)begin
    compared=compared+1;
    if({f0[0],f1[0],pb[0],ft[0],bz[0],ready[0],raw[0][280],ov[0]}!==
       {f0[1],f1[1],pb[1],ft[1],bz[1],ready[1],raw[1][280],ov[1]})begin
      errors=errors+1;if(errors<5)$display("FILL_OVERLAP_STATUS_MISMATCH cycle=%0d",compared);
    end
    if(raw[0][280]&&raw[0]!==raw[1])begin errors=errors+1;$display("FILL_OVERLAP_RAW_MISMATCH");end
    if(ov[0]&&{load[0],destb[0],destq[0]}!=={load[1],destb[1],destq[1]})begin errors=errors+1;$display("FILL_OVERLAP_LOAD_MISMATCH");end
    if(ft!=0)$fatal(1,"FILL_OVERLAP valid schedule fault");
   end
   if(raw[0][280])nraw=nraw+1;
   if(ov[0])nload=nload+1;
  end
 end
 task reset_pair;
  begin
   rst_n=0;bv=0;start=0;lv=0;fv=0;repeat(8)@(negedge clk);
   rst_n=1;repeat(8)@(negedge clk);
  end
 endtask
 task begin_bank(input integer bank,input integer epoch);
  begin bb=1'(bank);bep=16'(epoch);bv=1;@(negedge clk);bv=0;repeat(4)@(negedge clk);end
 endtask
 task fill_beat(input integer bank,input integer epoch,input integer slot);
  begin fv=3;fb={2{1'(bank)}};fs={2{6'(slot)}};fe={2{16'(epoch)}};fd={data(bank,epoch,1,slot),data(bank,epoch,0,slot)};end
 endtask
 task load_beat(input integer bank,input integer epoch,input integer slot,input integer release_bank);
  begin
   lv=1;cmd=0;cmd[0]=1'(bank);cmd[16:1]=16'(epoch);cmd[18:17]=2'(slot%2);cmd[24:19]=6'(slot);
   cmd[32:30]=fmt(slot);cmd[48:33]=16'(1000+epoch*64+slot);cmd[55:52]=8;cmd[56]=1'(release_bank);cmd[59:57]=2;cmd[61:60]=3;
  end
 endtask
 integer epoch[0:1];integer phase,src,other,slot,j,oldloads,oldraw,oldreads;
 initial begin
  reset_pair();epoch[0]=20;epoch[1]=0;begin_bank(0,epoch[0]);
  for(slot=0;slot<64;slot=slot+1)begin fill_beat(0,epoch[0],slot);@(negedge clk);end
  fv=0;repeat(8)@(negedge clk);
  for(phase=0;phase<8;phase=phase+1)begin
   src=phase%2;other=1-src;epoch[other]=21+phase;
   if(!ready[0][src]||!ready[1][src])$fatal(1,"FILL_OVERLAP source not ready phase=%0d",phase);
   begin_bank(other,epoch[other]);
   if(phase%3==2)begin start=1;sb=1'(src);sep=16'(epoch[src]);base=16'(phase*256);end
   for(slot=0;slot<64;slot=slot+1)begin
    fill_beat(other,epoch[other],slot);
    if(phase%3!=2)load_beat(src,epoch[src],slot,slot==63);
    @(negedge clk);start=0;
   end
   fv=0;lv=0;repeat((phase%3==2)?90:12)@(negedge clk);
  end
  repeat(12)@(negedge clk);
  if(errors||nload!=384||nraw!=256)$fatal(1,"FILL_OVERLAP FAIL errors=%0d load=%0d raw=%0d",errors,nload,nraw);
  $display("FILL_OVERLAP_VALID PASS phases=8 banks=2 formats=6 load_packets=%0d raw_packets=%0d compared_edges=%0d",nload,nraw,compared);
  valid_mode=0;
  // Empty owned bank: same-bank fill with either malformed LOAD or raw start.
  // Both must fault, issue no SRAM read, and emit no valid output. Counter and
  // pcbad side effects after the fault deliberately need not be identical.
  for(j=0;j<2;j=j+1)begin
   reset_pair();begin_bank(0,100+j);oldloads=nload;oldraw=nraw;oldreads=reads;
   fill_beat(0,100+j,0);
   if(j==0)load_beat(0,100+j,0,0);else begin start=1;sb=0;sep=16'(100+j);base=0;end
   @(negedge clk);fv=0;lv=0;start=0;repeat(12)@(negedge clk);
   if(ft!==3||nload!=oldloads||nraw!=oldraw||reads!=oldreads)$fatal(1,"FILL_OVERLAP malformed conflict escaped kind=%0d",j);
   $display("FILL_OVERLAP_INVALID PASS kind=%0d no_reads=1 no_output=1 faults=%b pcbad_candidate=%b pcbad_reference=%b",j,ft,pb[0],pb[1]);
  end
  $display("DMA_LOAD_FILL_OVERLAP PASS");$finish;
 end
endmodule
`default_nettype wire
