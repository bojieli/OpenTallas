`timescale 1ns/1ps
// Credit-faced service for the hardened lookup. Its eight-entry request FIFO
// holds the lookup's advertised eight credits, including its one pin capture
// in flight. A credit returns only when the read adapter reserves a row/PC.
// This service and boot_path need an explicit phase/ownership mux before ctrl.
module ot_dsrom_engram_rowstripe_service #(parameter integer CANONICAL=0,parameter integer APERTURE=0,parameter integer USE_LEASE=0) (
    input wire [63:0] pc_available,
    output wire [63:0] pc_want,pc_held,pc_claim,pc_release,
    input wire aperture_valid,
    input wire [64*30-1:0] pc_base,pc_limit,
    input wire ck,rst_n,input wire hq_v,input wire [30:0] hq_atom,input wire [2:0] hq_tag,
    output reg hq_cred,output wire [64*341-1:0] rq,input wire [2*8896-1:0] rd,
    output wire hr_v,output wire [2:0] hr_tag,output wire [3:0] hr_idx,output wire [255:0] hr_d,
    output wire fault
);
    reg iv_q;reg [33:0] id_q;
    reg [33:0] fifo[0:7];reg [2:0] rp,wp;reg [3:0] count;reg queue_fault;
    wire ready,read_fault;
    wire pop=(count!=0)&&ready&&!queue_fault;
    always @(posedge ck) id_q<={hq_atom,hq_tag};
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin iv_q<=0;rp<=0;wp<=0;count<=0;hq_cred<=0;queue_fault<=0;end
        else begin
            iv_q<=hq_v;hq_cred<=pop;
            if(iv_q && count==8 && !pop) queue_fault<=1;
            if(!queue_fault) begin
                case({iv_q,pop})
                    2'b10:count<=count+1'b1;
                    2'b01:count<=count-1'b1;
                    default:count<=count;
                endcase
                if(iv_q) begin fifo[wp]<=id_q;wp<=wp+1'b1;end
                if(pop) rp<=rp+1'b1;
            end
        end
    end
    ot_dsrom_engram_rowstripe_read #(.CANONICAL(CANONICAL),.APERTURE(APERTURE),.USE_LEASE(USE_LEASE)) u_read(.ck(ck),.rst_n(rst_n),.pc_available(pc_available),.pc_want(pc_want),.pc_held(pc_held),.pc_claim(pc_claim),.pc_release(pc_release),.aperture_valid(aperture_valid),.pc_base(pc_base),.pc_limit(pc_limit),
        .hq_valid(count!=0&&!queue_fault),.hq_ready(ready),.hq_atom(fifo[rp][33:3]),.hq_len(4'd9),.hq_tag(fifo[rp][2:0]),
        .rq(rq),.rd(rd),.hr_valid(hr_v),.hr_ready(1'b1),.hr_tag(hr_tag),.hr_idx(hr_idx),.hr_data(hr_d),.ce(),.fault(read_fault));
    assign fault=queue_fault|read_fault;
endmodule
