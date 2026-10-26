`timescale 1ps/1fs
// H-DIE 2026-10-15: STEADY-STATE double-buffer throughput variant (EPOCHS alternating banks 0/1) of the capacity /
// all-SM mapping variant of tb_hbm_svc_sm_stack_native -- ALL eight SMs of the stack,
// ROWS records each (default 64 = the 6-bit feed row index maximum), external images from
// tools/hbm_die_v15/svc_capacity_images_1705.py (book reservations, production installer). Same actual DUT.
module tb_hbm_svc_sm_stack_steady;
 parameter integer STACK=0;
 parameter integer ROWS=64;
 parameter integer EPOCHS=8;
 parameter integer DECOUPLE=1;
 parameter integer OVERLAP=1;
 parameter integer LBANKS=4;
 localparam integer SECT=((ROWS*136+127)/128)*4;
 localparam[7:0]ACTIVE=8'hff;
 reg stream=0,hbm=0;initial forever begin #416.666 stream=1;#416.667 stream=0;end
 initial begin #173;forever #512 hbm=~hbm;end
 reg[15:0]rbank=0,sbank=0;reg[15:0]repoch=51,sepoch=51;reg[9:0]pbase=0;reg[10:0]plimit=11'(ROWS+1);real done_t[0:63];integer ndone=0;
 reg srst=0,hrst=0;reg[7:0]reserve_v=0,start_v=0,cfg_we=0,go=0;
 wire[7:0]reserve_ready,active,done,fault,pv;wire[31:0]ready;wire[15:0]cache_ready,owned;
 reg[79:0]cfg_addr=0;reg[2047:0]cfg_data=0;reg[79:0]tags=0;
 wire[31:0]kv,krdy,kwe,kdone,rv,rrdy;wire[959:0]ka;wire[127:0]kl,rb;wire[543:0]kt,rt;wire[8191:0]kw,rd;wire[1023:0]ks;
 wire[8*1099-1:0]packet;wire[8*135-1:0]programme;wire[8*1082-1:0]lt0,lt1;wire[8*570-1:0]lb0,lb1;wire[95:0]fm;wire[343:0]expected_request;
 ot_hbm_svc_sm_stack_native #(.STACK(STACK),.DECOUPLE(DECOUPLE),.OVERLAP(OVERLAP),.LBANKS(LBANKS)) dut(
 .stream_clk({8{stream}}),.stream_rst_n({8{srst}}),.hbm_clk({8{hbm}}),.hbm_rst_n({8{hrst}}),
 .stream_bank_clk({16{stream}}),.hbm_fifo_clk({16{hbm}}),.hbm_pc_clk({32{hbm}}),
 .reserve_v(reserve_v),.reserve_ready(reserve_ready),.reserve_base({8{32'(STACK<<30)}}),.reserve_row_base({8{15'd20738}}),.reserve_total({8{12'(SECT)}}),.reserve_bank(rbank),.reserve_epoch({8{repoch}}),.reserve_rows({8{7'(ROWS)}}),.reserve_tag_base(tags),
 .block_ready(ready),.cache_ready(cache_ready),.cache_owned(owned),.start_v(start_v),.start_bank(sbank),.start_epoch({8{sepoch}}),
 .program_cfg_we(cfg_we),.program_cfg_addr(cfg_addr),.program_cfg_data(cfg_data),.program_start_v(go),.program_start_base({8{pbase}}),.program_start_limit({8{plimit}}),.program_start_loops({8{16'd1}}),
 .program_active(active),.program_done(done),.fault(fault),.expected_request(expected_request),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm),.packet_observe(packet),.programme_observe(programme),.programme_v(pv),
 .clk_phy(hbm),.rst_phy_n(hrst),.pc_clk_phy({32{hbm}}),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.controller_fault(native_fault));
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire native_fault;
 // Read-only audit probes: functional K wiring lives wholly inside actual parent.
 assign kv=dut.k_v;assign krdy=dut.k_rdy;assign ka=dut.k_addr;assign kl=dut.k_len;assign kwe=dut.k_we;
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(32'h28810000),.K_MEM(65536)) dram(
 .clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 reg[1087:0]records[0:7][0:ROWS-1];reg[1087:0]load_rows[0:ROWS-1];reg[9:0]tag_base[0:7];
 integer packets[0:7],feeds[0:7],sectors[0:7];integer cycle=0;string images,path,smname;integer early,earlystart;
 real reserve_at,ready_at,cache_at,done_at;
 function automatic all_land(input [31:0] v,input integer b);
  begin all_land=1;for(integer s=0;s<8;s=s+1)if(ACTIVE[s]&&!v[4*s+b])all_land=0;end
 endfunction
 function automatic all_bank(input [15:0] v,input integer b);
  begin all_bank=1;for(integer s=0;s<8;s=s+1)if(ACTIVE[s]&&!v[2*s+b])all_bank=0;end
 endfunction
 function automatic[255:0]word(input integer pc,input integer tag,input integer bank,input integer ep,input integer addr);
  reg[134:0]x;reg[25:0]control;integer row;
  begin
   x=0;
   if(pc<ROWS)begin x[83]=1;x[84]=bank[0];x[100:85]=ep[15:0];x[106:101]=pc[5:0];x[116:107]=10'(tag+pc);end
   if(pc>0)begin
    row=pc-1;control={1'b1,1'(row==0),1'(row==ROWS-1),12'(row),1'b1,3'b0,7'b0};
    x[25:0]=control;x[29]=1;x[39:30]=10'(tag+row);
   end
   if(early!=0&&pc==0)begin x[29]=1;x[39:30]=10'(tag);end
   if(pc==ROWS)begin x[117]=1;x[118]=bank[0];x[134:119]=ep[15:0];end
   word=0;word[255:240]=16'hc7a1;word[233:224]=addr[9:0];word[134:0]=x;
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
   if(|fault)begin
    $display("SM_STACK fault sources sm0: descriptor=%0d cdc=%0d cache=%0d programme=%0d feed=%0d reserve_v=%h rbank=%h ready=%h cache_ready=%h owned=%h start_v=%h go=%h active=%h",
     dut.sm_groups.sm_group[0].u_sm.descriptor_fault,dut.sm_groups.sm_group[0].u_sm.cdc_fault,dut.sm_groups.sm_group[0].u_sm.cache_fault,
     dut.sm_groups.sm_group[0].u_sm.programme_fault,dut.sm_groups.sm_group[0].u_sm.feed_fault,reserve_v,rbank,ready,cache_ready,owned,start_v,go,active);
    $fatal(1,"SM_STACK DUT fault cycle%0d mask%h",cycle,fault);
   end
   for(integer s=0;s<8;s=s+1)if(ACTIVE[s])begin
    if(packet[s*1099+1098])begin
     if(packet[s*1099+1088+:10]!==10'(((packets[s]/ROWS)%2==0?100:300)+packets[s]%ROWS)||packet[s*1099+:1088]!==records[s][packets[s]%ROWS])$fatal(1,"SM_STACK packet mismatch sm%0d row%0d",s,packets[s]);
     packets[s]=packets[s]+1;
    end
    if(lt0[s*1082+1081])begin
     if(lt0[s*1082+:1056]!==records[s][feeds[s]%ROWS][1055:0]||lt1[s*1082+:1056]!==records[s][feeds[s]%ROWS][1055:0]||lb0[s*570+:544]!=={records[s][feeds[s]%ROWS][1087:1056],records[s][feeds[s]%ROWS][1023:512]}||lb1[s*570+:544]!=={records[s][feeds[s]%ROWS][1087:1056],records[s][feeds[s]%ROWS][1023:512]})$fatal(1,"SM_STACK actual S1 consumer mismatch sm%0d row%0d",s,feeds[s]);
     feeds[s]=feeds[s]+1;
    end
   end
  end
 end
 initial begin
  early=$test$plusargs("EARLY");earlystart=$test$plusargs("EARLYSTART");if(!$value$plusargs("IMAGES=%s",images))$fatal(1,"archive images mandatory");
  for(integer s=0;s<8;s=s+1)begin
   packets[s]=0;feeds[s]=0;sectors[s]=0;tag_base[s]=10'd100;tags[s*10+:10]=tag_base[s];
   if(ACTIVE[s])begin
    smname=$sformatf("sm%02d",s+8*STACK);path={images,"/",smname,"/backing.hex"};$readmemh(path,dram.mem);
    path={images,"/",smname,"/records.hex"};$readmemh(path,load_rows);for(integer r=0;r<ROWS;r=r+1)records[s][r]=load_rows[r];
   end
  end
  repeat(4)@(negedge stream);srst=1;repeat(3)@(negedge hbm);hrst=1;repeat(20)@(negedge stream);
  for(integer b=0;b<2;b=b+1)for(integer pc=0;pc<ROWS+1;pc=pc+1)begin
   cfg_we=ACTIVE;for(integer s=0;s<8;s=s+1)begin cfg_addr[s*10+:10]=10'(b*128+pc);cfg_data[s*256+:256]=word(pc,b==0?100:300,b,51+b,b*128+pc);end
   @(negedge stream);
  end
  cfg_we=0;repeat(4)@(negedge stream);
  fork
   // reserve: epoch e on bank e%2 as soon as the DUT admits it (landing + cache bank of that index free)
   for(integer e=0;e<EPOCHS;e=e+1)begin
    @(negedge stream);rbank={8{2'(e%LBANKS)}};repoch=16'(51+e%2);for(integer s=0;s<8;s=s+1)tags[s*10+:10]=10'(e%2==0?100:300);
    #1;while((reserve_ready&ACTIVE)!=ACTIVE)begin @(negedge stream);#1;end
    reserve_v=ACTIVE;if(e==0)reserve_at=$realtime;$display("SM_STACK_STEADY t=%0t reserve e=%0d",$realtime,e);@(negedge stream);reserve_v=0;
   end
   // start: copy block e into cache bank e%2 when its landing block is resident
   for(integer e=0;e<EPOCHS;e=e+1)begin
    @(negedge stream);
    while(!all_land(ready,e%LBANKS)||(!earlystart&&!all_bank(~owned,e%2)))@(negedge stream);
    sbank={8{2'(e%LBANKS)}};sepoch=16'(51+e%2);start_v=ACTIVE;$display("SM_STACK_STEADY t=%0t start e=%0d",$realtime,e);@(negedge stream);start_v=0;
    if(e==0)ready_at=$realtime;
   end
   // programme: run epoch e's programme (base 128*(e%2)) once its cache bank is ready, back to back
   for(integer e=0;e<EPOCHS;e=e+1)begin
    @(negedge stream);
    while(!all_bank(cache_ready,e%2))@(negedge stream);
    if(e==0)cache_at=$realtime;
    if(earlystart)repeat(300)@(negedge stream); // mutant: programme late, start ignores cache ownership
    pbase=10'(128*(e%2));plimit=11'(128*(e%2)+ROWS+1);go=ACTIVE;$display("SM_STACK_STEADY t=%0t go e=%0d",$realtime,e);@(negedge stream);go=0;wait((done&ACTIVE)==ACTIVE);done_t[e]=$realtime;ndone=ndone+1;
   end
  join
  repeat(6)@(negedge stream);
  for(integer s=0;s<8;s=s+1)if(ACTIVE[s])begin
   if(packets[s]!=ROWS*EPOCHS||feeds[s]!=ROWS*EPOCHS||sectors[s]!=SECT*EPOCHS)$fatal(1,"SM_STACK counts sm%0d packets%0d feeds%0d sectors%0d",s,packets[s],feeds[s],sectors[s]);
  end
  $display("SM_STACK_STEADY PASS lbanks=%0d decouple=%0d overlap=%0d stack=%0d active=%h rows=%0d epochs=%0d first_done_ps=%0f last_done_ps=%0f steady_epoch_ps=%0f bytes_per_epoch_per_SM=%0d",LBANKS,DECOUPLE,OVERLAP,STACK,ACTIVE,ROWS,EPOCHS,done_t[0]-reserve_at,done_t[EPOCHS-1]-reserve_at,(done_t[EPOCHS-1]-done_t[1])/(EPOCHS-2),ROWS*136);
  for(integer e=0;e<EPOCHS;e=e+1)$display("SM_STACK_STEADY epoch=%0d done_ps=%0f",e,done_t[e]-reserve_at);
  $finish;
 end
 initial begin #300000000;$fatal(1,"SM_STACK timeout");end
endmodule
