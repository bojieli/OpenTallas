`timescale 1ns/1ps
// Actual production-width endpoint boundaries, every edge. Candidate changes
// sequence preclassification/timeout/write registration; neither deadline nor
// expected age is shifted. The two variants have separate identical channels.
module tb_coll_safe2_oldread_cycles;
 parameter integer MUT=0;
 localparam integer W=552,SQ=10,CR=512,CH=20,FW=SQ+1+W+32,RW=1+SQ+10+32;
 reg clk=0,rst_n=0;
 always #0.5 clk=~clk;
 reg [31:0] rng=32'h81335577;
 reg [1:0] iv=0,il=0,ready=0;
 reg [W-1:0] data[0:1];
 wire ir[0:1][0:1],ov[0:1][0:1],ol[0:1][0:1],fault[0:1][0:1];
 wire [W-1:0] od[0:1][0:1];
 wire fv[0:1][0:1],rv[0:1][0:1],finv[0:1][0:1],rinv[0:1][0:1];
 wire [FW-1:0] f[0:1][0:1],fin[0:1][0:1];
 wire [RW-1:0] r[0:1][0:1],rin[0:1][0:1];
 wire [31:0] tx[0:1][0:1],rx[0:1][0:1],replay[0:1][0:1];
 genvar v,g;
 generate for(v=0;v<2;v=v+1) begin:variant
  for(g=0;g<2;g=g+1) begin:side
   ot_s81ph_link_ep_safe2 #(.FLIT_BYTES(69),.CREDITS(CR),.SEQW(SQ),.CHANNEL_CYCLES(CH),
    .SRAM(1),.PIPE(2),.DNR(1),.RXPIPE(v),.TOREG(v),.MWR(v),.OLDREAD(v)) u_ep(
    .clk(clk),.rst_n(rst_n),.mem_rst_n({176{rst_n}}),.ch_b(1'b0),
    .in_valid(iv[g]),.in_ready(ir[v][g]),.in_data(data[g]),.in_last(il[g]),
    .out_valid(ov[v][1-g]),.out_ready(ready[1-g]),.out_data(od[v][1-g]),.out_last(ol[v][1-g]),
    .f_tx_v(fv[v][g]),.f_tx(f[v][g]),.f_rx_v(finv[v][g]),.f_rx(fin[v][g]),
    .r_tx_v(rv[v][g]),.r_tx(r[v][g]),.r_rx_v(rinv[v][g] && !(c>=900 && c<1200)),.r_rx(rin[v][g]),
    .fault(fault[v][g]),.fault_code(),.credit_stalls(),.st_flits_tx(tx[v][g]),
    .st_flits_rx_ok(rx[v][g]),.st_crc_err(),.st_naks(),.st_replays(replay[v][g]),
    .st_timeouts(),.st_retx_flits(),.st_max_replay_occ());
   ot_dsrom_link_chan #(.W(FW),.MAXD(CH),.ERR_PERIOD(53),.ERR_OFFSET(3+g),.ERR_STRIDE(37)) uf(
    .clk(clk),.rst_n(rst_n),.delay(16'd0),.in_valid(fv[v][g]),.in_data(f[v][g]),
    .out_valid(finv[v][1-g]),.out_data(fin[v][1-g]),.err_injected());
   ot_dsrom_link_chan #(.W(RW),.MAXD(CH),.ERR_PERIOD(29),.ERR_OFFSET(3+g),.ERR_STRIDE(11)) ur(
    .clk(clk),.rst_n(rst_n),.delay(16'd0),.in_valid(rv[v][1-g]),.in_data(r[v][1-g]),
    .out_valid(rinv[v][g]),.out_data(rin[v][g]),.err_injected());
  end
 end endgenerate
 wire rb_forward = variant[1].side[0].u_ep.g_rb_safe.u_m.g_slice[0].hit || variant[1].side[1].u_ep.g_rb_safe.u_m.g_slice[0].hit;
 wire fifo_forward = (variant[1].side[0].u_ep.g_fifo_safe.rd_group[0] && variant[1].side[0].u_ep.g_fifo_safe.u_m.g_slice[0].hit) || (variant[1].side[1].u_ep.g_fifo_safe.rd_group[0] && variant[1].side[1].u_ep.g_fifo_safe.u_m.g_slice[0].hit);
 integer c=0,err=0,checks=0,takes=0,returns=0,refills=0,rb_hits=0,fifo_hits=0,timeouts=0,j,b;
 reg [1:0] prev_valid=0;
 initial begin data[0]=0;data[1]=0;end
 always @(negedge clk) begin
  c=c+1;
  if(c>2) for(j=0;j<2;j=j+1) begin
   checks=checks+1;
   if(ir[0][j]!==ir[1][j] || ov[0][j]!==ov[1][j] ||
      fv[0][j]!==fv[1][j] || rv[0][j]!==rv[1][j] ||
      fault[0][j]!==fault[1][j] ||
      (ov[0][j] && {ol[0][j],od[0][j]}!=={ol[1][j],od[1][j]}) ||
      (fv[0][j] && f[0][j]!==f[1][j]) || (rv[0][j] && r[0][j]!==r[1][j])) begin
    err=err+1;
    if(err<8)$display("COLL_CYCLE_ERR cycle=%0d side=%0d ready=%b/%b ov=%b/%b fv=%b/%b rv=%b/%b",c,j,ir[0][j],ir[1][j],ov[0][j],ov[1][j],fv[0][j],fv[1][j],rv[0][j],rv[1][j]);
   end
   if(rst_n&&iv[j]&&ir[0][j])takes=takes+1;
   if(rst_n&&ov[0][j]&&ready[j])returns=returns+1;
   if(rst_n&&ov[0][j]&&!prev_valid[j])refills=refills+1;
   prev_valid[j]=ov[0][j];
  end
  if(rst_n&&(variant[1].side[0].u_ep.timeout||variant[1].side[1].u_ep.timeout))timeouts=timeouts+1;
  if(rst_n&&rb_forward)rb_hits=rb_hits+1;
  if(rst_n&&fifo_forward)fifo_hits=fifo_hits+1;
  rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
  rst_n=!(c<7 || (c>=1800&&c<1810));
  // Fill/stall, drain/refill, randomized simultaneous traffic, reset, repeat.
  ready=(c%900<180)?2'b00:((c%900<400)?2'b11:rng[1:0]);
  for(j=0;j<2;j=j+1) begin
   if(!rst_n)iv[j]=0;
   else if(!iv[j]||ir[0][j]) begin
    iv[j]=(c%900<650);il[j]=rng[j+2];
    for(b=0;b<W;b=b+1)data[j][b]=rng[(b+j)%32]^((b/32+c+j)&1);
   end
  end
  if(c==12000) begin
   if(err==0&&takes>1000&&returns>500&&refills>10&&fifo_hits>0&&timeouts>0)
    $display("COLL_CYCLES PASS checks=%0d accepts=%0d returns=%0d refills=%0d rb_hits=%0d fifo_hits=%0d timeouts=%0d resets=2 MUT=%0d",checks,takes,returns,refills,rb_hits,fifo_hits,timeouts,MUT);
   else $display("COLL_CYCLES FAIL errors=%0d accepts=%0d returns=%0d refills=%0d rb_hits=%0d fifo_hits=%0d timeouts=%0d MUT=%0d",err,takes,returns,refills,rb_hits,fifo_hits,timeouts,MUT);
   $finish;
  end
 end
endmodule
