`timescale 1ps/1fs
// Margin-first successor of ot_qwen_hbm_code_pair_context (bank-local leaf +
// fixed II1 read pipeline), owner rule 2026-10-06. Separate default-off top;
// the original leaf, read pipeline and context stay byte-identical.
//
// Fault-free behaviour: rd_r, wr_r and visible_* are cycle-identical to the
// original context; rom_rd, rsp_v, rd_corrected and rd_uncorrectable are the
// original values delayed by exactly LAT_DELTA=5 edges (II1, no backpressure).
// Same-edge read/write order is preserved because read and write requests
// take the same two register edges to the macro pins.
//
// Read path (request in cycle t):
//   E(t)   central request registers at the input pins (DMR valid/row)
//   E(t+1) per-bank kept request registers (one hierarchy per bank)
//   E(t+2) SRAM samples its registered inputs
//   E(t+3) bank-local protected capture (assembled 288-bit SECDED code, no enable)
//   E(t+4) coded 5:1 bank mux register (DMR one-hot select)
//   E(t+5) coded transport register + registered UE/corrected flags
//   E(t+6) W6 decode, virtual-bank steer, fault gate -> output flops at pins
// Protection: payload stays SECDED-coded until the output flop; the pipeline
// tag word is the original single SECDED control word (correcting); every new
// derived select/request register is duplicated and compared. Detected faults
// set a duplicated sticky fault one edge later; a response whose own code is
// uncorrectable, or any response after a detection, is never delivered valid.
// Difference against the original only under a fault: inhibition of NEW
// rd_r/wr_r acceptance follows detection by one edge (fail-closed).
module ot_qwen_hbm_code_bank_margin #(
  parameter integer BANK=0
)(
  input wire clk, por_n,
  input wire rq_v_a, rq_v_b,
  input wire [12:0] rq_row_a, rq_row_b,
  input wire wq_v_a, wq_v_b,
  input wire [12:0] wq_row_a, wq_row_b,
  input wire [255:0] wq_data,
  input wire [31:0] wq_checks,
  output reg [287:0] cap_code,
  output reg err
);
  function automatic [71:0] assemble(input [63:0] data,input [7:0] check);
    integer bitpos,j;
    begin
      assemble=0; j=0;
      for(bitpos=1;bitpos<=71;bitpos=bitpos+1)
        if((bitpos & (bitpos-1))!=0) begin assemble[bitpos-1]=data[j];j=j+1;end
      assemble[0]=check[0];assemble[1]=check[1];assemble[3]=check[2];
      assemble[7]=check[3];assemble[15]=check[4];assemble[31]=check[5];
      assemble[63]=check[6];assemble[71]=check[7];
    end
  endfunction
  reg re_a, re_b, we_a, we_b, re2_a, re2_b;
  reg [9:0] raddr_a, raddr_b, waddr_a, waddr_b;
  reg [2:0] cs_a, cs_b, wsel_a, wsel_b, cs2_a, cs2_b;
  reg [255:0] wd;
  reg [31:0] wchk;
  wire [255:0] data_q, check_q;
  always @(posedge clk or negedge por_n)
    if(!por_n) begin re_a<=0;re_b<=0;we_a<=0;we_b<=0;re2_a<=0;re2_b<=0;err<=0; end
    else begin
      re_a<=rq_v_a && rq_row_a[12:10]==3'(BANK);
      re_b<=rq_v_b && rq_row_b[12:10]==3'(BANK);
      we_a<=wq_v_a && wq_row_a[12:10]==3'(BANK);
      we_b<=wq_v_b && wq_row_b[12:10]==3'(BANK);
      re2_a<=re_a; re2_b<=re_b;
      err<=(re_a!=re_b) || (we_a!=we_b) || (re2_a!=re2_b) ||
           (re_a && (raddr_a!=raddr_b || cs_a!=cs_b)) ||
           (we_a && (waddr_a!=waddr_b || wsel_a!=wsel_b)) ||
           (re2_a && cs2_a!=cs2_b);
    end
  always @(posedge clk) begin
    raddr_a<=rq_row_a[9:0]; raddr_b<=rq_row_b[9:0];
    cs_a<=rq_row_a[2:0]; cs_b<=rq_row_b[2:0];
    waddr_a<=wq_row_a[9:0]; waddr_b<=wq_row_b[9:0];
    wsel_a<=wq_row_a[2:0]; wsel_b<=wq_row_b[2:0];
    wd<=wq_data; wchk<=wq_checks;
    cs2_a<=cs_a; cs2_b<=cs_b;
  end
  wire w_ce=we_a && we_b;
  ot_sram_1r1w_1024x256_m2_r2c2 data_store(
    .clk(clk),.r_ce_in(re_a),.r_addr_in(raddr_a),.rd_out(data_q),
    .w_ce_in(w_ce),.w_addr_in(waddr_a),.wd_in(wd),.w_mask_in({256{1'b1}}),
    .rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
  ot_sram_1r1w_128x256_m1_r2c2 check_store(
    .clk(clk),.r_ce_in(re_a),.r_addr_in(raddr_a[9:3]),.rd_out(check_q),
    .w_ce_in(w_ce),.w_addr_in(waddr_a[9:3]),.wd_in(256'(wchk) << (wsel_a*32)),
    .w_mask_in(256'hffffffff << (wsel_a*32)),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
  // Unconditional capture: the SRAM SS clk->q leaves no room for an enable
  // mux before the capture D pin. cap_code is consumed only on the edge after
  // a real read (tag pipeline msel), so capturing every edge is exact.
  wire [31:0] selected_checks=check_q >> (cs2_a*32);
  always @(posedge clk)
    for(integer k=0;k<4;k=k+1)
      cap_code[k*72+:72]<=assemble(data_q[k*64+:64],selected_checks[k*8+:8]);
endmodule

module ot_qwen_hbm_code_pair_margin #(
  parameter integer ENABLE=0, COLUMN_BASE=0, ROWS=4496
)(
  input wire clk, por_n,
  input wire wr_v, output wire wr_r,
  input ot_hbm_r14_pkg::owned_t wr_owned,
  input wire wr_span_bound, wr_kind,
  input wire [12:0] wr_row, input wire [11:0] wr_column,
  output wire visible_v, input wire visible_r,
  output ot_hbm_r14_pkg::identity_t visible_id,
  output wire [11:0] visible_tag, output wire [4:0] visible_beat,
  output wire [12:0] visible_row, output wire [11:0] visible_column,
  input wire [1:0] rd_v, rd_span_bound, rd_published,
  input wire [25:0] rd_row, output wire [1:0] rd_r, rsp_v,
  input wire [5:0] virtual_bank,
  output wire [2659:0] rom_rd,
  output wire [1:0] rd_corrected, rd_uncorrectable,
  output wire fault
);
  import ot_hbm_r14_pkg::*;
  import ot_gpu_w6_secded_pkg::*;
  localparam integer BANKS=5;
  generate if (!ENABLE || ROWS>BANKS*1024) begin : off
    assign wr_r=0; assign visible_v=0; assign visible_id='0;
    assign visible_tag=0; assign visible_beat=0;
    assign visible_row=0; assign visible_column=0;
    assign rd_r=0; assign rsp_v=0; assign rom_rd=0;
    assign rd_corrected=0; assign rd_uncorrectable=0; assign fault=0;
  end else begin : on
    // Pipeline tag word (single SECDED word, as the original control word).
    typedef struct packed {
      logic visible;
      logic [4:0][1:0] v;      // per stage, per port valid
      logic [2:0][5:0] pb;     // physical bank (port1,port0), stages 0..2
      logic [4:0][5:0] vb;     // virtual bank (port1,port0), stages 0..4
    } control_t;
    typedef struct packed {
      identity_t id; logic [11:0] tag; logic [4:0] beat;
      logic [12:0] row; logic [11:0] column;
    } metadata_t;
    reg [71:0] control_code;
    reg [287:0] metadata_code;
    wire [65:0] cd=decode64(control_code);
    control_t c, n;
    assign c=cd[$bits(control_t)-1:0];
    wire control_bad=cd[65] || (|cd[63:$bits(control_t)]);
    wire [255:0] metadata_raw;
    wire [3:0] metadata_ue;
    for(genvar k=0;k<4;k=k+1) begin : md
      wire [65:0] d=decode64(metadata_code[k*72+:72]);
      assign metadata_raw[k*64+:64]=d[63:0];
      assign metadata_ue[k]=d[65];
    end
    metadata_t m;
    assign m=metadata_raw[$bits(metadata_t)-1:0];
    wire metadata_bad=c.visible && ((|metadata_ue) || (|metadata_raw[255:$bits(metadata_t)]));
    // Duplicated sticky fault: every use sees the OR of both copies.
    reg fq_a, fq_b;
    assign fault=fq_a || fq_b;
    // ---------------- request side (same-cycle handshakes) ----------------
    wire column_ok=(wr_column==12'(COLUMN_BASE)) || (wr_column==12'(COLUMN_BASE+1));
    wire format_ok=!wr_kind && column_ok && (wr_row<ROWS);
    assign wr_r=wr_span_bound && format_ok && !fault && (!c.visible || visible_r);
    wire write_fire=wr_v && wr_r;
    assign visible_v=c.visible && !fault;
    assign visible_id=m.id; assign visible_tag=m.tag; assign visible_beat=m.beat;
    assign visible_row=m.row; assign visible_column=m.column;
    wire [1:0] read_fire, request_bad;
    for(genvar p=0;p<2;p=p+1) begin : port
      assign rd_r[p]=rd_span_bound[p] && rd_published[p] && (rd_row[p*13+:13]<ROWS) && !fault;
      assign read_fire[p]=rd_v[p] && rd_r[p];
      assign request_bad[p]=read_fire[p] && (virtual_bank[p*3+:3]>=5);
    end
    wire format_bad=wr_v && wr_span_bound && !format_ok;
    // ---------------- E(t): central request registers at the pins ----------------
    reg [1:0] rq_v_a, rq_v_b, wq_v_a, wq_v_b;
    reg [12:0] rq_row_a [0:1], rq_row_b [0:1];
    reg [12:0] wq_row_a, wq_row_b;
    reg [255:0] wq_data;
    reg [31:0] wq_checks;
    wire [31:0] write_checks;
    function automatic [7:0] checks(input [71:0] code);
      checks={code[71],code[63],code[31],code[15],code[7],code[3],code[1],code[0]};
    endfunction
    for(genvar k=0;k<4;k=k+1) begin : encode
      wire [71:0] encoded=encode64(wr_owned.data[k*64+:64]);
      assign write_checks[k*8+:8]=checks(encoded);
    end
    always @(posedge clk or negedge por_n)
      if(!por_n) begin rq_v_a<=0; rq_v_b<=0; wq_v_a<=0; wq_v_b<=0; end
      else begin
        rq_v_a<=read_fire; rq_v_b<=read_fire;
        for(integer p=0;p<2;p=p+1) begin
          wq_v_a[p]<=write_fire && wr_column==12'(COLUMN_BASE+p);
          wq_v_b[p]<=write_fire && wr_column==12'(COLUMN_BASE+p);
        end
      end
    always @(posedge clk) begin
      for(integer p=0;p<2;p=p+1) begin
        rq_row_a[p]<=rd_row[p*13+:13]; rq_row_b[p]<=rd_row[p*13+:13];
      end
      wq_row_a<=wr_row; wq_row_b<=wr_row;
      wq_data<=wr_owned.data; wq_checks<=write_checks;
    end
    // ---------------- E(t+1..t+3): kept per-bank storage ----------------
    wire [287:0] cap [0:1][0:BANKS-1];
    wire [9:0] bank_err;
    for(genvar p=0;p<2;p=p+1) begin : column
      for(genvar b=0;b<BANKS;b=b+1) begin : bank
        ot_qwen_hbm_code_bank_margin #(.BANK(b)) u_bank(
          .clk(clk),.por_n(por_n),
          .rq_v_a(rq_v_a[p]),.rq_v_b(rq_v_b[p]),.rq_row_a(rq_row_a[p]),.rq_row_b(rq_row_b[p]),
          .wq_v_a(wq_v_a[p]),.wq_v_b(wq_v_b[p]),.wq_row_a(wq_row_a),.wq_row_b(wq_row_b),
          .wq_data(wq_data),.wq_checks(wq_checks),
          .cap_code(cap[p][b]),.err(bank_err[p*5+b]));
      end
    end
    // ---------------- E(t+3..t+6): coded mux, transport, decode/steer ----------------
    reg [4:0] msel_a [0:1], msel_b [0:1];
    reg [4:0] osel_a [0:1], osel_b [0:1];
    reg [1:0] vld5_a, vld5_b, unc5, corr5;
    reg [287:0] sel_code [0:1], sel_code2 [0:1];
    reg [2659:0] rom_rd_q;
    reg [1:0] rsp_v_q, corr_q, unc_q;
    wire [1:0] sel_err;
    wire [1:0] unc_now, corr_now;
    wire [255:0] out_data [0:1];
    for(genvar p=0;p<2;p=p+1) begin : stage
      wire [287:0] mux_tree;
      wire [3:0] ue_w, co_w;
      assign mux_tree=({288{msel_a[p][0]}} & cap[p][0]) | ({288{msel_a[p][1]}} & cap[p][1]) |
                      ({288{msel_a[p][2]}} & cap[p][2]) | ({288{msel_a[p][3]}} & cap[p][3]) |
                      ({288{msel_a[p][4]}} & cap[p][4]);
      for(genvar k=0;k<4;k=k+1) begin : flags
        wire [65:0] d=decode64(sel_code[p][k*72+:72]);
        assign ue_w[k]=d[65]; assign co_w[k]=d[64];
      end
      for(genvar k=0;k<4;k=k+1) begin : dec
        wire [65:0] d=decode64(sel_code2[p][k*72+:72]);
        assign out_data[p][k*64+:64]=d[63:0];
      end
      assign unc_now[p]=c.v[4][p] && (|ue_w);
      assign corr_now[p]=c.v[4][p] && (|co_w);
      assign sel_err[p]=(msel_a[p]!=msel_b[p]) || (osel_a[p]!=osel_b[p]) || (vld5_a[p]!=vld5_b[p]);
      always @(posedge clk) begin
        sel_code[p]<=mux_tree;        // E(t+4)
        sel_code2[p]<=sel_code[p];    // E(t+5)
      end
      always @(posedge clk or negedge por_n)
        if(!por_n) begin
          msel_a[p]<=0; msel_b[p]<=0; osel_a[p]<=0; osel_b[p]<=0;
          vld5_a[p]<=0; vld5_b[p]<=0; unc5[p]<=0; corr5[p]<=0;
        end else begin
          for(integer b=0;b<BANKS;b=b+1) begin
            msel_a[p][b]<=c.v[2][p] && c.pb[2][p*3+:3]==3'(b);   // E(t+3)
            msel_b[p][b]<=c.v[2][p] && c.pb[2][p*3+:3]==3'(b);
`ifdef CODE_PAIR_MARGIN_MUTANT_TAG_SKEW
            osel_a[p][b]<=c.v[4][p] && c.vb[3][p*3+:3]==3'(b);   // bench-only negative control
            osel_b[p][b]<=c.v[4][p] && c.vb[3][p*3+:3]==3'(b);
`else
            osel_a[p][b]<=c.v[4][p] && c.vb[4][p*3+:3]==3'(b);   // E(t+5)
            osel_b[p][b]<=c.v[4][p] && c.vb[4][p*3+:3]==3'(b);
`endif
          end
          vld5_a[p]<=c.v[4][p]; vld5_b[p]<=c.v[4][p];
          unc5[p]<=unc_now[p]; corr5[p]<=corr_now[p];
        end
    end
    // Output gate: duplicated sticky fault, this edge's UE of either port
    // (the original suppresses both ports on any read UE), select mismatch.
`ifdef CODE_PAIR_MARGIN_MUTANT_NO_UE_GATE
    wire gate=fault || (|sel_err);              // bench-only negative control
`else
    wire gate=fault || (|unc5) || (|sel_err);
`endif
    always @(posedge clk or negedge por_n)
      if(!por_n) begin rom_rd_q<=0; rsp_v_q<=0; corr_q<=0; unc_q<=0; end
      else begin
        for(integer p=0;p<2;p=p+1) begin
          for(integer b=0;b<BANKS;b=b+1)
            rom_rd_q[(p*5+b)*266+:266]<=(osel_a[p][b] && osel_b[p][b] && vld5_a[p] && vld5_b[p] && !gate) ?
                                       {10'b0,out_data[p]} : 266'b0;
          rsp_v_q[p]<=vld5_a[p] && vld5_b[p] && !gate;
        end
        corr_q<=corr5; unc_q<=unc5;
      end
    assign rom_rd=rom_rd_q; assign rsp_v=rsp_v_q;
    assign rd_corrected=corr_q; assign rd_uncorrectable=unc_q;
    // ---------------- control word and sticky fault ----------------
    always @* begin
      n=c;
      n.v[0]=read_fire;
      for(integer k=1;k<5;k=k+1) n.v[k]=c.v[k-1];
      n.pb[0]={rd_row[25:23],rd_row[12:10]};
      for(integer k=1;k<3;k=k+1) n.pb[k]=c.pb[k-1];
      n.vb[0]=virtual_bank;
      for(integer k=1;k<5;k=k+1) n.vb[k]=c.vb[k-1];
      if(visible_v && visible_r) n.visible=0;
      if(write_fire) n.visible=1;
    end
    wire detect=control_bad || metadata_bad || (|request_bad) || format_bad ||
                (|bank_err) || (|sel_err) || (|unc5) || (fq_a!=fq_b);
    always @(posedge clk or negedge por_n) begin
      if(!por_n) begin control_code<=0; metadata_code<=0; fq_a<=0; fq_b<=0; end
      else begin
        fq_a<=fq_a || detect; fq_b<=fq_b || detect;
        if(!control_bad) begin
          control_code<=encode64(64'(n));
          if(write_fire) begin : receipt
            metadata_t next_metadata;
            next_metadata={wr_owned.id,wr_owned.physical_tag,wr_owned.beat,wr_row,wr_column};
            for(integer k=0;k<4;k=k+1)
              metadata_code[k*72+:72]<=encode64(64'(256'(next_metadata)>>(k*64)));
          end
        end
      end
    end
  end endgenerate
endmodule
