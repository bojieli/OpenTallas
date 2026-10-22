`timescale 1ns/1ps
// STW-S81c-COLLA2-LEP 10-22: cycle equivalence of ot_sram_showahead_1r1w_land (RX landing register, macro reads one
// row ahead) vs the shipped ot_sram_showahead_1r1w (LOCAL_HIT/LOCAL_RA/LOCAL_WA, WREG 1) and a behavioural FIFO, in
// the lep RX shape (W 553, DEPTH 12, SB 8).  Random credit-legal writes / pair pops with occupancy phases 0..DEPTH;
// q compared EVERY cycle the FIFO is non-empty.  +define+MUT_NOAHEAD / MUT_NOWHIT must FAIL.
module tb_showahead_land;
  localparam integer W=553, AW=4, DEPTH=12, SB=8, NS=(W+SB-1)/SB;
  reg clk=0, rn=0; always #1 clk=~clk;
  reg we; reg [AW-1:0] wp, rp; reg [AW:0] n; reg [W-1:0] wd; reg adv_a, adv_b;
  wire [W-1:0] q_old, q_new;
  ot_sram_showahead_1r1w #(.W(W),.AW(AW),.LOCAL_HIT(1),.SB(SB),.LOCAL_RA(1),.LOCAL_WA(1),.DEPTH(DEPTH)) u_old(
    .clk(clk),.rst_n({NS{rn}}),.we(we),.wa(wp),.wd(wd),.ra(rp),.q(q_old),.advance_a(adv_a),.advance_b(adv_b));
  ot_sram_showahead_1r1w_land #(.W(W),.AW(AW),.SB(SB),.DEPTH(DEPTH)) u_new(
    .clk(clk),.rst_n({NS{rn}}),.we(we),.wa(wp),.wd(wd),.we_l(we),.wa_l(wp),.advance_a(adv_a),.advance_b(adv_b),.q(q_new));
  reg [W-1:0] mem [0:DEPTH-1];
  integer cyc=0, chk=0, bad=0, phase=0, maxn=0, hitw=0, ahead=0, k;
  wire pop = adv_a && adv_b;
  function automatic [W-1:0] rnd(); integer i; begin for(i=0;i<W;i=i+32) rnd[i+:32]=$urandom; end endfunction
  // drive on negedge (stimulus), check on negedge before changing (q settled after the posedge)
  always @(negedge clk) begin
    if(rn && n!=0) begin
      chk=chk+1;
      if(q_new!==mem[rp] || q_old!==mem[rp]) begin bad=bad+1;
        if(bad<6) $display("MISMATCH cyc %0d n %0d rp %0d new_ok %0d old_ok %0d", cyc, n, rp, q_new===mem[rp], q_old===mem[rp]); end
    end
    if(cyc%400==0) phase=$urandom%4;            // 0 trickle, 1 fill (writes >> pops), 2 drain, 3 back-to-back both
    we = rn && n!=DEPTH && (phase==1 ? ($urandom%8!=0) : phase==2 ? ($urandom%4==0) : phase==3 ? 1'b1 : ($urandom%3==0));
    adv_a = rn && n!=0 && (phase==1 ? ($urandom%4==0) : phase==2 ? ($urandom%8!=0) : phase==3 ? ($urandom%2==0) : ($urandom%2==0));
    adv_b = adv_a ? 1'b1 : ($urandom%2==0);      // advance = a && b (pair release); b alone never advances
    wd = rnd();
    if(we && wp==(pop ? ((rp==DEPTH-1)?0:rp+1) : rp)) hitw=hitw+1;
    if(pop && n>=2) ahead=ahead+1;
    cyc=cyc+1;
  end
  always @(posedge clk) if(rn) begin
    if(we) mem[wp] <= wd;
    wp <= we ? ((wp==DEPTH-1)?0:wp+1) : wp;
    rp <= pop ? ((rp==DEPTH-1)?0:rp+1) : rp;
    n <= n + we - pop;
    if(n>maxn) maxn=n;
  end
  initial begin
    wp=0; rp=0; n=0; we=0; adv_a=0; adv_b=0; wd=0;
    for(k=0;k<DEPTH;k=k+1) mem[k]=0;
    repeat(6) @(posedge clk); @(negedge clk) rn=1;
    repeat(200000) @(posedge clk);
    $display("LAND_STATS checks %0d mismatches %0d max_occupancy %0d write_hit_to_next_head %0d pops_with_n_ge2 %0d", chk, bad, maxn, hitw, ahead);
    if(bad==0 && chk>100000 && maxn==DEPTH && hitw>1000 && ahead>1000) $display("LAND_EQ PASS"); else $display("LAND_EQ FAIL");
    $finish;
  end
endmodule
