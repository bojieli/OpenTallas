`timescale 1ns/1ps
// Opt2 caller-side request join. The original bulk-copy descriptor, allocation,
// credit, response/tag and SRAM consume loops stay byte-identical.
// Pair descriptor: 64 logical lines at base_A; actual addresses alternate A4/B4
// per chunk step. Compiler must supply installed physical 32-line spans.
// Queue ownership follows actual descriptor acceptance and actual request pops.
module ot_hbm_accel_w2_pair_request_join #(
    parameter integer ENABLE=0,
    parameter integer DQ=4
) (
    input wire clk,
    input wire rst_n,
    input wire d_valid,
    output wire d_ready,
    input wire d_pair,
    input wire d_bound,
    input wire [31:0] d_base_a,
    input wire [31:0] d_base_b,
    input wire [23:0] d_lines,
    output wire bc_d_valid,
    input wire bc_d_ready,
    output wire [31:0] bc_d_base,
    output wire [23:0] bc_d_lines,
    input wire bc_req_v,
    output wire bc_req_ready,
    input wire [31:0] bc_req_addr,
    input wire [9:0] bc_req_tag,
    output wire req_v,
    input wire req_ready,
    output wire [31:0] req_addr,
    output wire [9:0] req_tag,
    output wire fault
);
    assign bc_d_base=d_base_a;
    assign bc_d_lines=d_lines;
    assign req_tag=bc_req_tag;
    generate if (!ENABLE) begin:g_off
        assign bc_d_valid=d_valid;
        assign d_ready=bc_d_ready;
        assign req_v=bc_req_v;
        assign bc_req_ready=req_ready;
        assign req_addr=bc_req_addr;
        assign fault=1'b0;
    end else begin:g_pair
        localparam integer QW=(DQ<=1)?1:$clog2(DQ);
        reg [31:0] qa[0:DQ-1],qb[0:DQ-1];
        reg [23:0] qlines[0:DQ-1];
        reg [DQ-1:0] qpair,qbound;
        reg [QW-1:0] wp,rp;
        reg [QW:0] cnt;
        reg active,pack,bound,failed;
        reg [31:0] a,b;
        reg [23:0] left;
        reg [5:0] offset;
        wire [32:0] linear_end={1'b0,d_base_a}+{9'd0,d_lines};
        wire config_ok=d_bound && d_lines!=0 && !linear_end[32] &&
            (!d_pair || (d_lines==64 && d_base_a<=32'hffffffc0 && d_base_b<=32'hffffffe0));
        wire room=cnt<DQ;
        assign bc_d_valid=d_valid && config_ok && room && !failed;
        assign d_ready=bc_d_ready && config_ok && room && !failed;
        wire push=d_valid && d_ready;
        wire load=!active && cnt!=0 && !failed;
        assign req_v=bc_req_v && active && bound && !failed;
        assign bc_req_ready=req_ready && active && bound && !failed;
        wire pop=req_v && req_ready;
        wire [4:0] index={offset[5:3],offset[1:0]};
        wire [31:0] aa=a+{27'd0,index};
        wire [31:0] bb=b+{27'd0,index};
        assign req_addr=pack?(offset[2]?bb:aa):bc_req_addr;
        assign fault=failed;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                wp<=0;rp<=0;cnt<=0;active<=0;pack<=0;bound<=0;failed<=0;
                left<=0;offset<=0;a<=0;b<=0;
            end else begin
                if (d_valid && !config_ok) failed<=1;
                case ({push,load})
                    2'b10:cnt<=cnt+1'b1;
                    2'b01:cnt<=cnt-1'b1;
                    default:;
                endcase
                if (push) wp<=(wp==DQ-1)?0:wp+1'b1;
                if (load) begin
                    rp<=(rp==DQ-1)?0:rp+1'b1;
                    active<=1;pack<=qpair[rp];bound<=qbound[rp];
                    a<=qa[rp];b<=qb[rp];left<=qlines[rp];offset<=0;
                end else if (pop) begin
                    left<=left-1'b1;offset<=offset+1'b1;
                    if (left==1) active<=0;
                end
            end
        end
        always @(posedge clk) if (push) begin
            qa[wp]<=d_base_a;qb[wp]<=d_base_b;qlines[wp]<=d_lines;
            qpair[wp]<=d_pair;qbound[wp]<=d_bound;
        end
    end endgenerate
endmodule
