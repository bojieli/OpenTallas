module top (
    input wire ck,
    input wire rst_n,
    input wire [7:0] re,
    input wire [191:0] addr,
    output wire [255:0] q,
    input wire [7:0] vm_we,
    input wire [191:0] vm_waddr,
    input wire [255:0] vm_wdata,
    input wire w16_we,
    input wire [23:0] w16_addr,
    input wire [511:0] w16_data,
    input wire w1_we,
    input wire [23:0] w1_addr,
    input wire [31:0] w1_data,
    output wire fault
);
qfd_dv_s8x_vmr #(.MIF(0)) u_child (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(fault));
endmodule
