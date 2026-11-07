`timescale 1ps/1ps
module tb;
  localparam W=64, D=4, KW=6;
  logic fc=0, rc=0, fs=0, rst=0;
  logic [W-1:0] data=0;
  logic [KW-1:0] strap=0;
  wire [W-1:0] qa[2], qb[2];
  wire [1:0] ra, rb, fa, fb;
  logic [W-1:0] qb_p[2]; logic [1:0] rb_p=0, fb_p=0;
  integer same_cycle_diffs=0;
  integer errors=0, checks=0, ready_checks=0, seed, cases, phase, start_f, start_r;
  for(genvar g=0;g<2;g++) begin : modes
    ot_dp_clk_landing_cas #(.W(W),.DEPTH(D),.WREG(1),.FREG(1),.DSREP(8),.WRITE_CHUNK(8),.WFALL(g)) dut
      (.fclk(fc),.t_rst_n(fs),.clk(rc),.rst_n(rst),.strap_k(strap),.d(data),.q(qa[g]),.ready(ra[g]),.fault(fa[g]));
    ot_dp_clk_landing_cas_ref #(.W(W),.DEPTH(D),.WREG(0),.FREG(0),.DSREP(1),.WFALL(g)) ref_i
      (.fclk(fc),.t_rst_n(fs),.clk(rc),.rst_n(rst),.strap_k(KW'(strap-2)),.d(data),.q(qb[g]),.ready(rb[g]),.fault(fb[g]));
  end
  task check_outputs;
    for(integer g=0;g<2;g++) begin
      checks++;
      if(ra[g] && rb_p[g]) begin
        ready_checks++;
        if(qa[g] != qb[g]) same_cycle_diffs++;
        if(qa[g] !== qb_p[g] || fa[g] || fb_p[g]) begin
          if(errors<8) $display("DIFF mode=%0d check=%0d phase=%0d K=%0d data=%h/%h fault=%b/%b",g,checks,phase,strap,qa[g],qb_p[g],fa[g],fb_p[g]);
          errors++;
        end
      end
      qb_p[g]=qb[g];rb_p[g]=rb[g];fb_p[g]=fb[g];
    end
  endtask
  initial begin
    if(!$value$plusargs("seed=%d",seed))seed=11;
    if(!$value$plusargs("n=%d",cases))cases=120;
    for(integer t=0;t<cases;t++) begin
      phase=25+($urandom(seed)%780);
      start_f=2+($urandom%13);
      start_r=2+($urandom%13);
      strap=KW'($urandom%64);
      if(t<cases/2) begin strap=6'd4; start_r=start_f+($urandom%2); end
      fs=0;rst=0;fc=0;rc=0;rb_p=0;fb_p=0;
      fork
        begin
          for(integer c=0;c<180;c++) begin
            #200;data={$urandom,$urandom};
            #216;fc=1;
            #417;fc=0;
            if(c==start_f)fs=1;
            if(c==105)fs=0;
            if(c==113)fs=1;
          end
        end
        begin
          #(phase);
          for(integer c=0;c<180;c++) begin
            #416;rc=1;
            #1;check_outputs();
            #416;rc=0;
            if(c==start_r)rst=1;
            if(c==109)rst=0;
            if(c==118)rst=1;
          end
        end
      join
      // Reset all state through the declared synchronous resets before another
      // unrelated strap/start frame. Data is deliberately compared even while
      // invalid: both versions have identical storage and reset semantics.
      fs=0;rst=0;
      repeat(16) begin #416;fc=1;rc=1;#417;fc=0;rc=0;end
    end
    $display("FREG_PIN_CYCLE_EQ cases=%0d modes=2 checks=%0d ready_checks=%0d errors=%0d zero_delay_diffs=%0d %s",cases,checks,ready_checks,errors,same_cycle_diffs,(errors==0 && ready_checks>0 && same_cycle_diffs>0)?"PASS":"FAIL");
    if(errors!=0 || ready_checks==0 || same_cycle_diffs==0)$fatal(1,"writer chunk proof failed");
    $finish;
  end
endmodule
