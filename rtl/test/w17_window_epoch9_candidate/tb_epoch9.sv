`timescale 1ns/1ps
// CORRECTNESS ONLY. Synthetic queue service, actual owner muxes and KARB.
// No DRAM timings, checkpoint data, engine, performance or clock qualification.
module w17_epoch9_synthetic_pc (
 input wire clk,rst_n,
 input wire [31:0] req_v,output reg [31:0] req_rdy,
 input wire [959:0] req_addr,input wire [127:0] req_len,
 input wire [543:0] req_tag,input wire [31:0] req_we,
 output reg [31:0] rsp_v,input wire [31:0] rsp_rdy,
 output reg [543:0] rsp_tag,output reg [127:0] rsp_beat,
 output reg [8191:0] rsp_data
);
 integer cycle=0, requests=0,responses=0,held=0,ooo=0,last_sequence=-1;
 integer q_count[0:31];
 reg qa[0:31][0:7];
 integer due[0:31][0:7],seq[0:31][0:7];
 reg [29:0] addr[0:31][0:7]; reg [16:0] tag[0:31][0:7];
 integer rsp_sequence[0:31];
 reg injected=0;
 reg [16:0] previous_tag;
 integer p,k,pick,free_slot,delay_cycles,n;
 reg [16:0] chosen_tag;
 reg [255:0] chosen_data;
 function automatic [255:0] sector(input [29:0] a);
  for(integer b=0;b<32;b=b+1) sector[b*8+:8]=8'(1+((a+b)%120));
 endfunction
 // Input stimulus is fixed at negedge, avoiding ready changes in the sampling region.
 always @(negedge clk) begin
  for(integer g=0;g<32;g=g+1)
   req_rdy[g]=rst_n && cycle%7!=0 && q_count[g]+integer'(rsp_v[g])<8;
 end
 always @(posedge clk) begin
  if(!rst_n) begin
   cycle=0;requests=0;responses=0;held=0;ooo=0;last_sequence=-1;injected=0;previous_tag=0;
   rsp_v<=0;rsp_tag<=0;rsp_beat<=0;rsp_data<=0;
   for(p=0;p<32;p=p+1) begin q_count[p]=0;rsp_sequence[p]=0;for(k=0;k<8;k=k+1) qa[p][k]=0;end
  end else begin
   cycle=cycle+1;
   for(p=0;p<32;p=p+1) begin
    if(rsp_v[p]&&!rsp_rdy[p]) held=held+1;
    if(rsp_v[p]&&rsp_rdy[p]) begin
     if(rsp_sequence[p]<last_sequence) ooo=ooo+1;
     last_sequence=rsp_sequence[p];previous_tag=rsp_tag[p*17+:17];
     responses=responses+1;rsp_v[p]<=0;
    end
   end
   // Issue order intentionally differs from return order; held outputs are immutable.
   for(p=0;p<32;p=p+1) begin
    if(!rsp_v[p]||rsp_rdy[p]) begin
     pick=-1;
     for(k=0;k<8;k=k+1) if(qa[p][k]&&due[p][k]<=cycle)
      if(pick<0||seq[p][k]>seq[p][pick]) pick=k;
     if(pick>=0) begin
      qa[p][pick]=0;chosen_tag=tag[p][pick];chosen_data=sector(addr[p][pick]);
      if(!injected) begin
       if($test$plusargs("STALE")) begin chosen_tag=chosen_tag^17'h20;injected=1;end
       else if($test$plusargs("UNKNOWN_SECTOR")) begin chosen_tag[4:0]=31;injected=1;end
       else if($test$plusargs("POISON")) begin chosen_data[6:0]=7'h7f;injected=1;end
       else if($test$plusargs("DUPLICATE")&&responses>0) begin chosen_tag=previous_tag;injected=1;end
      end
      rsp_v[p]<=1;rsp_tag[p*17+:17]<=chosen_tag;rsp_beat[p*4+:4]<=0;
      rsp_data[p*256+:256]<=chosen_data;rsp_sequence[p]=seq[p][pick];
     end
    end
    if(req_v[p]&&req_rdy[p]) begin
     if(req_we[p]||req_len[p*4+:4]!=1||req_tag[p*17+14+:3]!=3'b100)
      $fatal(1,"bad synthetic service admission/owner");
     free_slot=-1;for(k=7;k>=0;k=k-1) if(!qa[p][k]) free_slot=k;
     if(free_slot<0) $fatal(1,"synthetic queue overflow");
     qa[p][free_slot]=1;addr[p][free_slot]=req_addr[p*30+:30];tag[p][free_slot]=req_tag[p*17+:17];
     seq[p][free_slot]=requests;requests=requests+1;
     delay_cycles=12+((req_addr[p*30+:2]==0)?24:0);
     due[p][free_slot]=((cycle+delay_cycles+7)/8)*8;
    end
    n=0;for(k=0;k<8;k=k+1) n=n+integer'(qa[p][k]);q_count[p]=n;
   end
  end
 end
endmodule

module tb_epoch9;
 localparam integer BASE=262144,FIRST=1048448;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,prime_v=0,start_v=0,stream_go=0;
 reg [20:0] prime_row=0;
 wire prime_ready,start_ready,staged_v,busy,done,fault;
 wire [4:0] fault_code;
 wire [31:0] refill_cycles,sectors_read,rows_fetched;
 wire [7:0] rows_refilled;
 wire kv_v;wire kv_ready=cycle%5!=0;
 wire [3:0] kv_m;wire [16959:0] kv_w;
 wire [3:0] wv,wrdy,wwe,wwdone,wsv,wsrdy;
 wire [119:0] wa;wire [15:0] wl,wsbeat;wire [63:0] wt,wstag;
 wire [1023:0] wdata,wsdata;wire [127:0] wstrb;
 wire [3:0] mv,mrdy,mwe,mwdone,sv,srdy;
 wire [119:0] ma;wire [15:0] ml,sbeat;wire [63:0] mt,stag;
 wire [1023:0] mdata,sdata;wire [127:0] mstrb;
 wire mux_fault;
 wire [31:0] hv,hrdy,hwe,rv,rrdy;
 wire [959:0] ha;wire [127:0] hl,rbeat;wire [543:0] ht,rt;
 wire [8191:0] hdata,rdata;wire [1023:0] hstrb;
 wire [31:0] kg,bg,contended;
 integer cycle=0,admitted[0:31],consumed[0:31];
 integer accepted_beats=0,epoch_changes=0,max_pending=0,request_stalls=0,sink_holds=0;
 integer p,total,seed=510;reg saw511=0,saw0=0,saw1=0;
 reg [10:0] last_epoch=0;
 reg [31:0] held_pc=0;reg [276:0] held_return[0:31];
 reg held_request=0,held_beat=0;
 reg [49:0] request_snapshot;reg [16963:0] beat_snapshot;
 reg [255:0] expected_codes,expected_scales;
 function automatic integer pc_of(input integer a);
  pc_of=((a>>2)^(a>>7)^(a>>12))&31;
 endfunction
 function automatic [255:0] sector(input integer a);
  for(integer b=0;b<32;b=b+1) sector[b*8+:8]=8'(1+((a+b)%120));
 endfunction
 ot_chip_v41x_window_attn_source #(.REFILL_CREDITS(8),.TAGW(16),.WIN_STACK(0),.RETAIN_L0(0),.STREAM_II1(0)) dut (
  .clk(clk),.rst_n(rst_n),.retain_qk(1'b0),.retain_pv(1'b0),.retain_complete(1'b0),.retain_invalidate(1'b0),.retain_generation(16'b0),
  .region_base_sector(30'(BASE)),.region_sector_count(30'd2176),
  .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(10'b0),.prime_row(prime_row),
  .blk_v(1'b0),.blk_ready(),.blk_user(10'b0),.blk_row(21'b0),.blk_idx(4'b0),.blk_codes(256'b0),.blk_scale(8'b0),
  .start_v(start_v),.start_ready(start_ready),.start_user(10'b0),.start_first(21'(FIRST)),.start_count(8'd128),
  .staged_v(staged_v),.stream_go(stream_go),.busy(busy),.done(done),.fault(fault),.fault_code(fault_code),
  .refill_cycles(refill_cycles),.sectors_read(sectors_read),.rows_fetched(rows_fetched),.blocks_written(),.sectors_written(),.rows_refilled(rows_refilled),
  .kv_v(kv_v),.kv_ready(kv_ready),.kv_m(kv_m),.kv_w(kv_w),
  .m_v(wv),.m_rdy(wrdy),.m_addr(wa),.m_len(wl),.m_tag(wt),.m_we(wwe),.m_wdata(wdata),.m_wstrb(wstrb),.m_wr_done(wwdone),
  .s_v(wsv),.s_rdy(wsrdy),.s_tag(wstag),.s_beat(wsbeat),.s_data(wsdata));
 ot_chip_v41x_kv_rope_reqmux #(.HAW(30),.TAGW(16)) mux (
  .clk(clk),.rst_n(rst_n),.w_v(wv),.w_rdy(wrdy),.w_addr(wa),.w_len(wl),.w_tag(wt),.w_we(wwe),.w_wdata(wdata),.w_wstrb(wstrb),.w_wr_done(wwdone),
  .w_sv(wsv),.w_srdy(wsrdy),.w_stag(wstag),.w_sbeat(wsbeat),.w_sdata(wsdata),
  .c_v(4'b0),.c_rdy(),.c_addr(120'b0),.c_len(16'b0),.c_tag(64'b0),.c_we(4'b0),.c_wdata(1024'b0),.c_wstrb(128'b0),.c_wr_done(),
  .c_sv(),.c_srdy(4'b0),.c_stag(),.c_sbeat(),.c_sdata(),
  .p_v(4'b0),.p_rdy(),.p_addr(120'b0),.p_len(16'b0),.p_tag(64'b0),.p_we(4'b0),.p_wdata(1024'b0),.p_wstrb(128'b0),.p_wr_done(),
  .p_sv(),.p_srdy(4'b0),.p_stag(),.p_sbeat(),.p_sdata(),
  .m_v(mv),.m_rdy(mrdy),.m_addr(ma),.m_len(ml),.m_tag(mt),.m_we(mwe),.m_wdata(mdata),.m_wstrb(mstrb),.m_wr_done(mwdone),
  .s_v(sv),.s_rdy(srdy),.s_tag(stag),.s_beat(sbeat),.s_data(sdata),.fault(mux_fault),.rope_grants(),.rope_wait_cycles());
 ot_chip_v41x_hbm_karb #(.NPC(32),.AW(30),.TAGW(16),.PIPE_OUT(0),.PIPE_RSP(0)) arb (
  .clk(clk),.rst_n(rst_n),.b_v(32'b0),.b_rdy(),.b_addr(960'b0),.b_len(128'b0),.b_tag(512'b0),.b_we(32'b0),.b_wdata(8192'b0),.b_wstrb(1024'b0),.b_wr_done(),
  .b_rsp_v(),.b_rsp_rdy(32'b0),.b_rsp_tag(),.b_rsp_beat(),.b_rsp_data(),
  .k_v(mv[0]),.k_rdy(mrdy[0]),.k_addr(ma[0+:30]),.k_len(ml[0+:4]),.k_tag(mt[0+:16]),.k_we(mwe[0]),.k_wdata(mdata[0+:256]),.k_wstrb(mstrb[0+:32]),.k_wr_done(mwdone[0]),
  .k_rsp_v(sv[0]),.k_rsp_rdy(srdy[0]),.k_rsp_tag(stag[0+:16]),.k_rsp_beat(sbeat[0+:4]),.k_rsp_data(sdata[0+:256]),
  .h_v(hv),.h_rdy(hrdy),.h_addr(ha),.h_len(hl),.h_tag(ht),.h_we(hwe),.h_wdata(hdata),.h_wstrb(hstrb),.h_wr_done(32'b0),
  .r_v(rv),.r_rdy(rrdy),.r_tag(rt),.r_beat(rbeat),.r_data(rdata),.k_grants(kg),.b_grants(bg),.contended(contended));
 assign mrdy[3:1]=0;assign mwdone[3:1]=0;assign sv[3:1]=0;assign stag[63:16]=0;assign sbeat[15:4]=0;assign sdata[1023:256]=0;
 w17_epoch9_synthetic_pc service (.clk(clk),.rst_n(rst_n),.req_v(hv),.req_rdy(hrdy),.req_addr(ha),.req_len(hl),.req_tag(ht),.req_we(hwe),
  .rsp_v(rv),.rsp_rdy(rrdy),.rsp_tag(rt),.rsp_beat(rbeat),.rsp_data(rdata));
 always @(posedge clk) begin
  if(!rst_n) begin
   cycle=0;accepted_beats=0;epoch_changes=0;max_pending=0;request_stalls=0;sink_holds=0;
   held_pc=0;held_request=0;held_beat=0;
   for(integer z=0;z<32;z=z+1) begin admitted[z]=0;consumed[z]=0;end
  end else begin
   cycle=cycle+1;
   if(held_request && !fault && !mux_fault && (!wv[0] || {wa[0+:30],wt[0+:16],wl[0+:4]}!==request_snapshot)) $fatal(1,"request changed while refused");
   held_request=wv[0]&&!wrdy[0];request_snapshot={wa[0+:30],wt[0+:16],wl[0+:4]};
   if(held_request) request_stalls=request_stalls+1;
   for(p=0;p<32;p=p+1) begin
    if(held_pc[p]&&{rt[p*17+:17],rbeat[p*4+:4],rdata[p*256+:256]}!==held_return[p]) $fatal(1,"held backend return changed");
    held_pc[p]=rv[p]&&!rrdy[p];held_return[p]={rt[p*17+:17],rbeat[p*4+:4],rdata[p*256+:256]};
    if(hv[p]&&hrdy[p]) begin
     if(pc_of(ha[p*30+:30])!=p || ht[p*17+14+:3]!=3'b100) $fatal(1,"backend map/owner mismatch");
     if(ha[p*30+:30]<BASE||ha[p*30+:30]>=BASE+2176||ht[p*17+:5]!=(ha[p*30+:30]-BASE)%17) $fatal(1,"address/sector mismatch");
     if(ht[p*17+5+:9]!=dut.u_window.refill_epoch) $fatal(1,"request epoch mismatch");
     admitted[p]=admitted[p]+1;
    end
    if(rv[p]&&rrdy[p]) consumed[p]=consumed[p]+1;
   end
   if(held_beat && {kv_m,kv_w}!==beat_snapshot) $fatal(1,"packed beat changed under sink hold");
   held_beat=kv_v&&!kv_ready;beat_snapshot={kv_m,kv_w};if(held_beat) sink_holds=sink_holds+1;
   if(kv_v&&kv_ready) begin
    if(kv_m!=4'hf||sectors_read!=2176||rows_refilled!=128) $fatal(1,"early/partial replay");
    for(integer lane=0;lane<4;lane=lane+1) for(integer g=0;g<16;g=g+1) begin
     expected_codes=sector(BASE+(accepted_beats*4+lane)*17+g);
     expected_scales=sector(BASE+(accepted_beats*4+lane)*17+16);
     if(kv_w[(lane*16+g)*265+:265]!=={1'b0,expected_scales[g*8+:8],expected_codes}) $fatal(1,"chronological synthetic stage data mismatch");
    end
    accepted_beats=accepted_beats+1;
   end
   #0.001;
   if(!fault&&!mux_fault) begin
    total=0;
    for(p=0;p<32;p=p+1) begin
     if(admitted[p]-consumed[p]!=service.q_count[p]+integer'(rv[p])) $fatal(1,"perPC request/return conservation");
     total=total+admitted[p]-consumed[p];
    end
    if(total!=dut.u_window.refill_pending||total>8||total<0) $fatal(1,"source/transport pending mismatch");
    if(total>max_pending) max_pending=total;
    if(dut.u_window.refill_epoch!=last_epoch) begin
     if(total!=0||dut.u_window.refill_issued!=0||dut.u_window.refill_received!=0) $fatal(1,"epoch advanced before clean row drain");
     epoch_changes=epoch_changes+1;last_epoch=dut.u_window.refill_epoch;
     if(last_epoch==511) saw511=1;if(last_epoch==0) saw0=1;if(last_epoch==1) saw1=1;
    end
    if(dut.u_window.state==0 && rows_fetched>0) begin
     if(total!=0||dut.u_window.refill_pending!=0||dut.u_window.refill_issued!=17'h1ffff||dut.u_window.refill_received!=17'h1ffff)
      $fatal(1,"row publication without complete drain");
    end
   end
  end
 end
 initial begin
  repeat(4) @(negedge clk);rst_n=1;repeat(2) @(negedge clk);
  // Legitimate provenance API: no preload of private row/stage metadata.
  for(integer row=0;row<128;row=row+1) begin
   while(!prime_ready) @(negedge clk);
   prime_v=1;prime_row=21'(FIRST+row);@(negedge clk);prime_v=0;
  end
  if($test$plusargs("ORIGINAL_NEGATIVE")) seed=511;
  if($value$plusargs("SEED=%d",seed)) begin end
  if(service.requests!=0||service.responses!=0||!start_ready) $fatal(1,"nonquiescent seed");
  // TEST-ONLY initial epoch seed at empty transport; no runtime reset/watcher.
  dut.u_window.refill_epoch=seed;last_epoch=seed;
  @(negedge clk);start_v=1;@(negedge clk);start_v=0;
  if($test$plusargs("ORIGINAL_NEGATIVE")) begin
   wait(mux_fault);repeat(4) @(negedge clk);
   if(wt[0+:16]!=16'h4000||wrdy[0]||service.requests!=0||rows_fetched!=0||staged_v||kv_v) $fatal(1,"epoch512 negative lost/aliased");
   $display("ORIGINAL_EPOCH512_REJECTED tag=4000 admitted=0 published=0");$finish;
  end
  wait(staged_v||fault||mux_fault);
  if(fault||mux_fault) begin
   if(service.injected) begin
    repeat(16) begin @(negedge clk);if(wv!=0||staged_v||kv_v||rows_fetched!=0) $fatal(1,"publication/admission after bad return");end
    $display("INJECTED_REPLY_REJECTED fault_code=%0d external_fault_drain=UNQUALIFIED",fault_code);$finish;
   end
   $fatal(1,"unexpected candidate fault");
  end
  if(service.injected) $fatal(1,"injected response failed to fault");
  if(!saw511||!saw0||!saw1||epoch_changes!=128||dut.u_window.refill_epoch!=126) $fatal(1,"healthy wrap witness incomplete");
  if(service.requests!=2176||service.responses!=2176||sectors_read!=2176||rows_fetched!=128||max_pending!=8) $fatal(1,"refill totals/credits");
  if(service.ooo==0||service.held==0||request_stalls==0) $fatal(1,"required OOO/held/stall coverage absent");
  repeat(3) @(negedge clk);stream_go=1;@(negedge clk);stream_go=0;
  wait(done);@(negedge clk);
  if(accepted_beats!=32||sink_holds==0||fault||mux_fault) $fatal(1,"replay coverage/completion");
  for(p=0;p<32;p=p+1) if(admitted[p]!=68||consumed[p]!=68) $fatal(1,"perPC totals");
  $display("EPOCH9_CORRECTNESS_PASS requests=2176 responses=2176 rows=128 beats=32 epoch_changes=128 final_epoch=126 max_pending=%0d ooo=%0d held=%0d request_stalls=%0d sink_holds=%0d",max_pending,service.ooo,service.held,request_stalls,sink_holds);
  $finish;
 end
 initial begin #200000; $fatal(1,"bounded correctness timeout");end
endmodule
