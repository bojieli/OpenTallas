`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_quarter_collect_pipe -- the sixteen (stack, quarter) range
// streams reassembled into the four-quarter, 64-key beat, at ONE BEAT PER
// CYCLE.
//
// Same contract, same key placement and same checks as
// ot_hdc_v41x_idx_shard_quarter_collect (which it leaves untouched): beat b,
// lane group q holds positions q Qs + 16 b + (0..15), o_kv a lane prefix,
// o_last[q] the port's last beat, o_ref the UE8M0 >= 253 refusal flag, and
// padding lanes carry zero keys.  The legacy collector drops o_valid for a
// cycle after every accepted beat (collect, offer, clear, collect ...), so it
// emits at most one 64-key beat every two cycles -- 32 keys/cycle, 68 sectors
// per cycle at 68 B per key, below the four stacks' HBM rate.  Here the edge
// that retires beat b also collects beat b + 1 from the held input beats, so
// a full beat can leave on every cycle (64 keys/cycle = 136 sectors/cycle).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_quarter_collect_pipe (
    input wire clk, rst_n,
    input wire cmd_v,
    input wire [29:0] cmd_nkeys,
    output wire busy,
    output reg fault,
    input wire [15:0] i_valid,
    output wire [15:0] i_ready,
    input wire [16*16-1:0] i_kv,
    input wire [16*16*544-1:0] i_key,
    output reg o_valid,
    input wire o_ready,
    output reg [63:0] o_kv,
    output reg [3:0] o_last,
    output reg [64*544-1:0] o_key,
    output reg [63:0] o_ref
);
    reg run;
    reg [29:0] n, qs, beat;
    reg [29:0] first [0:15];
    reg [29:0] count [0:15];
    reg [29:0] seq [0:15];
    reg [15:0] have;
    reg [15:0] held_kv [0:15];
    reg [16*544-1:0] held_key [0:15];
    reg [63:0] filled;
    wire [29:0] qlen3=n-qs-qs-qs;
    wire [29:0] last_beat=(qlen3-1'b1)>>4;

    function automatic [29:0] rank(input [29:0] x,input integer stack);
        integer r, lo;
        begin
            r=int'(x[5:0]); lo=r-16*stack;
            if(lo<0) lo=0;
            if(lo>16) lo=16;
            rank=((x>>6)<<4)+30'(lo);
        end
    endfunction
    function automatic ref_key(input [31:0] scale);
        ref_key=(scale[7:0]>=8'd253 || scale[15:8]>=8'd253 ||
                 scale[23:16]>=8'd253 || scale[31:24]>=8'd253);
    endfunction

    // expected lane mask and last flags of the beat being collected
    wire pop=o_valid && o_ready;
    wire last_pop=pop && beat==last_beat;
    wire [29:0] tb=pop ? beat+30'd1 : beat;
    integer q,l;
    reg [29:0] qlen;
    reg [63:0] expect_mask;
    reg [3:0] last_mask;
    always @* begin
        expect_mask=0;
        last_mask=0;
        for(q=0;q<4;q=q+1) begin
            qlen=(q==3) ? qlen3 : qs;
            last_mask[q]=(qlen==0) ? (tb==0) : (tb==((qlen-1)>>4));
            for(l=0;l<16;l=l+1)
                expect_mask[16*q+l]=((tb<<4)+30'(l)<qlen);
        end
    end
    assign busy=run || o_valid;
    genvar gi;
    generate for(gi=0;gi<16;gi=gi+1) begin:g_ready
        assign i_ready[gi]=run && count[gi]!=0 && !have[gi];
    end endgenerate

    integer i,j,s,quarter,slot;
    reg [29:0] physical, local_key, global_key, relative, key_beat;
    reg future, can_collect;
    reg [63:0] collected;
    reg [543:0] key_word;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            run<=0; fault<=0; o_valid<=0; n<=0; qs<=0; beat<=0;
            have<=0; filled<=0; o_kv<=0; o_last<=0; o_key<=0; o_ref<=0;
            for(i=0;i<16;i=i+1) begin
                first[i]<=0;count[i]<=0;seq[i]<=0;
                held_kv[i]<=0;held_key[i]<=0;
            end
        end else if(cmd_v && !busy) begin
            n<=cmd_nkeys;
            qs<={2'b00,cmd_nkeys[29:5],3'b000};
            beat<=0; have<=0; filled<=0; o_valid<=0;
            o_kv<=0;o_last<=0;o_key<=0;o_ref<=0;
            fault<=cmd_nkeys==0; run<=cmd_nkeys!=0;
            for(i=0;i<16;i=i+1) begin
                first[i]<=rank(30'((i%4))*((cmd_nkeys>>5)<<3),i/4);
                count[i]<=rank((i%4==3 ? cmd_nkeys : 30'((i%4)+1)*((cmd_nkeys>>5)<<3)),i/4)
                         -rank(30'((i%4))*((cmd_nkeys>>5)<<3),i/4);
                seq[i]<=0;
            end
        end else if(run || o_valid) begin
            for(i=0;i<16;i=i+1) begin
                if(i_valid[i] && i_ready[i]) begin
                    held_kv[i]<=i_kv[i*16 +: 16];
                    held_key[i]<=i_key[i*16*544 +: 16*544];
                    have[i]<=1;
                    seq[i]<=seq[i]+1'b1;
                end
            end
            if(pop) begin
                o_valid<=0; o_kv<=0; o_last<=0; o_key<=0; o_ref<=0; filled<=0;
                if(last_pop) run<=0;
                else beat<=beat+1'b1;
            end
            // collect beat tb: the current beat while it is incomplete, or the
            // next beat at the edge that retires the current one
            can_collect=run && (!o_valid || (pop && !last_pop));
            if(can_collect) begin
                collected=pop ? 64'd0 : filled;
                for(i=0;i<16;i=i+1) if(have[i]) begin
                    s=i/4; quarter=i%4; future=0;
                    physical=(first[i] & 30'h3ffffc00)+((seq[i]-1'b1)<<4);
                    for(j=0;j<16;j=j+1) begin
                        local_key=physical+30'(j);
                        if(local_key>=first[i] && local_key<first[i]+count[i]) begin
                            global_key=((local_key>>4)<<6)+30'(s*16)+{26'b0,local_key[3:0]};
                            relative=global_key-30'(quarter)*qs;
                            key_beat=relative>>4;
                            if(key_beat>tb) future=1;
                            else if(key_beat==tb) begin
                                slot=quarter*16+int'(relative[3:0]);
                                if(!held_kv[i][j]) fault<=1;
                                else if(!collected[slot]) begin
                                    key_word=held_key[i][j*544 +: 544];
                                    o_key[slot*544 +: 544]<=key_word;
                                    o_ref[slot]<=ref_key(key_word[543:512]);
                                    collected[slot]=1;
                                end
                            end
                        end
                    end
                    if(!future) have[i]<=0;
                end
                filled<=collected;
                if(collected==expect_mask) begin
                    o_kv<=expect_mask;
                    o_last<=last_mask;
                    o_valid<=1;
                end
            end
        end
    end
endmodule
