`default_nettype none
module ot_hbm_sm_attn_front_static_nomarker #(parameter integer KVMUT = 0,   // KVMUT: bench negative control only (ot_hbm_sm_kv_line MUT)
    parameter integer INT8W = 0)(  // HBM-QINT8B (10-20) opt-in, default off (0 = the netlist / behaviour as before): command
                                   // mode 3 = one packed line as two BF16 rows of one chunk (ot_hbm_sm_i8w_front)
    input wire clk,rst_n,
    input wire [190:0] command,
    input wire [63:0] kv_desc,
    input wire [1098:0] packet,
    input wire xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
    output wire [42:0] request,
    output wire [3271:0] rl,rr,
    output wire [4137:0] bl,br,
    input wire [183:0] ql,qr,
    output wire rv,output wire [11:0] rrow,output wire [255:0] rdata,
    output wire fault,output reg schedule_fault
);
 ot_hbm_sm_attn_front_static #(.KVMUT(KVMUT),.INT8W(INT8W)) u_front (
.clk(clk),
.rst_n(rst_n),
.command({command[190:116],1'b0,command[115:0]}),
.kv_desc(kv_desc),
.packet(packet),
.xw_en(xw_en),
.xw_addr(xw_addr),
.xw_grp(xw_grp),
.xw_data(xw_data),
.request(request),
.rl(rl),
.rr(rr),
.bl(bl),
.br(br),
.ql(ql),
.qr(qr),
.rv(rv),
.rrow(rrow),
.rdata(rdata),
.fault(fault),
.schedule_fault(schedule_fault)
 );
endmodule
`default_nettype wire
