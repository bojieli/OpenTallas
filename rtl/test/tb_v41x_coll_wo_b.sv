`timescale 1ns/1ps
// First 64 rows of real 200K layer-0 wo_b TP4 partials, four 512-bit words.
// Hex provenance is pinned by tools/rtl_v41x_coll_die_gate.py.
module tb_v41x_coll_wo_b;
  localparam N=4, FW=512, TAGW=8, PW=FW+3+TAGW;
  reg clk=0,rst_n=0;
  always #5 clk=~clk;
  reg [FW-1:0] p0[0:3],p1[0:3],p2[0:3],p3[0:3],expw[0:3];
  wire [N-1:0] ready,ov,ol,oe,flt;
  wire [N*FW-1:0] od;
  wire [N*N-1:0] txv;
  wire [N*PW-1:0] txr;
  wire [2*N*N-1:0] co;
  integer cyc=0, recv[0:3], first_out=-1, last_out=-1;
  genvar s,t;
  generate for(s=0;s<N;s=s+1) begin : die
    integer sent=0;
    wire [N-1:0] rv;
    wire [N*PW-1:0] rr;
    wire [2*N-1:0] ci;
    wire [FW-1:0] local_word = (s==0)?p0[sent]:(s==1)?p1[sent]:(s==2)?p2[sent]:p3[sent];
    for(t=0;t<N;t=t+1) begin : link
      if(s==t) begin
        assign rv[t]=0; assign rr[t*PW+:PW]=0; assign ci[2*t+:2]=0;
      end else begin
        assign rv[t]=txv[t*N+s]; assign rr[t*PW+:PW]=txr[t*PW+:PW];
        assign ci[2*t+:2]=co[2*(t*N+s)+:2];
      end
    end
    ot_rom_oneshot_die_px #(.N(4),.RANK(s),.LANES(16),.TAGW(8),
      .DEPTH(16),.RELAY(0),.PAIRWISE(1),.ADD_LAT(3)) dut (
      .clk(clk),.rst_n(rst_n),.in_valid(rst_n && cyc>=20+3*s && sent<4),
      .in_ready(ready[s]),.in_data(local_word),.in_last(sent==3),
      .in_mode(1'b0),.in_tag(8'd19),
      .tx_valid(txv[s*N+:N]),.tx_rec(txr[s*PW+:PW]),.tx_ready(4'b1111),.cr_in(ci),
      .rx_valid(rv),.rx_rec(rr),.cr_out(co[2*s*N+:2*N]),
      .rl_tx_valid(),.rl_tx_rec(),.rl_rx_valid(4'b0),.rl_rx_rec({N*PW{1'b0}}),
      .out_valid(ov[s]),.out_data(od[s*FW+:FW]),.out_last(ol[s]),
      .out_rank(),.out_err(oe[s]),.fault(flt[s]),.fault_code());
    always @(posedge clk) if(rst_n && cyc>=20+3*s && sent<4 && ready[s]) sent<=sent+1;
    always @(posedge clk) if(ov[s]) begin
      if(od[s*FW+:FW] !== expw[recv[s]] || ol[s] !== (recv[s]==3) || oe[s])
        $fatal(1,"wo_b rank=%0d word=%0d mismatch got=%h exp=%h",s,recv[s],od[s*FW+:FW],expw[recv[s]]);
      recv[s]=recv[s]+1;
      if (s==0) begin
        if (first_out<0) first_out=cyc;
        last_out=cyc;
      end
    end
  end endgenerate
  initial begin
    for(integer j=0;j<4;j=j+1) recv[j]=0;
    $readmemh("rtl/test/data/v41x_coll/wo_b_rank0.hex",p0);
    $readmemh("rtl/test/data/v41x_coll/wo_b_rank1.hex",p1);
    $readmemh("rtl/test/data/v41x_coll/wo_b_rank2.hex",p2);
    $readmemh("rtl/test/data/v41x_coll/wo_b_rank3.hex",p3);
    $readmemh("rtl/test/data/v41x_coll/wo_b_expected.hex",expw);
    repeat(5) @(posedge clk); rst_n=1;
    wait(recv[0]==4 && recv[1]==4 && recv[2]==4 && recv[3]==4);
    repeat(3) @(posedge clk);
    if(|flt) $fatal(1,"wo_b fault %b",flt);
    $display("WO_B_PASS 64_real_layer0_rows 4_ranks pairwise_exact skewed first=%0d last=%0d",first_out,last_out);
    $finish;
  end
  always @(posedge clk) begin cyc<=cyc+1; if(cyc>200) $fatal(1,"wo_b timeout"); end
endmodule
