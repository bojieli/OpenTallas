`timescale 1ps/1fs
module tb_hbm_svc_sm_stack_native;
 parameter integer STACK=0;
 localparam[7:0]ACTIVE=STACK==0?8'hff:8'h1f;
 reg stream=0,hbm=0;initial forever begin #416.666 stream=1;#416.667 stream=0;end
 initial begin #173;forever #512 hbm=~hbm;end
 reg srst=0,hrst=0;reg[7:0]reserve_v=0,start_v=0,cfg_we=0,go=0;
 wire[7:0]reserve_ready,active,done,fault,pv;wire[15:0]ready,cache_ready,owned;
 reg[79:0]cfg_addr=0;reg[2047:0]cfg_data=0;reg[79:0]tags=0;
 wire[31:0]kv,krdy,kwe,kdone,rv,rrdy;wire[959:0]ka;wire[127:0]kl,rb;wire[543:0]kt,rt;wire[8191:0]kw,rd;wire[1023:0]ks;
 wire[8*1099-1:0]packet;wire[8*135-1:0]programme;wire[8*1082-1:0]lt0,lt1;wire[8*570-1:0]lb0,lb1;wire[95:0]fm;wire[343:0]expected_request;
 ot_hbm_svc_sm_stack_native #(.STACK(STACK)) dut(
 .stream_clk({8{stream}}),.stream_rst_n({8{srst}}),.hbm_clk({8{hbm}}),.hbm_rst_n({8{hrst}}),
 .stream_bank_clk({16{stream}}),.hbm_fifo_clk({16{hbm}}),.hbm_pc_clk({32{hbm}}),
 .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base({8{32'(STACK<<30)}}),.reserve_row_base({8{15'd20738}}),.reserve_total({8{12'd172}}),.reserve_bank(8'd0),.reserve_epoch({8{16'd51}}),.reserve_rows({8{7'd40}}),.reserve_tag_base(tags),
 .block_ready(ready),.cache_ready(cache_ready),.cache_owned(owned),.start_v(start_v),.start_bank(8'd0),.start_epoch({8{16'd51}}),
 .program_cfg_we(cfg_we),.program_cfg_addr(cfg_addr),.program_cfg_data(cfg_data),.program_start_v(go),.program_start_base(80'd0),.program_start_limit({8{11'd41}}),.program_start_loops({8{16'd1}}),
 .program_active(active),.program_done(done),.fault(fault),.expected_request(expected_request),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm),.packet_observe(packet),.programme_observe(programme),.programme_v(pv),
 .clk_phy(hbm),.rst_phy_n(hrst),.pc_clk_phy({32{hbm}}),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.controller_fault(native_fault));
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire native_fault;
 // Read-only audit probes: functional K wiring lives wholly inside actual parent.
 assign kv=dut.k_v;assign krdy=dut.k_rdy;assign ka=dut.k_addr;assign kl=dut.k_len;assign kwe=dut.k_we;
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(32'h28810000),.K_MEM(65536)) dram(
 .clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 reg[1087:0]records[0:7][0:39];reg[1087:0]load_rows[0:39];reg[9:0]tag_base[0:7];
 integer packets[0:7],feeds[0:7],sectors[0:7];integer cycle=0;string images,path,smname;integer early;
 real reserve_at,ready_at,cache_at,done_at;
 function automatic[255:0]word(input integer pc,input integer tag);
  reg[134:0]x;reg[25:0]control;integer row;
  begin
   x=0;
   if(pc<40)begin x[83]=1;x[84]=0;x[100:85]=51;x[106:101]=pc;x[116:107]=tag+pc;end
   if(pc>0)begin
    row=pc-1;control={1'b1,1'(row==0),1'(row==39),12'(row),1'b1,3'b0,7'b0};
    x[25:0]=control;x[29]=1;x[39:30]=tag+row;
   end
   if(early!=0&&pc==0)begin x[29]=1;x[39:30]=tag;end
   if(pc==40)begin x[117]=1;x[118]=0;x[134:119]=51;end
   word=0;word[255:240]=16'hc7a1;word[233:224]=pc;word[134:0]=x;
  end
 endfunction
 always @(posedge hbm)if(hrst)begin
  if(native_fault)$fatal(1,"SM_STACK PHY aperture");
  for(integer p=0;p<32;p=p+1)if(kv[p]&&krdy[p])begin
   if((((ka[p*30+:30]>>2)^(ka[p*30+:30]>>7)^(ka[p*30+:30]>>12))&31)!=p)$fatal(1,"SM_STACK actualPC mapping");
   sectors[p/4]=sectors[p/4]+kl[p*4+:4];
  end
 end
 always @(posedge stream)begin
  cycle=cycle+1;#2;
  if(srst&&hrst)begin
   if(|fault)$fatal(1,"SM_STACK DUT fault cycle%0d mask%h",cycle,fault);
   for(integer s=0;s<8;s=s+1)if(ACTIVE[s])begin
    if(packet[s*1099+1098])begin
     if(packet[s*1099+1088+:10]!==10'(tag_base[s]+packets[s])||packet[s*1099+:1088]!==records[s][packets[s]])$fatal(1,"SM_STACK packet mismatch sm%0d row%0d",s,packets[s]);
     packets[s]=packets[s]+1;
    end
    if(lt0[s*1082+1081])begin
     if(lt0[s*1082+:1056]!==records[s][feeds[s]][1055:0]||lt1[s*1082+:1056]!==records[s][feeds[s]][1055:0]||lb0[s*570+:544]!=={records[s][feeds[s]][1087:1056],records[s][feeds[s]][1023:512]}||lb1[s*570+:544]!=={records[s][feeds[s]][1087:1056],records[s][feeds[s]][1023:512]})$fatal(1,"SM_STACK actual S1 consumer mismatch sm%0d row%0d",s,feeds[s]);
     feeds[s]=feeds[s]+1;
    end
   end
  end
 end
 initial begin
  early=$test$plusargs("EARLY");if(!$value$plusargs("IMAGES=%s",images))$fatal(1,"archive images mandatory");
  for(integer s=0;s<8;s=s+1)begin
   packets[s]=0;feeds[s]=0;sectors[s]=0;tag_base[s]=10'd1000;tags[s*10+:10]=tag_base[s];
   if(ACTIVE[s])begin
    smname=$sformatf("sm%02d",s+8*STACK);path={images,"/",smname,"/backing.hex"};$readmemh(path,dram.mem);
    path={images,"/",smname,"/records.hex"};$readmemh(path,load_rows);for(integer r=0;r<40;r=r+1)records[s][r]=load_rows[r];
   end
  end
  repeat(4)@(negedge stream);srst=1;repeat(3)@(negedge hbm);hrst=1;repeat(20)@(negedge stream);
  for(integer pc=0;pc<41;pc=pc+1)begin
   cfg_we=ACTIVE;for(integer s=0;s<8;s=s+1)begin cfg_addr[s*10+:10]=pc;cfg_data[s*256+:256]=word(pc,tag_base[s]);end
   @(negedge stream);
  end
  cfg_we=0;repeat(4)@(negedge stream);
  reserve_v=ACTIVE;#1;if((reserve_ready&ACTIVE)!=ACTIVE)$fatal(1,"SM_STACK reservation notready");reserve_at=$realtime;
  @(negedge stream);reserve_v=0;
  wait(((ready[0]&&(!ACTIVE[1]||ready[2])&&(!ACTIVE[2]||ready[4])&&(!ACTIVE[3]||ready[6])&&(!ACTIVE[4]||ready[8])&&(!ACTIVE[5]||ready[10])&&(!ACTIVE[6]||ready[12])&&(!ACTIVE[7]||ready[14]))));ready_at=$realtime;
  @(negedge stream);start_v=ACTIVE;@(negedge stream);start_v=0;
  wait(cache_ready[0]&&(!ACTIVE[1]||cache_ready[2])&&(!ACTIVE[2]||cache_ready[4])&&(!ACTIVE[3]||cache_ready[6])&&(!ACTIVE[4]||cache_ready[8])&&(!ACTIVE[5]||cache_ready[10])&&(!ACTIVE[6]||cache_ready[12])&&(!ACTIVE[7]||cache_ready[14]));cache_at=$realtime;
  @(negedge stream);go=ACTIVE;@(negedge stream);go=0;wait((done&ACTIVE)==ACTIVE);done_at=$realtime;
  repeat(6)@(negedge stream);
  for(integer s=0;s<8;s=s+1)if(ACTIVE[s])begin
   if(packets[s]!=40||feeds[s]!=40||sectors[s]!=172||owned[s*2])$fatal(1,"SM_STACK counts sm%0d packets%0d feeds%0d sectors%0d owned%0d",s,packets[s],feeds[s],sectors[s],owned[s*2]);
  end
  $display("SM_STACK_NATIVE_SOURCE_JOIN PASS stack=%0d active=%h physicalPCowners=32 nativeResponseSRAM=32 landingSRAM=64 cacheSRAM=40 programmeSRAM=8 actualrecords=%0d fixedprogramme=41 prefetch_ps=%0f copy_ps=%0f programme_ps=%0f fullnative=0 pricequalified=0",STACK,ACTIVE,STACK==0?320:200,ready_at-reserve_at,cache_at-ready_at,done_at-cache_at);$finish;
 end
 initial begin #300000000;$fatal(1,"SM_STACK timeout");end
endmodule
