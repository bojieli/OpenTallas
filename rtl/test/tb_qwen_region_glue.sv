`timescale 1ns/1ps
module tb_qwen_region_glue;
  reg clk=0; always #5 clk=~clk;
  reg [127:0] wd;
  reg [3:0] gm;
  reg ws;
  reg [511:0] rd;
  wire [127:0] oq;
  wire [511:0] rq;
  integer mut=0, checks=0, errors=0, cyc, k;
  reg stop=0;
  wire ock=clk & !stop;
  ot_qwen_tile_operand u_op(.clk(ock),.w_d(wd),.gm_d(gm),.wsrc_d(ws),.w_q(oq));
  ot_qwen_tile_rqr_half u_rq(.clk(clk),.d(rd),.q(rq));
  reg [127:0] mq_ref, s2_ref, oq_extra;
  reg [3:0] gm_ref;
  reg ws_ref;
  reg [511:0] rq_ref;
  // Literal old MEM_PIPE/S2 recurrence (KV_LOCAL=0 means mq_kv=0).
  always @(posedge clk) begin
    mq_ref<=wd; gm_ref<=gm; ws_ref<=ws;
    for(integer j=0;j<8;j=j+1)
      s2_ref[16*j+:16]<=(!gm_ref[j/2]||ws_ref)?16'd0:mq_ref[16*j+:16];
    rq_ref<=rd;
    oq_extra<=oq;
  end
  wire [127:0] got_o=(mut==1)?oq_extra:oq;
  wire [511:0] got_r=(mut==2)?{rq[511:2],rq[0],rq[1]}:rq;
  reg [31:0] rng=32'h794e1b35;
  function automatic [31:0] advance(input [31:0] a);
    advance={a[30:0],a[31]^a[21]^a[1]^a[0]};
  endfunction
  initial begin
    if($value$plusargs("MUT=%d",mut)) begin end
    wd=0;gm=0;ws=0;rd=0;
    for(cyc=0;cyc<258;cyc=cyc+1) begin
      @(negedge clk);
      for(k=0;k<16;k=k+1) begin rng=advance(rng);rd[32*k+:32]=rng;end
      for(k=0;k<4;k=k+1) begin rng=advance(rng);wd[32*k+:32]=rng;end
      gm=cyc%16;ws=(cyc%5)==0;
      if(mut==3 && cyc==40) stop=1;
      @(posedge clk); #1;
      if(cyc>=2) begin
        checks=checks+2;
        if(got_o!==s2_ref)begin errors=errors+1;if(errors<5)$display("REGION_GLUE_MISMATCH operand cyc=%0d",cyc);end
        if(got_r!==rq_ref)begin errors=errors+1;if(errors<5)$display("REGION_GLUE_MISMATCH rqr cyc=%0d",cyc);end
      end
    end
    if(errors!=0)begin $display("REGION_GLUE_FAIL mut=%0d errors=%0d checks=%0d",mut,errors,checks);$fatal(1,"exact recurrence mismatch");end
    $display("REGION_GLUE_PASS checks=%0d operand_edges=2 rqr_edges=1",checks);$finish;
  end
endmodule
