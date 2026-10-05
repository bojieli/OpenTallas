`timescale 1ns/1ps
module tb_spec_token_reset_repro;
 reg clk=0,rst_n=0,n_set=0,tw_v=0,req_v=0;
 always #0.5 clk=~clk;
 reg [31:0] n_val=0,tw_pos=0,req_pos=0;reg [16:0] tw_tok=0;
 wire [3:0] ready,v,p,l,e;wire [31:0] n[0:3],a[0:3];wire [16:0] t[0:3];
`define PORTS(I) .clk(clk),.rst_n(rst_n),.n_set(n_set),.n_val(n_val),.n(n[I]),.tw_v(tw_v),.tw_pos(tw_pos),.tw_tok(tw_tok),.req_v(req_v),.req_ready(ready[I]),.req_kind(4'd10),.req_idx(16'd0),.req_pos(req_pos),.a_v(v[I]),.a_addr(a[I]),.a_tok(t[I]),.a_pad(p[I]),.a_last(l[I]),.a_err(e[I])
 ot_dshbm_spec_state ref0(`PORTS(0));
 ot_dshbm_spec_state_f failed(`PORTS(1));
 ot_dshbm_spec_state_f_token_edge #(.TOKEN_EDGE_FIX(1)) fixed0(`PORTS(2));
 ot_dshbm_spec_state_f_token_edge defaultoff(`PORTS(3));
`undef PORTS
 reg [52:0] hist[0:5];integer age=0,i,ref_bad=0,fixed_bad=0,off_bad=0,beats=0;
 wire [52:0] word0={v[0],a[0],t[0],p[0],l[0],e[0]};
 always @(posedge clk) begin
  if(!rst_n)begin age=0;for(i=0;i<=5;i=i+1)hist[i]=0;end
  else begin
   for(i=5;i>0;i=i-1)hist[i]=hist[i-1];hist[0]=word0;age=age+1;
   if(age>5) begin
    if(hist[5]!=={v[1],a[1],t[1],p[1],l[1],e[1]})ref_bad=ref_bad+1;
    if(hist[5]!=={v[2],a[2],t[2],p[2],l[2],e[2]})begin fixed_bad=fixed_bad+1;$display("FIX_MISMATCH age=%0d expected=%h got=%h",age,hist[5],{v[2],a[2],t[2],p[2],l[2],e[2]});end
    if(hist[5]!=={v[3],a[3],t[3],p[3],l[3],e[3]})off_bad=off_bad+1;
   end
   if(ready[0]!==ready[2]||n[0]!==n[2])$fatal(1,"ready/commit changed");
   if(v[2])beats=beats+1;
  end
 end
 task tick;begin @(negedge clk);end endtask
 task commit(input [31:0] count);begin tick;n_set=1;n_val=count;tick;n_set=0;repeat(5)tick;end endtask
 task read8;begin tick;req_v=1;req_pos=8;tick;req_v=0;repeat(12)tick;end endtask
 integer j;
 initial begin
  for(j=0;j<=5;j=j+1)hist[j]=0;
  repeat(3)tick;rst_n=1;commit(5);
  for(j=0;j<16;j=j+1)begin tick;tw_v=1;tw_pos=j;tw_tok=17'h10000+j;end
  tick;tw_v=0;repeat(7)tick;
  tick;tw_v=1;tw_pos=8;tw_tok=17'h19934;tick;tw_v=0;repeat(7)tick;
  // This write has committed in the source before the reset. The old f3 loses it.
  tick;tw_v=1;tw_pos=8;tw_tok=17'h1a277;tick;tw_v=0;rst_n=0;
  tick;rst_n=1;read8;
  // Commit/rollback changes only the origin/count, never erases existing token debt.
  commit(5);commit(3);read8;
  tick;req_v=1;req_pos=8;tick;req_v=0;tw_v=1;tw_pos=8;tw_tok=17'h05555;
  tick;tw_v=0;repeat(14)tick;
  if(fixed_bad!=0||ref_bad==0||off_bad!=ref_bad)$fatal(1,"REPRO failed fixed=%0d legacy=%0d off=%0d",fixed_bad,ref_bad,off_bad);
  $display("PASS token_reset_repro legacy_mismatches=%0d defaultoff_mismatches=%0d fixed_mismatches=%0d beats=%0d",ref_bad,off_bad,fixed_bad,beats);$finish;
 end
endmodule
