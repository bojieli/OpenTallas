`timescale 1ns/1ps
module tb_qfd_vm_producer_row_lease_provenance;
parameter integer MUT=0;
reg clk=0; always #5 clk=~clk;
reg rst_n=0; wire request_v, request_ready;
reg acquire=0,query=0,release_v=0,flush=0,qready=0;
wire acquire_ready,query_ready,release_ready,flush_ack,write_allowed,qvalid,drained,fault;
wire [511:0] qpayload; wire [31:0] version,qversion; wire [15:0] qcontext;
reg [15:0] context_id=0; reg [31:0] leased_version=0; reg [378:0] descriptor=0;
reg [39:0] query_seq=0; wire [39:0] qseq; reg mode=0; wire qmode; reg [15:0] token=0; reg [20:0] epoch=0; wire [15:0] qtoken,qrec; wire [20:0] qepoch; wire [3:0] qphase; wire [95:0] qaddr; wire [4:0] qroot; wire response_ready; wire [3:0] read_phase; wire [95:0] read_address;
ot_qfd_vm_producer_lease_provenance #(.ENABLE(1)) lease(
 .clk(clk),.rst_n(rst_n),.acquire_v(acquire),.acquire_ready(acquire_ready),
 .held_ib(descriptor),.held_mode(mode),.held_context(context_id),.held_token(token),
 .request_phase({1'b0,bank}),.request_address({85'b0,bank,row}),.request_root(5'b0),.request_recipient(16'b1),
 .query_seq40(query_seq),.q_seq40(qseq),.read_seq40(),.query_mode(mode),.query_token(token),.query_epoch(epoch),.q_token(qtoken),.q_epoch(qepoch),.query_v(query),.query_ready(query_ready),.query_context(context_id),.query_version(leased_version),.commit_v(commit),.commit_pending(pending),
 .native_write_allowed(write_allowed),.acquire_version(version),
 .read_v(request_v),.read_ready(request_ready),.read_ib(),.read_mode(),.read_phase(read_phase),.read_address(read_address),.read_root(),.read_recipient(),
 .response_v(response_v),.response_ready(response_ready),.response_data(data),
 .q_v(qvalid),.q_ready(qready),.q_data(qpayload),.q_context(qcontext),.q_version(qversion),
 .q_mode(qmode),.q_phase(qphase),.q_address(qaddr),.q_root(qroot),.q_recipient(qrec),
 .release_v(release_v),.release_ready(release_ready),.release_context(context_id),.release_token(token),.release_version(leased_version),
 .recipients_quiescent(1'b1),.source_output_drained(drained),
 .transport_flush_req(flush),.transport_flush_ack(flush_ack),.fault(fault),.blocked_write_cycles(),.leased_cycles());
reg [2:0] bank=0; reg [7:0] row=0;
wire [7:0] re; wire [63:0] ra; wire rq; wire [2:0] rqb;
wire [511:0] ro,data; wire response_v,commit,pending;
// Fixture loader is handshaken; this mask MUST NOT be used on posted SU writes.
reg [7:0] offered_we=0; wire [7:0] we=write_allowed ? offered_we : 8'b0; reg [63:0] wl=0; reg [127:0] wm=0; reg [4095:0] wd=0;
wire [4095:0] xo; wire [3071:0] so; wire ovf;
integer b,a,i,elapsed,reads=0,commits=0;
function automatic [511:0] pattern(input integer bank_i,input integer row_i);
 integer j; begin for(j=0;j<512;j=j+1) pattern[j]=((j+bank_i*7+row_i*13)%5)<2; end
endfunction
ot_qfd_vm_producer_row_binding_seq40 #(.MUT(MUT)) binding(
.clk(clk),.rst_n(rst_n),.request_v(request_v),.request_ready(request_ready),.decoded_bank(read_phase[2:0]),.decoded_row(read_address[7:0]),
.re(re),.ra(ra),.rq(rq),.rqb(rqb),.native_ro(ro),.response_v(response_v),.response_ready(response_ready),.response_data(data),
.accepted_write(|we),.commit_v(commit),.commit_pending(pending));
ot_qfd_vm_region_leaf #(.DEPTH(174),.LAW(8),.DEPTHS(695),.LAWS(10),.USE_MACRO(0)) native(
.clk(clk),.leaf_clocks(72'b0),.rst_entries(17'b0),.me_entries(25'b0),.xv_entries(9'b0),.pop_entries(9'b0),
.sv_entries(6'b0),.swe_entries(6'b0),.swl_entries(60'b0),.swm_entries(96'b0),.swd_entries(3072'b0),.rqb_entries(4'b0),
.rst_n(rst_n),.me_in(1'b0),.re(re),.ra(ra),.we(we),.wl(wl),.wm(wm),.wd(wd),.xv(1'b0),.rq(rq),.rqb(rqb),
.sre(6'b0),.sra(60'b0),.sv(3'b0),.swe(2'b0),.swl(20'b0),.swm(32'b0),.swd(1024'b0),.pop(1'b0),.xo(xo),.ro(ro),.so(so),.ovf(ovf));
task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
always @(posedge clk) if(rst_n&&commit) commits=commits+1;
initial begin
 repeat(4) tick(); rst_n=1; flush=1; tick(); flush=0; repeat(16) tick();
 for(a=0;a<2;a=a+1) begin
  for(b=0;b<8;b=b+1) begin wl[b*8+:8]=a; wd[b*512+:512]=pattern(b,a); end
  wm={128{1'b1}}; offered_we=8'hff; tick(); offered_we=0; wm=0; repeat(12) tick();
 end
 if(commits!=2||pending||version!=2) $fatal(1,"actual commit version mismatch");
 for(i=0;i<64;i=i+1) begin
  bank=i%8; row=(i/8)%2; query_seq=(40'd1<<32)+i; epoch=21'hb0000+i;
  if(i%2==0) begin
   context_id=i+100; descriptor=i+379'h1234567; token=77+i/2; mode=i[1]; descriptor[179:156]=mode ? 24'd0 : 24'd17; acquire=1; #1;
   if(!acquire_ready) $fatal(1,"acquire not ready"); leased_version=version; tick(); acquire=0;
  end
  if(request_v) $fatal(1,"acquisition synthesizes a query");
  query=1; #1; if(!query_ready) $fatal(1,"query not ready"); tick(); query=0;
  elapsed=0;
  while(!qvalid) begin
   if(write_allowed) $fatal(1,"write reservation lost during native query");
   tick(); elapsed=elapsed+1; if(elapsed>20) $fatal(1,"native query timeout");
  end
  if(qpayload!==pattern(bank,row)||qversion!=leased_version||qcontext!=context_id||qseq!=query_seq||qmode!=mode||qtoken!=token||qepoch!=epoch||qphase!={1'b0,bank}||qaddr!={85'b0,bank,row}||qroot!=0||qrec!=1) $fatal(1,"retained native ROW/provenance mismatch");
  // Offered writes must remain backpressured during private result stall.
  offered_we=8'hff; wm={128{1'b1}};
  for(b=0;b<8;b=b+1) begin wl[b*8+:8]=row; wd[b*512+:512]=~pattern(b,row); end
  repeat(3) begin tick(); if(write_allowed||(|we)||version!=leased_version||qpayload!==pattern(bank,row)) $fatal(1,"lease changed under offered writes"); end
  offered_we=0; wm=0; qready=1; tick(); qready=0; if(qvalid||!drained) $fatal(1,"duplicate native output");
  reads=reads+1;
  if(i%2==1) begin
   release_v=1; #1; if(!release_ready) $fatal(1,"matching native release not ready"); tick(); release_v=0;
   if(!write_allowed) $fatal(1,"write reservation not released");
  end
 end
 if(fault) $fatal(1,"native lease protocol fault");
 $display("PASS integrated native ROW lease full247metadata/full40seq/canonicalIBmode %0d reads all512bits,32 operations x2 queries,version=%0d commits=%0d",reads,version,commits); $finish;
end
initial begin #1000000; $fatal(1,"timeout"); end
endmodule
