`timescale 1ns/1ps
// Logical balanced full32 control composition. Placement and scheduler taps
// are provisional: this module is NOT the end-to-end vector-memory proof.
// All116 fans are a real closed-master parameterization with their OWN clock pins.
module ot_qfd_vm_band_controls #(parameter integer MUT=0, PHW=2)(
 input wire [115:0] clk_child,
 input wire me_early,
 input wire [19:0] pc,
 input wire [27:0] lc,
 input wire [27:0] tags,
 output wire [639:0] pc_columns,
 output wire [895:0] lc_columns,
 output wire [895:0] tags_columns,
 output wire [31:0] me_columns
);
 wire me_root;
 wire [3:0] me_group;
 wire [19:0] pc_root;
 wire [27:0] lc_root;
 wire [27:0] tag_root;
 wire [19:0] pc_group[0:3];
 wire [27:0] lc_group[0:3];
 wire [27:0] tag_group[0:3];
 ot_qfd_vm_fan_t #(.W(1),.EN(0),.MEREG(1)) u_me_root
 (.clk(clk_child[0]),.me_e(1'b0),.d(me_early),.q(me_root));
 ot_qfd_vm_fan_t #(.W(20),.EN(1),.MEREG(1)) u_pc_root
 (.clk(clk_child[5]),.me_e(me_group[0]),.d(pc),.q(pc_root));
 ot_qfd_vm_fan_t #(.W(28),.EN(1),.MEREG(1)) u_lc_root
 (.clk(clk_child[42]),.me_e(me_group[0]),.d(lc),.q(lc_root));
 ot_qfd_vm_fan_t #(.W(28),.EN(1),.MEREG(1)) u_tag_root
 (.clk(clk_child[79]),.me_e(me_group[0]),.d(tags),.q(tag_root));
 genvar g,c;
 generate for(g=0;g<4;g=g+1)begin: groups
   ot_qfd_vm_fan_t #(.W(1),.EN(0),.MEREG(1)) u_me
    (.clk(clk_child[1+g]),.me_e(1'b0),.d(me_root),.q(me_group[g]));
   ot_qfd_vm_fan_t #(.W(20),.EN(1),.MEREG(1)) u_pc
    (.clk(clk_child[6+g]),.me_e(me_group[g]),.d(pc_root),.q(pc_group[g]));
   ot_qfd_vm_fan_t #(.W(28),.EN(1),.MEREG(1)) u_lc
    (.clk(clk_child[43+g]),.me_e(me_group[g]),.d(lc_root),.q(lc_group[g]));
   ot_qfd_vm_fan_t #(.W(28),.EN(1),.MEREG(1)) u_tag
    (.clk(clk_child[80+g]),.me_e(me_group[g]),.d(tag_root),.q(tag_group[g]));
 end
 for(c=0;c<32;c=c+1)begin: columns
   wire [27:0] lc_q,tag_q;
   ot_qfd_vm_fan_t #(.W(20),.EN(1),.MEREG(1),.MUT((MUT==1 && c==7)?1:0)) u_pc
    (.clk(clk_child[10+c]),.me_e(me_group[c/8]),.d(pc_group[c/8]),.q(pc_columns[20*c+:20]));
   ot_qfd_vm_fan_t #(.W(28),.EN(1),.MEREG(1)) u_lc
    (.clk(clk_child[47+c]),.me_e(me_group[c/8]),.d(lc_group[c/8]),.q(lc_q));
   assign lc_columns[28*c+:28]=lc_q;
   ot_qfd_vm_fan_t #(.W(28),.EN(1),.MEREG(1)) u_tag
    (.clk(clk_child[84+c]),.me_e(me_group[c/8]),.d(tag_group[c/8]),.q(tag_q));
   assign tags_columns[28*c+:28]=tag_q ^ ((MUT==2 && c==23)?(28'h1<<(PHW+1)):28'h0);
   assign me_columns[c]=me_group[c/8];
 end endgenerate
endmodule
