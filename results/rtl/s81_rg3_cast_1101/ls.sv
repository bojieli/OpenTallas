module ls;
  reg ck=0, rst=1; reg [3:0] sid; reg [512:0] qi; reg [275:0] si; reg [1087:0] rri;
  wire [512:0] qo_a, qo_b; wire [275:0] so_a, so_b; wire [183:0] rqo_a, rqo_b; wire f_a, f_b;
  dsdv_idx_rg3_old a(.ck(ck),.rst(rst),.sid(sid),.qi(qi),.qo(qo_a),.si(si),.so(so_a),.rqo(rqo_a),.rri(rri),.fault(f_a));
  dsdv_idx_rg3     b(.ck(ck),.rst(rst),.sid(sid),.qi(qi),.qo(qo_b),.si(si),.so(so_b),.rqo(rqo_b),.rri(rri),.fault(f_b));
  integer c, bad=0, act=0, seed=1;
  task rnd; integer k; begin
    for (k=0;k<17;k=k+1) qi[k*32 +: 32] = $random(seed); qi[512]=$random(seed);
    for (k=0;k<9;k=k+1) si[k*32 +: 32] = $random(seed);
    for (k=0;k<34;k=k+1) rri[k*32 +: 32] = $random(seed);
  end endtask
  initial begin
    sid = 4'd2; rnd;
    for (c=0;c<20000;c=c+1) begin
      if (c==8) rst=0;
      rnd; #1 ck=1; #1 ck=0;
      if ({qo_a,so_a,rqo_a,f_a} !== {qo_b,so_b,rqo_b,f_b}) begin bad=bad+1; if (bad<4) $display("MISMATCH cycle %0d", c); end
      if (a.ipd_s !== b.ipd_s) bad=bad+1;
      if (a.ws == 3'd3) act=act+1;
    end
    $display("RG3_LOCKSTEP cycles=%0d mismatches=%0d scan_item_cycles=%0d", c, bad, act); $finish;
  end
endmodule
