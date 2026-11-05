`timescale 1ps/1fs
// DIE-KV-71/HHP 11-05: old vs form ot_qkd_static_ctrl_pc_emb, PROFILE 1 (slots are free), every output on every edge.
module tb_emb_ls;
  parameter integer CTX=1, SR=1;
  reg clk=0, rst_n=0; always #416 clk=~clk;
  reg cmd_v=0; reg [31:0] cmd=0; reg [9:0] first=0; reg s_v=0,s_we=0; reg [4:0] s_bank=0,s_col=0; reg [18:0] s_row=0; reg [346:0] s_ctx=0;
  `define WIRES(p) wire p``credit,p``row_v,p``col_v,p``col_we,p``busy,p``fault,p``idle,p``s_cr,p``col_sr,p``boot; wire [2:0] p``row_op; wire [4:0] p``row_bank,p``col_bank,p``col_col; wire [18:0] p``row_row; wire [346:0] p``ctx;
  `define PORTS(p) .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd(cmd),.cmd_first(first),.reserved_rd(1'b0),.reserved_static_col(1'b0),.reserved_write_col(1'b0),.boot_window(1'b0),.col_boot(p``boot),.cmd_credit(p``credit),\
   .row_v(p``row_v),.row_op(p``row_op),.row_bank(p``row_bank),.row_row(p``row_row),.col_v(p``col_v),.col_bank(p``col_bank),.col_col(p``col_col),.col_we(p``col_we),.busy(p``busy),.fault(p``fault),.phase_idle(p``idle),\
   .s_context(s_ctx),.col_context(p``ctx),.s_v(s_v),.s_we(s_we),.s_bank(s_bank),.s_col(s_col),.s_row(s_row),.s_cr(p``s_cr),.col_sr(p``col_sr)
  `WIRES(o_) `WIRES(n_)
  ot_qkd_static_ctrl_pc_emb_old #(.CORE_CLOCK(1),.ENABLE(1),.PROFILE(1),.CONTEXT_DESC(CTX),.STATIC_REFRESH(SR)) old(`PORTS(o_));
  ot_qkd_static_ctrl_pc_emb     #(.CORE_CLOCK(1),.ENABLE(1),.PROFILE(1),.CONTEXT_DESC(CTX),.STATIC_REFRESH(SR)) dut(`PORTS(n_));
  wire [63:0] ov={o_credit,o_row_v,o_col_v,o_col_we,o_busy,o_fault,o_idle,o_s_cr,o_col_sr,o_boot,o_row_op,o_row_bank,o_col_bank,o_col_col,o_row_row};
  wire [63:0] nv={n_credit,n_row_v,n_col_v,n_col_we,n_busy,n_fault,n_idle,n_s_cr,n_col_sr,n_boot,n_row_op,n_row_bank,n_col_bank,n_col_col,n_row_row};
  integer seed=1, cycles=400000, cyc=0, sincerst=0, pc=30, psv=10, pbad=2, out=0, s_out=0, need_go=0;
  longint c_cred=0,c_col=0,c_fault=0,c_sr=0;
  function automatic int r(int m); return $urandom_range(m-1,0); endfunction
  initial begin
    if(!$value$plusargs("seed=%d",seed)) seed=1; if(!$value$plusargs("cycles=%d",cycles)) cycles=400000;
    void'($urandom(seed));
    forever begin
      @(negedge clk); cyc++; sincerst++;
      if(sincerst%2000==1) begin pc=r(60); psv=r(30); pbad=r(4)==0?r(30):0; end
      if(sincerst>12000 || (n_fault && sincerst>60)) begin rst_n=0; sincerst=0; out=0; s_out=0; end else if(sincerst>4) rst_n=1;
      cmd_v=0;
      if(n_credit && out>0) out--;
      if(r(100)<pc && out<6) begin
        automatic int t=r(100);
        automatic logic [10:0] n; automatic logic [9:0] f;
        cmd_v=1; out++;
        if(need_go) begin need_go=0; cmd={2'b01,30'(r(1000))}; first=r(1024); end
        else if(t<20) begin need_go=1; n=1+r(40); f=r(int'(n)); if(r(100)<pbad) begin case(r(3)) 0:n=0; 1:n=1025+r(100); 2:f=n; endcase end cmd={2'b00,n,19'(64+r(4))}; first=f; end
        else if(t<40) begin cmd={2'b01,30'(r(1000))}; first=r(1024); end
        else if(t<70) begin cmd={2'b10,17'(r(1000)),5'(r(32)),5'(r(8))}; first=r(1024); end
        else begin automatic logic [8:0] m=1+r(r(4)==0?256:16); need_go=1; f=r(129); if(r(100)<pbad) begin case(r(3)) 0:m=r(2)?256:257+r(200); 1:f=r(2)?129:129+r(200); 2:f=128; endcase end cmd={2'b11,1'(r(2)),1'(r(2)),m,19'(64+r(4))}; first=f; end
      end
      if(n_s_cr && s_out>0) s_out--; s_v=r(100)<psv && s_out<3; if(s_v) s_out++; s_we=r(4)==0; s_bank=r(8); s_col=r(32); s_row=64+r(3); for(int i=0;i<11;i++) s_ctx[i*32+:32]=$urandom;
    end
  end
  always @(posedge clk) if(rst_n) begin
    if(ov!==nv || (o_col_sr && o_ctx!==n_ctx)) begin $display("FAIL cycle %0d since_rst %0d old %h new %h ctxdiff %0d",cyc,sincerst,ov,nv,o_ctx!==n_ctx); $finish; end
    c_cred+=n_credit; c_col+=n_col_v; c_fault+=n_fault; c_sr+=n_col_sr;
    if(cyc>=cycles) begin $display("PASS cycles %0d credit %0d col %0d col_sr %0d fault_cycles %0d",cyc,c_cred,c_col,c_sr,c_fault); $finish; end
  end
endmodule
