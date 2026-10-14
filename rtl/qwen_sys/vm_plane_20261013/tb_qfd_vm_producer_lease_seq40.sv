`timescale 1ns/1ps
module tb_qfd_vm_producer_lease_seq40;
parameter integer MUT=0;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,acquire_v=0,commit_v=0,commit_pending=0,read_ready=0,response_v=0,q_ready=0,release_v=0,quiet=1,flush=0;
reg [378:0] ib=0; reg mode=0; reg [15:0] ctx=0,release_ctx=0;
reg [31:0] release_ver=0; reg [3:0] phase=0;
reg [95:0] address=0; reg [4:0] root=0; reg [15:0] recipient=0;
reg [511:0] data=0; reg [39:0] query_seq=0; wire [39:0] qseq; reg query_mode=0; reg [378:0] expected_ib; reg query=0,bad_identity=0; wire query_ready;
wire ar,wa,rv,rr,qv,relready,drained,fa,fault;
wire [31:0] ver,qver,blocked,leased;
wire [378:0] rib; wire rmode,qmode; wire [511:0] qdata;
wire [15:0] qctx,qrec; wire [3:0] qp; wire [95:0] qa; wire [4:0] qr;
ot_qfd_vm_producer_lease_seq40 #(.ENABLE(1),.MUT(MUT)) dut(
.clk(clk),.rst_n(rst_n),.acquire_v(acquire_v),.acquire_ready(ar),.held_ib(ib),.held_mode(mode),.held_context(ctx),
.query_v(query),.query_ready(query_ready),.query_seq40(query_seq),.q_seq40(qseq),.query_mode(query_mode),.query_context(ctx ^ (bad_identity ? 16'h1 : 16'h0)),.query_version(expected_ver ^ (bad_identity ? 32'h1 : 32'h0)),.request_phase(phase),.request_address(address),.request_root(root),.request_recipient(recipient),
.commit_v(commit_v),.commit_pending(commit_pending),.native_write_allowed(wa),.acquire_version(ver),
.read_v(rv),.read_ready(read_ready),.read_ib(rib),.read_mode(rmode),.response_v(response_v),.response_ready(rr),.response_data(data),
.q_v(qv),.q_ready(q_ready),.q_data(qdata),.q_context(qctx),.q_version(qver),.q_mode(qmode),.q_phase(qp),.q_address(qa),.q_root(qr),.q_recipient(qrec),
.release_v(release_v),.release_ready(relready),.release_context(release_ctx),.release_version(release_ver),.recipients_quiescent(quiet),
.source_output_drained(drained),.transport_flush_req(flush),.transport_flush_ack(fa),.fault(fault),.blocked_write_cycles(blocked),.leased_cycles(leased));
task tick; begin @(posedge clk); #1; @(negedge clk); end endtask
task ck(input bit ok,input string why); begin if(!ok) $fatal(1,"FAIL %s",why); end endtask
integer op,i; reg [511:0] expected; reg [31:0] expected_ver;
initial begin
 tick(); rst_n=1; tick(); ck(!ar,"reset requires flush fence"); flush=1; tick(); ck(fa,"flush ack"); flush=0; tick();
 for(op=0;op<32;op=op+1) begin
  ib={379{1'b1}} ^ op; ctx=op+16'hb000; mode=op[0]; phase=op[3:0]; address=96'hfeed0000+op; root=op; recipient=16'h1200+op; query_seq=(40'd1<<32)+op*2;
  ib[179:156]=mode ? 24'd0 : 24'd17; expected_ib=ib; query_mode=mode;
  acquire_v=1; commit_pending=1; commit_v=1; tick(); commit_v=0;
  ck(!ar&&!wa,"acquire drains accepted commits and blocks new writes"); tick(); commit_pending=0; mode=~mode; #1; expected_ver=ver; ck(!ar,"offered mode disagrees with canonical accepted IB"); tick(); mode=~mode; #1; ck(ar,"drained ready");
  tick(); acquire_v=0; ck(!rv&&query_ready,"acquire reserves only; no synthetic read");
  bad_identity=1; query=1; #1; ck(!query_ready,"stale query context/version rejected"); tick();
  bad_identity=0; query_mode=~mode; #1; ck(!query_ready,"registered request mode mismatch rejected"); tick(); ck(!rv,"mismatched request mode emitted read"); query_mode=mode; tick(); query=0; ck(rv,"explicit accepted native read request"); ib=0; tick(); ck(rib==expected_ib&&rmode==mode,"immutable descriptor and accepted mode");
  read_ready=1; tick(); read_ready=0; ck(rr&&!wa,"wait actual response reserves writes");
  expected=0; for(i=0;i<512;i=i+1) expected[i]=((i+op)%3)==0;
  data=expected; response_v=1; tick(); response_v=0; ck(qv&&!wa,"operation reservation survives private capture");
  ck(qver==expected_ver&&qctx==ctx&&qmode==mode&&qp==phase&&qa==address&&qr==root&&qrec==recipient&&qseq==query_seq,"payload provenance");
  for(i=0;i<7;i=i+1) begin data=~expected; tick(); ck(qv&&qdata==expected&&qver==expected_ver&&!wa,"operation blocks offered writes through stalls"); end
  commit_v=0; q_ready=1; tick(); q_ready=0; ck(!qv&&drained,"output consumed exactly once");
  response_v=1; data=~expected; tick(); response_v=0; ck(qdata==expected,"retained payload after consumption");
  // Second DIFFERENT address under same operation/version. Offered writes
  // remain backpressured; only actual commits (none) change version.
  address=address+1; phase=phase+1; query_seq=query_seq+1; query=1; #1; ck(query_ready,"next native query same lease"); tick(); query=0;
  ck(rv&&rib==expected_ib&&!wa,"second query retained descriptor and reservation");
  read_ready=1; tick(); read_ready=0; expected=~expected; data=expected; response_v=1; tick(); response_v=0;
  ck(qv&&qdata==expected&&qver==expected_ver&&qa==address&&qseq==query_seq,"second address same version");
  q_ready=1; tick(); q_ready=0; ck(!qv&&drained&&!wa,"second consumed once reservation remains");
  release_ctx=ctx; release_ver=expected_ver; quiet=0; release_v=1; #1; ck(!relready,"real recipient retirement fence"); tick(); release_v=0; quiet=1;
  ck(!ar,"no second acquisition before release"); release_v=1; #1; ck(relready,"matching release ready"); tick(); release_v=0;
  ck(!fault,"positive protocol has no fault");
 end
 $display("PASS lease 32 operations all512bits/full40seq/canonicalIBmode, write reservation across two queries, both modes, 4bit phases; blocked=%0d leased=%0d",blocked,leased); $finish;
end
initial begin #100000; $fatal(1,"timeout"); end
endmodule
