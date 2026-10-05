`timescale 1ns/1ps
// Simulation-only direct backend replay. No die, transport or payload fixture.
module tb;
  reg clk=0, rst_n=0;
  reg [31:0] req_v=0;
  wire [31:0] req_rdy, rsp_v, wr_done;
  reg [959:0] req_addr=0;
  reg [127:0] req_len=0;
  reg [511:0] req_tag=0;
  wire [511:0] rsp_tag;
  wire [127:0] rsp_beat;
  wire [8191:0] rsp_data;
  ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .MEM_WORDS(1),
    .LENW(4), .REFPB(3), .MEM_MODE(1)) dut (
    .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(req_rdy),
    .req_addr(req_addr), .req_len(req_len), .req_tag(req_tag),
    .req_we(32'b0), .req_wdata(8192'b0), .req_wstrb(1024'b0),
    .wr_done(wr_done), .rsp_v(rsp_v), .rsp_rdy(32'hffffffff),
    .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data));
  integer start_cycle=12300, next_req, idx=0, active=-1, pc, addr;
  integer c, p, w, requests=0, responses=0, qmax=0, rmax=0;
  integer accepted[0:31], returned[0:31];
  longint refs, acts, reads, writes, edge_cycle;
  reg take_req, take_rsp;
  reg [31:0] pattern_word;
  initial begin
    if ($value$plusargs("START=%d", start_cycle)) begin end
    for(p=0;p<32;p=p+1) begin accepted[p]=0; returned[p]=0; end
    #0.5; clk=1; #0.001; clk=0; rst_n=1;
    next_req=start_cycle+3;
    for(c=0;c<200000;c=c+1) begin
      edge_cycle=dut.cyc;
      req_v=0; take_req=0; take_rsp=0;
      if (edge_cycle==next_req && idx<2176) begin
        if(active!=-1) $fatal(1,"more than one credit");
        addr=30'h40000+idx;
        pc=((addr>>2)^(addr>>7)^(addr>>12))&31;
        if(dut.pc_of(addr)!=pc || dut.row_of(addr)!=8 ||
           dut.bank_of(addr)!=(((((addr>>12)^((addr>>15)>>2))&7)<<2)|((addr^(addr>>15))&3)))
          $fatal(1,"address map mismatch");
        req_addr[pc*30+:30]=addr;
        req_len[pc*4+:4]=1;
        req_tag[pc*16+:16]=idx;
        req_v[pc]=1;
        if(!req_rdy[pc]) $fatal(1,"unexpected backpressure");
        take_req=1; active=idx; requests=requests+1; accepted[pc]=accepted[pc]+1;
      end
      for(p=0;p<32;p=p+1) if(rsp_v[p]) begin
        if(take_rsp || active<0 || p!=pc || rsp_tag[p*16+:16]!=active || rsp_beat[p*4+:4]!=0)
          $fatal(1,"response identity/credit mismatch");
        for(w=0;w<8;w=w+1) begin
          pattern_word=((addr*32'd8+w)*32'h9e3779b1)^32'h5bd1e995;
          if(rsp_data[p*256+w*32+:32]!==pattern_word) $fatal(1,"pattern address mismatch");
        end
        take_rsp=1; responses=responses+1; returned[p]=returned[p]+1;
        $display("S %0d %0d %0d %0d %0d",active,edge_cycle,p,rsp_tag[p*16+:16],rsp_beat[p*4+:4]);
        active=-1; idx=idx+1;
        next_req=edge_cycle+2;
        if(idx%17==0 && idx<2176) next_req=next_req+3;
      end
      #0.499; clk=1; #0.001;
      refs=0; acts=0; reads=0; writes=0;
      for(p=0;p<32;p=p+1) begin
        refs=refs+dut.st_ref[p]; acts=acts+dut.st_act[p];
        reads=reads+dut.st_rd[p]; writes=writes+dut.st_wr[p];
        if(dut.q_n[p]>qmax) qmax=dut.q_n[p];
        if(dut.r_n[p]>rmax) rmax=dut.r_n[p];
        if(dut.q_n[p]>1 || dut.r_n[p]>1) $fatal(1,"queue credit violated");
        if(take_rsp && (dut.q_n[p]!=0 || dut.r_n[p]!=0)) $fatal(1,"queues not empty after response");
      end
      if(wr_done!=0 || writes!=0) $fatal(1,"unexpected write");
      if(take_req) $display("R %0d %0d %0d %0d %0d %0d %0d %0d",active,edge_cycle,pc,addr,req_tag[pc*16+:16],dut.h_tcol[pc],refs,acts);
      clk=0;
      if(responses==2176) begin
        for(p=0;p<32;p=p+1) begin
          if(accepted[p]!=68 || returned[p]!=68) $fatal(1,"per-channel totals");
          $display("PC %0d %0d %0d %0d %0d %0d",p,accepted[p],returned[p],dut.st_rd[p],dut.st_ref[p],dut.st_act[p]);
        end
        if(requests!=2176 || reads!=2176 || active!=-1) $fatal(1,"total mismatch");
        $display("SUMMARY %0d %0d %0d %0d %0d %0d %0d %0d %0d",start_cycle,edge_cycle,edge_cycle+2,requests,responses,refs,acts,qmax,rmax);
        $finish;
      end
    end
    $fatal(1,"bounded cycle timeout");
  end
endmodule
