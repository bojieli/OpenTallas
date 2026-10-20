module red_reference (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [7:0]     l_ov,
    input  wire [8*32-1:0] l_out,
    input  wire [1:0]     l_red0,
    input  wire           l_redsq0,
    input  wire           l_last0,
    input  wire [23:0]    l_raddr0,
    output wire           red_we,
    output wire [23:0]    red_addr,
    output wire [31:0]    red_data,
    output reg            rd_v,
    output wire           busy,
    output wire           fault
);
 localparam integer SW=8, AW=24, LV=4;
 reg r1,r2,rc;
 always @(posedge ck or negedge rst_n) if(!rst_n) begin r1<=0;r2<=0;end else begin r1<=1;r2<=r1;end
 always @(posedge ck or negedge r2) if(!r2) rc<=0;else rc<=1;
 wire rst_c=rc;
    reg              rd_mx, rd_sq, rd_last;
    reg [AW-1:0]     rd_addr;
    reg [SW*32-1:0]  rd_x;
    integer li;
    always @(posedge ck or negedge rst_c) begin
        if (!rst_c) rd_v <= 1'b0;
        else rd_v <= l_ov[0] && l_red0 != 2'd0;
    end
    always @(posedge ck) begin
        rd_mx <= (l_red0 == 2'd2); rd_sq <= l_redsq0; rd_last <= l_last0; rd_addr <= l_raddr0;
        for (li = 0; li < SW; li = li + 1)
            rd_x[32*li +: 32] <= l_ov[li] ? l_out[32*li +: 32] : (l_red0 == 2'd2) ? l_out[31:0] : 32'd0;
    end
    ot_hdc_vreduce #(.SW(SW), .LV(LV), .AW(AW)) u_red (.clk(ck), .rst_n(rst_c), .v_in(rd_v), .mx_in(rd_mx),
        .sq_in(rd_sq), .last_in(rd_last), .addr_in(rd_addr), .x_in(rd_x),
        .o_we(red_we), .o_addr(red_addr), .o_data(red_data), .busy(busy), .fault(fault));
endmodule
module sc_reference #(parameter integer MUT = 0, parameter integer MU_NU = 4) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [100:0]   sc_cfg,
    input  wire [47:0]    dn_i,
    output wire [47:0]    dn_o,
    input  wire [47:0]    up_i,
    output wire [47:0]    up_o,
    input  wire           red_we,
    input  wire [23:0]    red_addr,
    input  wire [31:0]    red_data,
    input  wire [7:0]     vm_we,
    input  wire [1:0]     vm_win0,         // lane 0 vm_waddr[23:22]
    input  wire [31:0]    vm_wdata0,
    input  wire           am_v,
    input  wire [23:0]    am_idx,
    input  wire [31:0]    am_val,
    input  wire [1:0]     am_u,
    output wire           w1_we,
    output wire [23:0]    w1_addr,
    output wire [31:0]    w1_data,
    output wire           tok_v,
    output wire [23:0]    tok_idx,
    output wire           tok_own,
    output wire [31:0]    tok_val,
    output wire [1:0]     tok_user,
    output wire           busy,
    output wire           fault
);
 reg r1,r2;
 always @(posedge ck or negedge rst_n) if(!rst_n) begin r1<=0;r2<=0;end else begin r1<=1;r2<=r1;end
 wire cv,root,dir,fuse; wire[5:0] nb,amnb; wire[23:0] ss,rx; wire[31:0] eps;wire[4:0] k;
 assign {cv,root,dir,nb,ss,fuse,rx,eps,k,amnb}=sc_cfg;
 qfd_dv_scalar2 #(.MU_NU(4)) u_ref(.ck(ck),.rst_n(r2),.cfg_v(cv),.cfg_root(root),.cfg_rdir(dir),.cfg_nb(nb),.cfg_ss(ss),.cfg_fuse(fuse),.cfg_rx(rx),.cfg_eps(eps),.cfg_k(k),.cfg_amnb(amnb),
 .dn_i(dn_i),.dn_o(dn_o),.up_i(up_i),.up_o(up_o),
 .ps_v(red_we && red_addr[23:22]==3),.ps_idx({2'b00,red_addr[21:0]}),.ps_val(red_data),
 .rb_v((|vm_we) && vm_win0==3),.rb_val(vm_wdata0),.am_v(am_v),.am_idx(am_idx),.am_val(am_val),.am_u(am_u),
 .w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.busy(busy),.fault(fault));
 endmodule
