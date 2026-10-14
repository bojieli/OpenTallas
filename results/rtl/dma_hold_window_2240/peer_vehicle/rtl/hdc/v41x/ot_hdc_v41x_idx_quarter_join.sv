`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_quarter_join -- QUARTER-PER-STACK index-key layout: the
// four quarter streams joined into the four-quarter, 64-key beat, one beat per
// cycle.
//
// Layout.  A scan of N keys is split into the selector's four position
// quarters (Qs = 8 floor(N / 32); quarter q < 3 is [q Qs, (q+1) Qs), quarter
// 3 is [3 Qs, N)).  Here stack q holds quarter q's keys, in position order, as
// one contiguous range of its own 1,024-key super-blocks (17 x 4 KB, the
// layout of ot_hdc_v41x_idx_kstream_range), so each stack runs ONE sequential
// stream: one bank per bank group open per pseudo-channel, no second stream
// to share its banks with, no per-pseudo-channel context arbitration.
// (The legacy layout interleaves stacks in 16-key groups, so every stack runs
// four quarter streams whose banks collide for some N.)  As N grows the
// quarter boundaries q Qs move by 8 q positions every 32 keys: those keys
// migrate from the head of stack q's range to the tail of stack q-1's -- a
// ring per stack, 48 keys (3.3 KB) of HBM copy per 32 decode steps.
//
// Contract (unchanged, the selector's): beat b, lane group q holds positions
// q Qs + 16 b + (0..15); o_kv a lane prefix (16 b + lane < L_q); o_last[q] on
// port q's last beat (beat ceil(L_q / 16) - 1, or beat 0 for an empty
// quarter); padding lanes carry zero keys; o_ref the UE8M0 >= 253 refusal
// flag.  Input q is stack q's 16-key beat (ot_hdc_v41x_idx_kstream_range
// o_valid/o_kv/o_key).  That stream starts at its first super-block's key 0,
// so the quarter's first key sits at stream key cmd_skip[q] (the ring head, a
// multiple of 8): the join drops the cmd_skip / 16 leading beats and, for a
// head at 8 mod 16, joins the upper half of one stream beat with the lower
// half of the next (a carry of 8 keys per stream).  A beat leaves when every
// quarter that still has keys has what it needs; a full beat can leave on
// every cycle (64 keys/cycle = 136 sectors/cycle at 68 B per key).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_quarter_join (
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [29:0] cmd_nkeys,
    input wire [4*10-1:0] cmd_skip,      // quarter q's first key within its stream's first super-block
    output wire busy,
    output reg fault,
    input wire [3:0] i_valid,
    output reg [3:0] i_ready,
    input wire [4*16-1:0] i_kv,
    input wire [4*16*544-1:0] i_key,
    output reg o_valid,
    input wire o_ready,
    output reg [63:0] o_kv,
    output reg [3:0] o_last,
    output reg [64*544-1:0] o_key,
    output reg [63:0] o_ref
);
    reg run;
    reg [29:0] beat, qs, n;
    reg [5:0] drop [0:3];                // leading stream beats still to discard
    reg [3:0] half;                      // quarter head at 8 mod 16
    reg [3:0] primed;                    // carry holds the head beat's upper half
    reg [8*544-1:0] carry [0:3];
    reg [7:0] carry_kv [0:3];
    wire [29:0] qlen [0:3];
    assign qlen[0]=qs; assign qlen[1]=qs; assign qlen[2]=qs; assign qlen[3]=n-qs-qs-qs;
    wire [29:0] last_beat=(qlen[3]-1'b1)>>4;
    function automatic ref_key(input [31:0] scale);
        ref_key=(scale[7:0]>=8'd253 || scale[15:8]>=8'd253 ||
                 scale[23:16]>=8'd253 || scale[31:24]>=8'd253);
    endfunction
    // per quarter: does output beat `beat` need a stream beat now, is it here
    reg [3:0] need, have;
    reg [3:0] pre;                       // a stream beat to drop or to prime the carry
    integer q,l;
    always @* begin
        for(q=0;q<4;q=q+1) begin
            pre[q]=run && (drop[q]!=0 || (half[q] && !primed[q] && qlen[q]!=0));
            // aligned: keys 16b..16b+15 are one stream beat; half: the stream
            // beat supplies keys 16b+8..16b+23, needed while 16b+8 < L_q
            need[q]=run && !pre[q] && (half[q] ? ((beat<<4)+30'd8 < qlen[q]) : ((beat<<4) < qlen[q]));
        end
    end
    wire room=!o_valid || o_ready;
    wire ready_all=((i_valid & need)==need) && pre==4'b0;
    wire take=run && room && ready_all;
    always @* i_ready=(pre & i_valid) | (take ? need : 4'b0);
    assign busy=run || o_valid;
    reg [15:0] m;
    reg [16*544-1:0] w;
    reg [15:0] wkv;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            run<=0; fault<=0; o_valid<=0; beat<=0; qs<=0; n<=0;
            o_kv<=0; o_last<=0; o_key<=0; o_ref<=0; half<=0; primed<=0;
            for(q=0;q<4;q=q+1) begin drop[q]<=0; carry[q]<=0; carry_kv[q]<=0; end
        end else if(cmd_v && !busy) begin
            n<=cmd_nkeys; qs<={2'b00,cmd_nkeys[29:5],3'b000};
            beat<=0; fault<=cmd_nkeys==0 || (|{cmd_skip[32],cmd_skip[22],cmd_skip[12],cmd_skip[2:0]}); run<=cmd_nkeys!=0;
            primed<=0;
            for(q=0;q<4;q=q+1) begin
                drop[q]<=cmd_skip[10*q+4 +: 6];
                half[q]<=cmd_skip[10*q+3];
            end
        end else begin
            if(o_valid && o_ready) o_valid<=0;
            for(q=0;q<4;q=q+1) if(pre[q] && i_valid[q]) begin
                if(drop[q]!=0) drop[q]<=drop[q]-1'b1;
                else begin
                    primed[q]<=1'b1;
                    carry[q]<=i_key[(16*q+8)*544 +: 8*544];
                    carry_kv[q]<=i_kv[16*q+8 +: 8];
                end
            end
            if(take) begin
                for(q=0;q<4;q=q+1) begin
                    for(l=0;l<16;l=l+1) m[l]=((beat<<4)+30'(l))<qlen[q];
                    if(half[q]) begin
                        w={i_key[16*q*544 +: 8*544],carry[q]};
                        wkv={need[q] ? i_kv[16*q +: 8] : 8'd0,carry_kv[q]};
                        if(need[q]) begin
                            carry[q]<=i_key[(16*q+8)*544 +: 8*544];
                            carry_kv[q]<=i_kv[16*q+8 +: 8];
                        end
                    end else begin
                        w=i_key[16*q*544 +: 16*544];
                        wkv=need[q] ? i_kv[16*q +: 16] : 16'd0;
                    end
                    o_kv[16*q +: 16]<=m;
                    o_last[q]<=(qlen[q]==0) ? (beat==0) : (beat==((qlen[q]-1'b1)>>4));
                    // every key the quarter needs must be present in the stream
                    if((m & ~wkv)!=0) fault<=1;
                    for(l=0;l<16;l=l+1) begin
                        o_key[(16*q+l)*544 +: 544]<=m[l] ? w[l*544 +: 544] : 544'd0;
                        o_ref[16*q+l]<=m[l] && ref_key(w[l*544+512 +: 32]);
                    end
                end
                o_valid<=1;
                if(beat==last_beat) run<=0;
                beat<=beat+1'b1;
            end
        end
    end
endmodule
