`timescale 1ns/1ps
// DIE-HBM-61/CUTS 11-03: ot_hfd_coll_q3_vm_core #(WCUT,VOH) vs the main 3465966986 core (modules prefixed gold_).
// Every output equal on every edge, except writer_fault == gold writer_fault one edge later (WCUT 1).
// Stimulus: random lanes with legal COLL addresses; slot_valid/slot_owner = the gold decode of this edge (a legal
// compiler reservation) except for rare injected errors; rare address/slot errors; periodic resets (fault is sticky).
module tb_q3vm_cut;
  parameter integer WCUT=1, VOH=1, MUTW=0, CYC=60000, ERR=400;
  reg clk=0; always #0.5 clk=~clk;
  reg rst_n=0; reg [1:0] sid=0; reg [3:0] rgx_v=0; reg [159:0] rgx_addr=0; reg [2047:0] rgx_data=0; reg rgx_vm=1;
  reg tkw_v=0; reg [567:0] tkw_d=0; reg [4:0] islot=0; reg [7:0] sv=0; reg [31:0] so=0; reg [23:0] vsel=0; reg [2047:0] rd=0;
  wire [2047:0] a_as, b_as; wire [8*281-1:0] a_kq, b_kq; wire a_f, b_f;
  `define PORTS(P) .vmasm_clk({16{clk}}),.vmasm_sel(vsel),.vmasm_rd_il(rd),.writer_clk_rgx_data0(clk),.writer_clk_rgx_data1(clk),\
    .writer_clk_rgx_data2(clk),.writer_clk_rgx_data3(clk),.writer_clk_rgx_ctrl(clk),.writer_clk_tkw(clk),.writer_clk_meta(clk),\
    .writer_clk_body(clk),.writer_clk_bank0(clk),.writer_clk_bank1(clk),.writer_clk_bank2(clk),.writer_clk_bank3(clk),\
    .writer_clk_bank4(clk),.writer_clk_bank5(clk),.writer_clk_bank6(clk),.writer_clk_bank7(clk),.writer_rst_n(rst_n),\
    .writer_sid(sid),.writer_rgx_v(rgx_v),.writer_rgx_addr(rgx_addr),.writer_rgx_data0(rgx_data[511:0]),\
    .writer_rgx_data1(rgx_data[1023:512]),.writer_rgx_data2(rgx_data[1535:1024]),.writer_rgx_data3(rgx_data[2047:1536]),\
    .writer_rgx_vm(rgx_vm),.writer_tkw_v(tkw_v),.writer_tkw_d(tkw_d),.writer_ingress_slot(islot),.writer_slot_valid(sv),\
    .writer_slot_owner(so),.vmasm_as_il(P``_as),.writer_kq0(P``_kq[280:0]),.writer_kq1(P``_kq[561:281]),\
    .writer_kq2(P``_kq[842:562]),.writer_kq3(P``_kq[1123:843]),.writer_kq4(P``_kq[1404:1124]),.writer_kq5(P``_kq[1685:1405]),\
    .writer_kq6(P``_kq[1966:1686]),.writer_kq7(P``_kq[2247:1967]),.writer_fault(P``_f)
  gold_ot_hfd_coll_q3_vm_core u_g(`PORTS(a));
  ot_hfd_coll_q3_vm_core #(.WCUT(WCUT),.VOH(VOH)) u_n(`PORTS(b));
  defparam u_n.u_writer.MUT = MUTW;
  reg af_d=0; always @(posedge clk) af_d<=a_f;
  wire ef = WCUT ? af_d : a_f;
  function [39:0] laddr(input [1:0] s); reg b18; begin
    b18=$urandom%2; laddr=0; laddr[18]=b18; laddr[17:16]=b18?2'd0:s; laddr[15:3]=13'($urandom%8191); end endfunction
  integer cyc, l, bad=0, nc=0, nf=0, nfr=0, nr=0, ph, inj=0;
  initial begin
    for(cyc=0;cyc<CYC;cyc=cyc+1) begin
      @(negedge clk);
      ph=cyc%3000; rst_n=(ph>=4); if(ph==4) nr=nr+1;
      sid=sid; rgx_vm=1;
      // slot reservation for THIS edge's launch = the gold decode of the state captured last edge (legal programme)
      sv=u_g.u_writer.core.used; so=u_g.u_writer.core.bank_owner;
      rgx_v=4'($urandom); tkw_v=$urandom%2;
      for(l=0;l<4;l=l+1) rgx_addr[l*40+:40]=laddr(sid);
      tkw_d={laddr(sid),16'($urandom),{16{$urandom}}};
      for(l=0;l<64;l=l+1) rgx_data[l*32+:32]=$urandom;
      islot={tkw_v,rgx_v};
      if($urandom%ERR==0) begin inj=inj+1; case($urandom%5)
        0: sv=sv^8'(1<<($urandom%8)); 1: so=so^32'(1<<($urandom%32)); 2: islot=islot^5'(1<<($urandom%5));
        3: rgx_addr[($urandom%4)*40]=1'b1; 4: rgx_vm=0; endcase end
      vsel=$urandom; for(l=0;l<64;l=l+1) rd[l*32+:32]=$urandom;
      if(cyc>8 && ph>8) begin
        nc=nc+1; nf=nf+b_f;
        if(a_as!==b_as || a_kq!==b_kq || ef!==b_f) begin bad=bad+1;
          if(bad<=5) $display("Q3VM_EQ_MISMATCH cyc=%0d as %b kq %b fault gold_d=%b new=%b",cyc,a_as===b_as,a_kq===b_kq,ef,b_f); end
      end
    end
    if(bad==0) $display("Q3VM_EQ PASS WCUT=%0d VOH=%0d MUTW=%0d compared=%0d fault_cycles=%0d resets=%0d injected=%0d",WCUT,VOH,MUTW,nc,nf,nr,inj);
    else $display("Q3VM_EQ FAIL WCUT=%0d VOH=%0d MUTW=%0d mismatches=%0d of %0d",WCUT,VOH,MUTW,bad,nc);
    $finish;
  end
endmodule
