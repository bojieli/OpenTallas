`timescale 1ns/1ps
// Source-derived from ot_ratio_cdc_fifo, disjoint additive protected control.
module ot_dsrom_vm_ratio_fifo #(
    parameter int W     = 64,
    parameter int DEPTH = 4,            // entries, power of two
    parameter int HOLD  = 2             // extra DOWN cycles of each side; (HOLD + 1) * T_own must exceed T_peer
) (
    input  logic         wclk,
    input  logic         wrst_n,        // synchronous to wclk
    input  logic         w_v,
    output logic         w_rdy,
    input  logic [W-1:0] w_d,
    input  logic         rclk,
    input  logic         rrst_n,        // synchronous to rclk
    output logic         r_v,
    input  logic         r_rdy,
    output logic [W-1:0] r_d,
    output logic         w_live,        // write side in RUN with the reader seen up
    output logic         control_fault,
    output logic         r_live         // read side in RUN with the writer seen up
);
    localparam int AW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam int CW = $clog2(HOLD + 1);
    initial if (HOLD < 1 || DEPTH < 2 || (DEPTH & (DEPTH - 1)) != 0) $error("ot_ratio_cdc_fifo: HOLD >= 1, DEPTH a power of two >= 2");
    localparam logic [1:0] S_DOWN = 2'b00, S_WAIT = 2'b01, S_RUN = 2'b10;

    // ---------------- write domain ----------------
    logic [W-1:0]  mem [DEPTH];         // write-domain storage      (crosses: mem[i] -> sh[i])
    logic [AW:0]   wp;                  // write pointer             (crosses: wp -> wp_r)
    logic [1:0]    w_st;                // write-side state          (crosses: w_st -> w_st_r)
    logic [CW-1:0] w_cnt;
    logic          w_ok;                // reader seen not-RUN during this DOWN
    logic [AW:0]   rp_w;                // sampler of rp   (never reset: always a real sample)
    logic [1:0]    r_st_w;              // sampler of r_st
    logic          w_fire;
    logic [AW:0]   rp;
    logic [1:0]    r_st;

    always_ff @(posedge wclk) begin
        rp_w   <= rp;
        r_st_w <= r_st;
    end
    assign w_live = (w_st == S_RUN) && (r_st_w != S_DOWN);
    assign w_rdy  = wrst_n && !control_fault && w_live && ((wp - rp_w) != (AW+1)'(DEPTH));
    assign w_fire = w_v && w_rdy;
    always_ff @(posedge wclk) begin
        if (!wrst_n) begin
            w_st <= S_DOWN; w_cnt <= CW'(HOLD); w_ok <= 1'b0; wp <= '0;
        end else begin
            case (w_st)
                S_DOWN: begin
                    wp <= '0;
                    if (r_st_w != S_RUN) w_ok <= 1'b1;
                    if (w_cnt != '0) w_cnt <= w_cnt - 1'b1;
                    else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;
                end
                S_WAIT: begin
                    wp <= '0;
                    if (r_st_w != S_DOWN) w_st <= S_RUN;
                end
                default: begin // S_RUN
                    if (r_st_w == S_DOWN) begin
                        w_st <= S_DOWN; w_cnt <= CW'(HOLD); w_ok <= 1'b1; wp <= '0;
                    end else if (w_fire) wp <= wp + 1'b1;
                end
            endcase
        end
    end
    always_ff @(posedge wclk) if (w_fire) mem[wp[AW-1:0]] <= w_d;

    // ---------------- read domain ----------------
    logic [W-1:0]  sh [DEPTH];          // read-domain shadow of every entry (flop -> flop, every cycle)
    logic [CW-1:0] r_cnt;
    logic          r_ok;
    logic [AW:0]   wp_r;                // sampler of wp
    logic [1:0]    w_st_r;              // sampler of w_st
    logic          r_take;

    always_ff @(posedge rclk) begin
        wp_r   <= wp;
        w_st_r <= w_st;
        for (int i = 0; i < DEPTH; i++) sh[i] <= mem[i];
    end
    assign r_live = (r_st == S_RUN) && (w_st_r != S_DOWN);
    assign r_v    = rrst_n && !control_fault && r_live && (wp_r != rp);
    assign r_d    = sh[rp[AW-1:0]];
    assign r_take = r_v && r_rdy;
    always_ff @(posedge rclk) begin
        if (!rrst_n) begin
            r_st <= S_DOWN; r_cnt <= CW'(HOLD); r_ok <= 1'b0; rp <= '0;
        end else begin
            case (r_st)
                S_DOWN: begin
                    rp <= '0;
                    if (w_st_r != S_RUN) r_ok <= 1'b1;
                    if (r_cnt != '0) r_cnt <= r_cnt - 1'b1;
                    else if (r_ok || w_st_r != S_RUN) r_st <= S_WAIT;
                end
                S_WAIT: begin
                    rp <= '0;
                    if (w_st_r != S_DOWN) r_st <= S_RUN;
                end
                default: begin // S_RUN
                    if (w_st_r == S_DOWN) begin
                        r_st <= S_DOWN; r_cnt <= CW'(HOLD); r_ok <= 1'b1; rp <= '0;
                    end else if (r_take) rp <= rp + 1'b1;
                end
            endcase
        end
    end

    // Independent control copy. Packet bits themselves carry SECDED.
    // Mapping must retain both storage rails; no merged-copy qualification.
    (* keep=1,dont_touch=1 *) logic [AW:0] wp_check,rp_check,rp_w_check,wp_r_check;
    (* keep=1,dont_touch=1 *) logic [1:0] w_st_check,r_st_check,r_st_w_check,w_st_r_check;
    (* keep=1,dont_touch=1 *) logic [CW-1:0] w_cnt_check,r_cnt_check;
    (* keep=1,dont_touch=1 *) logic w_ok_check,r_ok_check;
    logic w_live_check,r_live_check,w_rdy_check,r_v_check,w_fire_check,r_take_check;
    assign control_fault=wp!=wp_check||rp!=rp_check||rp_w!=rp_w_check||wp_r!=wp_r_check||
        w_st!=w_st_check||r_st!=r_st_check||r_st_w!=r_st_w_check||w_st_r!=w_st_r_check||
        w_cnt!=w_cnt_check||r_cnt!=r_cnt_check||w_ok!=w_ok_check||r_ok!=r_ok_check;
    assign w_live_check=(w_st_check==S_RUN)&&(r_st_w_check!=S_DOWN);
    assign r_live_check=(r_st_check==S_RUN)&&(w_st_r_check!=S_DOWN);
    assign w_rdy_check=wrst_n&&w_live_check&&((wp_check-rp_w_check)!=(AW+1)'(DEPTH))&&!control_fault;
    assign r_v_check=rrst_n&&r_live_check&&(wp_r_check!=rp_check)&&!control_fault;
    assign w_fire_check=w_v&&w_rdy_check;
    assign r_take_check=r_v_check&&r_rdy;

always_ff @(posedge wclk) begin
        rp_w_check   <= rp_check;
        r_st_w_check <= r_st_check;
    end
always_ff @(posedge wclk) begin
        if (!wrst_n) begin
            w_st_check <= S_DOWN; w_cnt_check <= CW'(HOLD); w_ok_check <= 1'b0; wp_check <= '0;
        end else begin
            case (w_st_check)
                S_DOWN: begin
                    wp_check <= '0;
                    if (r_st_w_check != S_RUN) w_ok_check <= 1'b1;
                    if (w_cnt_check != '0) w_cnt_check <= w_cnt_check - 1'b1;
                    else if (w_ok_check || r_st_w_check != S_RUN) w_st_check <= S_WAIT;
                end
                S_WAIT: begin
                    wp_check <= '0;
                    if (r_st_w_check != S_DOWN) w_st_check <= S_RUN;
                end
                default: begin // S_RUN
                    if (r_st_w_check == S_DOWN) begin
                        w_st_check <= S_DOWN; w_cnt_check <= CW'(HOLD); w_ok_check <= 1'b1; wp_check <= '0;
                    end else if (w_fire_check) wp_check <= wp_check + 1'b1;
                end
            endcase
        end
    end
always_ff @(posedge rclk) begin
        wp_r_check   <= wp_check;
        w_st_r_check <= w_st_check;
    end
always_ff @(posedge rclk) begin
        if (!rrst_n) begin
            r_st_check <= S_DOWN; r_cnt_check <= CW'(HOLD); r_ok_check <= 1'b0; rp_check <= '0;
        end else begin
            case (r_st_check)
                S_DOWN: begin
                    rp_check <= '0;
                    if (w_st_r_check != S_RUN) r_ok_check <= 1'b1;
                    if (r_cnt_check != '0) r_cnt_check <= r_cnt_check - 1'b1;
                    else if (r_ok_check || w_st_r_check != S_RUN) r_st_check <= S_WAIT;
                end
                S_WAIT: begin
                    rp_check <= '0;
                    if (w_st_r_check != S_DOWN) r_st_check <= S_RUN;
                end
                default: begin // S_RUN
                    if (w_st_r_check == S_DOWN) begin
                        r_st_check <= S_DOWN; r_cnt_check <= CW'(HOLD); r_ok_check <= 1'b1; rp_check <= '0;
                    end else if (r_take_check) rp_check <= rp_check + 1'b1;
                end
            endcase
        end
    end
endmodule
