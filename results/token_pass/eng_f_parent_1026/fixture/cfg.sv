`timescale 1ps/1fs
module dsdv_eng_cfg #(
    parameter [7:0]  UID = 8'hE6,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [275:0]  vi_s,          // rung inputs (branches of the unit's vi pins; bits [49:0] are read)
    input  wire [275:0]  vi_n,
    input  wire          ks_v,          // f_ks[52] (branch of the f_ks pin)
    input  wire [3:0]    st,            // the core's sticky status
    output reg           cfg_en,
    output reg           cfg_layer,
    output reg  [1:0]    cfg_rank,
    output reg           fault
);
    localparam [2:0] K_CTL = 3'd0, K_XQ = 3'd1, K_XB = 3'd2;
    wire [0:0] rl;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_r (.clk(ck), .rst_n_in(rst_n), .rst_n(rl));
    // pin-side capture (valid / ks reset-gated; the decoded fields are plain flops)
    reg        sv, nv, kv;
    reg [49:1] sd, nd;
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin sv <= 1'b0; nv <= 1'b0; kv <= 1'b0; end
        else begin sv <= vi_s[0]; nv <= vi_n[0]; kv <= ks_v; end
    always @(posedge ck) begin sd <= vi_s[49:1]; nd <= vi_n[49:1]; end
    // header / continuation tracking per direction (XQ / XB = header + 3 raw fragments)
    reg  [1:0] fs, fn;
    wire       hs = sv && (fs == 2'd0 || MUT == 3), hn = nv && (fn == 2'd0 || MUT == 3);
    wire       xs = sd[3:1] == K_XQ || sd[3:1] == K_XB, xn = nd[3:1] == K_XQ || nd[3:1] == K_XB;
    wire       ms = hs && sd[3:1] == K_CTL && (MUT == 2 || (sd[36:21] == 16'd0 && sd[41] && sd[49:42] == UID));
    wire       mn = hn && nd[3:1] == K_CTL && (MUT == 2 || (nd[36:21] == 16'd0 && nd[41] && nd[49:42] == UID));
    wire [3:0] f  = ms ? sd[40:37] : nd[40:37];                  // {rank 2, layer, en}
    reg        done;                                             // configured since reset
    always @(posedge ck or negedge rl[0])
        if (!rl[0]) begin
            fs <= 2'd0; fn <= 2'd0; done <= 1'b0; fault <= 1'b0;
            cfg_en <= (MUT == 5); cfg_layer <= 1'b0; cfg_rank <= 2'd0;
        end else begin
            fs <= (fs != 2'd0) ? fs - 2'd1 : (hs && xs) ? 2'd3 : 2'd0;
            fn <= (fn != 2'd0) ? fn - 2'd1 : (hn && xn) ? 2'd3 : 2'd0;
            if (ms || mn) begin
                cfg_en <= f[0]; cfg_layer <= f[1];
                cfg_rank <= (MUT == 1) ? {f[2], f[3]} : f[3:2];
                done <= 1'b1;
            end
            fault <= fault | st[3] | st[1] | st[0] | (st[2] && MUT != 4) | (ms && mn) | (kv && !done);
        end
endmodule
