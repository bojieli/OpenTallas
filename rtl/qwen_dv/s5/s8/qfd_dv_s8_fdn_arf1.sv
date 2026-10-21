`timescale 1ns/1ps
// Existing ARF1 stamps before original fdn output register; split regional timing must be measured.
module qfd_dv_s8_fdn_arf1 #(parameter integer USE_SEL_COPIES=0) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [115:0]   cmd_i,
    input  wire [452:0]   hr_i,
    input  wire [1087:0]  st_up_i,
    input  wire [47:0]    sc_up_i,
    input  wire [1037:0]  ch_dn_i,
    input  wire [8:0]     treq_i,
    output reg  [115:0]   cmd_q,
    output reg  [452:0]   hr_q,
    output reg  [1087:0]  sw_q,
    output reg  [47:0]    scu_q,
    output reg  [1037:0]  chd_q,
    output reg  [8:0]     treq_q,
    input wire [45:0] chu_ar_sel, chu_dd_sel,
    input  wire [1094:0]  chu_q,
    input  wire [1094:0]  own_ch,
    output reg  [1094:0]  ch_dn_o,
    output wire           pc_bad,
    input  wire [9:0]     agu_q,
    input  wire [9:0]     ag_own,
    output reg  [9:0]     ag_dn_o,
    input  wire [1087:0]  st_dn_c,
    output wire [1087:0]  st_dn_o,
    input  wire [47:0]    sc_dn_c,
    output wire [47:0]    sc_dn_o,
    input  wire [106:0]   st_c,
    output wire [106:0]   st,
    input  wire [49:0]    cc_c,
    output wire [49:0]    cc_o,
    input  wire [513:0]   l9_i,
    output wire [65:0]    l9_r0, l9_r1, l9_r2, l9_r3, l9_r4, l9_r5, l9_r6, l9_r7,
    output wire [8:0]     treq_c
);
    assign st_dn_o = st_dn_c; assign sc_dn_o = sc_dn_c; assign st = st_c; assign cc_o = cc_c;
    assign l9_r0 = {l9_i[513:512], l9_i[63:0]};
    assign l9_r1 = {l9_i[513:512], l9_i[127:64]};
    assign l9_r2 = {l9_i[513:512], l9_i[191:128]};
    assign l9_r3 = {l9_i[513:512], l9_i[255:192]};
    assign l9_r4 = {l9_i[513:512], l9_i[319:256]};
    assign l9_r5 = {l9_i[513:512], l9_i[383:320]};
    assign l9_r6 = {l9_i[513:512], l9_i[447:384]};
    assign l9_r7 = {l9_i[513:512], l9_i[511:448]};
    assign treq_c = treq_i;
    wire [3:0] rst;
    qfd_dv_s6_rst2x4 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    // valid / control bits (reset copy 0: 20 loads)
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin cmd_q[0] <= 1'b0; hr_q[0] <= 1'b0; sw_q[1087] <= 1'b0; scu_q[47] <= 1'b0;
                           chd_q[1037] <= 1'b0; chd_q[519] <= 1'b0; treq_q[8] <= 1'b0; end
        else begin cmd_q[0] <= cmd_i[0]; hr_q[0] <= hr_i[0]; sw_q[1087] <= st_up_i[1087]; scu_q[47] <= sc_up_i[47];
                   chd_q[1037] <= ch_dn_i[1037]; chd_q[519] <= ch_dn_i[519]; treq_q[8] <= treq_i[8]; end
    // payload (no reset)
    always @(posedge ck) begin
        cmd_q[115:1] <= cmd_i[115:1]; hr_q[452:1] <= hr_i[452:1]; sw_q[1086:0] <= st_up_i[1086:0];
        scu_q[46:0] <= sc_up_i[46:0]; chd_q[1036:520] <= ch_dn_i[1036:520]; chd_q[518:0] <= ch_dn_i[518:0];
        treq_q[7:0] <= treq_i[7:0];
    end
    wire p_ar = chu_q[1094], p_dd = chu_q[547];
    wire [1094:0] ch_raw;
    generate for(genvar c=0;c<46;c=c+1) begin:g_ch_select
      localparam integer ARW=(547-c*12<12)?547-c*12:12;
      localparam integer DDW=(548-c*12<12)?548-c*12:12;
      wire sa=USE_SEL_COPIES?chu_ar_sel[c]:p_ar;
      wire sd=USE_SEL_COPIES?chu_dd_sel[c]:p_dd;
      assign ch_raw[548+c*12+:ARW]=sa?chu_q[548+c*12+:ARW]:own_ch[548+c*12+:ARW];
      assign ch_raw[c*12+:DDW]=sd?chu_q[c*12+:DDW]:own_ch[c*12+:DDW];
    end endgenerate
    reg [3:0] arf_sid; reg arf_sid_ok;
    wire setid=cmd_q[0] && cmd_q[3:1]==3'd7;
    always @(posedge ck or negedge rst[1])
      if(!rst[1]) begin arf_sid<=0;arf_sid_ok<=0;end
      else if(setid) begin arf_sid<=cmd_q[7:4];arf_sid_ok<=1;end
    wire go=cmd_q[0] && arf_sid_ok && (cmd_q[115:112]==arf_sid || cmd_q[115:112]==4'hf) && cmd_q[3:1]!=3'd7;
    reg arf_arm;reg[31:0]arf_tag;reg[15:0]arf_wm1,arf_cnt;
    // One header predicate, then independent real kept guard cells per field.
    wire xcc_header=(cmd_q[3:1]==0) && (cmd_q[5:4]==0);
    wire [7:0] xcc_guard;
    generate for(genvar g=0;g<8;g=g+1)begin:g_xcc_guard
      qfd_dv_s8_fdn_and2 #(.ID(g)) u_g(.a(go),.b(xcc_header),.y(xcc_guard[g]));
    end endgenerate
    wire c_xcc=xcc_guard[0];
    wire [6:0] fr_guard;
    generate for(genvar g=0;g<7;g=g+1)begin:g_fr_guard
      qfd_dv_s8_fdn_and2 #(.ID(20+g)) u_g(.a(arf_arm),.b(ch_raw[1094]),.y(fr_guard[g]));
    end endgenerate
    wire arf_fr=fr_guard[0];wire arf_last=arf_cnt==arf_wm1;
    wire arf_bad=(c_xcc && arf_arm && !(arf_fr && arf_last)) || (ch_raw[1094] && !arf_arm && arf_sid==0);
    // Payload/tag/counter are meaningful only while arf_arm. Control reset uses
    // the existing independent kept copy1, preserving original copy0's20loads.
    always @(posedge ck or negedge rst[1])
      if(!rst[1])arf_arm<=0;
      else if(c_xcc)arf_arm<=1;
      else if(arf_fr && arf_last)arf_arm<=0;
    wire[15:0] arf_wm1_load=cmd_q[22:7]-16'd1;
    wire[15:0] arf_cnt_inc=arf_cnt+16'd1;
    generate for(genvar g=0;g<3;g=g+1)begin:g_tag
      localparam integer LO=g*12,GW=(32-LO<12)?32-LO:12;
      always @(posedge ck) if(xcc_guard[1+g]) arf_tag[LO+:GW]<=cmd_q[23+LO+:GW];
    end
    for(genvar g=0;g<2;g=g+1)begin:g_counter
      localparam integer LO=g*12,GW=(16-LO<12)?16-LO:12;
      always @(posedge ck) if(xcc_guard[4+g]) arf_wm1[LO+:GW]<=arf_wm1_load[LO+:GW];
      always @(posedge ck)
        if(xcc_guard[6+g]) arf_cnt[LO+:GW]<=0;
        else if(fr_guard[5+g]) arf_cnt[LO+:GW]<=arf_cnt_inc[LO+:GW];
    end endgenerate
    wire[546:0]ar_out;
    // These branches were identical in the original ternary, including X/Z.
    assign ar_out[511:0]=ch_raw[1059:548];
    assign ar_out[513]=ch_raw[1061];
    generate for(genvar g=0;g<3;g=g+1)begin:g_tag_mux
      localparam integer LO=g*12,GW=(32-LO<12)?32-LO:12;
      qfd_dv_s8_fdn_mux #(.W(GW),.ID(g)) u_m(.s(fr_guard[1+g]),
        .a(arf_tag[LO+:GW]),.b(ch_raw[1062+LO+:GW]),.y(ar_out[514+LO+:GW]));
    end endgenerate
    qfd_dv_s8_fdn_mux #(.W(2),.ID(4)) u_meta(.s(fr_guard[4]),
      .a({1'b1,arf_last}),.b({ch_raw[1094],ch_raw[1060]}),.y({ar_out[546],ar_out[512]}));
    wire[1094:0]ch_m={ar_out,ch_raw[547:0]};
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin ch_dn_o[1094] <= 1'b0; ch_dn_o[547] <= 1'b0; ag_dn_o <= 10'd0; end
        else begin ch_dn_o[1094] <= ch_m[1094]; ch_dn_o[547] <= ch_m[547]; ag_dn_o <= agu_q | ag_own; end
    always @(posedge ck) begin ch_dn_o[1093:548] <= ch_m[1093:548]; ch_dn_o[546:0] <= ch_m[546:0]; end
    wire pc = (p_ar && own_ch[1094]) || (p_dd && own_ch[547]);
    reg pq;
    always @(posedge ck or negedge rst[0]) if (!rst[0]) pq <= 1'b0; else pq <= pc | arf_bad;
    assign pc_bad = pq;
endmodule


(* keep_hierarchy="yes" *) module qfd_dv_s8_fdn_and2 #(parameter integer ID=0)(input wire a,b,output wire y);
 assign y=a & b;
endmodule
(* keep_hierarchy="yes" *) module qfd_dv_s8_fdn_mux #(parameter integer W=12,ID=0)(input wire s,input wire[W-1:0]a,b,output wire[W-1:0]y);
 assign y=s ? a : b;
endmodule
