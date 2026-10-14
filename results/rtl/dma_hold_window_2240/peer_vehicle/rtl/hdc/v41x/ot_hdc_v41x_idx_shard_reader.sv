`timescale 1ns/1ps
// Correctness-rate reader for the four-stack, compact pooled-index image.
// Reads exactly two code sectors/key and one scale sector/eight keys, then
// emits the existing four-quarter, 64-key batch contract. One HBM sector is
// outstanding at a time. This serial policy is intentionally a baseline for
// bit-exact integration; it cannot substantiate the modeled scan bandwidth.
module ot_hdc_v41x_idx_shard_reader #(
    parameter integer NPC=32, HAW=28, TAGW=16, LENW=4, BEATW=4
) (
    input  wire clk,rst_n,
    input  wire cmd_v,
    input  wire [HAW-1:0] cmd_base_sec,
    input  wire [29:0] cmd_nkeys,
    output wire busy,
    output reg fault,
    output wire [4*NPC-1:0] req_v,
    input  wire [4*NPC-1:0] req_rdy,
    output wire [4*NPC*HAW-1:0] req_addr,
    output wire [4*NPC*LENW-1:0] req_len,
    output wire [4*NPC*TAGW-1:0] req_tag,
    input  wire [4*NPC-1:0] rsp_v,
    output wire [4*NPC-1:0] rsp_rdy,
    input  wire [4*NPC*TAGW-1:0] rsp_tag,
    input  wire [4*NPC*BEATW-1:0] rsp_beat,
    input  wire [4*NPC*256-1:0] rsp_data,
    output wire o_valid,
    input  wire o_ready,
    output reg [63:0] o_kv,
    output wire [3:0] o_last,
    output reg [64*544-1:0] o_key,
    output reg [63:0] o_ref,
    output reg [47:0] cnt_keys_streamed,
    output reg [47:0] cnt_hbm_beats,
    output reg [47:0] cnt_refused
);
    localparam [2:0] IDLE=0, SELECT=1, REQ=2, RSP=3, OUT=4;
    localparam [1:0] SCALE=0, CODE0=1, CODE1=2;
    localparam integer LPC=$clog2(NPC);
    reg [2:0] st;
    reg [1:0] part,q;
    reg [3:0] lane;
    reg [29:0] n,beat,qs;
    reg [HAW-1:0] base_sec;
    reg [255:0] scale_cache,code_lo;
    wire present;
    wire [29:0] global_key,local_key;
    wire [1:0] stack;
    wire [HAW-1:0] scale_sec,code_sec;
    wire [2:0] scale_slot;
    ot_hdc_v41x_idx_shard_addr #(.HAW(HAW)) u_addr (
        .i_nkeys(n),.i_beat(beat),.i_quarter(q),.i_lane(lane),
        .i_base_sec(base_sec),.o_present(present),.o_global(global_key),
        .o_stack(stack),.o_local(local_key),.o_scale_sec(scale_sec),
        .o_scale_slot(scale_slot),.o_code_sec(code_sec));

    wire [HAW-1:0] sec = part==SCALE ? scale_sec :
                         part==CODE0 ? code_sec : code_sec+HAW'(1);
    function automatic [LPC-1:0] pc_of(input [HAW-1:0] a);
        pc_of=LPC'((a>>2) ^ (a>>(2+LPC)) ^ (a>>(2+2*LPC)));
    endfunction
    wire [LPC-1:0] pc=pc_of(sec);
    wire [$clog2(4*NPC)-1:0] port_num={stack,pc};
    assign busy=st!=IDLE;
    assign o_valid=st==OUT;
    genvar p;
    generate for(p=0;p<4*NPC;p=p+1) begin : g_ports
        assign req_v[p]=st==REQ && port_num==p;
        assign rsp_rdy[p]=st==RSP && port_num==p;
        assign req_addr[p*HAW +: HAW]=sec;
        assign req_len[p*LENW +: LENW]=LENW'(1);
        assign req_tag[p*TAGW +: TAGW]='0;
    end endgenerate
    wire [255:0] rd=rsp_data[port_num*256 +: 256];
    wire rsp_fire=st==RSP && rsp_v[port_num];
    wire [31:0] scales=scale_cache[scale_slot*32 +: 32];
    wire refused=(scales[7:0]>=8'd253 || scales[15:8]>=8'd253 ||
                  scales[23:16]>=8'd253 || scales[31:24]>=8'd253);
    wire [5:0] slot={q,lane};
    wire [29:0] qlen0=qs, qlen3=n-qs-qs-qs;
    genvar qi;
    generate for(qi=0;qi<4;qi=qi+1) begin : g_last
        wire [29:0] qlen=qi==3 ? qlen3 : qlen0;
        assign o_last[qi]=(qlen==0) ? (beat==0) : (beat==((qlen-1'b1)>>4));
    end endgenerate

    task automatic next_slot;
        begin
            if(lane==15) begin
                lane<=0;
                if(q==3) st<=OUT;
                else begin q<=q+1'b1;st<=SELECT;end
            end else begin lane<=lane+1'b1;st<=SELECT;end
        end
    endtask
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            st<=IDLE;part<=SCALE;q<=0;lane<=0;n<=0;beat<=0;qs<=0;base_sec<=0;
            scale_cache<=0;code_lo<=0;o_kv<=0;o_ref<=0;o_key<=0;fault<=0;
            cnt_keys_streamed<=0;cnt_hbm_beats<=0;cnt_refused<=0;
        end else begin
            case(st)
                IDLE: if(cmd_v) begin
                    n<=cmd_nkeys;qs<={2'b00,cmd_nkeys[29:5],3'b000};
                    base_sec<=cmd_base_sec;beat<=0;q<=0;lane<=0;
                    o_kv<=0;o_ref<=0;o_key<=0;fault<=cmd_nkeys==0;
                    if(cmd_nkeys!=0) st<=SELECT;
                end
                SELECT: begin
                    if(!present) next_slot();
                    else begin
                        part<=(lane[2:0]==0) ? SCALE : CODE0;
                        st<=REQ;
                    end
                end
                REQ: if(req_rdy[port_num]) st<=RSP;
                RSP: if(rsp_fire) begin
                    cnt_hbm_beats<=cnt_hbm_beats+1'b1;
                    if(rsp_tag[port_num*TAGW +: TAGW]!='0 ||
                       rsp_beat[port_num*BEATW +: BEATW]!='0) fault<=1'b1;
                    case(part)
                        SCALE: begin scale_cache<=rd;part<=CODE0;st<=REQ;end
                        CODE0: begin code_lo<=rd;part<=CODE1;st<=REQ;end
                        CODE1: begin
                            o_key[slot*544 +: 544]<={scales,rd,code_lo};
                            o_kv[slot]<=1'b1;
                            o_ref[slot]<=refused;
                            cnt_keys_streamed<=cnt_keys_streamed+1'b1;
                            if(refused) cnt_refused<=cnt_refused+1'b1;
                            next_slot();
                        end
                        default: fault<=1'b1;
                    endcase
                end
                OUT: if(o_ready) begin
                    if((beat<<4)+30'd16>=qlen3) st<=IDLE;
                    else begin
                        beat<=beat+1'b1;q<=0;lane<=0;
                        o_kv<=0;o_ref<=0;o_key<=0;st<=SELECT;
                    end
                end
                default: st<=IDLE;
            endcase
        end
    end
endmodule
