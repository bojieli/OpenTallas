`timescale 1ns/1ps
`default_nettype none
// Logical integration vehicle only: eight actual owned landing leaves.
// The compiler reserves one LOAD output slot per cycle. This is a fixed-slot
// merge, never an arbiter: two outputs or mismatched namespace fields fault.
// Physical hop/landing realization and production dispatch remain plan work.
module ot_hbm_static_load_quad_vehicle #(
    parameter integer RPIPE=1
)(
    input wire clk,rst_n,
    input wire begin_v,begin_bank,input wire[15:0]begin_epoch,
    input wire[15:0]fill_v,fill_bank,
    input wire[95:0]fill_slot,input wire[255:0]fill_epoch,
    input wire[4095:0]fill_data,
    input wire[7:0]load_v,input wire[495:0]load_cmd,
    output wire[15:0]block_ready,output wire[7:0]leaf_fault,
    output reg[280:0]vm_dq,output reg route_fault
);
    wire[7:0]full0,full1,pcbad,busy;
    wire[2247:0]load_dq,raw_dq;
    wire[23:0]dest_bank;wire[15:0]dest_q;wire[7:0]load_out_v;
    for(genvar b=0;b<8;b=b+1)begin:lane
        ot_hbm_svc_vmdel_lane_load_static #(.NPC(2),.SHPRE(1),.RPIPE(RPIPE)) u(
            .clk(clk),.rst_n(rst_n),.bank_id(3'(b)),
            .begin_v_i(begin_v),.begin_bank_i(begin_bank),.begin_epoch_i(begin_epoch),
            .start_i(1'b0),.start_bank_i(1'b0),.start_epoch_i(16'd0),.start_base_sector_i(16'd0),
            .fill_v_i(fill_v[b*2+:2]),.fill_bank_i(fill_bank[b*2+:2]),
            .fill_slot_i(fill_slot[b*12+:12]),.fill_epoch_i(fill_epoch[b*32+:32]),.fill_data_i(fill_data[b*512+:512]),
            .full0_all(full0),.full1_all(full1),.pcbad_all(pcbad),
            .full0(full0[b]),.full1(full1[b]),.pcbad(pcbad[b]),
            .block_ready(block_ready[b*2+:2]),.busy(busy[b]),.fault(leaf_fault[b]),
            .load_v_i(load_v[b]),.load_cmd_i(load_cmd[b*62+:62]),
            .load_dest_bank(dest_bank[b*3+:3]),.load_dest_q(dest_q[b*2+:2]),
            .load_dq(load_dq[b*281+:281]),.load_out_v(load_out_v[b]),.dq(raw_dq[b*281+:281])
        );
    end
    reg[280:0]merged;
    reg collision,namespace_bad;
    integer count;
    always @*begin
        merged=281'd0;count=0;namespace_bad=1'b0;
        for(integer b=0;b<8;b=b+1)if(load_out_v[b])begin
            count=count+1;
            merged=merged|load_dq[b*281+:281];
            if(load_dq[b*281+264+:3]!=dest_bank[b*3+:3]||
               load_dq[b*281+277+:2]!=dest_q[b*2+:2]||load_dq[b*281+279])namespace_bad=1'b1;
        end
        collision=count>1;
    end
    always @(posedge clk)begin
        vm_dq[279:0]<=merged[279:0];
        if(!rst_n)begin vm_dq[280]<=1'b0;route_fault<=1'b0;end
        else begin
            vm_dq[280]<=merged[280]&&!collision&&!namespace_bad;
            route_fault<=route_fault||collision||namespace_bad;
        end
    end
endmodule
`default_nettype wire
