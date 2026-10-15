`timescale 1ns/1ps
// One capture edge at each face of the typed native attention transport.
// Scheduled events are required inputs. Availability mismatches only fault;
// this block has no queue, ready-driven scheduling, inferred epoch or retry.
// Each instance is synchronous to ck. Crossing into another clock family is
// a separate mandatory real-RTL/compiled-phase integration obligation.
module qkd_native_attention_record #(
    parameter integer KV_SIDE=1,
    parameter integer MUT=0
)(
    input wire ck,rst_n,
    input wire tx_event,tx_expected,
    input wire [3:0] tx_kind,tx_expected_kind,
    input wire [15:0] tx_epoch,tx_expected_epoch,
    input wire [5:0] tx_layer,tx_expected_layer,
    input wire [4:0] tx_beat,tx_expected_beat,
    input wire [511:0] tx_data,
    output reg tx_valid,output reg [547:0] tx_payload,
    input wire rx_event,rx_expected,
    input wire [547:0] rx_payload,
    input wire [3:0] rx_expected_kind,
    input wire [15:0] rx_expected_epoch,
    input wire [5:0] rx_expected_layer,
    input wire [4:0] rx_expected_beat,
    output reg rx_valid,
    output reg [3:0] rx_kind,
    output reg [15:0] rx_epoch,
    output reg [5:0] rx_layer,
    output reg [4:0] rx_beat,
    output reg [511:0] rx_data,
    output reg fault,output reg [3:0] fault_cause
);
    localparam [3:0] CMD=1,Q=2,RESULT=3,STATUS=4;
    function legal(input [3:0] kind,input [5:0] layer,input [4:0] beat,input [511:0] data);
        begin
            legal=layer<36 && ((kind==Q)||(kind==RESULT)||
                (kind==CMD && beat==0 && data[511:19]==0 && data[18:1]<8192)||
                (kind==STATUS && beat==0 && data[511:5]==0));
        end
    endfunction
    function direction(input [3:0] kind,input bit transmit);
        begin
            if((KV_SIDE!=0)==transmit)direction=kind==RESULT||kind==STATUS;
            else direction=kind==CMD||kind==Q;
        end
    endfunction
    wire [3:0] rk=rx_payload[542:539];
    wire [5:0] rl=rx_payload[538:533];
    wire [15:0] re=rx_payload[532:517];
    wire [4:0] rb=rx_payload[516:512];
    wire tx_time_bad=MUT!=1 && tx_event!=tx_expected;
    wire rx_time_bad=MUT!=1 && rx_event!=rx_expected;
    wire tx_record_bad=tx_event && (!legal(tx_kind,tx_layer,tx_beat,tx_data)||!direction(tx_kind,1'b1)||
        (MUT!=2 && {tx_kind,tx_epoch,tx_layer,tx_beat}!={tx_expected_kind,tx_expected_epoch,tx_expected_layer,tx_expected_beat}));
    wire rx_record_bad=rx_event && (rx_payload[547:543]!=0||!legal(rk,rl,rb,rx_payload[511:0])||!direction(rk,1'b0)||
        (MUT!=2 && {rk,re,rl,rb}!={rx_expected_kind,rx_expected_epoch,rx_expected_layer,rx_expected_beat}));
    wire bad=tx_time_bad||rx_time_bad||tx_record_bad||rx_record_bad;
    always @(posedge ck or negedge rst_n)begin
        if(!rst_n)begin
            tx_valid<=0;tx_payload<=0;rx_valid<=0;rx_kind<=0;rx_epoch<=0;rx_layer<=0;rx_beat<=0;rx_data<=0;
            fault<=0;fault_cause<=0;
        end else begin
            tx_valid<=0;rx_valid<=0;
            if(!fault)begin
                if(bad)begin
                    fault<=1;fault_cause<={rx_record_bad,tx_record_bad,rx_time_bad,tx_time_bad};
                end else begin
                    tx_valid<=tx_event;
                    if(tx_event)tx_payload<={5'd0,tx_kind,tx_layer,tx_epoch,tx_beat,tx_data};
                    rx_valid<=rx_event;
                    if(rx_event)begin
                        rx_kind<=rk;rx_epoch<=re;rx_layer<=rl;rx_beat<=rb;rx_data<=rx_payload[511:0];
                    end
                end
            end
        end
    end
endmodule
