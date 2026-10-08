`timescale 1ps/1fs
// Actual 36-macro score/PV bank join. Typed contiguous writes establish current
// context ownership; no old/unwritten region may replay. E/output/CDC remain
// separate. Simulation delay pins the selected SRAM SS clock-to-Q only.
module ot_dsrom_softmax_sram_join #(
    parameter real SRAM_CLKQ_PS=455.3205489475797
)(
    input wire clk,rst_n,
    input wire begin_valid,begin_short,
    input wire [15:0] begin_tag,
    output wire begin_ready,
    input wire release_valid,
    input wire wr_valid,wr_pv,
    input wire [2:0] wr_beat,
    input wire [15:0] wr_tag,
    input wire [1023:0] wr_data,
    output wire wr_ready,
    output wire write_commit,
    output wire [6:0] write_commit_addr,
    input wire replay_valid,replay_pv,
    input wire [15:0] replay_tag,
    output wire replay_ready,
    output wire core_valid,core_pv,
    output wire [8191:0] core_data,
    output wire [15:0] core_tag,
    output wire [6:0] core_addr,
    output wire corrected,fault,busy,
    output wire score_done,pv_done
);
    (* keep="true",dont_touch="true" *) reg active,active_n,short_row,short_row_n;
    (* keep="true",dont_touch="true" *) reg [15:0] tag,tag_n;
    (* keep="true",dont_touch="true" *) reg [5:0] sw,sw_n,pw,pw_n;
    (* keep="true",dont_touch="true" *) reg sd,sd_n,pd,pd_n,wkind,wkind_n,bkind,bkind_n,running,running_n;
    (* keep="true",dont_touch="true" *) reg [5:0] issued,issued_n,returned,returned_n;
    (* keep="true",dont_touch="true" *) reg [6:0] read_addr,read_addr_n;
    (* keep="true",dont_touch="true" *) reg [22:0] return_identity,return_identity_n;
    (* keep="true",dont_touch="true" *) reg return_v,return_v_n,failed,failed_n;
    wire [5:0] score_limit=short_row?6'd8:6'd40;
    wire [5:0] burst_limit=bkind?6'd32:score_limit;
    wire integrity=(active_n==~active)&&(short_row_n==~short_row)&&(tag_n==~tag)
        &&(sw_n==~sw)&&(pw_n==~pw)&&(sd_n==~sd)&&(pd_n==~pd)&&(wkind_n==~wkind)
        &&(bkind_n==~bkind)&&(running_n==~running)&&(issued_n==~issued)
        &&(returned_n==~returned)&&(read_addr_n==~read_addr)
        &&(return_identity_n==~return_identity)&&(return_v_n==~return_v)&&(failed_n==~failed)
        &&(sw<=score_limit)&&(pw<=32)&&(issued<=burst_limit)&&(returned<=issued);
    wire serial_fault,replay_fault,serial_wr_ready;
    wire macro_w_valid;
    wire [6:0] macro_w_addr;
    wire [9215:0] macro_w_code,macro_q_raw,macro_q;
    wire replay_out_valid;
    wire [6:0] expected_core_addr=(bkind?7'd40:7'd0)+{1'b0,returned};
    wire bad_replay_output=replay_out_valid && (!running || core_tag!=tag || core_addr!=expected_core_addr);
    assign fault=failed||!integrity||serial_fault||replay_fault||bad_replay_output;
    assign busy=active;
    assign score_done=sd;
    assign pv_done=pd;
    assign begin_ready=!active&&!fault;
    assign replay_ready=active&&!running&&!fault && (replay_pv?(sd&&!pd&&pw==32):(!sd&&sw==score_limit));
    assign wr_ready=serial_wr_ready&&active&&!running&&!fault&&!release_valid &&
        (wr_pv?(sd&&!pd&&pw<32):(!sd&&sw<score_limit));
    wire write_fire=wr_valid&&wr_ready;
    wire bad_write_tag=write_fire && wr_tag!=tag;
    wire replay_fire=replay_valid&&replay_ready;
    wire bad_replay_tag=replay_fire && replay_tag!=tag;
    wire bad_release=release_valid && (!active||running||!sd||!pd);
    wire macro_w_ready=active&&!running&&!fault;
    wire macro_w_en=macro_w_valid&&macro_w_ready;
    wire [6:0] expected_write_addr=(wkind?7'd40:7'd0)+{1'b0,(wkind?pw:sw)};
    wire bad_commit=macro_w_en && macro_w_addr!=expected_write_addr;
    assign write_commit=macro_w_en&&!bad_commit&&!fault;
    assign write_commit_addr=macro_w_addr;
    wire macro_r_en=running&&(issued<burst_limit)&&!fault;
    wire unused_rd_ready,unused_mre,unused_out_valid,unused_corrected;
    wire [6:0] unused_mra;
    wire [15:0] unused_mrt,unused_out_tag;
    wire [2:0] unused_out_beat;
    wire [1023:0] unused_out_data;
    ot_dsrom_softmax_serial_row writer(
        .clk(clk),.rst_n(rst_n),.wr_valid(write_fire&&!bad_write_tag),.wr_ready(serial_wr_ready),
        .wr_data(wr_data),.wr_beat(wr_beat),.wr_addr((wr_pv?7'd40:7'd0)+{1'b0,(wr_pv?pw:sw)}),.wr_tag(wr_tag),
        .mem_w_valid(macro_w_valid),.mem_w_ready(macro_w_ready),.mem_w_addr(macro_w_addr),.mem_w_code(macro_w_code),
        .rd_valid(1'b0),.rd_ready(unused_rd_ready),.rd_addr(7'd0),.rd_tag(16'd0),
        .mem_r_en(unused_mre),.mem_r_addr(unused_mra),.mem_r_tag(unused_mrt),
        .mem_return_valid(1'b0),.mem_return_tag(16'd0),.mem_return_code(9216'd0),
        .out_valid(unused_out_valid),.out_ready(1'b0),.out_data(unused_out_data),.out_beat(unused_out_beat),
        .out_tag(unused_out_tag),.out_corrected(unused_corrected),.fault(serial_fault));
    genvar bank;
    generate for(bank=0;bank<36;bank=bank+1)begin:g_sram
        ot_sram_1r1w_128x256_m1_r2c2 mem(
            .clk(clk),.r_ce_in(macro_r_en),
`ifdef SOFTMAX_JOIN_ALIAS_ADDRESS
            .r_addr_in(read_addr^7'd1),
`else
            .r_addr_in(read_addr),
`endif
            .rd_out(macro_q_raw[256*bank +:256]),
            .w_ce_in(macro_w_en&&!bad_commit),.w_addr_in(macro_w_addr),.wd_in(macro_w_code[256*bank +:256]),
            .w_mask_in({256{1'b1}}),.rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
    end endgenerate
`ifdef SYNTHESIS
    assign macro_q=macro_q_raw;
`else
    assign #(SRAM_CLKQ_PS) macro_q=macro_q_raw;
`endif
    ot_dsrom_softmax_core_replay replay(
        .clk(clk),.rst_n(rst_n),.return_valid(return_v&&!failed),.return_code(macro_q),
        .return_tag(return_identity[22:7]),.return_addr(return_identity[6:0]),
        .core_valid(replay_out_valid),.core_data(core_data),.core_tag(core_tag),.core_addr(core_addr),
        .corrected(corrected),.fault(replay_fault));
    assign core_valid=replay_out_valid&&!fault;
    assign core_pv=(core_addr>=40);
    always @(posedge clk)begin
        if(!rst_n)begin
            active<=0;active_n<=1;short_row<=0;short_row_n<=1;tag<=0;tag_n<=~16'd0;
            sw<=0;sw_n<=~6'd0;pw<=0;pw_n<=~6'd0;sd<=0;sd_n<=1;pd<=0;pd_n<=1;
            wkind<=0;wkind_n<=1;bkind<=0;bkind_n<=1;running<=0;running_n<=1;
            issued<=0;issued_n<=~6'd0;returned<=0;returned_n<=~6'd0;read_addr<=0;read_addr_n<=~7'd0;
            return_identity<=0;return_identity_n<=~23'd0;return_v<=0;return_v_n<=1;failed<=0;failed_n<=1;
        end else if(fault||bad_write_tag||bad_replay_tag||bad_release||bad_commit)begin failed<=1;failed_n<=0;end
        else begin
            return_v<=macro_r_en;return_v_n<=~macro_r_en;
            if(begin_valid&&begin_ready)begin
                active<=1;active_n<=0;tag<=begin_tag;tag_n<=~begin_tag;short_row<=begin_short;short_row_n<=~begin_short;
                sw<=0;sw_n<=~6'd0;pw<=0;pw_n<=~6'd0;sd<=0;sd_n<=1;pd<=0;pd_n<=1;
                issued<=0;issued_n<=~6'd0;returned<=0;returned_n<=~6'd0;bkind<=0;bkind_n<=1;
            end
            if(release_valid)begin active<=0;active_n<=1;end
            if(write_fire && wr_beat==0)begin wkind<=wr_pv;wkind_n<=~wr_pv;end
            if(macro_w_en)begin
                if(wkind)begin pw<=pw+6'd1;pw_n<=~(pw+6'd1);end
                else begin sw<=sw+6'd1;sw_n<=~(sw+6'd1);end
            end
            if(replay_fire)begin
                running<=1;running_n<=0;bkind<=replay_pv;bkind_n<=~replay_pv;
                issued<=0;issued_n<=~6'd0;returned<=0;returned_n<=~6'd0;
                read_addr<=replay_pv?7'd40:7'd0;read_addr_n<=~(replay_pv?7'd40:7'd0);
            end
            if(macro_r_en)begin
                return_identity<={tag,read_addr};return_identity_n<=~{tag,read_addr};
                issued<=issued+6'd1;issued_n<=~(issued+6'd1);
                read_addr<=read_addr+7'd1;read_addr_n<=~(read_addr+7'd1);
            end
            if(core_valid)begin
                returned<=returned+6'd1;returned_n<=~(returned+6'd1);
                if(returned==burst_limit-1)begin
                    running<=0;running_n<=1;
                    if(bkind)begin pd<=1;pd_n<=0;end else begin sd<=1;sd_n<=0;end
                end
            end
        end
    end
endmodule
