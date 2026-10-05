`timescale 1ns/1ps
// Bounded in-order auxiliary service queue. A request reserves its eventual
// response slot before leaving; queued plus in-flight entries never exceed
// DEPTH. Service responses must arrive in request order and echo generation
// and weight-stream address. Each response contains all enabled scale planes.
// A stale/misordered response is refused and surfaced, never attached to a new
// operation. clear must also cancel/drain the external producer's generation.
module ot_a3_lq8_auxiliary_prefetch #(
    parameter integer LANES=8,
    parameter integer DEPTH=2,
    parameter bit REGISTER_REQUESTS=0,
    parameter integer PW=(DEPTH<2)?1:$clog2(DEPTH),
    parameter integer CW=$clog2(DEPTH+1)
)(
    input wire clk,rst_n,clear,
    input wire request_valid,
    output wire request_ready,
    input wire [31:0] request_generation,request_a,request_s,request_ws,request_w,
    output wire service_valid,
    input wire service_ready,
    output wire [31:0] service_generation,service_a,service_s,service_ws,service_w,
    input wire response_valid,
    output wire response_ready,response_mismatch,
    input wire [31:0] response_generation,response_w,
    input wire [63:0] response_a_data,
    input wire [31:0] response_s_data,
    input wire [8*LANES-1:0] response_ws_data,
    output wire auxiliary_valid,
    input wire auxiliary_ready,
    output wire [31:0] auxiliary_generation,auxiliary_a,auxiliary_s,auxiliary_ws,auxiliary_w,
    output wire [63:0] auxiliary_a_data,
    output wire [31:0] auxiliary_s_data,
    output wire [8*LANES-1:0] auxiliary_ws_data,
    output reg [CW-1:0] occupied
);
    reg [PW-1:0] head,tail,response_tail,dispatch_head;
    reg [CW-1:0] pending,complete,unsent;
    reg [159:0] identities[0:DEPTH-1];
    reg [95+8*LANES:0] data[0:DEPTH-1];
    wire enabled=rst_n && !clear;
    // The registered mode reserves the existing identity slot before dispatch.
    // No duplicate request payload buffer: queued + pending + complete <= DEPTH.
    assign service_valid=enabled && (REGISTER_REQUESTS ? unsent!=0 :
                                   request_valid && occupied<CW'(DEPTH));
    assign request_ready=enabled && occupied<CW'(DEPTH) &&
                         (REGISTER_REQUESTS || service_ready);
    assign {service_generation,service_a,service_s,service_ws,service_w}=
        REGISTER_REQUESTS ? identities[dispatch_head] :
        {request_generation,request_a,request_s,request_ws,request_w};
    wire identity_matches=response_generation==identities[response_tail][159:128] &&
                 response_w==identities[response_tail][31:0];
    assign response_ready=enabled && pending!=0 && identity_matches;
    assign response_mismatch=enabled && response_valid && (pending==0 || !identity_matches);
    assign auxiliary_valid=enabled && complete!=0;
    assign {auxiliary_generation,auxiliary_a,auxiliary_s,auxiliary_ws,auxiliary_w}=identities[head];
    assign {auxiliary_ws_data,auxiliary_s_data,auxiliary_a_data}=data[head];
    wire take=request_valid && request_ready;
    wire send_request=service_valid && service_ready;
    wire push=response_valid && response_ready;
    wire pop=auxiliary_valid && auxiliary_ready;
    function automatic [PW-1:0] next_ptr(input [PW-1:0] p);
        next_ptr=(p==PW'(DEPTH-1))?{PW{1'b0}}:p+1'b1;
    endfunction
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin head<=0;tail<=0;response_tail<=0;pending<=0;complete<=0;occupied<=0;dispatch_head<=0;unsent<=0;end
        else if(clear)begin head<=0;tail<=0;response_tail<=0;pending<=0;complete<=0;occupied<=0;dispatch_head<=0;unsent<=0;end
        else begin
            case({take,pop})
                2'b10:occupied<=occupied+1'b1;
                2'b01:occupied<=occupied-1'b1;
                default:begin end
            endcase
            if(REGISTER_REQUESTS)begin
                case({take,send_request})
                    2'b10:unsent<=unsent+1'b1;
                    2'b01:unsent<=unsent-1'b1;
                    default:begin end
                endcase
                if(send_request)dispatch_head<=next_ptr(dispatch_head);
            end
            case({send_request,push})
                2'b10:pending<=pending+1'b1;
                2'b01:pending<=pending-1'b1;
                default:begin end
            endcase
            case({push,pop})
                2'b10:complete<=complete+1'b1;
                2'b01:complete<=complete-1'b1;
                default:begin end
            endcase
            if(take)begin
                identities[tail]<={request_generation,request_a,request_s,request_ws,request_w};
                tail<=next_ptr(tail);
            end
            if(push)begin
                data[response_tail]<={response_ws_data,response_s_data,response_a_data};
                response_tail<=next_ptr(response_tail);
            end
            if(pop)head<=next_ptr(head);
        end
    end
endmodule
