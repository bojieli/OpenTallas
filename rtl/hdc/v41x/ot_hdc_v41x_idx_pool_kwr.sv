`timescale 1ns/1ps
// Runtime index-key writer.  In SHARDED mode consecutive 16-key groups are
// placed on successive stacks and each stack's groups are packed locally.
// SHARDED=0 preserves the reduced vehicle's replicated image.
module ot_hdc_v41x_idx_pool_kwr #(
    parameter integer AW=24, NW=16, NL=8, HAW=28, SHARDED=0
) (
    input wire clk, rst_n,
    input wire [AW-1:0] cfg_ik_base,
    input wire su_go,
    input wire [1:0] i_dst,
    input wire [AW-1:0] i_obase, i_orow,
    input wire [NW-1:0] i_nout, i_kdim,
    input wire [NL-1:0] kv_we,
    input wire [NL*AW-1:0] kv_waddr,
    input wire [NL*32-1:0] kv_wdata,
    output reg w_v,
    input wire w_rdy,
    output wire [3:0] w_stack_mask,
    output reg [HAW-1:0] w_csec,
    output reg [511:0] w_codes,
    output reg [HAW-1:0] w_ssec,
    output reg [2:0] w_sslot,
    output reg [31:0] w_scales,
    output reg fault,
    output reg [31:0] dbg_keys
);
    reg busy;
    reg [AW-1:0] rbase,row;
    wire [AW-1:0] local_row = SHARDED ? ((row >> 6) << 4) | (row & 4'hf) : row;
    assign w_stack_mask=SHARDED ? (4'b0001 << row[5:4]) : 4'b1111;
    reg [NW-1:0] kdim;
    reg [15:0] elem[0:127];
    reg [127:0] got,need;
    reg wbad;
    wire hit=su_go && i_dst==2'd3 && (i_obase>>4)>=cfg_ik_base;
    wire [AW-1:0] rb_e=rbase+(row>>4)*kdim*16+row[3:0];
    reg [AW-1:0] off,b0;
    reg [511:0] block;
    reg [136:0] enc[0:3];
    integer i,j;
    always @* begin
        for(i=0;i<4;i=i+1) begin
            for(j=0;j<32;j=j+1) block[16*j +: 16]=(32*i+j<kdim) ? elem[32*i+j] : 16'd0;
            enc[i]=enc32(block);
        end
        b0=((rbase>>4)-cfg_ik_base)/128*17;
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            busy<=0;w_v<=0;fault<=0;got<=0;need<=0;wbad<=0;dbg_keys<=0;
        end else begin
            if(w_v && w_rdy) w_v<=0;
            fault<=0;
            if(hit) begin
                if(busy || w_v || i_nout!=1 || (i_kdim!=32 && i_kdim!=128)) fault<=1;
                else begin
                    busy<=1;rbase<=i_obase;row<=i_orow;kdim<=i_kdim;
                    got<=0;need<=i_kdim==32 ? {{96{1'b0}},{32{1'b1}}} : {128{1'b1}};
                    wbad<=0;
                end
            end else if(busy) begin
                for(integer q=0;q<NL;q=q+1) if(kv_we[q]) begin
                    off=kv_waddr[q*AW +: AW]-rb_e;
                    if(kv_waddr[q*AW +: AW]>=rb_e && off<kdim*16 && off[3:0]==0) begin
                        elem[off>>4]<=kv_wdata[32*q+16 +: 16];
                        got[off>>4]<=1;
                        if(kv_wdata[32*q +: 16]!=0) wbad<=1;
                    end
                end
                if((got&need)==need) begin
                    busy<=0;got<=0;w_v<=1;dbg_keys<=dbg_keys+1;
                    if(enc[0][136] || enc[1][136] || enc[2][136] || enc[3][136] || wbad) fault<=1;
                end
            end
        end
    end
    always @(posedge clk) begin
        w_csec<=(b0+1+(local_row>>6))*128+2*(local_row&63);
        w_ssec<=b0*128+(local_row>>3);
        w_sslot<=local_row[2:0];
        for(integer b=0;b<4;b=b+1) begin
            w_codes[128*b +: 128]<=enc[b][127:0];
            w_scales[8*b +: 8]<=enc[b][135:128];
        end
    end
    function automatic [136:0] enc32(input [511:0] v);
        reg [7:0] emax,e,u;
        reg [6:0] m;
        reg bad,any;
        reg [127:0] c;
        integer k,d;
        begin
            emax=0;bad=0;any=0;c=0;
            for(k=0;k<32;k=k+1) if(v[16*k +: 15]!=0) begin
                any=1;if(v[16*k+7 +: 8]>emax) emax=v[16*k+7 +: 8];
            end
            u=any ? emax-8'd2 : 8'd0;
            if(any && (emax<2 || emax>254 || u>252)) bad=1;
            for(k=0;k<32;k=k+1) begin
                e=v[16*k+7 +: 8];m=v[16*k +: 7];
                if(v[16*k +: 15]!=0) begin
                    d=e-emax+2;
                    if(e==0 || e==255 || m[5:0]!=0) bad=1;
                    case(d)
                        2:c[4*k +: 3]=m[6]?3'd7:3'd6;
                        1:c[4*k +: 3]=m[6]?3'd5:3'd4;
                        0:c[4*k +: 3]=m[6]?3'd3:3'd2;
                        -1:begin c[4*k +: 3]=3'd1;if(m[6]) bad=1;end
                        default:bad=1;
                    endcase
                    c[4*k+3]=v[16*k+15];
                end
            end
            enc32={bad,u,c};
        end
    endfunction
endmodule
