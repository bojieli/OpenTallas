`timescale 1ns/1ps
/*verilator lint_off BLKSEQ*/
/*verilator lint_off WIDTH*/
/*verilator lint_off UNUSED*/
module ot_sram_1r1w_128x256_m1_r2c2_m55 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [6:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [6:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
    localparam integer WORDS = 128;
    localparam integer BITS = 256;
    localparam integer MUX = 1;
    localparam integer AW = 7;
    localparam integer ROWS = 128;
    localparam integer NSR = 2;
    localparam integer NSC = 2;
    localparam integer PR = 130;
    localparam integer PC = 258;
    localparam integer RA = 7;
    localparam integer CB = 8;
    reg [PC-1:0] arr [0:PR-1];
    integer init_i;
    initial begin
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};
    end
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction
    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction
    function automatic cell_read(input integer r, input integer c);
        reg v;
        begin
            v = arr[r][c];
            cell_read = v;
        end
    endfunction
    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
        begin
            old = arr[r][c];
            nv = v;
            arr[r][c] = nv;
        end
    endtask
    function automatic [65:0] decode(input integer a);
        integer r0, r1;
        reg [1:0] sel_n;
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 2'd1;
            decode = {sel_n, r1[31:0], r0[31:0]};
        end
    endfunction
    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction
    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= word_read(r_addr_in);
        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);
    end
endmodule
/*verilator lint_on BLKSEQ*/
/*verilator lint_on WIDTH*/
/*verilator lint_on UNUSED*/
`timescale 1ns/1ps
module ot_hbm_su_programme_mem_m55 #(
  parameter integer BANKS=1, BASE=0, OREG=0, MUT=0
)(input logic clk, input logic [BANKS-1:0] clk_macro, input logic ren, input logic [15:0] addr,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data, output logic [255:0] data);
  wire [256*BANKS-1:0] q;
  logic [8:0] select_q;
  always_ff @(posedge clk) if (ren) select_q <= addr[15:7];
  integer mux_bank;
  generate if (OREG == 0) begin:g_direct
    always_comb begin
      data='0;
      for(mux_bank=0;mux_bank<BANKS;mux_bank=mux_bank+1) if(select_q==mux_bank) data=q[256*mux_bank+:256];
    end
  end else begin:g_pairreg
    localparam integer PAIRS=(BANKS+1)/2;
    logic [255:0] pair_q [0:PAIRS-1];
    logic [8:0] sel2;
    always_ff @(posedge clk) sel2 <= select_q;
    for (genvar p=0;p<PAIRS;p=p+1) begin:pr
      if (2*p+1 < BANKS) begin:two
        always_ff @(posedge clk) pair_q[p] <= select_q[0] ? q[256*(2*p+1)+:256] : q[256*(2*p)+:256];
      end else begin:one
        always_ff @(posedge clk) pair_q[p] <= q[256*(2*p)+:256];
      end
    end
    wire [8:0] psel = (MUT==1) ? select_q : sel2;
    integer mp;
    always_comb begin
      data='0;
      for(mp=0;mp<PAIRS;mp=mp+1) if(psel[8:1]==mp[7:0]) data=pair_q[mp];
    end
  end endgenerate
  genvar bank;
  generate for(bank=0;bank<BANKS;bank=bank+1) begin:g
    wire [255:0] bank_q;
    assign q[256*bank+:256]=bank_q;
    ot_sram_1r1w_128x256_m1_r2c2_m55 mem(
      .clk(clk_macro[bank]), .r_ce_in(ren && addr[15:7]==bank), .r_addr_in(addr[6:0]), .rd_out(bank_q),
      .w_ce_in(cfg_we && cfg_bank==BASE+bank), .w_addr_in(cfg_row),
      .wd_in(cfg_data), .w_mask_in({256{1'b1}}),
      .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
  end endgenerate
endmodule
module ot_hbm_su_programme_mem_r4_m55 #(
  parameter integer BANKS=1, OG=2, GRP=0, RS=4, MUT=0
)(input logic clk, input logic [BANKS-1:0] clk_macro, input logic ren, input logic [15:0] addr,
  input logic [BANKS-1:0] w_ce, input logic [7*BANKS-1:0] w_row, input logic [256*BANKS-1:0] w_data,
  output logic [255:0] data);
  localparam integer LOG=(OG<=1)?0:$clog2(OG);
  localparam integer NOG=(BANKS+OG-1)/OG;
  localparam integer SW=256/RS;
  localparam integer NG=(GRP>0)?(NOG+GRP-1)/GRP:NOG;
  initial if((1<<LOG)!=OG || SW*RS!=256 || BANKS<1) $fatal(1,"mem_r4: OG power of two, RS divides 256");
  wire [256*BANKS-1:0] q;
  wire [8:0] bank_a = addr[15:7];
  logic [255:0] og_q [0:NOG-1];
  (* keep *) logic [RS-1:0] h1 [0:NOG-1];
  (* keep *) logic [RS-1:0] h2 [0:NOG-1];
  genvar o, r, bank, gg;
  generate for(o=0;o<NOG;o=o+1) begin:og
    localparam integer NB=((o+1)*OG<=BANKS)?OG:(BANKS-o*OG);
    if(LOG>0) begin:lsel
      (* keep *) logic [LOG-1:0] sl [0:RS-1];
      for(r=0;r<RS;r=r+1) begin:rs
        always_ff @(posedge clk) if(ren) sl[r] <= bank_a[LOG-1:0];
        logic [SW-1:0] m;
        integer b;
        always_comb begin
          m='0;
          for(b=0;b<NB;b=b+1) if(sl[r]==b[LOG-1:0]) m=q[256*(o*OG+b)+SW*r+:SW];
        end
        always_ff @(posedge clk) og_q[o][SW*r+:SW] <= m;
      end
    end else begin:nsel
      always_ff @(posedge clk) og_q[o] <= q[256*o+:256];
    end
    for(r=0;r<RS;r=r+1) begin:hr
      always_ff @(posedge clk) if(ren) h1[o][r] <= (bank_a>>LOG)==o && bank_a<BANKS;
      always_ff @(posedge clk) h2[o][r] <= h1[o][r];
    end
  end endgenerate
  generate if(GRP==0) begin:g_flat
    integer mo, rr;
    always_comb begin
      data='0;
      for(mo=0;mo<NOG;mo=mo+1) for(rr=0;rr<RS;rr=rr+1)
        data[SW*rr+:SW]=data[SW*rr+:SW] | (og_q[mo][SW*rr+:SW] & {SW{(MUT==1)?h1[mo][rr]:h2[mo][rr]}});
    end
  end else begin:g_grp
    logic [255:0] gq [0:NG-1];
    (* keep *) logic [RS-1:0] h3 [0:NG-1];
    for(gg=0;gg<NG;gg=gg+1) begin:gr
      for(r=0;r<RS;r=r+1) begin:rs
        logic [SW-1:0] m; logic hit;
        integer mo;
        always_comb begin
          m='0; hit=0;
          for(mo=gg*GRP;mo<(gg+1)*GRP && mo<NOG;mo=mo+1) begin
            m=m | (og_q[mo][SW*r+:SW] & {SW{(MUT==1)?h1[mo][r]:h2[mo][r]}});
            hit=hit | h2[mo][r];
          end
        end
        always_ff @(posedge clk) begin gq[gg][SW*r+:SW] <= m; h3[gg][r] <= hit; end
      end
    end
    integer mg, rr;
    always_comb begin
      data='0;
      for(mg=0;mg<NG;mg=mg+1) for(rr=0;rr<RS;rr=rr+1)
        data[SW*rr+:SW]=data[SW*rr+:SW] | (gq[mg][SW*rr+:SW] & {SW{h3[mg][rr]}});
    end
  end endgenerate
  generate for(bank=0;bank<BANKS;bank=bank+1) begin:g
    wire [255:0] bank_q;
    assign q[256*bank+:256]=bank_q;
    ot_sram_1r1w_128x256_m1_r2c2_m55 mem(
      .clk(clk_macro[bank]), .r_ce_in(ren && bank_a==bank), .r_addr_in(addr[6:0]), .rd_out(bank_q),
      .w_ce_in(w_ce[bank]), .w_addr_in(w_row[7*bank+:7]),
      .wd_in(w_data[256*bank+:256]), .w_mask_in({256{1'b1}}),
      .rr_en(2'b0), .rr_addr(14'b0), .cr_en(2'b0), .cr_sel(16'b0));
  end endgenerate
endmodule
module ot_hbm_su_programme_m55 #(
  parameter integer LINE_BITS=9688, EDGES=7111,
  parameter integer COLS=(LINE_BITS+255)/256,
  parameter integer INDEX_GROUPS=(COLS+15)/16,
  parameter integer INDEX_PACK=1,
  parameter integer INDEX_BANKS=(EDGES+128*INDEX_PACK-1)/(128*INDEX_PACK),
  parameter [32*COLS-1:0] DICT_BANKS={COLS{32'd1}},
  parameter integer MACROS=INDEX_GROUPS*INDEX_BANKS+COLS,
  parameter integer PIPE=0, MUT=0,
  parameter integer IOG=4, IGRP=4, DOG=2, RS=4, CFGR=4,   
  parameter integer FADV=0                                
)(input logic clk, rst_n, input logic [MACROS-1:0] clk_macro,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row,
  input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault,
  output logic [15:0] edge_index,
  output logic [LINE_BITS-1:0] command);
  function automatic integer dict_base(input integer c);
    integer v,k;
    begin
      v=INDEX_GROUPS*INDEX_BANKS;
      for(k=0;k<c;k=k+1) v=v+DICT_BANKS[32*k+:32];
      dict_base=v;
    end
  endfunction
  localparam integer TOTAL_BANKS=dict_base(COLS);
  localparam integer XSTG=(IGRP>0 || INDEX_PACK>1)?1:0;
  localparam integer XI=(PIPE==2)?(2+XSTG):(PIPE!=0)?2:0;  
  localparam integer XD=(PIPE!=0)?1:0;           
  localparam integer XP=XI+XD;
  initial if(MACROS!=TOTAL_BANKS) $fatal(1,"programme MACROS capacity mismatch");
  initial if(PIPE==1 && INDEX_PACK!=1) $fatal(1,"programme PIPE 1 requires unpacked indices");
  initial if(FADV<0 || (PIPE!=2 && FADV!=0) || FADV>XP-1) $fatal(1,"programme FADV only with PIPE 2, < XP");
  logic issue,v1,v2;
  logic [15:0] pc, count, e1,e2;
  logic busy_i, fault_i;
  wire [INDEX_GROUPS*256-1:0] index_rows;
  wire [INDEX_GROUPS*256-1:0] indices;
  localparam integer INDEX_SHIFT=$clog2(INDEX_PACK);
  initial if(INDEX_PACK<1 || INDEX_PACK>16 || (INDEX_PACK & (INDEX_PACK-1))!=0 || (INDEX_PACK!=1 && COLS!=1))
    $fatal(1,"packed programme indices require power-of-two pack<=16 and exactly one dictionary column");
  generate if(INDEX_PACK==1)begin:g_unpacked_index
    assign indices=index_rows;
  end else begin:g_packed_index
    logic [INDEX_SHIFT-1:0] word_slot;
    always_ff @(posedge clk)if(issue)word_slot<=pc[INDEX_SHIFT-1:0];
    assign indices={240'd0,index_rows[16*word_slot+:16]};
  end endgenerate
  logic nb;
  always_comb begin
    nb=busy_i;
    if(start && !(busy_i || length==0 || length>EDGES || (PIPE==2 && cfg_we))) nb=1;
    if(c_v && c_e==count-1) nb=0;
  end
  logic d_ren; logic [15:0] d_e; logic [INDEX_GROUPS*256-1:0] d_addr;
  logic [COLS-1:0] d_ren_c;                      
  logic [COLS*RS-1:0] c_v_c;                     
  logic c_v; logic [15:0] c_e;
  wire [COLS*256-1:0] templates;
  wire write_enable=cfg_we && !busy_i && cfg_bank<TOTAL_BANKS;
  genvar g,c;
  generate for(g=0;g<((PIPE==2)?0:INDEX_GROUPS);g=g+1) begin:ix
    ot_hbm_su_programme_mem_m55 #(.BANKS(INDEX_BANKS),.BASE(g*INDEX_BANKS),.OREG(PIPE!=0),.MUT(MUT==1)) mem(
      .clk(clk),.clk_macro(clk_macro[g*INDEX_BANKS+:INDEX_BANKS]),.ren(issue),.addr(pc >> INDEX_SHIFT),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(index_rows[g*256+:256]));
  end
  for(c=0;c<((PIPE==2)?0:COLS);c=c+1) begin:dt
    ot_hbm_su_programme_mem_m55 #(.BANKS(DICT_BANKS[32*c+:32]),.BASE(dict_base(c)),.OREG(PIPE!=0),.MUT(MUT==1)) mem(
      .clk(clk),.clk_macro(clk_macro[dict_base(c)+:DICT_BANKS[32*c+:32]]),.ren(d_ren),.addr(d_addr[c*16+:16]),.cfg_we(write_enable),.cfg_bank(cfg_bank),
      .cfg_row(cfg_row),.cfg_data(cfg_data),.data(templates[c*256+:256]));
  end
  if(PIPE==2) begin:g_m4
    logic [TOTAL_BANKS-1:0] wce_r;
    (* keep *) logic [6:0] wrow_r [0:CFGR-1];
    (* keep *) logic [255:0] wdat_r [0:CFGR-1];
    logic [6:0] row_late;
    always_ff @(posedge clk) row_late <= cfg_row;
    integer wb, wk;
    always_ff @(posedge clk) begin
      if(!rst_n) wce_r<='0;
      else for(wb=0;wb<TOTAL_BANKS;wb=wb+1) wce_r[wb] <= write_enable && cfg_bank==wb;
      for(wk=0;wk<CFGR;wk=wk+1) begin
        wrow_r[wk] <= (MUT==3 && wk==CFGR-1) ? row_late : cfg_row;
        wdat_r[wk] <= cfg_data;
      end
    end
    wire [7*TOTAL_BANKS-1:0] w_row; wire [256*TOTAL_BANKS-1:0] w_data;
    for(genvar wbg=0;wbg<TOTAL_BANKS;wbg=wbg+1) begin:wmap
      assign w_row[7*wbg+:7]=wrow_r[(wbg*CFGR)/TOTAL_BANKS];
      assign w_data[256*wbg+:256]=wdat_r[(wbg*CFGR)/TOTAL_BANKS];
    end
    for(g=0;g<INDEX_GROUPS;g=g+1) begin:ix
      ot_hbm_su_programme_mem_r4_m55 #(.BANKS(INDEX_BANKS),.OG(IOG),.GRP((INDEX_PACK>1)?0:IGRP),.RS(RS),.MUT(MUT==1)) mem(
        .clk(clk),.clk_macro(clk_macro[g*INDEX_BANKS+:INDEX_BANKS]),.ren(issue),.addr(pc >> INDEX_SHIFT),
        .w_ce(wce_r[g*INDEX_BANKS+:INDEX_BANKS]),.w_row(w_row[7*g*INDEX_BANKS+:7*INDEX_BANKS]),
        .w_data(w_data[256*g*INDEX_BANKS+:256*INDEX_BANKS]),.data(index_rows[g*256+:256]));
    end
    for(c=0;c<COLS;c=c+1) begin:dt
      ot_hbm_su_programme_mem_r4_m55 #(.BANKS(DICT_BANKS[32*c+:32]),.OG(DOG),.GRP(0),.RS(RS),.MUT(MUT==1)) mem(
        .clk(clk),.clk_macro(clk_macro[dict_base(c)+:DICT_BANKS[32*c+:32]]),.ren(d_ren_c[c]),.addr(d_addr[c*16+:16]),
        .w_ce(wce_r[dict_base(c)+:DICT_BANKS[32*c+:32]]),.w_row(w_row[7*dict_base(c)+:7*DICT_BANKS[32*c+:32]]),
        .w_data(w_data[256*dict_base(c)+:256*DICT_BANKS[32*c+:32]]),.data(templates[c*256+:256]));
    end
  end
  if(PIPE==0) begin:g_p0
    assign d_ren=v1; assign d_e=e1; assign d_addr=indices;
    assign c_v=v2; assign c_e=e2;
    assign busy=busy_i; assign fault=fault_i;
  end else if(PIPE==2) begin:g_p2
    logic va, vb, vi, vd; logic [15:0] ea, eb, ei, ed;
    logic [INDEX_GROUPS*256-1:0] indices_r;
    (* keep *) logic [COLS-1:0] vi_c;
    (* keep *) logic [COLS*RS-1:0] vd_c;
    if(INDEX_PACK>1) begin:g_pk
      logic [15:0] ixw;
      always_ff @(posedge clk) begin ixw<=index_rows[16*ea[INDEX_SHIFT-1:0]+:16]; indices_r<={{(INDEX_GROUPS*256-16){1'b0}},ixw}; end
    end else begin:g_upk
      always_ff @(posedge clk) indices_r<=indices;
    end
    always_ff @(posedge clk) begin
      ea<=e1; ei<=(XSTG>0)?eb:ea; eb<=ea; ed<=e2;
    end
    always_ff @(posedge clk) if(!rst_n) begin va<=0; vb<=0; vi<=0; vd<=0; vi_c<='0; vd_c<='0; end
      else begin
        va<=v1; vb<=va; vi<=(XSTG>0)?vb:va; vd<=v2;
        vi_c<={COLS{(XSTG>0)?vb:va}}; vd_c<={(COLS*RS){v2}};
      end
    assign d_ren=vi; assign d_e=ei; assign d_addr=indices_r; assign d_ren_c=vi_c;
    assign c_v=vd; assign c_e=ed; assign c_v_c=vd_c;
    logic [XP-1:0] busy_d, fault_d; logic busy_q;
    always_ff @(posedge clk) if(!rst_n) begin busy_d<='0; fault_d<='0; busy_q<=0; end
      else begin
        busy_d<={busy_d[XP-2:0],busy_i}; fault_d<={fault_d[XP-2:0],fault_i};
        busy_q<=(MUT==2)?nb:(nb && busy_d[XP-2]);
      end
    assign busy=busy_q;
    assign fault=fault_d[XP-1-FADV];
  end else begin:g_p1
    logic va, vi, vd; logic [15:0] ea, ei, ed;
    logic [INDEX_GROUPS*256-1:0] indices_r;
    always_ff @(posedge clk) begin
      indices_r<=indices; ea<=e1; ei<=ea; ed<=e2;
    end
    always_ff @(posedge clk) if(!rst_n) begin va<=0; vi<=0; vd<=0; end else begin va<=v1; vi<=va; vd<=v2; end
    assign d_ren=vi; assign d_e=ei; assign d_addr=indices_r;
    assign c_v=vd; assign c_e=ed;
    logic [XP-1:0] busy_d, fault_d; logic busy_q;
    always_ff @(posedge clk) if(!rst_n) begin busy_d<='0; fault_d<='0; busy_q<=0; end
      else begin
        busy_d<={busy_d[XP-2:0],busy_i}; fault_d<={fault_d[XP-2:0],fault_i};
        busy_q<=(MUT==2)?nb:(nb && busy_d[XP-2]);
      end
    assign busy=busy_q;
    assign fault=fault_d[XP-1];
  end endgenerate
  always_ff @(posedge clk) begin
    if(!rst_n) begin
      busy_i<=0; issue<=0; valid<=0; done<=0; fault_i<=0;
      v1<=0; v2<=0; edge_index<=0;
      if(PIPE==0) begin pc<=0; count<=0; e1<=0; e2<=0; end
    end else begin
      valid<=c_v; v1<=issue; v2<=d_ren; done<=0;
      if(cfg_we && (busy_i || cfg_bank>=TOTAL_BANKS)) fault_i<=1;
      busy_i<=nb;
      if(start) begin
        if(busy_i || length==0 || length>EDGES || (PIPE==2 && cfg_we)) fault_i<=1;
        else begin issue<=1; pc<=0; count<=length; end
      end
      if(issue) begin
        e1<=pc;
        if(pc==count-1) issue<=0; else pc<=pc+1;
      end
      if(d_ren) e2<=d_e;
      if(c_v) begin
        edge_index<=c_e;
        if(c_e==count-1) done<=1;
      end
    end
  end
  generate if(PIPE==0) begin:g_cmd0
    always_ff @(posedge clk) command <= (rst_n && c_v) ? templates[LINE_BITS-1:0] : '0;
  end else if(PIPE==1) begin:g_cmd1
    always_ff @(posedge clk) command <= c_v ? templates[LINE_BITS-1:0] : '0;
  end else begin:g_cmd2
    for(genvar cb=0;cb<LINE_BITS;cb=cb+1) begin:cbit
      always_ff @(posedge clk) command[cb] <= c_v_c[(cb/256)*RS+(cb%256)/(256/RS)] & templates[cb];
    end
  end endgenerate
endmodule
`timescale 1ns/1ps
module ot_hbm_su_programme_pgcol_m55 #(
  parameter integer DB=3, EDGES=7111, CFGR=1, MUT=0, PMUT=0,
  parameter integer CPIN=0, RRLY=0, FADV=1    
)(input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  localparam integer IB=(EDGES+2047)/2048;
  localparam integer MAC=IB+DB;
  initial if(MAC>31) $fatal(1,"pgcol: local bank space is 5 bits (31 = reject)");
  wire [1:0] rl;
  generate if(RRLY!=0) begin:g_rr
    ot_rst_relay_m55 #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rl));
  end else begin:g_nrr
    assign rl={2{rst_n}};
  end endgenerate
  wire rst_c=rl[0];
  logic q_we, q_any; logic [4:0] q_bank;
  generate if(CPIN!=0) begin:g_cp
    always_ff @(posedge clk) begin
      if(!rst_c) begin q_we<=0; q_any<=0; end else begin q_we<=cfg_we; q_any<=cfg_any; end
      q_bank<=cfg_bank;
    end
  end else begin:g_ncp
    assign q_we=cfg_we; assign q_any=cfg_any; assign q_bank=cfg_bank;
  end endgenerate
  logic [1:0] s_q; logic [31:0] l_q;
  always_ff @(posedge clk) begin
    if(!rst_c) s_q<='0; else s_q<={s_q[0],start};
    l_q<={l_q[15:0],length};
  end
  wire s_in=(PMUT==1)?s_q[1]:s_q[0];
  wire [15:0] l_in=(PMUT==1)?l_q[31:16]:l_q[15:0];
  wire p_we=q_we | (q_any & s_in);
  wire [15:0] p_bank=q_we ? {11'd0,q_bank} : 16'hffff;
  ot_hbm_su_programme_m55 #(.LINE_BITS(256),.EDGES(EDGES),.COLS(1),.INDEX_PACK(16),.DICT_BANKS(DB),.MACROS(MAC),
    .PIPE(2),.CFGR(CFGR),.FADV(FADV),.MUT(MUT)) u_p(
    .clk(clk),.rst_n(rl[1]),.clk_macro({MAC{clk}}),.cfg_we(p_we),.cfg_bank(p_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),
    .start(s_in),.length(l_in),.busy(busy),.valid(valid),.done(done),.fault(fault),.edge_index(edge_index),
    .command(command));
endmodule
module ot_hbm_su_programme_pgcol_s_m55(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol_m55 #(.DB(3),.CFGR(1),.CPIN(1),.RRLY(1),.FADV(2)) u_c(.*);
endmodule
module ot_hbm_su_programme_pgcol_l_m55(
  input logic clk, rst_n,
  input logic cfg_we, cfg_any, input logic [4:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [255:0] command);
  ot_hbm_su_programme_pgcol_m55 #(.DB(13),.CFGR(2),.CPIN(1),.RRLY(1),.FADV(2)) u_c(.*);
endmodule
module ot_hbm_su_programme_pghead_m55 #(
  parameter integer NC=10, XP=4, MUT=0, OREG=1, FREG=1, CLAT=2, HRLY=1, DLAT=1
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic [NC-1:0] l_fault, l_valid,
  output logic [NC-1:0] o_we, output logic o_any, output logic [4:0] o_bank, output logic [6:0] o_row,
  output logic [255:0] o_data, output logic fault);
  wire hr;
  generate if(HRLY!=0) begin:g_hr
    ot_rst_relay_m55 #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(hr));
  end else begin:g_nhr
    assign hr=rst_n;
  end endgenerate
  logic c_we; logic [15:0] c_bank; logic [6:0] c_row; logic [255:0] c_data;
  always_ff @(posedge clk) begin
    if(!hr) c_we<=0; else c_we<=cfg_we;
    c_bank<=cfg_bank; c_row<=cfg_row; c_data<=cfg_data;
  end
  wire [NC-1:0] d_we;
  genvar c;
  for(c=0;c<NC;c=c+1) begin:dec
    assign d_we[c]=c_we && c_bank[15:5]==11'(c);
  end
  wire d_any=(MUT==1)?1'b0:c_we;
  wire d_oor=c_we && c_bank[15:5]>=11'(NC);
  generate if(OREG!=0) begin:g_or
    logic [6:0] r2_row; logic [255:0] r2_data;
    always_ff @(posedge clk) begin
      if(!hr) begin o_we<='0; o_any<=0; end else begin o_we<=d_we; o_any<=d_any; end
      o_bank<=c_bank[4:0]; r2_row<=c_row; r2_data<=c_data;
    end
    if(DLAT!=0) begin:g_dl
      always_ff @(posedge clk) begin o_row<=r2_row; o_data<=r2_data; end
    end else begin:g_ndl
      assign o_row=r2_row; assign o_data=r2_data;
    end
  end else begin:g_nor
    assign o_we=d_we; assign o_any=d_any; assign o_bank=c_bank[4:0]; assign o_row=c_row; assign o_data=c_data;
  end endgenerate
  wire oor;
  generate if(CLAT>0) begin:g_cl
    logic [CLAT-1:0] oor_d;
    always_ff @(posedge clk) if(!hr) oor_d<='0; else oor_d<={oor_d,d_oor};
    assign oor=oor_d[CLAT-1];
  end else begin:g_ncl
    assign oor=d_oor;
  end endgenerate
  logic [NC-1:0] lf;
  generate if(FREG!=0) begin:g_fr
    always_ff @(posedge clk) if(!hr) lf<='0; else lf<=l_fault;
  end else begin:g_nfr
    assign lf=l_fault;
  end endgenerate
  logic hf; logic [XP-2:0] hf_d;
  always_ff @(posedge clk) if(!hr) begin hf<=0; hf_d<='0; fault<=0; end
    else begin
      if(oor || (|(l_valid ^ {NC{l_valid[0]}}))) hf<=1;
      hf_d<={hf_d,hf};
      fault<=hf_d[XP-2] | (|lf);
    end
endmodule
module ot_hbm_su_programme_pslice_c5 #(
  parameter integer SB=2422, NC=(SB+255)/256,
  parameter [32*NC-1:0] DICT_CAP={32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3},
  parameter integer MUT=0, MUT_COL=1
)(input logic clk, rst_n,
  input logic cfg_we, input logic [15:0] cfg_bank, input logic [6:0] cfg_row, input logic [255:0] cfg_data,
  input logic start, input logic [15:0] length,
  output logic busy, valid, done, fault, output logic [15:0] edge_index, output logic [SB-1:0] command); /*verilator hier_block*/
  wire [NC-1:0] we, l_busy, l_valid, l_done, l_fault; wire any; wire [4:0] bank; wire [6:0] row; wire [255:0] data;
  wire [16*NC-1:0] l_edge; wire [256*NC-1:0] cmd;
  ot_hbm_su_programme_pghead_m55 #(.NC(NC),.MUT(MUT==2),.OREG(MUT!=6),.FREG(MUT!=7),.CLAT(2),.HRLY(MUT!=8)) u_h(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.l_fault(l_fault),.l_valid(l_valid),.o_we(we),.o_any(any),.o_bank(bank),
    .o_row(row),.o_data(data),.fault(fault));
  genvar c;
  for(c=0;c<NC;c=c+1) begin:g_c
    localparam integer CAP=DICT_CAP[32*c+:32];
    initial if(CAP>13) $fatal(1,"pslice_c5: column dictionary over the L leaf (13 banks)");
    ot_hbm_su_programme_pgcol_m55 #(.DB((CAP<=3)?3:13),.CFGR((CAP<=3)?1:2),.PMUT(MUT==1 && c==MUT_COL),
      .CPIN(MUT!=5),.RRLY(MUT!=4),.FADV(2),
      .MUT((MUT==3 && c==MUT_COL)?1:0)) u_c(
      .clk(clk),.rst_n(rst_n),.cfg_we(we[c]),.cfg_any(any),.cfg_bank(bank),.cfg_row(row),.cfg_data(data),
      .start(start),.length(length),.busy(l_busy[c]),.valid(l_valid[c]),.done(l_done[c]),.fault(l_fault[c]),
      .edge_index(l_edge[16*c+:16]),.command(cmd[256*c+:256]));
  end
  assign busy=l_busy[0]; assign valid=l_valid[0]; assign done=l_done[0]; assign edge_index=l_edge[15:0];
  assign command=cmd[SB-1:0];
endmodule
`timescale 1ns/1ps
module ot_rst_relay_m55 #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;
    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate
    assign rst_n = relay_q[TREE_STAGES-1];
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay: REGIONS must be >= 1");
    end
endmodule
