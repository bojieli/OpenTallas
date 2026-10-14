`timescale 1ps/1fs
// Production QDQ records/golden from tb_hgi_qdq_q_tput on four actual native B2
// slices and protected group1 CDC. DMA preload and group0 exact readback are real
// native interfaces. Group leases remain held throughout; release is not proven.
module tb_hgi_qdq_native_peer4 #(parameter integer MUT=0,PHASE=61,FASTFIN=0,FRONTFAST=0,DRAIN=0,FINFLAGS=0);
 reg [3:0] cclk=0;always #416.6665 cclk=~cclk;
 wire clk=cclk[0];reg vclk=0;integer phase_run=PHASE;
 initial begin void'($value$plusargs("PHASE=%d",phase_run));#(phase_run);forever #555.5555 vclk=~vclk;end
 reg rst_n=0;reg [3:0] q_owned=0;
 reg [4*683-1:0] rec=0;wire [11:0] ret;
 wire [3:0] rg_req,wg_req;
 wire [32*17-1:0] peer_rq;wire [32*281-1:0] peer_wq;
 wire [32*257-1:0] peer_rr;wire [31:0] peer_rc,peer_wc,peer_done;
 wire [31:0] adapter_fault,client_fault;
 reg [32*16-1:0] check_rq=0;wire [32*257-1:0] check_rr;
 reg [32*281-1:0] dma_q=0;wire [31:0] dma_done;
 wire [32*18-1:0] bank_status;
 wire [31:0] cdrained,vdrained;wire [3:0] qdrained;
 generate if(DRAIN==0)begin:g_original
 assign cdrained=0;assign vdrained=0;assign qdrained=0;
 ot_hgi_qdq_native_peer4 #(.MUT_QDQ(MUT==2?1:0),.FASTFIN(FASTFIN),.FRONTFAST(FRONTFAST),.FINFLAGS(FINFLAGS)) endpoint(
  .cclk(cclk),.vclk(vclk),.rst_n(rst_n),.permit(q_owned),.mirror(4'b0),.rec(rec),.ret(ret),
  .rg_req(rg_req),.wg_req(wg_req),.rg_gnt(q_owned),.wg_gnt(q_owned),
  .peer_rq(peer_rq),.peer_rq_credit(peer_rc),.peer_rr(peer_rr),
  .peer_wq(peer_wq),.peer_wq_credit(peer_wc),.peer_wq_done(peer_done),.adapter_fault(adapter_fault));
 end else begin:g_drained
 ot_hgi_qdq_native_peer4_drain #(.MUT_QDQ(MUT==2?1:0),.FASTFIN(FASTFIN),.FRONTFAST(FRONTFAST),.FINFLAGS(FINFLAGS)) endpoint(
  .cclk(cclk),.vclk(vclk),.rst_n(rst_n),.permit(q_owned),.mirror(4'b0),.rec(rec),.ret(ret),
  .rg_req(rg_req),.wg_req(wg_req),.rg_gnt(q_owned),.wg_gnt(q_owned),
  .peer_rq(peer_rq),.peer_rq_credit(peer_rc),.peer_rr(peer_rr),
  .peer_wq(peer_wq),.peer_wq_credit(peer_wc),.peer_wq_done(peer_done),.adapter_fault(adapter_fault),.cdrained(cdrained),.vdrained(vdrained),.qdrained(qdrained));
 end endgenerate
 ot_hbm_b2_su_vm4 vehicle(.cclk(cclk),.vclk(vclk),.rst_n(rst_n),.permit(4'hf),.mirror(4'b0),
  .crq(check_rq),.crq_credit(),.crr(check_rr),.cwq('0),.cwq_credit(),.cwq_done(),
  .peer_rq(peer_rq),.peer_rq_credit(peer_rc),.peer_rr(peer_rr),
  .peer_wq(peer_wq),.peer_wq_credit(peer_wc),.peer_wq_done(peer_done),
  .dma_q(dma_q),.dma_done(dma_done),.fault(client_fault),.bank_status(bank_status));
 reg [255:0] gin [0:127]; reg [255:0] gout [0:127];
 integer nrec, fd, k, s, j, op [0:15], n [0:15], ab [0:15], ob [0:15], cost [0:15], blk [0:15], iss [0:15];
 integer cyc = 0, words = 0, bad = 0, bk = 0, total_cost = 0, nret = 0, t0 = 0, prev = 0, started = 0;
 integer rows = 1;   // +ROWS=m: every record walks m rows (row stride = n, in place; rows > 0 read / write beyond the vectors:
                     // only row 0 is compared) -- exercises the read walk's row advance, which the m = 1 production shapes do not
 string dir, fn;
 reg [255:0] sd;
 always @(posedge clk) cyc <= cyc + 1;
 task vm_write(input integer quad, input [14:0] sec, input [255:0] d);
  integer lane;
  begin
   lane=quad*8+int'(sec[2:0]);
   @(negedge vclk);dma_q[lane*281+:281]={1'b1,1'b0,2'(quad),sec[12:0],d,8'hff};
   @(negedge vclk);dma_q[lane*281+280]=0;
   while(!dma_done[lane])@(negedge vclk);
  end
 endtask
 task vm_read(input integer quad,input [14:0] sec);
  integer lane;
  begin
   lane=quad*8+int'(sec[2:0]);
   @(negedge clk);check_rq[lane*16+:16]={1'b1,sec};
   @(negedge clk);check_rq[lane*16+15]=0;
   while(!check_rr[lane*257+256])@(negedge clk);
   sd=check_rr[lane*257+:256];
  end
 endtask
 function [255:0] desc(input [2:0] fmt, input [39:0] base, input [19:0] nn, input [19:0] mm, input [31:0] stride);
  begin desc = 256'd0; desc[1:0] = 2'd1; desc[4:2] = fmt; desc[47:8] = base; desc[67:48] = nn; desc[87:68] = mm; desc[119:88] = stride; end
 endfunction
 integer nretq[0:3],prevq[0:3];
 always @(negedge clk) if(started&&rst_n)begin
  if(|adapter_fault|| |client_fault)$fatal(1,"FATAL native adapter fault");
  for(integer q=0;q<4;q=q+1)begin
   if(ret[q*3+2])$fatal(1,"FATAL quadrant%0d fault after%0d dones MUT%0d",q,nretq[q],MUT);
   if(ret[q*3+1])begin
    $display("NATIVE_QDQ_TPUT q%0d rec%0d issue%0d ret%0d cost%0d",q,nretq[q],iss[nretq[q]],cyc-t0,cost[nretq[q]]);
    prevq[q]=cyc-t0;nretq[q]++;
   end
  end
 end
 reg [127:0] h; reg [255:0] da, dd;
 initial begin
  for(integer q=0;q<4;q=q+1)begin nretq[q]=0;prevq[q]=0;end
  if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "FATAL: +DIR");
  void'($value$plusargs("ROWS=%d", rows));
  fd = $fopen({dir, "/recs.txt"}, "r");
  if(!fd)$fatal(1,"FATAL missing production record file %s",dir);
  if($fscanf(fd,"%d",nrec)!=1 || nrec!=8)$fatal(1,"FATAL production must contain8 records, got%0d",nrec);
  for (k = 0; k < nrec; k = k + 1) begin
   void'($fscanf(fd, "%d %d %d %d %d %d", op[k], n[k], ab[k], ob[k], cost[k], blk[k]));
   ab[k] = ab[k] % 65536; ob[k] = ob[k] % 65536;          // slice-local (sid 0), bank phase unchanged
  end
  // multi-row walk: IN PLACE (O = A, legal: a beat is read before it is written), so the m-row range stays inside the
  // record's own region (the production bases are >= 1,792 words apart)
  if (rows > 1) for (k = 0; k < nrec; k = k + 1) begin
   if (rows * n[k] > 1792) $fatal(1, "FATAL: +ROWS too large for the record regions");
   ob[k] = ab[k];
  end
  $fclose(fd);
  for(k=0;k<nrec;k=k+1)if(n[k]<=0||cost[k]<=0)$fatal(1,"FATAL empty production record%0d",k);
  repeat (4) @(posedge clk); rst_n = 1; repeat (8) @(posedge clk);
  for(integer quad=0;quad<4;quad=quad+1)
  for (k = 0; k < nrec; k = k + 1) begin           // actual DMA preload (untimed)
   fn = $sformatf("%s/in_%0d.hex", dir, k); $readmemh(fn, gin, 0, n[k] / 8 - 1);
   for (s = 0; s < n[k] / 8; s = s + 1) vm_write(quad,15'(ab[k] / 8 + s), gin[s]);
  end
  repeat (8) @(negedge clk);
  q_owned=4'hf;
  t0 = cyc; started = 1;
  for (k = 0; k < nrec; k = k + 1) begin
   while (!(ret[0]&&ret[3]&&ret[6]&&ret[9])) @(negedge clk);
   h = 128'd0; h[127:124] = 4'd4; h[123:118] = 6'(op[k]); h[99:93] = (MUT == 1) ? 7'b0010000 : 7'b0010001;
   if (op[k] == 6) h[71:64] = 8'd16;
   da = desc(3'd0, 40'(ab[k]), 20'(n[k]), 20'(rows), rows > 1 ? 32'(n[k]) : 32'd0);
   dd = desc(3'd0, 40'(ob[k]), 20'(n[k]), 20'(rows), rows > 1 ? 32'(n[k]) : 32'd0);
   for(integer quad=0;quad<4;quad=quad+1)rec[quad*683+:683] = {21'(n[k]), 21'(n[k]), dd, da, h, 1'b1}; iss[k] = cyc - t0; total_cost = total_cost + cost[k];
   @(negedge clk); for(integer quad=0;quad<4;quad=quad+1)rec[quad*683]=0;
  end
  while (nretq[0]<nrec || nretq[1]<nrec || nretq[2]<nrec || nretq[3]<nrec) begin @(negedge clk); if (cyc - t0 > 200000) $fatal(1, "FATAL: liveness (%0d dones)", nret); end
  if(DRAIN!=0)begin
   for(integer dq=0;cdrained!=32'hffffffff||vdrained!=32'hffffffff||qdrained!=4'hf;dq=dq+1)begin
    @(negedge clk);if(dq>2000)$fatal(1,"FATAL actual quant drain timedout c%h v%h q%h",cdrained,vdrained,qdrained);
   end
   $display("NATIVE_QDQ_DRAIN PASS lanes32 quadrants4 source_and_VM_obligations_zero");
  end
  for(integer quad=0;quad<4;quad=quad+1)
  for (k = 0; k < nrec; k = k + 1) begin
   bk = bad; fn = $sformatf("%s/out_%0d.hex", dir, k); $readmemh(fn, gout, 0, n[k] / 8 - 1);
   for (s = 0; s < n[k] / 8; s = s + 1) begin
    vm_read(quad,15'(ob[k] / 8 + s));
    for (j = 0; j < 8; j = j + 1) begin
     if (sd[j*32 +: 32] !== gout[s][j*32 +: 32]) begin
      if (bad < 8) $display("MISMATCH rec %0d word %0d: %h != %h", k, 8*s + j, sd[j*32 +: 32], gout[s][j*32 +: 32]);
      bad = bad + 1;
     end
     words = words + 1;
    end
   end
   $display("EXACT %0d mismatch %0d", k, bad - bk);
  end
  for(k=0;k<32;k=k+1)if(bank_status[k*18+17])$fatal(1,"FATAL bank%0d status%h",k,bank_status[k*18+:18]);
  if(words!=13312||total_cost!=168)$fatal(1,"FATAL immutable production shape words%0d cost%0d",words,total_cost);
  if(bad)$fatal(1,"FATAL %0d of %0d words mismatch",bad,words);
  prev=0;for(integer quad=0;quad<4;quad=quad+1)if(prevq[quad]>prev)prev=prevq[quad];
  $display("NATIVE_QDQ_EXACT PASS quadrants=4 records=%0d words=%0d cycles=%0d priced_per_quarter=%0d PHASE=%0d",4*nrec,words,prev,total_cost,phase_run);
  if(prev*10>total_cost*11)$fatal(1,"NATIVE_QDQ_PRICE_MISS cycles%0d immutable%0d limit1.10",prev,total_cost);
  $display("NATIVE_QDQ_TPUT PASS");$finish;
 end
 initial begin #1000000000;$fatal(1,"FATAL native QDQ timeout");end
endmodule
