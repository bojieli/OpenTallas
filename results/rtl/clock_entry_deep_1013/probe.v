module deep(input a,b);wire[511:0] hop;ot_qfd_vm_su_t u0(.clk(a),.q(hop));ot_qfd_vm_su_t u1(.clk(b),.swd(hop));endmodule
