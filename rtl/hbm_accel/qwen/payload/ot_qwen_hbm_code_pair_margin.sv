`timescale 1ps/1fs
// Margin-first successor of ot_qwen_hbm_code_pair_context (bank-local leaf +
// fixed II1 read pipeline), owner rule 2026-10-06. Separate default-off top;
// the original leaf, read pipeline and context stay byte-identical.
//
// Fault-free behaviour: rd_r, wr_r and visible_* are cycle-identical to the
// original context; rom_rd, rsp_v, rd_corrected and rd_uncorrectable are the
// original values delayed by exactly LAT_DELTA=6 edges (II1, no backpressure).
// Same-edge read/write order is preserved because read and write requests
// take the same two register edges to the macro pins.
//
// Read path (request in cycle t):
//   E(t)   central request registers at the input pins (DMR valid/row)
//   E(t+1) per-bank kept request registers (one hierarchy per bank)
//   E(t+2) SRAM samples its registered inputs
//   E(t+3) bank-local protected capture (assembled 288-bit SECDED code, no enable)
//   E(t+4) coded 5:1 bank mux register (DMR one-hot select)
//   E(t+5) coded transport register + registered syndrome + UE/corrected flags
//   E(t+6) W6 correction -> corrected-data register; slot enables (DMR) from
//          virtual bank, valid and fault gate
//   E(t+7) AND steer into the output flops at the pins
// Protection: payload stays SECDED-coded until the output stage (decode split
// at the syndrome register); pipeline tags, visible bit, visible metadata and
// every derived select/request register are duplicated in kept shadow modules
// and compared (fail-closed: an upset faults instead of being corrected).
// Detected faults set a duplicated sticky fault one edge later; a response
// whose own code is uncorrectable, or any response after a detection, is never
// delivered valid; a receipt whose metadata copies disagree is never visible.
// Difference against the original only under a fault: inhibition of NEW
// rd_r/wr_r acceptance follows detection by one edge (fail-closed).
// Duplicate ("b") copies live in their own kept hierarchy so synthesis cannot
// merge them with the primary copies (ORFS SYNTH_HIERARCHICAL keeps modules).
module ot_qwen_hbm_code_shadow_r #(parameter integer W=1)(
  input wire clk, por_n, input wire [W-1:0] d, output reg [W-1:0] q);
  always @(posedge clk or negedge por_n) if(!por_n) q<=0; else q<=d;
endmodule
module ot_qwen_hbm_code_shadow_n #(parameter integer W=1)(
  input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
  always @(posedge clk) q<=d;
endmodule

module ot_qwen_hbm_code_bank_margin #(
  parameter integer BANK=0, DIST=0
)(
  input wire clk, por_n,
  input wire rq_v_a_in, rq_v_b_in,
  input wire [12:0] rq_row_a_in, rq_row_b_in,
  input wire wq_v_a_in, wq_v_b_in,
  input wire [12:0] wq_row_a_in, wq_row_b_in,
  input wire [255:0] wq_data_in,
  input wire [31:0] wq_checks_in,
  output reg [287:0] cap_code,
  output reg err
);
  // DIST=1: every request/write signal of the bank is registered once at the bank boundary (kept per bank), so the
  // long wire from the central request registers is a full cycle and the 256-bit write data is staged per bank.
  // Reads and writes shift together, so same-edge read/write order is unchanged; the bank answers one edge later.
  wire rq_v_a, rq_v_b, wq_v_a, wq_v_b;
  wire [12:0] rq_row_a, rq_row_b, wq_row_a, wq_row_b;
  wire [255:0] wq_data; wire [31:0] wq_checks;
  if(DIST) begin : dstg
    reg rva, wva; reg [12:0] rra, wra; reg [255:0] wdd; reg [31:0] wcc;
    wire rvb, wvb; wire [12:0] rrb, wrb;
    always @(posedge clk or negedge por_n) if(!por_n) begin rva<=0; wva<=0; end else begin rva<=rq_v_a_in; wva<=wq_v_a_in; end
    always @(posedge clk) begin rra<=rq_row_a_in; wra<=wq_row_a_in; wdd<=wq_data_in; wcc<=wq_checks_in; end
    ot_qwen_hbm_code_shadow_r #(.W(2)) u_dv_b(.clk(clk),.por_n(por_n),.d({rq_v_b_in,wq_v_b_in}),.q({rvb,wvb}));
    ot_qwen_hbm_code_shadow_n #(.W(26)) u_dr_b(.clk(clk),.d({rq_row_b_in,wq_row_b_in}),.q({rrb,wrb}));
    assign rq_v_a=rva; assign wq_v_a=wva; assign rq_row_a=rra; assign wq_row_a=wra;
    assign wq_data=wdd; assign wq_checks=wcc;
    assign rq_v_b=rvb; assign wq_v_b=wvb; assign rq_row_b=rrb; assign wq_row_b=wrb;
  end else begin : nodstg
    assign rq_v_a=rq_v_a_in; assign rq_v_b=rq_v_b_in; assign wq_v_a=wq_v_a_in; assign wq_v_b=wq_v_b_in;
    assign rq_row_a=rq_row_a_in; assign rq_row_b=rq_row_b_in; assign wq_row_a=wq_row_a_in; assign wq_row_b=wq_row_b_in;
    assign wq_data=wq_data_in; assign wq_checks=wq_checks_in;
  end
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
  reg re_a, we_a, re2_a;
  reg [9:0] raddr_a, waddr_a;
  reg [2:0] cs_a, wsel_a, cs2_a;
  wire re_b, we_b, re2_b;
  wire [9:0] raddr_b, waddr_b;
  wire [2:0] cs_b, wsel_b, cs2_b;
  ot_qwen_hbm_code_shadow_r #(.W(3)) u_tag_b(.clk(clk),.por_n(por_n),
    .d({rq_v_b && rq_row_b[12:10]==3'(BANK), wq_v_b && wq_row_b[12:10]==3'(BANK), re_b}),
    .q({re_b, we_b, re2_b}));
  ot_qwen_hbm_code_shadow_n #(.W(29)) u_addr_b(.clk(clk),
    .d({rq_row_b[9:0], rq_row_b[2:0], wq_row_b[9:0], wq_row_b[2:0], cs_b}),
    .q({raddr_b, cs_b, waddr_b, wsel_b, cs2_b}));
  reg [255:0] wd;
  reg [31:0] wchk;
  wire [255:0] data_q, check_q;
  always @(posedge clk or negedge por_n)
    if(!por_n) begin re_a<=0;we_a<=0;re2_a<=0;err<=0; end
    else begin
      re_a<=rq_v_a && rq_row_a[12:10]==3'(BANK);
      we_a<=wq_v_a && wq_row_a[12:10]==3'(BANK);
      re2_a<=re_a;
      err<=(re_a!=re_b) || (we_a!=we_b) || (re2_a!=re2_b) ||
           (re_a && (raddr_a!=raddr_b || cs_a!=cs_b)) ||
           (we_a && (waddr_a!=waddr_b || wsel_a!=wsel_b)) ||
           (re2_a && cs2_a!=cs2_b);
    end
  always @(posedge clk) begin
    raddr_a<=rq_row_a[9:0]; cs_a<=rq_row_a[2:0];
    waddr_a<=wq_row_a[9:0]; wsel_a<=wq_row_a[2:0];
    wd<=wq_data; wchk<=wq_checks;
    cs2_a<=cs_a;
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
  parameter integer ENABLE=0, COLUMN_BASE=0, ROWS=4496, MARGIN2=0
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
  // decode64 split at its syndrome: {overall, syndrome[6:0]} then correction.
  // w6_correct(code, w6_syndrome(code)) == decode64(code)[63:0] for every code.
  function automatic [7:0] w6_syndrome(input [71:0] code);
    logic [6:0] syndrome; integer p,k;
    begin
      syndrome='0;
      for (k=0;k<7;k=k+1)
        for (p=1;p<=71;p=p+1)
          if ((p & (1<<k)) != 0) syndrome[k]=syndrome[k]^code[p-1];
      w6_syndrome={^code, syndrome};
    end
  endfunction
  function automatic [63:0] w6_correct(input [71:0] code, input [7:0] syn);
    logic [71:0] c; integer p,j;
    begin
      c=code;
      if (syn[6:0]!=0) begin
        if (syn[7] && syn[6:0]<=71) c[syn[6:0]-1]=~c[syn[6:0]-1];
      end
      j=0; w6_correct='0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin w6_correct[j]=c[p-1]; j=j+1; end
    end
  endfunction
  // MARGIN2=1 (owner 2026-10-06, die-IO closure): pin-flopped inputs, registered rd_r/wr_r/visible_v/fault outputs,
  // per-bank distribution stage, W6 correction in two stages: +3 read edges over MARGIN2=0 (LAT_DELTA 9 vs the original
  // context).  Interface change: rd_r is a registered credit (!fault); wr_r is a registered single-slot credit; a
  // request is accepted only when its own span/published/format qualifiers hold (checked after the pin flops).
  localparam integer P=MARGIN2, D=MARGIN2;
  function automatic [71:0] w6_flip(input [7:0] syn);
    begin
      w6_flip='0;
      if (syn[6:0]!=0 && syn[7] && syn[6:0]<=71) w6_flip[syn[6:0]-1]=1'b1;
    end
  endfunction
  function automatic [63:0] w6_extract(input [71:0] c);
    integer p,j;
    begin
      j=0; w6_extract='0;
      for (p=1;p<=71;p=p+1)
        if ((p & (p-1)) != 0) begin w6_extract[j]=c[p-1]; j=j+1; end
    end
  endfunction
  generate if (!ENABLE || ROWS>BANKS*1024) begin : off
    assign wr_r=0; assign visible_v=0; assign visible_id='0;
    assign visible_tag=0; assign visible_beat=0;
    assign visible_row=0; assign visible_column=0;
    assign rd_r=0; assign rsp_v=0; assign rom_rd=0;
    assign rd_corrected=0; assign rd_uncorrectable=0; assign fault=0;
  end else begin : on
    // ---------------- MARGIN2 pin stage: inputs captured in flops at the pins ----------------
    reg wr_v_p, wr_span_p, wr_kind_p; reg [12:0] wr_row_p; reg [11:0] wr_column_p; owned_t wr_owned_p;
    reg [1:0] rd_v_p, rd_span_p, rd_pub_p; reg [25:0] rd_row_p; reg [5:0] vbank_p;
    reg [1:0] rd_r_q, rrr_p; reg wr_r_q, wrr_p, visible_v_q, fault_q;
    wire wr_v_i, wr_span_bound_i, wr_kind_i; wire [12:0] wr_row_i; wire [11:0] wr_column_i; owned_t wr_owned_i;
    wire [1:0] rd_v_i, rd_span_bound_i, rd_published_i; wire [25:0] rd_row_i; wire [5:0] virtual_bank_i;
    if(P) begin : pin
      always @(posedge clk or negedge por_n)
        if(!por_n) begin wr_v_p<=0; rd_v_p<=0; end
        else begin wr_v_p<=wr_v; rd_v_p<=rd_v; end
      always @(posedge clk) begin
        wr_span_p<=wr_span_bound; wr_kind_p<=wr_kind; wr_row_p<=wr_row; wr_column_p<=wr_column; wr_owned_p<=wr_owned;
        rd_span_p<=rd_span_bound; rd_pub_p<=rd_published; rd_row_p<=rd_row; vbank_p<=virtual_bank;
      end
      assign wr_v_i=wr_v_p; assign wr_span_bound_i=wr_span_p; assign wr_kind_i=wr_kind_p; assign wr_row_i=wr_row_p;
      assign wr_column_i=wr_column_p; assign wr_owned_i=wr_owned_p;
      assign rd_v_i=rd_v_p; assign rd_span_bound_i=rd_span_p; assign rd_published_i=rd_pub_p; assign rd_row_i=rd_row_p;
      assign virtual_bank_i=vbank_p;
    end else begin : nopin
      assign wr_v_i=wr_v; assign wr_span_bound_i=wr_span_bound; assign wr_kind_i=wr_kind; assign wr_row_i=wr_row;
      assign wr_column_i=wr_column; assign wr_owned_i=wr_owned;
      assign rd_v_i=rd_v; assign rd_span_bound_i=rd_span_bound; assign rd_published_i=rd_published; assign rd_row_i=rd_row;
      assign virtual_bank_i=virtual_bank;
    end
    // Pipeline tags and visible bit: plain registers plus a kept duplicate.
    // (A SECDED word costs a decode64+encode64 in the one-cycle loop, measured
    // -543 ps pre-placement at 770 ps; duplicate-and-compare keeps the loop
    // to plain logic and fails closed on any upset.)
    typedef struct packed {
      logic visible;
      logic [4+D:0][1:0] v;      // per stage, per port valid
      logic [2+D:0][5:0] pb;     // physical bank (port1,port0), stages 0..2(+D)
      logic [4+D:0][5:0] vb;     // virtual bank (port1,port0), stages 0..4(+D)
    } control_t;
    typedef struct packed {
      identity_t id; logic [11:0] tag; logic [4:0] beat;
      logic [12:0] row; logic [11:0] column;
    } metadata_t;
    reg [$bits(control_t)-1:0] ctl_a;
    wire [$bits(control_t)-1:0] ctl_b;
    control_t c, n;
    assign c=ctl_a;
    wire control_bad=(ctl_a!=ctl_b);
    // Visible receipt metadata: plain register drives the pins directly (the
    // original decoded SECDED to the pins, -439 ps pre-placement); the kept
    // duplicate must agree in the same cycle or visible_v stays low.
    reg [$bits(metadata_t)-1:0] meta_a;
    wire [$bits(metadata_t)-1:0] meta_b, meta_next;
    metadata_t m;
    assign m=meta_a;
    wire metadata_same=(meta_a==meta_b);
    wire metadata_bad=!metadata_same;
    // Duplicated sticky fault: every use sees the OR of both copies.
    reg fq_a; wire fq_b;
    wire fault_int=fq_a || fq_b;
    assign fault=P ? fault_q : fault_int;
    // ---------------- request side (same-cycle handshakes) ----------------
    wire column_ok=(wr_column_i==12'(COLUMN_BASE)) || (wr_column_i==12'(COLUMN_BASE+1));
    wire format_ok=!wr_kind_i && column_ok && (wr_row_i<ROWS);
    wire wr_acc_i=P ? (wrr_p && wr_span_bound_i && format_ok && !fault_int)
                    : (wr_span_bound_i && format_ok && !fault_int && (!c.visible || visible_r));
    assign wr_r=P ? wr_r_q : wr_acc_i;
    wire write_fire=wr_v_i && wr_acc_i;
    wire vis_now=P ? visible_v_q : (c.visible && !fault_int && metadata_same);
    assign visible_v=vis_now;
    assign visible_id=m.id; assign visible_tag=m.tag; assign visible_beat=m.beat;
    assign visible_row=m.row; assign visible_column=m.column;
    wire [1:0] read_fire, request_bad;
    for(genvar p=0;p<2;p=p+1) begin : port
      wire rd_acc_i=(P ? rrr_p[p] : 1'b1) && rd_span_bound_i[p] && rd_published_i[p] && (rd_row_i[p*13+:13]<ROWS) && !fault_int;
      assign rd_r[p]=P ? rd_r_q[p] : rd_acc_i;
      assign read_fire[p]=rd_v_i[p] && rd_acc_i;
      assign request_bad[p]=read_fire[p] && (virtual_bank_i[p*3+:3]>=5);
    end
    wire format_bad=wr_v_i && wr_span_bound_i && !format_ok;
    // ---------------- E(t): central request registers at the pins ----------------
    reg [1:0] rq_v_a, wq_v_a;
    wire [1:0] rq_v_b, wq_v_b;
    reg [12:0] rq_row_a [0:1];
    wire [12:0] rq_row_b [0:1];
    reg [12:0] wq_row_a;
    wire [12:0] wq_row_b;
    wire [1:0] wq_v_next;
    reg [255:0] wq_data;
    reg [31:0] wq_checks;
    wire [31:0] write_checks;
    function automatic [7:0] checks(input [71:0] code);
      checks={code[71],code[63],code[31],code[15],code[7],code[3],code[1],code[0]};
    endfunction
    for(genvar k=0;k<4;k=k+1) begin : encode
      wire [71:0] encoded=encode64(wr_owned_i.data[k*64+:64]);
      assign write_checks[k*8+:8]=checks(encoded);
    end
    always @(posedge clk or negedge por_n)
      if(!por_n) begin rq_v_a<=0; wq_v_a<=0; end
      else begin
        rq_v_a<=read_fire; wq_v_a<=wq_v_next;
      end
    always @(posedge clk) begin
      for(integer p=0;p<2;p=p+1) begin
        rq_row_a[p]<=rd_row_i[p*13+:13];
      end
      wq_row_a<=wr_row_i;
      wq_data<=wr_owned_i.data; wq_checks<=write_checks;
    end
    for(genvar p=0;p<2;p=p+1) begin : wcol
      assign wq_v_next[p]=write_fire && wr_column_i==12'(COLUMN_BASE+p);
    end
    ot_qwen_hbm_code_shadow_r #(.W(4)) u_req_b(.clk(clk),.por_n(por_n),
      .d({wq_v_next, read_fire}), .q({wq_v_b, rq_v_b}));
    ot_qwen_hbm_code_shadow_n #(.W(39)) u_row_b(.clk(clk),
      .d({wr_row_i, rd_row_i}), .q({wq_row_b, rq_row_b[1], rq_row_b[0]}));
    // ---------------- E(t+1..t+3): kept per-bank storage ----------------
    wire [287:0] cap [0:1][0:BANKS-1];
    wire [9:0] bank_err;
    for(genvar p=0;p<2;p=p+1) begin : column
      for(genvar b=0;b<BANKS;b=b+1) begin : bank
        ot_qwen_hbm_code_bank_margin #(.BANK(b),.DIST(D)) u_bank(
          .clk(clk),.por_n(por_n),
          .rq_v_a_in(rq_v_a[p]),.rq_v_b_in(rq_v_b[p]),.rq_row_a_in(rq_row_a[p]),.rq_row_b_in(rq_row_b[p]),
          .wq_v_a_in(wq_v_a[p]),.wq_v_b_in(wq_v_b[p]),.wq_row_a_in(wq_row_a),.wq_row_b_in(wq_row_b),
          .wq_data_in(wq_data),.wq_checks_in(wq_checks),
          .cap_code(cap[p][b]),.err(bank_err[p*5+b]));
      end
    end
    // ---------------- E(t+3..t+6): coded mux, transport, decode/steer ----------------
    reg [4:0] msel_a [0:1], osel_a [0:1];
    wire [4:0] msel_b [0:1], osel_b [0:1];
    wire [4:0] msel_next [0:1], osel_next [0:1];
    reg [1:0] vld5_a, unc5, corr5;
    wire [1:0] vld5_b;
    reg [287:0] sel_code [0:1], sel_code2 [0:1];
    reg [31:0] syn5 [0:1];        // registered W6 syndrome+overall parity per 72-bit word
    reg [2659:0] rom_rd_q;
    reg [1:0] rsp_v_q, corr_q, unc_q;
    reg [255:0] cd6 [0:1];
    reg [9:0] en6_a; wire [9:0] en6_b, en6_next;
    reg [1:0] v6_a, corr6, unc6; wire [1:0] v6_b, v6_next;
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
      wire [31:0] syn_now;
      for(genvar k=0;k<4;k=k+1) begin : dec
        assign syn_now[k*8+:8]=w6_syndrome(sel_code[p][k*72+:72]);
        assign out_data[p][k*64+:64]=P ? w6_extract(code6[k*72+:72]^flip6[k*72+:72])
                                       : w6_correct(sel_code2[p][k*72+:72],syn5[p][k*8+:8]);
      end
      // MARGIN2: W6 correction in two stages: flip mask + code held (E t+6), then XOR + gather (E t+7)
      reg [287:0] flip6, code6;
      always @(posedge clk) for(integer k=0;k<4;k=k+1) begin
        flip6[k*72+:72]<=w6_flip(syn5[p][k*8+:8]); code6[k*72+:72]<=sel_code2[p][k*72+:72];
      end
      for(genvar b=0;b<BANKS;b=b+1) begin : sel
        assign msel_next[p][b]=c.v[2+D][p] && c.pb[2+D][p*3+:3]==3'(b);   // E(t+3)
`ifdef CODE_PAIR_MARGIN_MUTANT_TAG_SKEW
        assign osel_next[p][b]=c.v[4+D][p] && c.vb[3+D][p*3+:3]==3'(b);   // bench-only negative control
`else
        assign osel_next[p][b]=c.v[4+D][p] && c.vb[4+D][p*3+:3]==3'(b);   // E(t+5)
`endif
      end
      ot_qwen_hbm_code_shadow_r #(.W(11)) u_sel_b(.clk(clk),.por_n(por_n),
        .d({msel_next[p], osel_next[p], c.v[4+D][p]}), .q({msel_b[p], osel_b[p], vld5_b[p]}));
      assign unc_now[p]=c.v[4+D][p] && (|ue_w);
      assign corr_now[p]=c.v[4+D][p] && (|co_w);
      assign sel_err[p]=(msel_a[p]!=msel_b[p]) || (osel_a[p]!=osel_b[p]) || (vld5_a[p]!=vld5_b[p]);
      always @(posedge clk) begin
        sel_code[p]<=mux_tree;        // E(t+4)
        sel_code2[p]<=sel_code[p];    // E(t+5)
        syn5[p]<=syn_now;             // E(t+5)
      end
      always @(posedge clk or negedge por_n)
        if(!por_n) begin
          msel_a[p]<=0; osel_a[p]<=0;
          vld5_a[p]<=0; unc5[p]<=0; corr5[p]<=0;
        end else begin
          msel_a[p]<=msel_next[p]; osel_a[p]<=osel_next[p];
          vld5_a[p]<=c.v[4+D][p];
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
    for(genvar p=0;p<2;p=p+1) begin : steer
      for(genvar b=0;b<BANKS;b=b+1) begin : slot
        assign en6_next[p*5+b]=osel_a[p][b] && osel_b[p][b] && vld5_a[p] && vld5_b[p] && !gate;
      end
      assign v6_next[p]=vld5_a[p] && vld5_b[p] && !gate;
      always @(posedge clk) cd6[p]<=out_data[p];                 // E(t+6)
    end
    ot_qwen_hbm_code_shadow_r #(.W(12)) u_en_b(.clk(clk),.por_n(por_n),.d({en6_next,v6_next}),.q({en6_b,v6_b}));
    wire out_err=(en6_a!=en6_b) || (v6_a!=v6_b);
    // MARGIN2 extra output stage (E t+7): control delayed in step with the corrected data
    reg [9:0] en7_a; reg [1:0] v7_a, corr7, unc7; wire [9:0] en7_b; wire [1:0] v7_b;
    ot_qwen_hbm_code_shadow_r #(.W(12)) u_en7_b(.clk(clk),.por_n(por_n),.d({en6_b,v6_b}),.q({en7_b,v7_b}));
    always @(posedge clk or negedge por_n)
      if(!por_n) begin en7_a<=0; v7_a<=0; corr7<=0; unc7<=0; end
      else begin en7_a<=en6_a; v7_a<=v6_a; corr7<=corr6; unc7<=unc6; end
    wire out_err7=P && ((en7_a!=en7_b) || (v7_a!=v7_b));
    wire [9:0] en_a=P ? en7_a : en6_a, en_b=P ? en7_b : en6_b;
    wire [1:0] v_a=P ? v7_a : v6_a, v_b=P ? v7_b : v6_b, corr_s=P ? corr7 : corr6, unc_s=P ? unc7 : unc6;
    always @(posedge clk or negedge por_n)
      if(!por_n) begin en6_a<=0; v6_a<=0; corr6<=0; unc6<=0; rom_rd_q<=0; rsp_v_q<=0; corr_q<=0; unc_q<=0; end
      else begin
        en6_a<=en6_next; v6_a<=v6_next; corr6<=corr5; unc6<=unc5;   // E(t+6)
        for(integer p=0;p<2;p=p+1) begin                             // E(t+7)
          for(integer b=0;b<BANKS;b=b+1)
            rom_rd_q[(p*5+b)*266+:266]<=(en_a[p*5+b] && en_b[p*5+b]) ? {10'b0,cd6[p]} : 266'b0;
          rsp_v_q[p]<=v_a[p] && v_b[p];
        end
        corr_q<=corr_s; unc_q<=unc_s;
      end
    assign rom_rd=rom_rd_q; assign rsp_v=rsp_v_q;
    assign rd_corrected=corr_q; assign rd_uncorrectable=unc_q;
    // ---------------- control word and sticky fault ----------------
    always @* begin
      n=c;
      n.v[0]=read_fire;
      for(integer k=1;k<5+D;k=k+1) n.v[k]=c.v[k-1];
      n.pb[0]={rd_row_i[25:23],rd_row_i[12:10]};
      for(integer k=1;k<3+D;k=k+1) n.pb[k]=c.pb[k-1];
      n.vb[0]=virtual_bank_i;
      for(integer k=1;k<5+D;k=k+1) n.vb[k]=c.vb[k-1];
      if(vis_now && visible_r) n.visible=0;
      if(write_fire) n.visible=1;
    end
    assign meta_next=write_fire ? {wr_owned_i.id,wr_owned_i.physical_tag,wr_owned_i.beat,wr_row_i,wr_column_i} : meta_a;
    ot_qwen_hbm_code_shadow_r #(.W($bits(control_t))) u_ctl_b(.clk(clk),.por_n(por_n),.d(n),.q(ctl_b));
    ot_qwen_hbm_code_shadow_r #(.W($bits(metadata_t))) u_meta_b(.clk(clk),.por_n(por_n),
      .d(write_fire ? {wr_owned_i.id,wr_owned_i.physical_tag,wr_owned_i.beat,wr_row_i,wr_column_i} : meta_b),.q(meta_b));
    wire detect=control_bad || (c.visible && metadata_bad) || (|request_bad) || format_bad ||
                (|bank_err) || (|sel_err) || out_err || out_err7 || (|unc5) || (fq_a!=fq_b);
    ot_qwen_hbm_code_shadow_r #(.W(1)) u_fault_b(.clk(clk),.por_n(por_n),.d(fq_b || detect),.q(fq_b));
    always @(posedge clk or negedge por_n) begin
      if(!por_n) begin ctl_a<=0; meta_a<=0; fq_a<=0; end
      else begin
        fq_a<=fq_a || detect;
        ctl_a<=n;
        meta_a<=meta_next;
      end
    end
    // MARGIN2 registered interface: credits and valid at flops (pin side), fault flop at the pin
    wire fault_nx=fault_int || detect;
    wire meta_same_nx=write_fire ? 1'b1 : metadata_same;
    always @(posedge clk or negedge por_n)
      if(!por_n) begin rd_r_q<=0; rrr_p<=0; wr_r_q<=0; wrr_p<=0; visible_v_q<=0; fault_q<=0; end
      else if(P) begin
        rd_r_q<={2{!fault_nx}}; rrr_p<=rd_r_q;
        wr_r_q<=!fault_nx && !wr_r_q && !n.visible;
        wrr_p<=wr_r_q;
        visible_v_q<=n.visible && !fault_nx && meta_same_nx;
        fault_q<=fault_nx;
      end
  end endgenerate
endmodule
