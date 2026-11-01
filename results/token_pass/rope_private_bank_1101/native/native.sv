`timescale 1ns/1fs
module qfd_dv_s5_rst2 (input wire ck, input wire rst_n, output wire rst);
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule

module qfd_s8k_rp_wbit (input wire ck, rst, d, c519, c518, output wire w);
    (* keep = 1 *) reg arm;
    always @(posedge ck or negedge rst) if (!rst) arm <= 1'b0; else arm <= d;
    assign w = arm & c519 & c518;
endmodule

module qfd_s8k_rp_wgrp #(parameter integer N = 24) (
    input wire ck, rst_n, c_rpa, w_m, k7, arm_m,
    input wire [N-1:0] c519, c518,
    output wire [N-1:0] w
);
    wire rst;
    qfd_dv_s5_rst2 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    // == master rp_arm next state: if(c_rpa)1 else if(rp_w && rp_k==7)0 else hold
    wire nx = c_rpa | (arm_m & ~(w_m & k7));
    generate for (genvar c = 0; c < N; c = c + 1) begin : g_b
        (* keep_hierarchy = "yes" *) qfd_s8k_rp_wbit u_b (.ck(ck), .rst(rst), .d(nx), .c519(c519[c]), .c518(c518[c]), .w(w[c]));
    end endgenerate
endmodule

module qfd_dv_s8_rp1 #(parameter integer USE_W_COPIES=0, parameter integer NW=89) (
 input wire ck,rst_n,
 input wire[115:0]cmd_q,input wire[1037:0]chd_q,
 input wire tw_we,input wire[1:0]tw_kind,input wire[23:0]tw_addr,input wire[1023:0]tw_data,
 output wire[115:0]ctl_cmd,output wire[1037:0]ctl_chd,
 output wire vtw_we,output wire[1:0]vtw_kind,output wire[23:0]vtw_addr,output wire[1023:0]vtw_data,
 output wire fault,
 input wire[NW-1:0]w519_cp,w518_cp
);
 wire rst;
 qfd_dv_s5_rst2 u_rl(.ck(ck),.rst_n(rst_n),.rst(rst));
 reg[3:0]sid_q;reg sid_ok;
 wire setid=cmd_q[0] && cmd_q[3:1]==3'd7;
 always @(posedge ck or negedge rst)
  if(!rst)begin sid_q<=0;sid_ok<=0;end
  else if(setid)begin sid_q<=cmd_q[7:4];sid_ok<=1;end
 wire go=cmd_q[0] && sid_ok && (cmd_q[115:112]==sid_q || cmd_q[115:112]==4'hf) && cmd_q[3:1]!=3'd7;
 wire[519:0]dd_q=chd_q[519:0];
 reg rp_arm;reg[9:0]rp_base;reg[2:0]rp_k;
 wire c_rpa=go && cmd_q[3:1]==0 && cmd_q[5:4]==1;
 wire rp_w=rp_arm && dd_q[519] && dd_q[518];
 wire rp_bk=rp_k[0];
 wire rp_bad=(c_rpa && rp_arm) || (rp_w && dd_q[514:512]!=rp_k) || (rp_w && tw_we);
 always @(posedge ck or negedge rst)
  if(!rst)begin rp_arm<=0;rp_base<=0;rp_k<=0;end
  else if(c_rpa)begin rp_arm<=1;rp_base<=cmd_q[15:6];rp_k<=0;end
  else if(rp_w)begin rp_k<=rp_k+3'd1;if(rp_k==7)rp_arm<=0;end
 // kept chunk selects: [0..85] vtw_data 12 b each, [86..87] vtw_addr 12 b each, [88] vtw_kind+vtw_we
 wire[NW-1:0]c519=USE_W_COPIES?w519_cp:{NW{dd_q[519]}};
 wire[NW-1:0]c518=USE_W_COPIES?w518_cp:{NW{dd_q[518]}};
 wire[NW-1:0]wk;
 wire k7=rp_k==3'd7;
 generate for(genvar g=0;g<(NW+23)/24;g=g+1)begin:g_wgrp
  localparam integer GN=(NW-g*24<24)?NW-g*24:24;
  (* keep_hierarchy = "yes" *) qfd_s8k_rp_wgrp #(.N(GN)) u_g(.ck(ck),.rst_n(rst_n),.c_rpa(c_rpa),.w_m(rp_w),.k7(k7),.arm_m(rp_arm),
   .c519(c519[g*24+:GN]),.c518(c518[g*24+:GN]),.w(wk[g*24+:GN]));
 end endgenerate
 wire[23:0]rp_addr={12'd0,1'b1,rp_bk,rp_base+{8'd0,rp_k[2:1]}};
 wire[1023:0]rp_data={dd_q[511:0],dd_q[511:0]};
 generate for(genvar i=0;i<1024;i=i+1)begin:g_vd
  assign vtw_data[i]=wk[i/12] ? rp_data[i] : tw_data[i];
 end
 for(genvar i=0;i<24;i=i+1)begin:g_va
  assign vtw_addr[i]=wk[86+i/12] ? rp_addr[i] : tw_addr[i];
 end endgenerate
 assign vtw_we=tw_we || wk[88];
 assign vtw_kind=wk[88] ? 2'd1 : tw_kind;
 assign ctl_cmd={cmd_q[115:1],cmd_q[0] && !c_rpa};
 assign ctl_chd={chd_q[1037:520],chd_q[519] && !rp_w,chd_q[518:0]};
 assign fault=rp_bad;
endmodule

module candidate #(parameter NU=4,UB=2,MUT=0,UFOLD=1,UVM_STRIDE=4096,
PIDX_STRIDE=128,UTAG_LSB=6,TABLE_USER_RELOC=0,BTAB_COMPACT=1)
(input [115:0] ic,input [1:0] ru,output [115:0] result,output bad);
wire [2:0] i_kind=ic[3:1];wire i_loc=ic[115:112]==14;
    wire [24:0]   ub = (NU > 1 && MUT != 12) ? 25'(ru) * 25'(UVM_STRIDE) : 25'd0;
    wire [9:0]    up = (NU > 1 && MUT != 12) ? 10'(ru) * 10'(PIDX_STRIDE) : 10'd0;
    wire [24:0]   r_ar = {1'b0, ic[27:4]} + ub, r_dd = {1'b0, ic[51:28]} + ub, r_em = {1'b0, ic[77:54]} + ub,
                  r_db = {1'b0, ic[49:26]} + ub;
    wire [9:0]    r_px = {1'b0, ic[12:4]} + up;
    wire [24:0]   r_ss = {1'b0, ic[34:11]} + ub, r_rx = {1'b0, ic[59:36]} + ub;
    wire [8:0]    table_bbase = (MUT==12 || ru==0)?9'd0:(ru==1)?9'd272:(ru==2)?9'd344:9'd416;
    // Compact sbase72..271 is the common read-only HEAD table, retained when
    // layer tables0..71 reload. Other users' layer tables occupy272..487.
    wire [9:0]    table_boffset = (BTAB_COMPACT!=0) ?
                  ((ic[23:15]<72)?{1'b0,table_bbase}:10'd0) : ((MUT==12)?10'd0:(10'(ru)*10'd128));
    wire [9:0]    r_sb = {1'b0, ic[23:15]} + table_boffset;
    // Native RP1 consumes eight 512-bit beats as two banks of four CROM rows.
    // Its row base has no hidden user selector; match the loader's128-row stride.
    wire [10:0]   r_rope = {1'b0, ic[15:6]} + ((MUT==12)?11'd0:(11'(ru)*11'd128));
    reg  [115:0]  rc; reg r_bad;
    always @* begin
        rc = ic; r_bad = 1'b0;
        if (NU > 1 && !i_loc) begin
            case (i_kind)
                3'd4: begin rc[27:4] = r_ar[23:0]; rc[51:28] = r_dd[23:0]; rc[77:54] = r_em[23:0];
                            r_bad = r_ar[24] | r_dd[24] | r_em[24]; end
                3'd2: begin
                    if (ic[24]) begin rc[49:26] = r_db[23:0]; r_bad = r_db[24]; end
                    if (TABLE_USER_RELOC != 0) begin
                        rc[23:15] = r_sb[8:0];
                        r_bad = r_bad | r_sb[9] | ((BTAB_COMPACT!=0)?(ic[23:15]>=272):(ic[23:15]>=128));
                    end
                end
                3'd3: if (TABLE_USER_RELOC != 0) begin
                    rc[34:11] = r_ss[23:0]; rc[59:36] = r_rx[23:0];
                    r_bad = r_ss[24] | r_rx[24] | (ic[34:11]>=UVM_STRIDE) | (ic[59:36]>=UVM_STRIDE);
                end
                3'd1: begin rc[12:4] = r_px[8:0]; r_bad = r_px[9]; end
                3'd0: if (ic[5:4] == 2'd0) begin
                          if (ic[23 + UTAG_LSB +: UB] != {UB{1'b0}}) r_bad = 1'b1;
                          rc[23 + UTAG_LSB +: UB] = ru;
                      end else if (TABLE_USER_RELOC != 0 && ic[5:4] == 2'd1) begin
                          rc[15:6] = r_rope[9:0];
                          // The complete four-row write must stay in this user's bank.
                          r_bad = r_rope[10] | (ic[15:6] > 10'd124);
                      end
                3'd6: if (UFOLD != 0) begin
                          if (ic[9:8] != 2'd0) r_bad = 1'b1;
                          rc[9:8] = (MUT == 16) ? 2'd0 : 2'(ru);
                      end
                default: ;
            endcase
            // STN user (UFOLD): beside the dbase relocation above, any dst
            if (UFOLD != 0 && i_kind == 3'd2) begin
                if (ic[52:51] != 2'd0) r_bad = 1'b1;
                rc[52:51] = (MUT == 16) ? 2'd0 : 2'(ru);
            end
        end
    end

assign result=rc;assign bad=r_bad;
endmodule
