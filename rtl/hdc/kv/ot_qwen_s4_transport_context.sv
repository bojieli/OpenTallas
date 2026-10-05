`timescale 1ps/1fs
// Full128 selected physical interface with actual shared finite transport.
// Four literal R14 controllers, real independent HCLK, explicit PHY pins.
// No behavioural DRAM/provider is included. Parent free/gated root relation,
// loaded source slots, pins and timing still require contextual qualification.
module ot_qwen_s4_transport_context #(
    parameter integer ENABLE=0,MEM_WORDS=36*131072,PHASE=0
)(
    input wire clk, hclk, rst_n, warm_rst_n,
    input wire d_v, go,
    input wire [18:0] d_row,
    input wire [10:0] d_n,
    output wire d_rdy, fault, quiet,
    output wire [127:0] l_v,
    output wire [128*17-1:0] l_sec,
    output wire [128*8-1:0] l_row,
    output wire [128*256-1:0] l_data,
    input wire [127:0] l_pop, w_v, wd_accept,
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
    generate if(ENABLE)begin:active
    wire h_rst_n;
    ot_reset_sync u_hrst(.clk(hclk),.async_rst_n(rst_n),.sync_rst_n(h_rst_n));
    wire [3:0] ready,cf,bf,q;
    wire all_ready=&ready;
    assign d_rdy=all_ready;assign fault=|cf;assign quiet=&q;
    for(genvar sk=0;sk<4;sk=sk+1)begin:stack
        wire b_dv,b_go,b_dr,b_gr,b_done_ready;
        wire [18:0] b_row;wire [10:0] b_n;
        wire [31:0] bwv,broom,bav,bardy,blv,blpop,pc_cf,pc_hf;
        wire [767:0] bsec;wire [8191:0] bdata,bldata;
        wire [287:0] btag,batag;wire [543:0] blsec;wire [255:0] blrow;
        wire [31:0] wr_v,wr_r;
        wire [159:0] wr_bank,wr_col;wire [95:0] credits;
        wire desc_v,go_v,desc_r,ctl_fault,ctl_cf,ctl_hf;
        wire [18:0] row;wire [10:0] n;
        wire desc_commit,go_commit;wire [2:0] desc_ordinal,go_ordinal;
        wire cbv,cbready,cbwf,cbrf;wire [3:0] cb;
        ot_qwen_s4_stack_transport #(.ENABLE(1),.STACK(sk),.MEM_ROWS(MEM_WORDS/131072),.WIRE_SPANS(41)) u_link(
            .clk(clk),.cold_por_n(rst_n),.warm_rst_n(warm_rst_n),
            .d_v(d_v),.go(go),.d_row(d_row),.d_n(d_n),.d_ready(ready[sk]),
            .w_v(w_v[sk*32+:32]),.w_sec(w_sec[sk*768+:768]),.w_data(w_data[sk*8192+:8192]),.w_tag(w_tag[sk*288+:288]),
            .w_room(w_room[sk*32+:32]),.wd_v(wd_v[sk*32+:32]),.wd_tag(wd_tag[sk*288+:288]),.wd_accept(wd_accept[sk*32+:32]),
            .l_v(l_v[sk*32+:32]),.l_sec(l_sec[sk*544+:544]),.l_row(l_row[sk*256+:256]),.l_data(l_data[sk*8192+:8192]),.l_pop(l_pop[sk*32+:32]),
            .b_desc_v(b_dv),.b_go(b_go),.b_desc_row(b_row),.b_desc_n(b_n),.b_desc_ready(b_dr),.b_go_ready(b_gr),
            .b_w_v(bwv),.b_w_sec(bsec),.b_w_data(bdata),.b_w_tag(btag),.b_w_room(broom),.b_wd_v(bav),.b_wd_tag(batag),.b_wd_ready(bardy),
            .b_l_v(blv),.b_l_sec(blsec),.b_l_row(blrow),.b_l_data(bldata),.b_l_pop(blpop),
            .b_desc_done(cbv&&!cb[3]),.b_go_done(cbv&&cb[3]),.b_done_ordinal(cb[2:0]),.b_done_ready(b_done_ready),
            .b_external_fault(ctl_cf|cbwf|cbrf|(|pc_cf)),.b_busy(|busy[sk*32+:32]),
            .c_fault(cf[sk]),.b_fault(bf[sk]),.quiet(q[sk]),.forward_debt(),.return_debt());
        // All traffic at this boundary already has a root reservation. Warm
        // cannot revoke it; only cold POR enters the backend reset tree.
        ot_qwen_s4_protected_control #(.MEM_ROWS(MEM_WORDS/131072)) u_control(
            .clk(clk),.hclk(hclk),.por_n(rst_n),.warm_rst_n(1'b1),
            .d_v(b_dv&&b_dr),.d_rdy(b_dr),.d_row(b_row),.d_n(b_n),.go(b_go),.go_ready(b_gr),
            .desc_v(desc_v),.desc_r(desc_r),.desc_row(row),.desc_n(n),.busy_all(&busy[sk*32+:32]),.h_go(go_v),
            .desc_commit(desc_commit),.go_commit(go_commit),.desc_ordinal(desc_ordinal),.go_ordinal(go_ordinal),
            .c_external_fault(1'b0),.h_external_fault(phy_fault|ctl_fault|(|pc_hf)),.c_fault(ctl_cf),.h_fault(ctl_hf));
        ot_qwen_s4_protected_ring #(.WIDTH(4),.DEPTH(4),.PC_ID(sk),.KIND(7)) u_callback(
            .wr_clk(hclk),.rd_clk(clk),.por_n(rst_n),.allow_new(1'b1),
            .wr_valid(desc_commit||go_commit),.wr_ready(cbready),.wr_data({go_commit,go_commit?go_ordinal:desc_ordinal}),.wr_occupancy(),.wr_fault(cbwf),
            .rd_valid(cbv),.rd_ready(b_done_ready),.rd_data(cb),.rd_owner(),.retire(cbv&&b_done_ready),.retired(),.rd_fault(cbrf),
            .retired_source(),.retired_source_valid());
        ot_hbm_r14_stream_stack #(.ENABLE(1),.REF_MODE(1),.CRED(32),.PHASE(PHASE),.WR_EN(1),.WQ(4),.PULLIN(0),.AQ_RD(0),.NCH(16)) u_ctl(
            .clk(hclk),.rst_n(h_rst_n),.desc_v(desc_v&&desc_r),.desc_r(desc_r),.desc_row(row),.desc_n(n),.go(go_v),.next_posted(1'b0),
            .row_v(row_v[sk*32+:32]),.row_op(row_op[sk*96+:96]),.row_bank(row_bank[sk*160+:160]),.row_row(row_row[sk*608+:608]),
            .col_v(col_v[sk*32+:32]),.col_bank(col_bank[sk*160+:160]),.col_col(col_col[sk*160+:160]),.cred_ret(credits),
            .busy(busy[sk*32+:32]),.fault(ctl_fault),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(wr_r),.col_we(col_we[sk*32+:32]),.wr_rd(32'b0),.col_aq());
        for(genvar p=0;p<32;p=p+1)begin:pc
            wire [23:0] head_sec;
            ot_qwen_s4_protected_pc #(.PC_ID(sk*32+p),.MEM_WORDS(MEM_WORDS),.LOCAL_WIRE_SPANS(local_spans(sk*32+p)),.ACK_BACKPRESSURE(1)) u_pc(
                .clk(clk),.hclk(hclk),.por_n(rst_n),.warm_rst_n(1'b1),
                .l_v(blv[p]),.l_sec(blsec[p*17+:17]),.l_row(blrow[p*8+:8]),.l_data(bldata[p*256+:256]),.l_pop(blpop[p]),
                .w_v(bwv[p]),.w_sec(bsec[p*24+:24]),.w_data(bdata[p*256+:256]),.w_tag(btag[p*9+:9]),.w_room(broom[p]),
                .wd_v(bav[p]),.wd_tag(batag[p*9+:9]),.wd_ready(bardy[p]),.c_fault(pc_cf[p]),
                .h_lv(h_lv[sk*32+p]),.h_lsec(h_lsec[(sk*32+p)*17+:17]),.h_lrow(h_lrow[(sk*32+p)*8+:8]),.h_ldata(h_ldata[(sk*32+p)*256+:256]),.h_cred(credits[p*3+:3]),
                .h_wv(wr_v[p]),.h_wsec(head_sec),.h_hand(wr_v[p]&&wr_r[p]),.h_wcon(col_v[sk*32+p]&&col_we[sk*32+p]),
                .h_cv(h_cv[sk*32+p]),.h_csec(h_csec[(sk*32+p)*24+:24]),.h_cdata(h_cdata[(sk*32+p)*256+:256]),.h_ctag(h_ctag[(sk*32+p)*9+:9]),
                .h_av(h_av[sk*32+p]),.h_atag(h_atag[(sk*32+p)*9+:9]),.h_fault(pc_hf[p]));
            // The R14 head comes from the checked local write-cache head,
            // not from the currently arriving global packet.
            wire [9:0] j={head_sec[14:6],head_sec[16]};
            assign wr_bank[p*5+:5]={j[9:7],j[1:0]};assign wr_col[p*5+:5]=j[6:2];
        end
    end
    end else begin:off
        assign {d_rdy,fault,quiet,l_v,l_sec,l_row,l_data,w_room,wd_v,wd_tag,
            row_v,col_v,col_we,busy,row_op,row_bank,col_bank,col_col,row_row,
            h_cv,h_csec,h_cdata,h_ctag}='0;
    end endgenerate
endmodule
