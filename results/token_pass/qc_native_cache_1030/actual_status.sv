module ot_qwen_status_obs_full32(input wire [15:0] lo,hi, output wire full);
    assign full = (&lo) && (&hi);
endmodule
module ot_qwen_status_obs_v1_state(
    input wire ck, input wire [2:0] rst_n, input wire [15:0] epoch16,
    input wire [61:0] obs_ctx, input wire [46:0] obs_res, input wire [59:0] obs_native,
    output wire [207:0] snapshot, output wire fault
);
    // Cold reset only. Link epoch_begin does not clear a count in the same STATUS receipt epoch.
    (* keep = "true", dont_touch = "true" *) reg [15:0] ep_lo,ep_hi,ep_id;
    reg [15:0] count_lo,count_hi;
    (* keep = "true", dont_touch = "true" *) reg [3:0] ctx_seen,nat_seen;
    (* keep = "true", dont_touch = "true" *) reg [2:0] res_seen;
    reg overflow, bad_q;
    wire ch_lo=ep_lo!=epoch16, ch_hi=ep_hi!=epoch16, ch_id=ep_id!=epoch16;
    wire [15:0] base_lo=ch_lo?16'd0:count_lo, base_hi=ch_hi?16'd0:count_hi;
    wire full_lo,full_hi;
    ot_qwen_status_obs_full32 u_full_lo(.lo(base_lo),.hi(base_hi),.full(full_lo));
    ot_qwen_status_obs_full32 u_full_hi(.lo(base_lo),.hi(base_hi),.full(full_hi));
    wire [15:0] next_lo=(obs_native[59]&&full_lo)?16'hffff:base_lo+{15'd0,obs_native[59]};
    wire [15:0] next_hi=(obs_native[59]&&full_hi)?16'hffff:base_hi+{15'd0,(obs_native[59]&&(&base_lo))};
    wire overflow_now=(!ch_id&&overflow)||(obs_native[59]&&full_lo);
    always @(posedge ck or negedge rst_n[0])
        if(!rst_n[0]) begin ep_lo<=0;count_lo<=0;end
        else begin ep_lo<=epoch16;count_lo<=next_lo;end
    always @(posedge ck or negedge rst_n[1])
        if(!rst_n[1]) begin ep_hi<=0;count_hi<=0;end
        else begin ep_hi<=epoch16;count_hi<=next_hi;end
    wire input_bad=(obs_ctx[61]&&(obs_ctx[60:59]==0||obs_ctx[60:59]!=obs_ctx[44:43])) ||
                   (obs_res[46]&&!obs_res[42]);
    always @(posedge ck or negedge rst_n[2])
        if(!rst_n[2]) begin ep_id<=0;ctx_seen<=0;res_seen<=0;nat_seen<=0;overflow<=0;bad_q<=0;end
        else begin
            ep_id<=epoch16;
            ctx_seen<={4{obs_ctx[61]}} | (ch_id?4'd0:ctx_seen);
            res_seen<={3{obs_res[46]}} | (ch_id?3'd0:res_seen);
            nat_seen<={4{obs_native[59]}} | (ch_id?4'd0:nat_seen);
            overflow<=overflow_now;
            bad_q<=(ch_id?1'b0:bad_q)||input_bad||(ch_lo!=ch_hi)||(ch_hi!=ch_id)||overflow_now;
        end
    wire [3:0] ctx_v=ctx_seen&{4{!ch_id}} | {4{obs_ctx[61]}};
    wire [2:0] res_v=res_seen&{3{!ch_id}} | {3{obs_res[46]}};
    wire [3:0] nat_v=nat_seen&{4{!ch_id}} | {4{obs_native[59]}};
    wire [60:0] cx; wire [45:0] rr; wire [58:0] nn;
    genvar g;
    for(g=0;g<4;g=g+1) begin:g_ctx_mask
        localparam integer LO=16*g, W=(LO+16<=61)?16:61-LO;
        assign cx[LO+:W]=obs_ctx[LO+:W]&{W{ctx_v[g]}};
    end
    for(g=0;g<3;g=g+1) begin:g_res_mask
        localparam integer LO=16*g, W=(LO+16<=46)?16:46-LO;
        assign rr[LO+:W]=obs_res[LO+:W]&{W{res_v[g]}};
    end
    for(g=0;g<4;g=g+1) begin:g_native_mask
        localparam integer LO=16*g, W=(LO+16<=59)?16:59-LO;
        assign nn[LO+:W]=obs_native[LO+:W]&{W{nat_v[g]}};
    end
    // Include same-edge events in the actual STATUS capture, with true held operation identities.
    assign snapshot={4'd1,ctx_v[0],cx,res_v[0],rr,nat_v[0],overflow_now,next_hi,next_lo,nn,2'd0};
    assign fault=bad_q||input_bad||overflow_now;
endmodule
