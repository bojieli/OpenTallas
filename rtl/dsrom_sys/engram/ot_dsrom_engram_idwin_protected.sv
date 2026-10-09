`timescale 1ns/1ps
// Full64-user, eight-deep protected mutable window state. ROM stays no-ECC.
// History18bits and metadata29bits occupy separately protected SECDED72 words.
// Single errors corrected before use; required uncorrectable reads fail closed.
module ot_dsrom_engram_idwin_protected #(
    parameter [16:0] PAD=17'd2
) (
    input wire clk,rst_n,t_valid,
    input wire [5:0] t_user,
    input wire [16:0] t_cid,
    input wire [20:0] t_pos,
    input wire t_first,t_dead,
    input wire rb_valid,
    input wire [5:0] rb_user,
    input wire [2:0] rb_n,
    output reg win_valid,
    output reg [67:0] win_ids,
    output reg win_dead,
    output reg fault,
    output reg corrected
);
    reg [71:0] hist[0:511];
    reg [71:0] meta[0:63]; // {position22, earliercount4, nextwrite3}
    wire [63:0] tm,rm,h1,h2,h3;
    wire tc,tu,rc,ru,c1,c2,c3,u1,u2,u3;
    ot_s81_secded_dec72 dt(.c(meta[t_user]),.d(tm),.ce(tc),.ue(tu));
    ot_s81_secded_dec72 dr(.c(meta[rb_user]),.d(rm),.ce(rc),.ue(ru));
    wire [2:0] p=tm[2:0];
    wire [3:0] n=t_first?4'd0:tm[6:3];
    wire [21:0] position=tm[28:7];
    wire [8:0] a1={t_user,p-3'd1},a2={t_user,p-3'd2},a3={t_user,p-3'd3};
    ot_s81_secded_dec72 d1(.c(hist[a1]),.d(h1),.ce(c1),.ue(u1));
    ot_s81_secded_dec72 d2(.c(hist[a2]),.d(h2),.ce(c2),.ue(u2));
    ot_s81_secded_dec72 d3(.c(hist[a3]),.d(h3),.ce(c3),.ue(u3));
    wire b0=t_dead;
    wire need1=!b0 && n>=1;
    wire b1=b0 || n<1 || h1[17];
    wire need2=!b1 && n>=2;
    wire b2=b1 || n<2 || h2[17];
    wire need3=!b2 && n>=3;
    wire b3=b2 || n<3 || h3[17];
    wire token_legal=!tu && tm[63:29]==0 && t_cid<99092 &&
        ((t_first && t_pos==0) || (!t_first && position=={1'b0,t_pos})) &&
        !(need1 && (u1 || h1[63:18]!=0 || h1[16:0]>=99092)) &&
        !(need2 && (u2 || h2[63:18]!=0 || h2[16:0]>=99092)) &&
        !(need3 && (u3 || h3[63:18]!=0 || h3[16:0]>=99092));
    wire rewind_legal=!ru && rm[63:29]==0 && rb_n>=1 && rb_n<=5 &&
        rm[28:7]>={19'b0,rb_n};
    wire conflict=t_valid && rb_valid && t_user==rb_user;
    wire [71:0] hist_new,tm_new,rm_new;
    wire [3:0] next_n=n==15?4'd15:n+4'd1;
    wire [21:0] next_position={1'b0,t_pos}+22'd1;
    wire [2:0] next_p=p+3'd1;
    wire [21:0] rewind_position=rm[28:7]-{19'b0,rb_n};
    wire [3:0] rewind_n=rm[6:3]-{1'b0,rb_n};
    wire [2:0] rewind_p=rm[2:0]-rb_n;
    ot_s81_secded_enc72 eh(.d({46'b0,t_dead,t_cid}),.c(hist_new));
    ot_s81_secded_enc72 et(.d({35'b0,next_position,next_n,next_p}),.c(tm_new));
    ot_s81_secded_enc72 er(.d({35'b0,rewind_position,rewind_n,rewind_p}),.c(rm_new));
    integer i;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            win_valid<=0;win_ids<=0;win_dead<=0;fault<=0;corrected<=0;
            for(i=0;i<64;i=i+1) meta[i]<=0;
        end else begin
            win_valid<=0;corrected<=0;
            if(!fault) begin
                if(conflict || (t_valid && !token_legal) || (rb_valid && !rewind_legal)) fault<=1;
                else begin
                    if(t_valid) begin
                        win_valid<=1;win_dead<=t_dead;
                        win_ids<={b3?PAD:h3[16:0],b2?PAD:h2[16:0],b1?PAD:h1[16:0],b0?PAD:t_cid};
                        hist[{t_user,p}]<=hist_new;meta[t_user]<=tm_new;
                        corrected<=tc || (need1 && c1) || (need2 && c2) || (need3 && c3);
                    end
                    if(rb_valid) begin meta[rb_user]<=rm_new;corrected<=rc || (t_valid && (tc || (need1&&c1) || (need2&&c2) || (need3&&c3)));end
                end
            end
        end
    end
endmodule
