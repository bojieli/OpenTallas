`timescale 1ns/1ps
module tb_idx_engine_static;
    parameter integer MUT = 0;
    localparam integer NK=4, NB=4, IH=32;
    reg clk=0; always #0.5 clk=~clk;
    reg rst_n=0,qv=0,kv=0;reg[3:0]keep=0,present=0;
    reg [7:0] qh=0;
    reg [511:0] qc=0; reg [31:0] qs=0; reg [15:0] qw=0;
    reg [2175:0] key=0;
    wire ar, br, av, bv; reg ready=1;
    wire [63:0]ascore,bscore;wire[3:0]ak,bk,af,bf;wire protocol_fault,online;assign br=1;
    wire [47:0] acnt,bcnt;
    ot_hdc_v41x_idx_engine_l #(.NK(NK),.IH(IH),.NB(NB),.FD(256),.FPL(7),.FML(5),.QL(5)) reference (
      .clk(clk),.rst_n(rst_n),.ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),
      .k_valid(kv),.k_ready(ar),.k_kv(present),.k_keep(keep),.k_key(key),
      .o_valid(av),.o_ready(ready),.o_kv(ak),.o_score(ascore),.o_fault(af),
      .cnt_keys_scored(acnt),.cnt_headsums_fused(),.cnt_faults());
    ot_hbm_idx_engine_static #(.MUT(MUT)) candidate(
     .clk(clk),.clk_tail(clk),.clk_chunk({4{clk}}),.clk_hslice({128{clk}}),.rst_n(rst_n),
     .ql_v(qv),.ql_head(qh),.ql_codes(qc),.ql_sc(qs),.ql_w(qw),.k_valid(kv),
     .k_kv(present),.k_keep(keep),.k_key(key),.o_valid(bv),.o_kv(bk),.o_score(bscore),.o_fault(bf),
     .cnt_keys_scored(bcnt),.cnt_headsums_fused(),.cnt_faults(),.online(online),.protocol_fault(protocol_fault));
    reg [71:0] expected[0:511], actual[0:511];
    integer an=0,bn=0,errors=0,cycle=0;
    reg [31:0] rng=32'hba87cd91;
    function automatic [31:0] next_random(input [31:0] x);
      reg [31:0] y; begin y=x^(x<<13);y=y^(y>>17);next_random=y^(y<<5);end
    endfunction
    always @(posedge clk) begin
      cycle=cycle+1;
      if (rst_n && av && ready) begin expected[an]={af,ak,ascore};an=an+1;end
      if (rst_n && bv && ready) begin actual[bn]={bf,bk,bscore};bn=bn+1;end
    end
    integer frame,h,j,n,cycles_wait;
    initial begin
      repeat(8) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);
      for(frame=0;frame<3;frame=frame+1) begin
        for(h=0;h<IH;h=h+1) begin
          @(negedge clk);qv=1;qh=h;
          for(j=0;j<16;j=j+1) begin rng=next_random(rng);qc[32*j+:32]=rng;end
          for(j=0;j<4;j=j+1) qs[8*j+:8]=120+(h%9);
          qw={1'b0,8'(120+h%7),7'(17+h)};
        end
        @(negedge clk);qv=0;repeat(100) @(negedge clk);
        for(n=0;n<64;n=n+1) begin
          if(!ar||!online)$fatal(1,"fixed launch slot not ready");
          kv=1;present=(n%11!=0)?4'hf:4'h5;keep=(n%5!=0)?4'hf:4'ha;
          for(integer kk=0;kk<4;kk=kk+1)begin
           for(j=0;j<16;j=j+1)begin rng=next_random(rng);key[544*kk+32*j+:32]=rng;end
           for(j=0;j<4;j=j+1)key[544*kk+512+8*j+:8]=121+((n+kk)%5);
          end
          ready=1;
          @(negedge clk);
        end
        kv=0;
        cycles_wait=0;
        while(an<64*(frame+1)||bn<64*(frame+1)) begin
          // Long legal output stall followed by changing consumer credit.
          ready=1;
          @(negedge clk);cycles_wait=cycles_wait+1;
          if(cycles_wait>2000) $fatal(1,"engine proof did not drain an=%0d bn=%0d",an,bn);
        end
      end
      for(n=0;n<192;n=n+1) if(expected[n]!==actual[n]) begin
        errors=errors+1;if(errors<5)$display("ENGINE_ERR n=%0d expected=%h actual=%h",n,expected[n],actual[n]);
      end
      $display("IDX_ENGINE_STATIC MUT=%0d beats=%0d refbeats=%0d errors=%0d cycle=%0d %s",MUT,bn,an,errors,cycle,errors==0?"PASS":"FAIL");
      if(errors!=0||protocol_fault)$fatal(1,"arithmetic/order mismatch");
      $finish;
    end
endmodule
