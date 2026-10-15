// TP8 distinct-line scatter protocol. Existing 508-bit corridor is unchanged:
// [507:380]=x, [379:1]=ib, [0]=ib_go.
// go=0: ib[378]=1 means LOAD, ib[8:0]=quad-line ID, ib[377:9]=0.
// go=1: original full ib is EXEC; no ib bit is reserved in EXEC.
// Idle is all zero. Root encoder must replace inactive legacy ib with zero.
module ot_qwen_xline_pack (
    input wire load_v, input wire [8:0] load_id, input wire [127:0] load_x,
    input wire exec_v, input wire [378:0] exec_ib,
    output wire [507:0] word
);
    wire [378:0] load_ib = {1'b1,369'b0,load_id};
    assign word = exec_v ? {128'b0,exec_ib,1'b1} :
                  load_v ? {load_x,load_ib,1'b0} : 508'b0;
endmodule

// Insert in tile ctl after its tap pin registers and before tile core inputs.
// No extra EXEC register: core's existing ib capture edge consumes x_hold.
// full tile_id is unchanged; line mapping is tile_id % 512 = tile_id[8:0].
module ot_qwen_xline_capture #(
    parameter integer MUT_IGNORE_ID = 0
) (
    input wire clk, input wire rst_n, input wire [15:0] tile_id,
    input wire [507:0] word,
    output wire ib_go, output wire [378:0] ib,
    output wire [127:0] xl, output wire fault
);
    wire exec_v = word[0];
    wire load_v = !exec_v && word[379];
    wire canonical = word[378:10] == 369'b0;
    wire match_id = MUT_IGNORE_ID != 0 || word[9:1] == tile_id[8:0];
    reg [127:0] x_hold;
    reg x_valid, fault_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin x_hold <= 0; x_valid <= 0; fault_q <= 0; end
        else begin
            if (load_v && !canonical) fault_q <= 1;
            if (load_v && canonical && match_id) begin
                x_hold <= word[507:380]; x_valid <= 1;
            end
            if (exec_v) begin
                if (!x_valid) fault_q <= 1;
                x_valid <= 0;
            end
        end
    end
    assign ib_go = rst_n && exec_v && x_valid;
    assign ib = exec_v ? word[379:1] : 379'b0;
    assign xl = x_hold;
    assign fault = fault_q;
endmodule

// Root scatter controller. VM accepts one independent request/root per edge.
// q_v are single-edge response pulses, q_id are tags pipelined with q_x.
// No new instruction accepted while scatter is busy. Existing layer scheduler
// additionally observes tile completion before issuing the next instruction.
module ot_qwen_xline_roots (
    input wire clk, input wire rst_n,
    input wire start, input wire [378:0] start_ib,
    output wire busy, output wire fault,
    output wire sel_v, output wire [8:0] sel_id,
    input wire qw_v, input wire [8:0] qw_id, input wire [127:0] qw_x,
    input wire qe_v, input wire [8:0] qe_id, input wire [127:0] qe_x,
    output wire [507:0] xw_d, output wire [507:0] xe_d
);
    reg active, fault_q;
    reg [378:0] ib_q;
    reg [9:0] issued, rw, re;
    reg ew, ee;
    wire vw = active && qw_v && rw<512 && qw_id==rw[8:0];
    wire ve = active && qe_v && re<512 && qe_id==re[8:0];
    assign busy=active;
    assign fault=fault_q;
    assign sel_v=active && issued<512;
    assign sel_id=issued[8:0];
    ot_qwen_xline_pack pw(vw,qw_id,qw_x,ew,ib_q,xw_d);
    ot_qwen_xline_pack pe(ve,qe_id,qe_x,ee,ib_q,xe_d);
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin active<=0; fault_q<=0; ib_q<=0; issued<=0; rw<=0; re<=0; ew<=0; ee<=0; end
        else begin
            ew<=0; ee<=0;
            if(start) begin
                if(active) fault_q<=1;
                else begin active<=1; issued<=0; rw<=0; re<=0; ib_q<=start_ib; end
            end
            if(sel_v) issued<=issued+1;
            if(active) begin
                if(qw_v && !vw || qe_v && !ve) fault_q<=1;
                if(vw) begin rw<=rw+1; if(rw==511) ew<=1; end
                if(ve) begin re<=re+1; if(re==511) ee<=1; end
                if(rw==512 && re==512 && !ew && !ee) active<=0;
            end
        end
    end
endmodule
