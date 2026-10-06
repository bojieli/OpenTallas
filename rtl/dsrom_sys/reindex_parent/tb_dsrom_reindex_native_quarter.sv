`timescale 1ns/1ps
// Minimum native quarter: literal sixteen lanes and twenty-bit global IDs.
// Expected words feed only the comparator. No score stand-in or query oracle.
module tb_dsrom_reindex_native_quarter;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,ql_v=0,ks_valid=0,ks_last=0,sc_ready=0;
 reg [7:0] ql_head=0;
 reg [511:0] ql_codes=0;
 reg [31:0] ql_sc=0;
 reg [15:0] ql_w=0,ks_lv=0,ks_ref=0;
 reg [8703:0] ks_key=0;
 reg [319:0] ks_idx=0;
 wire ql_ready,ks_ready,sc_valid,sc_last,protocol_fault;
 wire [3:0] sc_last_slices;
 wire [15:0] sc_lv,sc_fault;
 wire [255:0] sc_val;
 wire [319:0] sc_idx;
 ot_dsrom_reindex_native_quarter #(.ENABLE(1)) dut(.*);
 wire off_qr,off_kr,off_v,off_last,off_pf;
 wire [3:0] off_ls; wire [15:0] off_lv,off_fault;
 wire [255:0] off_val; wire [319:0] off_idx;
 ot_dsrom_reindex_native_quarter default_off(
  .clk(clk),.rst_n(rst_n),.ql_v(ql_v),.ql_ready(off_qr),
  .ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
  .ks_valid(ks_valid),.ks_ready(off_kr),.ks_last(ks_last),
  .ks_lv(ks_lv),.ks_ref(ks_ref),.ks_key(ks_key),.ks_idx(ks_idx),
  .sc_valid(off_v),.sc_ready(sc_ready),.sc_last(off_last),.sc_last_slices(off_ls),
  .sc_lv(off_lv),.sc_fault(off_fault),.sc_val(off_val),.sc_idx(off_idx),.protocol_fault(off_pf));
 reg [559:0] query_mem[0:31];
 // {valid,globalID20,refused,key544}; candidate masking remains after scoring.
 reg [565:0] key_mem[0:63]; reg [16:0] expected_mem[0:63];
 integer edges=0,accepted=0,received=0,checked=0,refused=0,invalid=0,stalled=0;
 integer accepted_at[0:3],latency_min=2147483647,latency_max=0;
 reg scoring=0,holding=0; reg [613:0] held_output;
 string fixture; integer negative_ids=0,negative_score=0;
 task load_query;
  begin
   for(integer h=0;h<32;h=h+1)begin
    @(negedge clk); while(!ql_ready)@(negedge clk);
    ql_head=h;ql_codes=query_mem[h][511:0];ql_sc=query_mem[h][543:512];
    ql_w=query_mem[h][559:544];ql_v=1;
   end
   @(negedge clk);ql_v=0;
  end
 endtask
 task drive_beat(input integer b);
  begin
   ks_last=b==3;
   for(integer l=0;l<16;l=l+1)begin
    ks_key[544*l+:544]=key_mem[16*b+l][543:0];
    ks_ref[l]=key_mem[16*b+l][544];
    ks_idx[20*l+:20]=key_mem[16*b+l][564:545];
    ks_lv[l]=key_mem[16*b+l][565];
    // Undriven data in invalid slots must not poison valid lanes or control.
    if(!ks_lv[l])ks_key[544*l+:544]='x;
   end
   if(b==0&&negative_ids)ks_idx[20+:20]=ks_idx[20+:20]+2;
  end
 endtask
 always @(posedge clk)begin
  edges=edges+1;
  if({off_qr,off_kr,off_v,off_last,off_pf,off_ls,off_lv,off_fault,off_val,off_idx} !== '0)
   $fatal(1,"default OFF admitted work or exposed data");
  if(rst_n&&scoring)begin
   if(protocol_fault)$fatal(1,"native slices diverged");
   if(holding && {sc_valid,sc_last_slices,sc_lv,sc_fault,sc_val,sc_idx} !== held_output)
    $fatal(1,"native score changed under backpressure");
   holding=sc_valid&&!sc_ready;
   if(holding)begin
    held_output={sc_valid,sc_last_slices,sc_lv,sc_fault,sc_val,sc_idx};stalled=stalled+1;
    if(ql_ready)$fatal(1,"query overwrite admitted with scores retained");
   end
   if(ks_valid&&ks_ready)begin accepted_at[accepted]=edges;accepted=accepted+1;end
   if(sc_valid&&sc_ready)begin
    if(received>=accepted||sc_last_slices!=={4{received==3}}||sc_last!==(received==3))
     $fatal(1,"native last/order mismatch");
    for(integer l=0;l<16;l=l+1)begin
     if(sc_idx[20*l+:20]!==key_mem[16*received+l][564:545]||sc_lv[l]!==key_mem[16*received+l][565])
      $fatal(1,"full global ID/valid changed lane=%0d beat=%0d",l,received);
     if(sc_lv[l])begin
      if({sc_fault[l],sc_val[16*l+:16]}!==expected_mem[16*received+l])
       $fatal(1,"golden mismatch lane=%0d beat=%0d got=%h expected=%h",l,received,{sc_fault[l],sc_val[16*l+:16]},expected_mem[16*received+l]);
      checked=checked+1;refused=refused+key_mem[16*received+l][544];
     end else invalid=invalid+1;
    end
    if(edges-accepted_at[received]<latency_min)latency_min=edges-accepted_at[received];
    if(edges-accepted_at[received]>latency_max)latency_max=edges-accepted_at[received];
    received=received+1;
   end
  end
 end
 always @(negedge clk)if(scoring)sc_ready=edges%7!=0&&edges%7!=1;
 initial begin
  if(!$value$plusargs("FIXTURE=%s",fixture))$fatal(1,"source fixture required");
  if($value$plusargs("NEGATIVE_IDS=%d",negative_ids))begin end
  if($value$plusargs("NEGATIVE_SCORE=%d",negative_score))begin end
  $readmemh({fixture,"/query.mem"},query_mem);
  $readmemh({fixture,"/keys.mem"},key_mem);
  $readmemh({fixture,"/expected.mem"},expected_mem);
  // A comparator-only mutation must fail the real native score comparison.
  if(negative_score)expected_mem[0]=expected_mem[0]^17'd1;
  repeat(3)@(negedge clk);rst_n=1;load_query();
  // Accepted native work is discarded only by real cold reset, then reload.
  @(negedge clk);drive_beat(0);ks_valid=1;
  do @(posedge clk);while(!ks_ready);
  @(negedge clk);ks_valid=0;rst_n=0;
  repeat(3)@(negedge clk);rst_n=1;load_query();
  @(negedge clk);scoring=1;
  for(integer b=0;b<4;b=b+1)begin
   repeat(b%3)@(negedge clk);
   drive_beat(b);ks_valid=1;
   do @(posedge clk);while(!ks_ready);
   @(negedge clk);ks_valid=0;
  end
  wait(received==4);@(negedge clk);
  while(!ql_ready)@(negedge clk);
  if(accepted!=4||checked!=61||refused!=1||invalid!=3||stalled==0)
   $fatal(1,"native coverage/count mismatch");
  $display("PASS_KC8_NATIVE_QUARTER lanes=16 globalID=20 accepted=%0d checked=%0d refused=%0d invalid=%0d stalled=%0d latency_min=%0d latency_max=%0d cold_reset_inflight=1 default_off=1 parent_qualified=0",accepted,checked,refused,invalid,stalled,latency_min,latency_max);
  $finish;
 end
endmodule
