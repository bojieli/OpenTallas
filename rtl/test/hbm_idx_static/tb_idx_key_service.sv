`timescale 1ps/1fs
// H-NETLIST idxcoll 2026-10-15: IDX key staging = the stack's eight HBM service groups (G-CIL-IDXKEY / G-SMVM-KEYSTAGE).
// One stack's actual service (8 ot_hbm_svc_sm_group = issuer + four-PC feed with landing / canonical-row SRAMs, 32 real
// controller leaves ot_hbm_svc_native_sector_pipeline_leaves, the DRAM fixture at the PHY row/column boundary) streams
// IDX key records (tools/hbm_die_v15/idx_key_images_2210.py: pair (beat b, port p) = row b of SM p's key region) through
// the DIE'S key_lines wiring (idx_key_wiring.svh, generated from the v16 contract edges svg_<q><p>.sm_packet ->
// hb_idx.key_lines) into the actual scorer ot_hbm_idx_score_static (4 engines, 512 hslices, metadata leaves).
// The testbench only initializes (programme + descriptor tables), pulses one run launch and plays the IDX calendar's
// beat_v / beat_index on the port-0 packet slots (the compiled key_slot); every reserve / start / go is hardware-issued.
// The SM programme gives the SM idle slots that expect the packet (command[29]=1, tag; command[25]=0): no SM issue.
// Checks: every packet of every port exact (tag (128*p + beat) % 1024, 1088-b pair == the installed record), the eight
// ports of a beat on the SAME edge (skew 0), the scorer accepts every beat (fault 0: valid + tag per port), and its
// engines emit one score beat per key beat; no SM S1 issue.
// +OLDTAG: programme/descriptor tag_base without the 128*p port term -> scorer and bench must fault.
// -DOT_KEYWIRE_MUT: ports 0 and 1 swapped in front of the die wiring (a miswired netlist) -> must fault.
// -GFIXED_GO=0: the event go of the service issuer (go when the block is resident) -> ports skew 0..20 edges -> fault.
// +EARLYGO: go slot before the HBM blocks are resident -> the issuer's missed-deadline fault.
module tb_idx_key_service;
 localparam integer STACK=0;   // SW: the wiring names below are stack 0's
 parameter integer ROWS=64;
 parameter integer EPOCHS=2;
 parameter integer LBANKS=4;
 parameter integer FIXED_GO=1;   // the die setting this binding requires (svg go on compiler slots)
 parameter integer GO0=400,GOGAP=100;   // go slots (stream edges after the run launch) of block 0 / 1
 localparam integer SECT=((ROWS*136+127)/128)*4;
 reg stream=0,hbm=0;initial forever begin #416.666 stream=1;#416.667 stream=0;end
 initial begin #173;forever #512 hbm=~hbm;end
 reg srst=0,hrst=0;reg cfg_we=0,desc_we=0,run_v=0;reg[9:0]cfg_addr[0:7];reg[255:0]cfg_data[0:7];reg[6:0]desc_addr=0;reg[255:0]desc_data[0:7];
 wire[7:0]running,run_done,active,fault;
 wire[31:0]kv,krdy,kwe,kdone,rv,rrdy;wire[959:0]ka;wire[127:0]kl,rb;wire[543:0]kt,rt;wire[8191:0]kw,rd;wire[1023:0]ks;
 wire[8*1099-1:0]packet;wire[8*83-1:0]command;wire[8*1082-1:0]lt0,lt1;wire[8*570-1:0]lb0,lb1;wire[95:0]fm;wire[343:0]expected_request;
 genvar g;
 for(g=0;g<8;g=g+1)begin:grp
  ot_hbm_svc_sm_group #(.STACK(STACK[1:0]),.SM(g),.LBANKS(LBANKS),.FIXED_GO(FIXED_GO)) u(
   .stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_bank_clk({2{stream}}),.hbm_fifo_clk({2{hbm}}),.hbm_pc_clk({4{hbm}}),
   .program_cfg_we(cfg_we),.program_cfg_addr(cfg_addr[g]),.program_cfg_data(cfg_data[g]),
   .desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data[g]),.run_v(run_v),.run_base(7'd0),.run_count(8'(EPOCHS)),
   .running(running[g]),.run_done(run_done[g]),.program_active(active[g]),.fault(fault[g]),
   .sm_packet(packet[g*1099+:1099]),.sm_command(command[g*83+:83]),.expected_request(expected_request[g*43+:43]),
   .lt0(lt0[g*1082+:1082]),.lt1(lt1[g*1082+:1082]),.lb0(lb0[g*570+:570]),.lb1(lb1[g*570+:570]),.fm(fm[g*12+:12]),
   .k_v(kv[g*4+:4]),.k_rdy(krdy[g*4+:4]),.k_addr(ka[g*120+:120]),.k_len(kl[g*16+:16]),.k_tag(kt[g*68+:68]),.k_we(kwe[g*4+:4]),
   .k_wdata(kw[g*1024+:1024]),.k_wstrb(ks[g*128+:128]),.k_wr_done(kdone[g*4+:4]),
   .kr_v(rv[g*4+:4]),.kr_rdy(rrdy[g*4+:4]),.kr_tag(rt[g*68+:68]),.kr_beat(rb[g*16+:16]),.kr_data(rd[g*1024+:1024]));
 end
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire native_fault;
 ot_hbm_svc_native_sector_pipeline_leaves controller(.clk(hbm),.rst_n(hrst),.pc_clk({32{hbm}}),
  .k_tag(kt),.k_wdata(kw),.k_addr(ka),.kr_rdy(rrdy),.k_wstrb(ks),.k_we(kwe),.k_len(kl),.k_rdy(krdy),.kr_v(rv),.kr_data(rd),.kr_beat(rb),
  .k_wr_done(kdone),.kr_tag(rt),.k_v(kv),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),
  .col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(32'h28810000),.K_MEM(65536)) dram(
  .clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 // ---------------- the die nets: svg_<SW|SE|NW|NE><p>__sm_packet and the generated hb_idx.key_lines wiring
`ifdef OT_KEYWIRE_MUT
 localparam integer SWAP=1;
`else
 localparam integer SWAP=0;
`endif
 wire[1098:0] p0=packet[(SWAP?1:0)*1099+:1099],p1=packet[(SWAP?0:1)*1099+:1099];
 wire[1098:0] p2=packet[2*1099+:1099],p3=packet[3*1099+:1099],p4=packet[4*1099+:1099],p5=packet[5*1099+:1099],p6=packet[6*1099+:1099],p7=packet[7*1099+:1099];
 // stack 0 (SW): the die net names of idx_key_wiring.svh (svg_SW<p>__sm_packet)
 wire[8791:0] key_lines;
 wire[1098:0] svg_SW0__sm_packet=p0,svg_SW1__sm_packet=p1,svg_SW2__sm_packet=p2,svg_SW3__sm_packet=p3,
  svg_SW4__sm_packet=p4,svg_SW5__sm_packet=p5,svg_SW6__sm_packet=p6,svg_SW7__sm_packet=p7;
`include "idx_key_wiring.svh"
 // ---------------- the actual scorer (stack STACK of the IDX parent), IDX calendar beats on the port-0 packet slots
 reg[7:0] bidx=0;wire beat_v=key_lines[0]&&srst;
 always @(posedge stream)if(beat_v)bidx<=bidx+8'd1;
 wire[609:0] score;wire score_fault;
 ot_hbm_idx_score_static scorer(.clk_ctl(stream),.clk_engine({4{stream}}),.clk_meta({4{stream}}),.clk_tail({4{stream}}),
  .clk_chunk({16{stream}}),.clk_hslice({512{stream}}),.rst_n(srst),.rank(7'd0),.first_ord(11'(STACK*342)),.nkeys(12'd2736),
  .keep_en(1'b0),.keep_bitmap(342'd0),.ql_v(1'b0),.ql_head(8'd0),.ql_codes(512'd0),.ql_sc(32'd0),.ql_w(16'd0),
  .beat_v(beat_v),.beat_index(bidx),.key_lines(key_lines),.score(score),.fault(score_fault));
 // ---------------- checks
 reg[1087:0]records[0:7][0:ROWS-1];reg[1087:0]load_rows[0:ROWS-1];
 integer packets[0:7];integer goat;integer cycle=0;string images,path,smname;integer oldtag,errors=0,skew_beats=0,scores=0,sm_issue=0;
 integer first_cycle[0:255];integer port_first[0:7],port_last[0:7];
 function automatic integer tagbase(input integer s,input integer b);tagbase=(oldtag!=0?0:128*s)+64*b;endfunction
 function automatic[255:0]word(input integer pc,input integer tag,input integer bank,input integer ep,input integer addr);
  reg[134:0]x;integer row;
  begin
   x=0;
   if(pc<ROWS)begin x[83]=1;x[84]=bank[0];x[100:85]=ep[15:0];x[106:101]=pc[5:0];x[116:107]=10'(tag+pc);end
   if(pc>0)begin row=pc-1;x[29]=1;x[39:30]=10'(tag+row);end      // SM idle slot that expects the key packet
   if(pc==ROWS)begin x[117]=1;x[118]=bank[0];x[134:119]=ep[15:0];end
   word=0;word[255:240]=16'hc7a1;word[233:224]=addr[9:0];word[134:0]=x;
  end
 endfunction
 function automatic[255:0]desc(input integer s,input integer e);
  reg[255:0]d;
  begin
   d=0;d[31:0]=32'(STACK<<30);d[46:32]=15'd20738;d[48:47]=2'(e%LBANKS);d[64:49]=16'(51+e%2);d[71:65]=7'(ROWS);
   d[81:72]=10'(tagbase(s,e%2));d[91:82]=10'(128*(e%2));d[102:92]=11'(128*(e%2)+ROWS+1);d[118:103]=16'd1;
   if(FIXED_GO!=0)d[142:119]=24'(goat+GOGAP*e);
   d[255:240]=16'h5d15;d[239:233]=7'(e);desc=d;
  end
 endfunction
 always @(posedge hbm)if(hrst)begin
  if(native_fault)$fatal(1,"KEY_SERVICE PHY aperture");
  for(integer p=0;p<32;p=p+1)if(kv[p]&&krdy[p])
   if((((ka[p*30+:30]>>2)^(ka[p*30+:30]>>7)^(ka[p*30+:30]>>12))&31)!=p)$fatal(1,"KEY_SERVICE actualPC mapping");
 end
 always @(posedge stream)begin
  cycle=cycle+1;#2;
  if(srst&&hrst)begin
   if(|fault)$fatal(1,"KEY_SERVICE DUT fault cycle%0d mask%h",cycle,fault);
   if(score[0])scores=scores+1;
   for(integer s=0;s<8;s=s+1)begin
    if(lt0[s*1082+1081]||lt1[s*1082+1081])sm_issue=sm_issue+1;
    if(packet[s*1099+1098])begin
     if(packets[s]==0)port_first[s]=cycle;port_last[s]=cycle;
     if(first_cycle[packets[s]]<0)first_cycle[packets[s]]=cycle;
     else if(first_cycle[packets[s]]!=cycle)skew_beats=skew_beats+1;
     if(packet[s*1099+1088+:10]!==10'((128*s+packets[s])%1024)||packet[s*1099+:1088]!==records[s][packets[s]%ROWS])begin
      errors=errors+1;if(errors<6)$display("KEY_SERVICE packet mismatch sm%0d beat%0d tag%0d",s,packets[s],packet[s*1099+1088+:10]);
     end
     // the die wiring: line s of key_lines == this SM's packet, field-permuted
     if(SWAP==0&&(key_lines[s*1099]!==1'b1||key_lines[s*1099+1+:10]!==packet[s*1099+1088+:10]||key_lines[s*1099+11+:1088]!==packet[s*1099+:1088]))begin
      errors=errors+1;if(errors<6)$display("KEY_SERVICE wiring mismatch sm%0d",s);
     end
     packets[s]=packets[s]+1;
    end
   end
  end
 end
 integer image_fd;
 initial begin
  oldtag=$test$plusargs("OLDTAG");goat=$test$plusargs("EARLYGO")?120:GO0;if(!$value$plusargs("IMAGES=%s",images))$fatal(1,"archive images mandatory");
  for(integer b=0;b<256;b=b+1)first_cycle[b]=-1;
  for(integer s=0;s<8;s=s+1)begin
   packets[s]=0;
   smname=$sformatf("sm%02d",s+8*STACK);path={images,"/",smname,"/backing.hex"};image_fd=$fopen(path,"r");if(image_fd==0)$fatal(1,"required image unavailable: %s",path);$fclose(image_fd);$readmemh(path,dram.mem);
   path={images,"/",smname,"/records.hex"};image_fd=$fopen(path,"r");if(image_fd==0)$fatal(1,"required image unavailable: %s",path);$fclose(image_fd);$readmemh(path,load_rows);for(integer r=0;r<ROWS;r=r+1)records[s][r]=load_rows[r];
  end
  repeat(4)@(negedge stream);srst=1;repeat(3)@(negedge hbm);hrst=1;repeat(20)@(negedge stream);
  for(integer b=0;b<2;b=b+1)for(integer pc=0;pc<ROWS+1;pc=pc+1)begin
   cfg_we=1;for(integer s=0;s<8;s=s+1)begin cfg_addr[s]=10'(b*128+pc);cfg_data[s]=word(pc,tagbase(s,b),b,51+b,b*128+pc);end
   @(negedge stream);
  end
  cfg_we=0;
  for(integer e=0;e<EPOCHS;e=e+1)begin desc_we=1;desc_addr=7'(e);for(integer s=0;s<8;s=s+1)desc_data[s]=desc(s,e);@(negedge stream);end
  desc_we=0;repeat(4)@(negedge stream);
  run_v=1;@(negedge stream);run_v=0;
  wait(run_done==8'hff||running==0);
  repeat(400)@(negedge stream);
  for(integer s=0;s<8;s=s+1)if(packets[s]!=ROWS*EPOCHS)begin errors=errors+1;$display("KEY_SERVICE count sm%0d packets%0d",s,packets[s]);end
  for(integer s=0;s<8;s=s+1)$display("KEY_SERVICE port%0d first_packet_cycle=%0d last_packet_cycle=%0d",s,port_first[s],port_last[s]);
  $display("KEY_SERVICE stack=%0d beats=%0d packets/port=%0d skew_beats=%0d scorer_fault=%0d score_beats=%0d sm_issue=%0d errors=%0d first_beat_cycle=%0d last_beat_cycle=%0d",
   STACK,bidx,packets[0],skew_beats,score_fault,scores,sm_issue,errors,first_cycle[0],first_cycle[ROWS*EPOCHS-1]);
  if(errors==0&&skew_beats==0&&score_fault==0&&bidx==ROWS*EPOCHS&&scores==ROWS*EPOCHS&&sm_issue==0)$display("TB_IDX_KEY_SERVICE PASS");
  else $display("TB_IDX_KEY_SERVICE FAIL");
  $finish;
 end
 initial begin #300000000;$fatal(1,"KEY_SERVICE timeout");end
endmodule
