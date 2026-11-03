// FF-census wrapper: ot_qwen_w12_matvec_part exactly as ot_qwen_rom_tile_logic_w12 (rc15) binds it in the selected
// native HEAD A0 tile (B-pilot parameter set; tile-unconnected outputs left open, tile-tied inputs tied), so synthesis
// prunes exactly what the tile prunes.  -DFF_TP=<0|1> selects TAILPUB on the rc16 copy; no define = rc14 original.
module head_tailpub_ff_wrap (
    input wire [7:0] ck_lsl, input wire [7:0] ck_tx, input wire [3:0] ck_reg, input wire clk, input wire rst_n, input wire go,
    input wire [17:0] i_nout, i_tiles, i_k, input wire i_wsrc,
    input wire [23:0] i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs, input wire [2:0] i_jsh,
    input wire [3:0] i_split, i_split_copy, input wire [23:0] i_wcs, input wire i_round, input wire [23:0] i_obase, i_ots, i_ojs,
    input wire i_mmode, i_oen, i_amax, i_rmax, input wire [23:0] i_mbase,
    input wire [1023:0] wrom_q, input wire [2047:0] kv_q, input wire [127:0] x_q, input wire [15:0] tile_id,
    output wire idle, output wire wrom_re, output wire [23:0] wrom_addr, output wire kv_re, output wire [95:0] kv_addr,
    output wire fault, output wire [511:0] t_out, output wire t_vout);
    ot_qwen_w12_matvec_part #(.W(16), .G(4), .IL(8), .AW(24), .NW(18), .INT8_WEIGHT(1), .INT8_SCALE_WCS_BASE(1),
        .PART(1), .GT(3072), .GBASE_PORT(1), .SMIN(7), .NX(0), .MEM_EXTRA(8), .ACC_LAT(7), .TREE_LAT(7),
        .FAST_ISSUE(1), .KV_PREP(4), .MUL_LAT(8), .WCONV(1), .LRST(3), .HIER(2), .HIER_HARD(1), .LRR(1), .XTX(2),
        .LOCAL_ROOTS(1), .CHILD_CLOCKS(1), .REGROOT(3), .ANR(1)
`ifdef FF_TP
        , .TAILPUB(`FF_TP)
`endif
    ) u_me (
        .ck_lsl(ck_lsl), .ck_tx(ck_tx), .ck_reg(ck_reg),
        .clk(clk), .rst_n(rst_n), .go(go), .go_cp({32{go}}), .ready(), .idle(idle),
        .i_nout(i_nout), .i_tiles(i_tiles), .i_k(i_k), .i_wsrc(i_wsrc),
        .i_wbase(i_wbase), .i_ts(i_ts), .i_ks(i_ks), .i_js(i_js),
        .i_xbase(i_xbase), .i_xks(i_xks), .i_xjs(i_xjs), .i_xcs(i_xcs),
        .i_jsh(i_jsh), .i_split(i_split), .i_split_copy(i_split_copy), .i_wcs(i_wcs), .i_round(i_round),
        .i_obase(i_obase), .i_ots(i_ots), .i_ojs(i_ojs),
        .i_mmode(i_mmode), .i_oen(i_oen), .i_amax(i_amax), .i_rmax(i_rmax), .i_mbase(i_mbase),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .scale_re(), .scale_gre(), .scale_addr(), .scale_q(1024'd0),
        .kv_re(kv_re), .kv_addr(kv_addr), .kv_q(kv_q),
        .x_re(), .x_addr(), .x_q(x_q),
        .ov(), .o_we(), .o_addr(), .o_mask(), .o_data(),
        .am_idx(), .am_val(), .am_any(), .mx_we(), .mx_addr(), .mx_mask(), .mx_data(),
        .progress(), .fault(fault),
        .i_gbase({16'd0, tile_id} * 4), .t_in(512'd0), .t_fault_in(1'b0),
        .t_out(t_out), .t_vout(t_vout), .t_fault(), .active_o());
endmodule
