// Full-width II=1 protected SRAM return path for no-ready score/PV inputs.
// Input return sampled at edge N; downstream samples decoded output at N+3.
// Native-clock only. SRAM request scheduling and CDC remain outside this unit.
module ot_dsrom_softmax_core_replay(
    input wire clk,rst_n,
    input wire return_valid,
    input wire [9215:0] return_code,
    input wire [15:0] return_tag,
    input wire [6:0] return_addr,
    output wire core_valid,
    output wire [8191:0] core_data,
    output wire [15:0] core_tag,
    output wire [6:0] core_addr,
    output wire corrected,
    output wire fault
);
    wire [127:0] lane_valid,lane_corrected,lane_ue;
    (* keep="true",dont_touch="true" *) reg [2:0] valid_pipe,valid_pipe_n;
    (* keep="true",dont_touch="true" *) reg [22:0] identity0,identity0_n,identity1,identity1_n,identity2,identity2_n;
    (* keep="true",dont_touch="true" *) reg failed,failed_n;
    wire integrity=(valid_pipe_n==~valid_pipe)&&(identity0_n==~identity0)
        &&(identity1_n==~identity1)&&(identity2_n==~identity2)&&(failed_n==~failed);
    wire valid_disagreement=(lane_valid!={128{valid_pipe[2]}});
    wire uncorrectable=valid_pipe[2]&&(|lane_ue);
    assign fault=failed||!integrity||valid_disagreement||uncorrectable;
    assign core_valid=valid_pipe[2]&&!fault;
    assign corrected=|lane_corrected;
    assign {core_tag,core_addr}=identity2;
    genvar lane;
    generate for(lane=0;lane<128;lane=lane+1)begin:g_decode
        wire unused_write_valid;
        wire [71:0] unused_write_code;
        ot_dsrom_softmax_ecc_lane codec(
            .clk(clk),.rst_n(rst_n),.w_valid(1'b0),.w_data(64'd0),
            .w_code_valid(unused_write_valid),.w_code(unused_write_code),
            .r_valid(return_valid&&!failed),
`ifdef SOFTMAX_CORE_REPLAY_SWAP_LANES
            .r_code(return_code[72*(lane^1) +:72]),
`else
            .r_code(return_code[72*lane +:72]),
`endif
            .r_data_valid(lane_valid[lane]),.r_data(core_data[64*lane +:64]),
            .corrected(lane_corrected[lane]),.uncorrectable(lane_ue[lane]));
    end endgenerate
    always @(posedge clk)begin
        if(!rst_n)begin
            valid_pipe<=0;valid_pipe_n<=~3'd0;
            identity0<=0;identity0_n<=~23'd0;identity1<=0;identity1_n<=~23'd0;identity2<=0;identity2_n<=~23'd0;
            failed<=0;failed_n<=1;
        end else if(fault)begin failed<=1;failed_n<=0;end
        else begin
            valid_pipe<={valid_pipe[1:0],return_valid};
            valid_pipe_n<=~{valid_pipe[1:0],return_valid};
            if(return_valid)begin identity0<={return_tag,return_addr};identity0_n<=~{return_tag,return_addr};end
            if(valid_pipe[0])begin identity1<=identity0;identity1_n<=~identity0;end
            if(valid_pipe[1])begin identity2<=identity1;identity2_n<=~identity1;end
        end
    end
endmodule
