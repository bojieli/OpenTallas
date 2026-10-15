`timescale 1ns/1ps
`default_nettype none
// Optional native-wrapper seam. Compiler chooses complete exclusive phases,
// including all fixed return edges. No arbitration or readiness-dependent mux.
// Disabled: existing residual VM and external gathered interfaces pass exactly.
module ot_hgi_hc_vm_gather_adapter_static #(
    parameter integer ENABLE_GATHER_READER=0
)(
    input wire clk,rst_n,
    input wire gather_phase,gather_launch,
    input wire [3:0] gather_npos,
    input wire [15:0] gather_base_sector,gather_stride_sector,
    input wire [135:0] residual_rq,
    input wire [7:0] residual_read,
    output wire [2055:0] residual_rr,
    output wire [135:0] local_rq,
    output wire [7:0] local_read,
    input wire [2055:0] local_rr,
    input wire external_mix_v,
    input wire [4:0] external_mix_row,
    input wire [2:0] external_mix_pos,
    input wire [31:0] external_mix_data,
    output wire gathered_mix_v,
    output wire [4:0] gathered_mix_row,
    output wire [2:0] gathered_mix_pos,
    output wire [31:0] gathered_mix_data,
    output wire gather_done,fault
);
    generate if(!ENABLE_GATHER_READER)begin:legacy
        assign local_rq=residual_rq;assign local_read=residual_read;assign residual_rr=local_rr;
        assign gathered_mix_v=external_mix_v;assign gathered_mix_row=external_mix_row;
        assign gathered_mix_pos=external_mix_pos;assign gathered_mix_data=external_mix_data;
        assign gather_done=0;assign fault=0;
    end else begin:native_gather
        wire [135:0] gather_rq;
        wire [7:0] gather_read;
        wire rf,gd;
        reg collision_fault,inflight;
        reg [18:0] residual_pending;
        wire residual_request=|residual_read;
        reg residual_record_active;
        always @*begin
            residual_record_active=0;
            for(integer b=0;b<8;b=b+1)residual_record_active=residual_record_active||residual_rq[b*17+16];
        end
        assign local_rq=gather_phase?gather_rq:residual_rq;
        assign local_read=gather_phase?gather_read:residual_read;
        assign residual_rr=gather_phase?2056'd0:local_rr;
        ot_hgi_hc_gathered_mix_reader_static reader(
            .clk(clk),.rst_n(rst_n),.launch(gather_launch),.npos(gather_npos),
            .base_sector(gather_base_sector),.position_stride_sector(gather_stride_sector),
            .local_rq(gather_rq),.local_read(gather_read),.local_rr(gather_phase?local_rr:2056'd0),
            .gathered_mix_v(gathered_mix_v),.gathered_mix_row(gathered_mix_row),
            .gathered_mix_pos(gathered_mix_pos),.gathered_mix_data(gathered_mix_data),.done(gd),.fault(rf));
        assign gather_done=gd;assign fault=collision_fault|rf;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin collision_fault<=0;inflight<=0;residual_pending<=0;end
            else begin
                residual_pending<={residual_pending[17:0],!gather_phase&&residual_request};
                if(gd)inflight<=0;
                if(gather_launch)begin
                    if(!gather_phase||(inflight&&!gd)||(|residual_pending)||residual_request||residual_record_active)collision_fault<=1;
                    inflight<=1;
                end
                if((gather_phase&&(residual_request||residual_record_active||(|residual_pending)))||
                   (!gather_phase&&((|gather_read)||(inflight&&!gd)))||external_mix_v)collision_fault<=1;
            end
        end
    end endgenerate
endmodule
`default_nettype wire
