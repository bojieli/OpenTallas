`timescale 1ns/1ps
// Existing consumer FIFO, grant and packet-capture registers kept together so
// the FIFO head mux never becomes an unregistered inter-leaf output.
module ot_lkep_tx_shared #(parameter integer NS=3,W=545,TFD=4,RL=2,SL=64,IDLE_P=1024)(
 input wire clk,rst_n,
 input wire [NS-1:0] th_vt,
 input wire [W+36-1:0] th_dt [0:NS-1],
 output wire [NS-1:0] tcrq,
 output reg b_v,
 output reg [W+52-1:0] b_f
);
 localparam integer SW=12,EW=24,TW=W+SW+EW,HB=2+SW+EW+W,FFW=HB+14;
 reg [1:0] rs; reg rto;
 always @(posedge clk or negedge rst_n) if(!rst_n) rs<=0;else rs<={rs[0],1'b1};
 always @(posedge clk) rto<=rs[1];
 genvar g;
    // ---------------------------------------------------------------- TX out: tile sink stage 1 -> consumer FIFO -> grant
    wire [NS-1:0]    th_v;
    wire [TW-1:0]    th_d [0:NS-1];
    reg  [NS-1:0]    gnt;
    generate for (g = 0; g < NS; g = g + 1) begin : g_to
        ot_lkep_sinkc #(.W(TW), .D(TFD), .N(RL), .SL(SL)) u_q (.clk(clk), .rst_c(rto), .i_v(th_vt[g]), .i_d(th_dt[g]),
            .h_v(th_v[g]), .h_d(th_d[g]), .pop(gnt[g]), .crq(tcrq[g]));
    end endgenerate

    // ---------------------------------------------------------------- gearbox pacer (exact mirror of its slot FIFO)
    reg  [9:0]    m_ic; reg m_idle; reg [1:0] m_ph; reg [2:0] m_sn;
    reg           a_v, x_v;                        // grant -> A (select) -> X (CRC partials) -> B (CRC) -> gearbox push
    wire          m_need = !m_idle && (m_ph != 2'd3);
    wire          m_take = m_need && (m_sn != 0);
    wire [1:0]    pend = {1'b0, a_v} + {1'b0, x_v} + {1'b0, b_v};
    wire          room = ({1'b0, m_sn} + {2'b0, pend}) <= 4'd3;
    reg  [1:0]    tsel;                                 // round-robin start for the tx grant
    integer       k, j;
    always @(*) begin
        gnt = 0;
        if (room)
            for (k = NS - 1; k >= 0; k = k - 1) begin
                j = (tsel + k) % NS;
                if (th_v[j]) gnt = {{(NS-1){1'b0}}, 1'b1} << j;
            end
    end
    reg  [HB-1:0] a_h, x_h;
    wire [13:0]   x_crc;

    integer i2;
    always @(posedge clk) begin
        for (i2 = 0; i2 < NS; i2 = i2 + 1)
            if (gnt[i2]) a_h <= {th_d[i2][TW-1:W], i2[1:0], th_d[i2][W-1:0]};
        x_h <= a_h;
        b_f <= {x_crc, x_h};
    end
    ot_crc_pipe #(.W(HB), .N(14), .POLY(14'h0805), .INIT(14'h3FFF), .NP(4)) u_crc_t (.clk(clk), .d(a_h), .crc(x_crc));
    always @(posedge clk or negedge rto)
        if (!rto) begin
            m_ic <= 0; m_idle <= (IDLE_P == 1); m_ph <= 0; m_sn <= 0; a_v <= 0; x_v <= 0; b_v <= 0; tsel <= 0;
        end else begin
            m_ic <= m_idle ? 10'd0 : m_ic + 1'b1;
            m_idle <= !m_idle && (m_ic == IDLE_P - 2);
            if (!m_idle) m_ph <= m_ph + 1'b1;
            m_sn <= m_sn + (b_v ? 3'd1 : 3'd0) - (m_take ? 3'd1 : 3'd0);
            a_v <= |gnt; x_v <= a_v; b_v <= x_v;
            if (|gnt) tsel <= (tsel == NS - 1) ? 2'd0 : tsel + 1'b1;
        end

endmodule
