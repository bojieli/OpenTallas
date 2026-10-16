`timescale 1ns/1ps
`default_nettype none
// Bench for ot_hgi_coll_inj_idx_join (INJLAT 12). It drives the COLL request pins exactly as
// ot_hgi_coll_q_static_ctl_v4 does: registered at edge P, changing after P. The SU answer is a registered
// model updated at P+9. The IDX producer is a header-exact model of ot_hbm_idx_topk_link_static tx
// ({1, 8'hff, rank, (rank-gbase)*64+group*4+l, data}, all four lanes at one edge, emits 8 edges apart, 16 emits).
// The bench samples inj_d at P+12 as the COLL qslots capture does and compares it with the expected word.
// Phase A: 16 emits x 4 flits through IDX lanes, interleaved with SU reads and mixed-lane edges; no fault allowed.
// Phase B: a read of an overwritten (stale) flit must raise fault.
module tb_hgi_coll_inj_idx_join;
 parameter integer MUT=0;
 localparam integer L=12;
 reg clk=0, rst_n=0;
 always #1 clk=~clk;
 reg [1:0] inj_rd=0; reg [31:0] inj_idx=0; reg [159:0] inj_addr=0;
 reg [1023:0] su_d=0; reg [3:0] tx_v=0; reg [2179:0] tx=0;
 wire [1023:0] inj_d; wire fault;
 ot_hgi_coll_inj_idx_join #(.INJLAT(L),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.inj_rd(inj_rd),.inj_idx(inj_idx),
  .inj_addr(inj_addr),.su_inj_d(su_d),.idx_tx_v(tx_v),.idx_tx(tx),.inj_d(inj_d),.fault(fault));
 function automatic [511:0] idxdata(input integer f);
  integer k; begin for(k=0;k<16;k=k+1) idxdata[32*k+:32]=32'h5c000000 ^ (f*977+k*131); end endfunction
 function automatic [255:0] sudata(input [39:0] a);
  integer k; begin for(k=0;k<8;k=k+1) sudata[32*k+:32]=a[31:0]*32'd2654435761+k; end endfunction
 integer cyc=0;
 reg [1:0] h_rd [0:4095]; reg [31:0] h_idx [0:4095]; reg [159:0] h_addr [0:4095];
 integer errors=0, idx_words=0, su_words=0;
 localparam integer RANK=3, GBASE=1;
 // ------------------------------------------------ calendar
 // emit g at edge T_g = 40+8g (tx pins change after T_g). Its 4 flits are read by COLL requests at
 // P = T_g-7+d for d in {0,1}: lanes {l0,l1} = flits {2d,2d+1}; P+10 = T_g+3+d >= T_g+3.
 // SU requests run at every other edge; edges with d=1 put lane0 on SU and lane1 on IDX as a mixed case
 // (flit 2 is then read by lane1 at d=2).
 function automatic integer flitof(input integer g,input integer l); flitof=(RANK-GBASE)*64+g*4+l; endfunction
 always @(posedge clk) begin
  cyc<=cyc+1;
  h_rd[cyc]<=inj_rd; h_idx[cyc]<=inj_idx; h_addr[cyc]<=inj_addr;
 end
 task automatic drive(input integer c);
  integer g, d, j; reg [39:0] lo;
  begin
   inj_rd=0; inj_idx=0; inj_addr=0; tx_v=0;
   // IDX emits
   if(c>=40 && c<40+8*16 && (c-40)%8==0) begin
    g=(c-40)/8; tx_v=4'hf;
    for(j=0;j<4;j=j+1) tx[j*545+:545]={1'b1,8'hff,8'(RANK),16'(flitof(g,j)),idxdata(flitof(g,j))};
   end
   // IDX reads (phase A)
   for(g=0;g<16;g=g+1) for(d=0;d<3;d=d+1) if(c==40+8*g-7+d) begin
    if(d==0) begin
     for(j=0;j<2;j=j+1) begin lo={1'b1,39'(flitof(g,j)*16)}; inj_rd[j]=1; inj_idx[16*j+:16]=16'(flitof(g,j)); inj_addr[80*j+:80]={lo+40'd8,lo}; end
    end else if(d==1) begin
     lo={1'b0,39'(c*16)}; inj_rd[0]=1; inj_idx[0+:16]=16'(c); inj_addr[0+:80]={lo+40'd8,lo};
     lo={1'b1,39'(flitof(g,3)*16)}; inj_rd[1]=1; inj_idx[16+:16]=16'(flitof(g,3)); inj_addr[80+:80]={lo+40'd8,lo};
    end else begin
     lo={1'b1,39'(flitof(g,2)*16)}; inj_rd[0]=1; inj_idx[0+:16]=16'(flitof(g,2)); inj_addr[0+:80]={lo+40'd8,lo};
     lo={1'b0,39'(c*16+7)}; inj_rd[1]=1; inj_idx[16+:16]=16'(c); inj_addr[80+:80]={lo+40'd8+40'd5,lo}; // TKM-mode SU read
    end
   end
   // SU-only reads on odd edges outside the IDX read edges
   if(inj_rd==0 && c>=20 && c<200 && c%2==1) for(j=0;j<2;j=j+1) begin
    lo={1'b0,39'(c*32+j*16)}; inj_rd[j]=1; inj_idx[16*j+:16]=16'(c); inj_addr[80*j+:80]={lo+40'd8,lo};
   end
   // phase B (after the fault check at 230): stale read of emit 0 flit 0 (overwritten by emit 2)
   if(c==240) begin lo={1'b1,39'(flitof(0,0)*16)}; inj_rd[0]=1; inj_idx[0+:16]=16'(flitof(0,0)); inj_addr[0+:80]={lo+40'd8,lo}; end
  end
 endtask
 // SU model: register updated at P+9 from the request launched at P.
 always @(posedge clk) begin : su_model
  integer j; reg [159:0] a;
  if(cyc>=L-4) begin
   a=h_addr[cyc-(L-4)];
   for(j=0;j<2;j=j+1) su_d[512*j+:512] <= (h_rd[cyc-(L-4)][j] && !a[80*j+39]) ? {sudata(a[80*j+40+:40]),sudata(a[80*j+:40])} : {16{32'hdeadbeef}};
  end
 end
 // COLL capture model at P+12
 always @(posedge clk) begin : coll_capture
  integer j; reg [159:0] a; reg [31:0] ix; reg [511:0] exp;
  if(cyc>=L-1 && cyc<235) begin
   a=h_addr[cyc-(L-1)]; ix=h_idx[cyc-(L-1)];
   for(j=0;j<2;j=j+1) if(h_rd[cyc-(L-1)][j]) begin
    if(a[80*j+39]) begin exp=idxdata(ix[16*j+:16]); idx_words=idx_words+1; end
    else begin exp={sudata(a[80*j+40+:40]),sudata(a[80*j+:40])}; su_words=su_words+1; end
    if(inj_d[512*j+:512]!==exp) begin
     if(errors<8) $display("MISMATCH cyc=%0d lane=%0d idxsrc=%0d ix=%0d got=%h exp=%h", cyc, j, a[80*j+39], ix[16*j+:16], inj_d[512*j+:32], exp[31:0]);
     errors=errors+1;
    end
   end
  end
 end
 integer c;
 reg faultA, faultB;
 initial begin
  for(c=0;c<4;c=c+1) @(posedge clk);
  #0.5 rst_n=1;
  for(c=4;c<300;c=c+1) begin
   @(posedge clk); #0.5 drive(cyc);
   if(cyc==232) faultA=fault;
  end
  faultB=fault;
  $display("inj_idx_join MUT=%0d idx_words=%0d su_words=%0d mismatches=%0d faultA=%0d faultB=%0d",
           MUT, idx_words, su_words, errors, faultA, faultB);
  if(errors==0 && faultA===1'b0 && faultB===1'b1 && idx_words==64) $display("PASS"); else $display("FAIL");
  $finish;
 end
endmodule
`default_nettype wire
