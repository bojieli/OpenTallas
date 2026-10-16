`timescale 1ns/1ps
// Additive physical candidate; not the production source. Every memory below
// is the target mapped macro. Read/config pins are captured locally, with one
// extra fixed edge per memory level. The original global image numbering is
// unchanged, including writes to banks unused by a particular quarter.
module ot_hbm_su_programme_local_mem #(
  parameter integer BANKS=1, BASE=0
)(input wire clk, rst_n, input wire [BANKS-1:0] clk_macro,
  input wire ren, input wire [15:0] addr,
  input wire cfg_we, input wire [15:0] cfg_bank,
  input wire [6:0] cfg_row, input wire [255:0] cfg_data,
  output reg [255:0] data);
  reg ren_q, we_q;
  reg [15:0] addr_q, bank_q;
  reg [6:0] row_q;
  reg [255:0] wd_q;
  reg [8:0] select_q;
  wire [256*BANKS-1:0] q;
  always @(posedge clk) begin
    addr_q <= addr; bank_q <= cfg_bank; row_q <= cfg_row; wd_q <= cfg_data;
    if(!rst_n) begin ren_q<=0; we_q<=0; end
    else begin ren_q<=ren; we_q<=cfg_we; end
    if(ren_q) select_q<=addr_q[15:7];
  end
  integer k;
  always @* begin
    data=0;
    for(k=0;k<BANKS;k=k+1) if(select_q==k) data=q[k*256+:256];
  end
  genvar b;
  generate for(b=0;b<BANKS;b=b+1) begin:bank
    ot_sram_1r1w_128x256_m1_r2c2 mem(
      .clk(clk_macro[b]),.r_ce_in(ren_q && addr_q[15:7]==b),.r_addr_in(addr_q[6:0]),
      .rd_out(q[b*256+:256]),.w_ce_in(we_q && bank_q==BASE+b),.w_addr_in(row_q),
      .wd_in(wd_q),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(14'b0),
      .cr_en(2'b0),.cr_sel(16'b0));
  end endgenerate
endmodule

module ot_hbm_su_programme_local_q #(
  parameter integer LINE_BITS=9688, EDGES=7116, COLS=(LINE_BITS+255)/256,
  parameter [32*COLS-1:0] DICT_BANKS={COLS{32'd1}},
  parameter integer Q=0, QW=LINE_BITS/4, GLOBAL_MACROS=301,
  parameter integer FIRST=Q*QW/256, LAST=((Q+1)*QW-1)/256,
  parameter integer IG=(COLS+15)/16, IB=(EDGES+127)/128,
  parameter integer GI0=FIRST/16, GI1=LAST/16,
  parameter integer LOCAL_MACROS=98, MUT=0
)(input wire clk_ctl, rst_n, input wire [LAST-FIRST:0] clk_cmd,
  input wire [LOCAL_MACROS-1:0] clk_macro,
  input wire cfg_we, input wire [15:0] cfg_bank,
  input wire [6:0] cfg_row, input wire [255:0] cfg_data,
  input wire start, input wire [15:0] length,
  output reg busy,valid,done,fault, output reg [15:0] edge_index,
  output wire [QW-1:0] command);
  function integer dict_base(input integer col);
    integer k; begin
      dict_base=IG*IB;
      for(k=0;k<col;k=k+1) dict_base=dict_base+DICT_BANKS[32*k+:32];
    end
  endfunction
  function integer local_dict_base(input integer col);
    integer k; begin
      local_dict_base=(GI1-GI0+1)*IB;
      for(k=FIRST;k<col;k=k+1) local_dict_base=local_dict_base+DICT_BANKS[32*k+:32];
    end
  endfunction
`ifndef SYNTHESIS
  initial begin
    if(LINE_BITS%4!=0 || Q<0 || Q>3 || COLS!=(LINE_BITS+255)/256)
      $fatal(1,"local programme dimensions");
    if(GLOBAL_MACROS!=dict_base(COLS) || LOCAL_MACROS!=local_dict_base(LAST+1))
      $fatal(1,"local programme actual macro capacity");
  end
`endif
  reg issue,v1,v2,v3,v4;
  reg [15:0] pc,count,e1,e2,e3,e4;
  wire [IG*256-1:0] indices;
  wire [COLS*256-1:0] templates;
  wire write_enable=cfg_we && !busy && cfg_bank<GLOBAL_MACROS;
  genvar g,c;
  generate for(g=0;g<IG;g=g+1) begin:ix
    if(g>=GI0 && g<=GI1) begin:active
      ot_hbm_su_programme_local_mem #(.BANKS(IB),.BASE(g*IB)) mem(
        .clk(clk_ctl),.rst_n(rst_n),.clk_macro(clk_macro[(g-GI0)*IB+:IB]),
        .ren(issue),.addr(pc),.cfg_we(write_enable),.cfg_bank(cfg_bank),
        .cfg_row(cfg_row),.cfg_data(cfg_data),.data(indices[g*256+:256]));
    end else begin:unused
      assign indices[g*256+:256]=0;
    end
  end
  for(c=0;c<COLS;c=c+1) begin:dt
    if(c>=FIRST && c<=LAST) begin:active
      localparam integer NB=DICT_BANKS[32*c+:32];
      localparam integer LB=local_dict_base(c);
      localparam integer LO=(c*256>Q*QW)?c*256:Q*QW;
      localparam integer HI=((c+1)*256<(Q+1)*QW)?(c+1)*256:(Q+1)*QW;
      wire ck=(MUT==4 && c==FIRST && Q==0)?1'b0:clk_cmd[c-FIRST];
      ot_hbm_su_programme_local_mem #(.BANKS(NB),.BASE(dict_base(c))) mem(
        .clk(ck),.rst_n(rst_n),.clk_macro(clk_macro[LB+:NB]),
        .ren(v2),.addr(indices[c*16+:16]),.cfg_we(write_enable),.cfg_bank(cfg_bank),
        .cfg_row(cfg_row),.cfg_data(cfg_data),.data(templates[c*256+:256]));
      // Separate related, phase-0 root per physical column: a control gate
      // drives at most256 command bits, never the old 9,689-load net.
      reg local_v4;
      reg [HI-LO-1:0] command_q;
      always @(posedge ck) begin
        if(!rst_n) begin local_v4<=0; command_q<=0; end
        else begin
          local_v4 <= (MUT==2)?v2:v3;
          if(local_v4) command_q<=templates[LO+:HI-LO];
          else command_q<=0;
        end
      end
      assign command[LO-Q*QW+:HI-LO]=command_q;
    end else begin:unused
      assign templates[c*256+:256]=0;
    end
  end endgenerate
  // Start at S; command/valid presented after S+5 and sampled at S+6.
  // The original producer presents after S+3. Steady II remains one edge.
  always @(posedge clk_ctl) begin
    if(!rst_n) begin
      busy<=0; issue<=0; valid<=0; done<=0; fault<=0;
      v1<=0; v2<=0; v3<=0; v4<=0;
      pc<=0; count<=0; e1<=0; e2<=0; e3<=0; e4<=0; edge_index<=0;
    end else begin
      v1<=issue; v2<=v1; v3<=v2; v4<=v3; valid<=v4; done<=0;
      if(cfg_we && (busy || cfg_bank>=GLOBAL_MACROS)) fault<=1;
      if(start) begin
        if(busy || length==0 || length>EDGES) fault<=1;
        else begin busy<=1; issue<=1; pc<=0; count<=length; end
      end
      if(issue) begin e1<=pc; if(pc==count-1) issue<=0; else pc<=pc+1; end
      if(v1) e2<=e1;
      if(v2) e3<=e2;
      if(v3) e4<=e3;
      if(v4) begin edge_index<=e4; if(e4==count-1) begin busy<=0; done<=1; end end
    end
  end
endmodule

module ot_hbm_su_programme_local #(
  parameter integer LINE_BITS=9688, EDGES=7116, COLS=(LINE_BITS+255)/256,
  parameter [32*COLS-1:0] DICT_BANKS={COLS{32'd1}},
  parameter integer GLOBAL_MACROS=301, LOCAL_MACROS=474, LOCAL_COLS=41, MUT=0
)(input wire [3:0] clk_ctl, input wire rst_n,
  input wire [LOCAL_COLS-1:0] clk_cmd,
  input wire [LOCAL_MACROS-1:0] clk_macro,
  input wire cfg_we, input wire [15:0] cfg_bank,
  input wire [6:0] cfg_row, input wire [255:0] cfg_data,
  input wire start, input wire [15:0] length,
  output wire busy,valid,done,fault, output wire [15:0] edge_index,
  output wire [LINE_BITS-1:0] command);
  localparam integer QW=LINE_BITS/4, IB=(EDGES+127)/128;
  function integer ncol(input integer q);
    begin ncol=((q+1)*QW-1)/256-q*QW/256+1; end
  endfunction
  function integer nmac(input integer q);
    integer c,first,last;
    begin
      first=q*QW/256; last=((q+1)*QW-1)/256;
      nmac=(last/16-first/16+1)*IB;
      for(c=first;c<=last;c=c+1) nmac=nmac+DICT_BANKS[32*c+:32];
    end
  endfunction
  function integer offset(input integer q, input integer kind);
    integer k; begin
      offset=0;
      for(k=0;k<q;k=k+1) if(kind==0)offset=offset+nmac(k);else offset=offset+ncol(k);
    end
  endfunction
`ifndef SYNTHESIS
  initial begin
    if(LOCAL_MACROS!=offset(4,0) || LOCAL_COLS!=offset(4,1))
      $fatal(1,"local programme top capacity");
  end
`endif
  wire [3:0] qb,qv,qd,qf;
  wire [63:0] qe;
  wire [LINE_BITS-1:0] raw_command;
  genvar q;
  generate for(q=0;q<4;q=q+1)begin:quarter
    localparam integer NM=nmac(q), NC=ncol(q), MO=offset(q,0), CO=offset(q,1);
    ot_hbm_su_programme_local_q #(.LINE_BITS(LINE_BITS),.EDGES(EDGES),.COLS(COLS),
      .DICT_BANKS(DICT_BANKS),.Q(q),.GLOBAL_MACROS(GLOBAL_MACROS),.LOCAL_MACROS(NM),.MUT(MUT)) u(
      .clk_ctl(clk_ctl[q]),.rst_n(rst_n),.clk_cmd(clk_cmd[CO+:NC]),.clk_macro(clk_macro[MO+:NM]),
      .cfg_we(cfg_we),.cfg_bank(cfg_bank),.cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),
      .busy(qb[q]),.valid(qv[q]),.done(qd[q]),.fault(qf[q]),.edge_index(qe[q*16+:16]),
      .command(raw_command[q*QW+:QW]));
  end endgenerate
  assign command=(MUT==1)?{raw_command[QW-1:0],raw_command[LINE_BITS-1:QW]}:raw_command;
  assign busy=|qb;
  assign valid=&qv;
  assign done=&qd;
  assign fault=|qf;
  assign edge_index=qe[15:0];
endmodule
