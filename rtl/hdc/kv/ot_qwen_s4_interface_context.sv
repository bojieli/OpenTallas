`timescale 1ps/1fs
// Actual 4-stack / 128-PC interface cut. No DRAM simulator, reduced array,
// synthetic service source or assumed PHY adapter. Global service wires and
// PHY returns are explicit boundary ports requiring loaded context closure.
// The parent core is outside this cut; service clk is its free-running root,
// not u_me's gated clock. HCLK is an independent external periodic root.
module ot_qwen_s4_interface_context #(
    parameter integer PROTECTED=0,
    parameter integer LOCAL_TRANSPORT=0,ACK_BACKPRESSURE=0,
    parameter integer MEM_WORDS=3*131072,
    parameter integer PHASE=0
)(
    input wire clk, hclk, rst_n, warm_rst_n,
    input wire d_v, go,
    input wire [18:0] d_row,
    input wire [10:0] d_n,
    output wire d_rdy, fault,
    output wire [127:0] l_v,
    output wire [128*17-1:0] l_sec,
    output wire [128*8-1:0] l_row,
    output wire [128*256-1:0] l_data,
    input wire [127:0] l_pop, w_v, wd_ready,
    input wire [128*24-1:0] w_sec,
    input wire [128*256-1:0] w_data,
    input wire [128*9-1:0] w_tag,
    output wire [127:0] w_room, wd_v,
    output wire [128*9-1:0] wd_tag,
    // Actual registered HCLK PHY return and completion inputs.
    input wire [127:0] h_lv, h_av,
    input wire [128*17-1:0] h_lsec,
    input wire [128*8-1:0] h_lrow,
    input wire [128*256-1:0] h_ldata,
    input wire [128*9-1:0] h_atag,
    input wire phy_fault,
    output wire [127:0] row_v, col_v, col_we, busy,
    output wire [128*3-1:0] row_op,
    output wire [128*5-1:0] row_bank, col_bank, col_col,
    output wire [128*19-1:0] row_row,
    // The actual WR capture follows the column command by one HCLK edge.
    output wire [127:0] h_cv,
    output wire [128*24-1:0] h_csec,
    output wire [128*256-1:0] h_cdata,
    output wire [128*9-1:0] h_ctag
);
    localparam integer NSTK=4, NPC=128, TAGW=9, CRED=32,
        LR=64, WBUF=16, WQ=4, SYNC=2;
    // Literal b3r12 PC-to-lfifo paths, rounded up at430.56um per cut.
    // Reuse charged u_l/u_w/u_a codec endpoints; preserve the real CDC.
    function automatic integer local_spans(input integer p);
        case(p)
            0: local_spans=14;
            1: local_spans=13;
            2: local_spans=12;
            3: local_spans=10;
            4: local_spans=9;
            5: local_spans=8;
            6: local_spans=7;
            7: local_spans=5;
            8: local_spans=5;
            9: local_spans=7;
            10: local_spans=8;
            11: local_spans=9;
            12: local_spans=10;
            13: local_spans=12;
            14: local_spans=13;
            15: local_spans=14;
            16: local_spans=13;
            17: local_spans=12;
            18: local_spans=11;
            19: local_spans=10;
            20: local_spans=8;
            21: local_spans=7;
            22: local_spans=6;
            23: local_spans=5;
            24: local_spans=5;
            25: local_spans=6;
            26: local_spans=7;
            27: local_spans=8;
            28: local_spans=10;
            29: local_spans=11;
            30: local_spans=12;
            31: local_spans=14;
            32: local_spans=14;
            33: local_spans=13;
            34: local_spans=12;
            35: local_spans=10;
            36: local_spans=9;
            37: local_spans=8;
            38: local_spans=7;
            39: local_spans=5;
            40: local_spans=5;
            41: local_spans=7;
            42: local_spans=8;
            43: local_spans=9;
            44: local_spans=10;
            45: local_spans=12;
            46: local_spans=13;
            47: local_spans=14;
            48: local_spans=13;
            49: local_spans=12;
            50: local_spans=11;
            51: local_spans=10;
            52: local_spans=8;
            53: local_spans=7;
            54: local_spans=6;
            55: local_spans=5;
            56: local_spans=5;
            57: local_spans=6;
            58: local_spans=7;
            59: local_spans=8;
            60: local_spans=10;
            61: local_spans=11;
            62: local_spans=12;
            63: local_spans=14;
            64: local_spans=13;
            65: local_spans=12;
            66: local_spans=11;
            67: local_spans=10;
            68: local_spans=8;
            69: local_spans=7;
            70: local_spans=6;
            71: local_spans=5;
            72: local_spans=5;
            73: local_spans=6;
            74: local_spans=7;
            75: local_spans=8;
            76: local_spans=10;
            77: local_spans=11;
            78: local_spans=12;
            79: local_spans=14;
            80: local_spans=14;
            81: local_spans=13;
            82: local_spans=12;
            83: local_spans=10;
            84: local_spans=9;
            85: local_spans=8;
            86: local_spans=7;
            87: local_spans=5;
            88: local_spans=5;
            89: local_spans=7;
            90: local_spans=8;
            91: local_spans=9;
            92: local_spans=10;
            93: local_spans=12;
            94: local_spans=13;
            95: local_spans=14;
            96: local_spans=13;
            97: local_spans=12;
            98: local_spans=11;
            99: local_spans=10;
            100: local_spans=8;
            101: local_spans=7;
            102: local_spans=6;
            103: local_spans=5;
            104: local_spans=5;
            105: local_spans=6;
            106: local_spans=7;
            107: local_spans=8;
            108: local_spans=10;
            109: local_spans=11;
            110: local_spans=12;
            111: local_spans=14;
            112: local_spans=14;
            113: local_spans=13;
            114: local_spans=12;
            115: local_spans=10;
            116: local_spans=9;
            117: local_spans=8;
            118: local_spans=7;
            119: local_spans=5;
            120: local_spans=5;
            121: local_spans=7;
            122: local_spans=8;
            123: local_spans=9;
            124: local_spans=10;
            125: local_spans=12;
            126: local_spans=13;
            127: local_spans=14;
            default: local_spans=0;
        endcase
    endfunction
    generate if(PROTECTED)begin:selected
    wire h_rst_n;
    ot_reset_sync u_hrst(.clk(hclk),.async_rst_n(rst_n),.sync_rst_n(h_rst_n));
    wire [3:0] desc_rk, sfault_k, busy_k;
    wire desc_r=&desc_rk, sfault=|sfault_k, busy_all=&busy_k;
    wire protected_dv, protected_go, protected_cf, protected_hf;
    wire [18:0] protected_row;
    wire [10:0] protected_n;
    wire [127:0] c_fault_p, h_fault_p, wr_v, wr_r;
    wire [128*3-1:0] cred_ret;
    wire [128*24-1:0] wr_sec;
    wire [128*5-1:0] wr_bank, wr_col;
    wire [127:0] h_wcon=col_v & col_we;
    assign fault=protected_cf;
    ot_qwen_s4_protected_control #(.MEM_ROWS(MEM_WORDS/131072)) u_control(
        .clk(clk),.hclk(hclk),.por_n(rst_n),.warm_rst_n(warm_rst_n),
        .d_v(d_v),.d_rdy(d_rdy),.d_row(d_row),.d_n(d_n),.go(go),
        .desc_v(protected_dv),.desc_r(desc_r),.desc_row(protected_row),.desc_n(protected_n),
        .busy_all(busy_all),.h_go(protected_go),
        .c_external_fault(|c_fault_p),.h_external_fault(phy_fault|sfault|(|h_fault_p)),
        .c_fault(protected_cf),.h_fault(protected_hf));
    function automatic [4:0] l2bank(input [16:0] l);
        reg [9:0] j;begin j={l[14:6],l[16]};l2bank={j[9:7],j[1:0]};end
    endfunction
    function automatic [4:0] l2col(input [16:0] l);
        reg [9:0] j;begin j={l[14:6],l[16]};l2col=j[6:2];end
    endfunction
    for (genvar sk = 0; sk < NSTK; sk = sk + 1) begin : stk
        ot_hbm_r14_stream_stack #(.ENABLE(1), .REF_MODE(1), .CRED(CRED), .PHASE(PHASE), .WR_EN(1), .WQ(WQ), .PULLIN(0), .AQ_RD(0), .NCH(16)) u_ctl (
            .clk(hclk), .rst_n(h_rst_n), .desc_v(protected_dv && desc_r), .desc_r(desc_rk[sk]), .desc_row(protected_row), .desc_n(protected_n),
            .go(protected_go), .next_posted(1'b0), .row_v(row_v[sk*32 +: 32]), .row_op(row_op[sk*96 +: 96]),
            .row_bank(row_bank[sk*160 +: 160]), .row_row(row_row[sk*608 +: 608]),
            .col_v(col_v[sk*32 +: 32]), .col_bank(col_bank[sk*160 +: 160]), .col_col(col_col[sk*160 +: 160]),
            .cred_ret(cred_ret[sk*96 +: 96]), .busy(busy[sk*32 +: 32]), .fault(sfault_k[sk]),
            .wr_v(wr_v[sk*32 +: 32]), .wr_bank(wr_bank[sk*160 +: 160]), .wr_col(wr_col[sk*160 +: 160]),
            .wr_r(wr_r[sk*32 +: 32]), .col_we(col_we[sk*32 +: 32]), .wr_rd(32'b0), .col_aq());
        assign busy_k[sk] = busy[sk*32];
    end

    for (genvar q = 0; q < NPC; q = q + 1) begin : pc
        ot_qwen_s4_protected_pc #(.MEM_WORDS(MEM_WORDS), .PC_ID(q), .TAGW(TAGW), .LD(LR), .WB(WBUF), .AD(LR), .SYNC(SYNC),
            .LOCAL_WIRE_SPANS(LOCAL_TRANSPORT?local_spans(q):0),.ACK_BACKPRESSURE(ACK_BACKPRESSURE)) u_cdc (
            .clk(clk), .por_n(rst_n), .warm_rst_n(warm_rst_n),
            .l_v(l_v[q]), .l_sec(l_sec[q*17 +: 17]), .l_row(l_row[q*8 +: 8]), .l_data(l_data[q*256 +: 256]), .l_pop(l_pop[q]),
            .w_v(w_v[q]), .w_sec(w_sec[q*24 +: 24]), .w_data(w_data[q*256 +: 256]), .w_tag(w_tag[q*TAGW +: TAGW]),
            .w_room(w_room[q]), .wd_ready(wd_ready[q]), .wd_v(wd_v[q]), .wd_tag(wd_tag[q*TAGW +: TAGW]), .c_fault(c_fault_p[q]),
            .hclk(hclk),
            .h_lv(h_lv[q]), .h_lsec(h_lsec[q*17 +: 17]), .h_lrow(h_lrow[q*8 +: 8]), .h_ldata(h_ldata[q*256 +: 256]), .h_cred(cred_ret[q*3 +: 3]),
            .h_wv(wr_v[q]), .h_wsec(wr_sec[q*24 +: 24]), .h_hand(wr_v[q] && wr_r[q]), .h_wcon(h_wcon[q]),
            .h_cv(h_cv[q]), .h_csec(h_csec[q*24 +: 24]), .h_cdata(h_cdata[q*256 +: 256]), .h_ctag(h_ctag[q*TAGW +: TAGW]),
            .h_av(h_av[q]), .h_atag(h_atag[q*TAGW +: TAGW]), .h_fault(h_fault_p[q]));
        assign wr_bank[q*5 +: 5] = l2bank(wr_sec[q*24 +: 17]);
        assign wr_col[q*5 +: 5]  = l2col(wr_sec[q*24 +: 17]);
    end

    end else begin:off
        assign {d_rdy,fault,l_v,l_sec,l_row,l_data,w_room,wd_v,wd_tag,
            row_v,col_v,col_we,busy,row_op,row_bank,col_bank,col_col,row_row,
            h_cv,h_csec,h_cdata,h_ctag}='0;
    end endgenerate
endmodule
