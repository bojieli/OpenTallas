`timescale 1ns/1ps
module tb_indexed_scalar_f20;
 parameter MUT=0, NATIVE_BANKED=1, SEGMENTED96=1;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,start=0,preload=0,readback=0;
 reg[23:0]ix=0,base=0,limit=0,dst=0;
 wire[543:0]rq;wire[8991:0]wq;
 wire[8223:0]raw_rr,rr;wire busy,done,fault;
 reg[8991:0]dq=0;reg[543:0]verify_rq=0;
 wire[575:0]status;
 reg cfg_v=0,desc_v=0,launch_v=0;reg[11:0]cfg_addr=0;reg[12:0]desc_limit=1;reg[255:0]cfg_data=0;
 wire active,active0,active1,reservation_active,configured,pf,tf,ef,es,eb,ed;wire[15:0]edge_index;wire[119:0]descriptor;
 wire[31:0]selector_fault;
 assign fault=pf|tf|ef|(|selector_fault);
 ot_hbm_su_indexed_scalar_f20 #(.READ_SAMPLE(10),.WRITE_COMMIT(5),.NATIVE_BANKED(NATIVE_BANKED),.SEGMENTED96(SEGMENTED96),.MUT_PHASE(MUT==3))dut(
 .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(8'd180),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(12'd0),.desc_limit(desc_limit),.desc_loops(16'd1),.launch_v(launch_v),
 .rr(rr),.rq(rq),.wq(wq),.active(active),.active0(active0),.active1(active1),.reservation_active(reservation_active),.done(done),.program_fault(pf),.configured(configured),
 .target_fault(tf),.engine_fault(ef),.edge_index(edge_index),.engine_busy(eb),.engine_done(ed),
 .engine_start(es),.descriptor(descriptor));
 assign busy=active;
 for(genvar q=0;q<4;q=q+1)begin:gq
  for(genvar b=0;b<8;b=b+1)begin:gb
   localparam I=q*8+b;
   wire[16:0]brq;wire[280:0]bwq;wire[256:0]brr,nrr;wire bd;
   ot_hbm_su_indexed_scalar_bank_select select0(.clk(clk),.rst_n(rst_n),.reserve(I<16?active0:active1),
    .normal_rq(verify_rq[I*17+:17]),.normal_wq(281'd0),
    .gather_rq(rq[I*17+:17]),.gather_wq(wq[I*281+:281]),.bank_rr(brr),.bank_done(bd),
    .bank_rq(brq),.bank_wq(bwq),.normal_rr(nrr),.normal_done(),.gather_rr(rr[I*257+:257]),.fault(selector_fault[I]));
   hfd_vms_bank_native_q0_faces bank(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
    .clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.rst_n(rst_n),.bid(3'(b)),.sid(2'(q)),
    .rslot_v(1'b1),.rslot(3'd0),.wslot_v(1'b1),.wslot(preload?3'd6:3'd0),
    .rq0(brq),.rr0(brr),.rq1(17'd0),.rq2(17'd0),.rq3(17'd0),.rq4(17'd0),
    .wq0(bwq),.wq_done0(bd),.wq1(281'd0),
    .dq(dq[I*281+:281]),.dq_done(),.kq(281'd0),.kq_done(),.xq(276'd0),.xq_done(),
    .xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(status[I*18+:18]));
   assign raw_rr[I*257+:257]=nrr;
  end
 end
 task automatic launch_descriptor;
  begin
   cfg_data=0;cfg_data[255:240]=16'hc7a1;
   cfg_data[23:0]=ix^(MUT==1?24'd1:24'd0);cfg_data[47:24]=base;cfg_data[71:48]=limit;
   cfg_data[95:72]=dst^(MUT==2?24'd8:24'd0);cfg_data[119:96]=24'd1;
   cfg_data[135:120]=16'd8;cfg_data[151:136]=16'd40;
   cfg_v=1;@(negedge clk);cfg_v=0;repeat(6)@(negedge clk);
   desc_v=1;@(negedge clk);desc_v=0;
   repeat(10)@(negedge clk);
   if(!configured)$fatal(1,"F20 target failed to configure pf=%b tf=%b",pf,tf);
   launch_v=1;start_c=cyc;@(negedge clk);launch_v=0;
  end
 endtask
 integer c,i,j,errors=0,checks=0,cyc=0,start_c,first_cycles=0;
 integer sel,score,idxadr,destadr,bank;
 reg[255:0]data,expected;
 always @(posedge clk)begin
  cyc=cyc+1;
  if(c==0)begin
   if(launch_v)$display("PROFILE launch cycle=%0d",cyc);
   if(active&&edge_index==0)$display("PROFILE local_edge0 cycle=%0d",cyc);
   if(es)$display("PROFILE engine_start cycle=%0d local=%0d",cyc,edge_index);
   if(ed)$display("PROFILE engine_done_observed cycle=%0d local=%0d",cyc,edge_index);
   if(done)$display("PROFILE programme_done_observed cycle=%0d",cyc);
  end
 end
 function automatic integer bankof(input integer adr);bankof=((adr>>16)&3)*8+((adr>>3)&7);endfunction
 task automatic load_sector(input integer adr,input[255:0]payload);
  begin
   @(negedge clk);dq=0;dq[bankof(adr)*281+:281]={1'b1,16'(adr>>3),payload,8'hff};
   @(negedge clk);dq=0;repeat(12)@(negedge clk);
  end
 endtask
 reg[159:0]case_mem[0:17];reg[31:0]score_mem[0:6911];reg[255:0]row_mem[0:17];
 string fixture_dir,rows_dir;
 task automatic run_authentic_bundle;
  integer l,n,t,wordadr,otheradr;
  begin
   if(!$value$plusargs("FIXTURE=%s",fixture_dir)||!$value$plusargs("ROWS=%s",rows_dir))$fatal(1,"fixture paths required");
   $readmemh({fixture_dir,"/cases.mem"},case_mem);$readmemh({fixture_dir,"/scores.mem"},score_mem);
   $readmemh({rows_dir,"/L0_6rows.mem"},row_mem,0,5);$readmemh({rows_dir,"/L2_6rows.mem"},row_mem,6,11);
   $readmemh({rows_dir,"/L14_6rows.mem"},row_mem,12,17);
   for(l=0;l<3;l=l+1)begin
    c=l==0?0:1;preload=1;verify_rq=0;
    base=row_mem[l*6][47:24];
    for(n=0;n<48;n=n+1)begin
     for(t=0;t<8;t=t+1)data[t*32+:32]=score_mem[l*6*384+n*8+t];
     wordadr=n<12?int'(base)+n*8:n<24?int'(row_mem[l*6][175:152])+(n-12)*8:n<36?int'(row_mem[l*6][199:176])+(n-24)*8:int'(row_mem[l*6][223:200])+(n-36)*8;
     load_sector(wordadr,data);
    end
    for(n=0;n<6;n=n+1)begin
     wordadr=row_mem[l*6+n][23:0];data={8{32'hdeadbeef}};
     for(t=0;t<6;t=t+1)begin
      otheradr=row_mem[l*6+t][23:0];
      if(otheradr/8==wordadr/8)data[(otheradr%8)*32+:32]=case_mem[l*6+t][63:32];
     end
     load_sector(wordadr,data);
     load_sector(case_mem[l*6+n][87:64],{8{32'h6f55aa33}});
    end
    preload=0;repeat(12)@(negedge clk);
    for(n=0;n<6;n=n+1)begin
     cfg_addr=12'(n);cfg_data=row_mem[l*6+n];
     if(MUT==1)cfg_data[23:0]=cfg_data[23:0]^24'd1;
     if(MUT==2)cfg_data[95:72]=cfg_data[95:72]^24'd8;
     cfg_v=1;@(negedge clk);cfg_v=0;@(negedge clk);
    end
    repeat(6)@(negedge clk);desc_limit=6;desc_v=1;@(negedge clk);desc_v=0;
    repeat(16)@(negedge clk);
    if(!configured)$fatal(1,"F20 six-row configuration failed");
    launch_v=1;start_c=cyc;@(negedge clk);launch_v=0;
    wait(done);@(negedge clk);
    $display("BUNDLE layer_group=%0d programme_cycles=%0d target=180 rows=6",l,cyc-start_c);
    repeat(12)@(negedge clk);
    for(n=0;n<6;n=n+1)begin
     wordadr=case_mem[l*6+n][87:64];bank=bankof(wordadr);verify_rq=0;
     verify_rq[bank*17+:17]={1'b1,16'(wordadr>>3)};@(negedge clk);verify_rq=0;repeat(7)@(negedge clk);
     expected={8{32'h6f55aa33}};
     for(t=0;t<6;t=t+1)begin
      otheradr=case_mem[l*6+t][87:64];
      if(otheradr/8==wordadr/8)expected[(otheradr%8)*32+:32]=case_mem[l*6+t][31:0];
     end
     checks=checks+8;
     if(raw_rr[bank*257+256]!==1 || raw_rr[bank*257+:256]!==expected)begin
      errors=errors+1;$display("AUTHENTIC MISMATCH layer=%0d scalar=%0d",l,n);
     end
     repeat(8)@(negedge clk);
    end
    if(fault!==0||status!==0)begin errors=errors+1;$display("AUTHENTIC FAULT engine=%b banks=%h",fault,status);end
   end
   if(errors)$fatal(1,"GATHER_F20_CURRENT FAIL authentic18 checks=%0d errors=%0d",checks,errors);
   $display("GATHER_F20_CURRENT PASS authentic_cases=18 masked_word_checks=%0d bundles=3 rows_per_bundle=6 banks=32 SRAMs=96 R=10 W=5 segmented96=1",checks);$finish;
  end
 endtask
 initial begin
  repeat(8)@(negedge clk);rst_n=1;preload=1;repeat(12)@(negedge clk);
  if($test$plusargs("FIXTURE"))run_authentic_bundle;
  // Six canonical scalar routes plus32 structural routes spanning all SID/bank.
  for(c=0;c<38;c=c+1)begin
   if(c<6)begin
    base=87360;limit=87744;idxadr=88512+c;destadr=88576+c;
    case(c)0:sel=7;1:sel=1;2:sel=383;3:sel=64;4:sel=128;default:sel=3;endcase
   end else begin
    base=0;limit=262144;sel=((c-6)/8)*65536+((c-6)%8)*8+2;
    idxadr=90000+c;destadr=120000+c;
   end
   score=base+sel;ix=idxadr;dst=destadr;
   // Score sectors have distinct perword values; golden derives from score
   // address independently of the engine's read result.
   for(j=0;j<8;j=j+1)data[j*32+:32]=32'h3e800000+32'((score/8)*8+j);
   load_sector(score,data);
   data={8{32'hdeadbeef}};data[(idxadr%8)*32+:32]=32'(sel);load_sector(idxadr,data);
   expected={8{32'h6f55aa33}};load_sector(destadr,expected);
   preload=0;repeat(10)@(negedge clk);
   launch_descriptor;
   wait(done);@(negedge clk);
   if(c==0)first_cycles=cyc-start_c;
   if(cyc-start_c!=first_cycles)begin errors=errors+1;$display("variable schedule");end
   repeat(12)@(negedge clk);readback=1;verify_rq=0;
   bank=bankof(destadr);verify_rq[bank*17+:17]={1'b1,16'(destadr>>3)};
   @(negedge clk);verify_rq=0;
   repeat(7)@(negedge clk);
   expected[(destadr%8)*32+:32]=32'h3e800000+32'(score);
   checks=checks+8;
   if(raw_rr[bank*257+256]!==1'b1||raw_rr[bank*257+:256]!==expected)begin
    if(errors<4)$display("ERR case%0d score%0d valid%b got%h expected%h",c,score,raw_rr[bank*257+256],raw_rr[bank*257+:256],expected);errors=errors+1;
   end
   if(fault!==0||status!==0)begin if(errors<4)$display("FAULT case%0d engine%b banks%h",c,fault,status);errors=errors+1;end
   readback=0;repeat(12)@(negedge clk);preload=1;
  end
  if(errors)$fatal(1,"GATHER_F20_CURRENT FAIL checks=%0d errors=%0d",checks,errors);
  $display("GATHER_F20_CURRENT PASS checks=%0d canonical_routes=6 structural_routes=32 banks=32 SRAMs=96 fixed_cycles=%0d",checks,first_cycles);$finish;
 end
endmodule
