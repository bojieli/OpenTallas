// census wrappers (QW-G5F 10-20): the leaf at its largest and smallest fan-in
module fcap16 (input wire ck, rs, input wire [15:0] f, output wire o); qfd_fault_capture #(.N(16)) u (.ck(ck), .rs(rs), .f(f), .o(o)); endmodule
module fcap1  (input wire ck, rs, input wire [0:0] f, output wire o);  qfd_fault_capture #(.N(1))  u (.ck(ck), .rs(rs), .f(f), .o(o)); endmodule
module for16  (input wire ck, rs, input wire [15:0] f, output wire o); qfd_fault_or #(.N(16)) u (.ck(ck), .rs(rs), .f(f), .o(o)); endmodule
