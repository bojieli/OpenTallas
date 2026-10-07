`timescale 1ps/1fs
// Full-width protected context; physical parallel homes/SSFF remain owner-qualified.
module ot_qwen_p0_parallel_transport_context #(
    parameter integer ENABLE=0,MEM_WORDS=36*131072,PHASE=0,
    parameter integer CDC_CONSUMER_JOIN=0,LANDING_RSEL=0,LOCAL_WIRE_SPANS=0,SAME_CYCLE_GO=0, // owner r9 protected landing read
    parameter integer KV_MAP=0 // 1: option-M quadrant-local KV stripe (ot_qwen_kv_map_m.svh); default off
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
    // Actual HCLK credit retirement and descriptor/GO consumption observations.
    output wire [128*3-1:0] h_cred_ret,
    output wire [3:0] h_desc_commit, h_go_commit,
    output wire [11:0] h_desc_ordinal, h_go_ordinal,
    output wire [127:0] h_cv,
    output wire [128*24-1:0] h_csec,
    output wire [128*256-1:0] h_cdata,
    output wire [128*9-1:0] h_ctag
);
    initial if(ENABLE && (CDC_CONSUMER_JOIN!=1 || LANDING_RSEL!=1 || MEM_WORDS!=36*131072))
        $fatal(1,"parallel protected P0 requires owner RSEL1 adapter/full36 backing");
`include "ot_qwen_kv_map_m.svh"
    // Per-PC stream index j of a logical sector and per-stack descriptor n (as ot_qwen_hbm_stream4_cdc).
    function automatic [9:0] l2j(input [16:0] l);
        l2j = (KV_MAP != 0) ? m_l2j(l) : {l[14:6], l[16]};
    endfunction
    function automatic [10:0] nstk(input integer sk, input [10:0] n);
        nstk = (KV_MAP != 0) ? m_n(sk, n) : n;
    endfunction
    generate if(ENABLE)begin:active
        wire h_rst_n;
        ot_reset_sync u_hrst(.clk(hclk),.async_rst_n(rst_n),.sync_rst_n(h_rst_n));
        wire [3:0] ready,cf,stack_quiet,admit_free;
        assign d_rdy=(&ready)&&(&admit_free);assign fault=|cf;assign quiet=&stack_quiet&&!fault;
        for(genvar sk=0;sk<4;sk=sk+1)begin:stack
            wire dv,go_v,dr,ctl_bad,ctl_cf,ctl_hf,gr;
            wire [18:0] row;wire [10:0] n;
            wire [31:0] wr_v,wr_r,pc_cf,pc_hf,cq,hq;
            wire [32*24-1:0] head_sec;
            wire [159:0] wr_bank,wr_col;
            wire [5:0] state;
            wire state_bad,cbv,cbready,cbwf,cbrf;
            wire [3:0] cb;
            // Every stack accepts the same descriptor on one common grant.
            // Warm blocks new root admission; accepted GO/landing/ACK owners drain.
            ot_qwen_s4_protected_control #(.MEM_ROWS(MEM_WORDS/131072),.SAME_CYCLE_GO(SAME_CYCLE_GO)) u_control(
                .clk(clk),.hclk(hclk),.por_n(rst_n),.warm_rst_n(warm_rst_n),
                .d_v(d_v&&d_rdy),.d_rdy(ready[sk]),.d_row(d_row),.d_n(d_n),.go(go),
                .desc_v(dv),.desc_r(dr),.desc_row(row),.desc_n(n),
                .busy_all(&busy[sk*32+:32]),.h_go(go_v),.go_ready(gr),
                .desc_commit(h_desc_commit[sk]),.go_commit(h_go_commit[sk]),
                .desc_ordinal(h_desc_ordinal[sk*3+:3]),.go_ordinal(h_go_ordinal[sk*3+:3]),
                .c_external_fault(state[5]||cbwf||cbrf||(|pc_cf)),
                .h_external_fault(phy_fault||ctl_bad||(|pc_hf)),.c_fault(ctl_cf),.h_fault(ctl_hf));
            // Actual HCLK consumption events cross back; no ideal descriptor
            // completion or ready assertion. One reserved callback per event.
            ot_qwen_s4_protected_ring #(.WIDTH(4),.DEPTH(4),.PC_ID(sk),.KIND(7)) u_callback(
                .wr_clk(hclk),.rd_clk(clk),.por_n(rst_n),.allow_new(1'b1),
                .wr_valid(h_desc_commit[sk]||h_go_commit[sk]),.wr_ready(cbready),
                .wr_data({h_go_commit[sk],h_go_commit[sk]?h_go_ordinal[sk*3+:3]:h_desc_ordinal[sk*3+:3]}),
                .wr_occupancy(),.wr_fault(cbwf),.rd_valid(cbv),.rd_ready(cbv&&!state_bad&&!cb_bad),
                .rd_data(cb),.rd_owner(),.retire(cbv&&!state_bad&&!cb_bad),.retired(),.rd_fault(cbrf));
            wire cb_bad=cbv&&((cb[2:0]!=state[2:0])||(cb[3]?!state[4]:!state[3]));
            assign admit_free[sk]=!state[3]&&!state[4]&&!state_bad&&!state[5];
            wire dp_next=(state[3]||(d_v&&d_rdy))&&!(cbv&&!cb[3]&&!cb_bad);
            wire gp_next=(state[4]||go)&&!(cbv&&cb[3]&&!cb_bad);
            ot_qwen_s4_checked_state #(.W(6)) u_state(.clk(clk),.por_n(rst_n),.en(!state_bad),
                .d({state[5]||cb_bad||(d_v&&!d_rdy)||(go&&!gr),gp_next,dp_next,
                    state[2:0]+3'(cbv&&cb[3]&&!cb_bad)}),.q(state),.bad(state_bad));
            (* async_reg="true" *) reg [1:0] hq_sync,hqi_sync,hf_sync,hfi_sync;
            always @(posedge clk or negedge rst_n)
                if(!rst_n)begin hq_sync<=0;hqi_sync<=3;hf_sync<=0;hfi_sync<=3;end
                else begin hq_sync<={hq_sync[0],&hq};hqi_sync<={hqi_sync[0],~(&hq)};
                    hf_sync<={hf_sync[0],ctl_hf||(|pc_hf)};hfi_sync<={hfi_sync[0],~(ctl_hf||(|pc_hf))};end
            assign cf[sk]=ctl_cf||state_bad||state[5]||hf_sync[1]||(hf_sync[1]!=~hfi_sync[1]);
            assign stack_quiet[sk]=(&cq)&&hq_sync[1]&&(hq_sync[1]==~hqi_sync[1])&&
                !state[3]&&!state[4]&&!cbv&&!d_v&&!go;
            ot_hbm_r14_stream_stack #(.ENABLE(1),.REF_MODE(1),.CRED(32),.PHASE(PHASE),
                .WR_EN(1),.WQ(4),.PULLIN(0),.AQ_RD(0),.NCH(16)) u_ctl(
                .clk(hclk),.rst_n(h_rst_n),.desc_v(dv&&dr),.desc_r(dr),.desc_row(row),.desc_n(nstk(sk,n)),
                .go(go_v),.next_posted(1'b0),.row_v(row_v[sk*32+:32]),.row_op(row_op[sk*96+:96]),
                .row_bank(row_bank[sk*160+:160]),.row_row(row_row[sk*608+:608]),
                .col_v(col_v[sk*32+:32]),.col_bank(col_bank[sk*160+:160]),.col_col(col_col[sk*160+:160]),
                .cred_ret(h_cred_ret[sk*96+:96]),.busy(busy[sk*32+:32]),.fault(ctl_bad),
                .wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),.wr_r(wr_r),
                .col_we(col_we[sk*32+:32]),.wr_rd(32'b0),.col_aq());
            ot_qwen_p0_parallel_bank #(.ENABLE(1),.PC_BASE(32*sk),.MEM_WORDS(MEM_WORDS),
                .LANDING_RSEL(LANDING_RSEL),.LOCAL_WIRE_SPANS(LOCAL_WIRE_SPANS),.KV_MAP(KV_MAP)) u_bank(
                .clk(clk),.hclk(hclk),.por_n(rst_n),.warm_rst_n(warm_rst_n),
                .l_v(l_v[sk*32+:32]),
                .l_sec(l_sec[sk*544+:544]),
                .l_row(l_row[sk*256+:256]),
                .l_data(l_data[sk*8192+:8192]),
                .l_pop(l_pop[sk*32+:32]),
                .w_v(w_v[sk*32+:32]),
                .w_sec(w_sec[sk*768+:768]),
                .w_data(w_data[sk*8192+:8192]),
                .w_tag(w_tag[sk*288+:288]),
                .w_room(w_room[sk*32+:32]),
                .wd_v(wd_v[sk*32+:32]),
                .wd_tag(wd_tag[sk*288+:288]),
                .wd_accept(wd_accept[sk*32+:32]),
                .c_fault(pc_cf),
                .h_lv(h_lv[sk*32+:32]),
                .h_lsec(h_lsec[sk*544+:544]),
                .h_lrow(h_lrow[sk*256+:256]),
                .h_ldata(h_ldata[sk*8192+:8192]),
                .h_cred(h_cred_ret[sk*96+:96]),
                .h_wv(wr_v),
                .h_cv(h_cv[sk*32+:32]),
                .h_csec(h_csec[sk*768+:768]),
                .h_cdata(h_cdata[sk*8192+:8192]),
                .h_ctag(h_ctag[sk*288+:288]),
                .h_av(h_av[sk*32+:32]),
                .h_atag(h_atag[sk*288+:288]),
                .h_fault(pc_hf),
                .h_wsec(head_sec),.h_hand(wr_v&wr_r),.h_wcon(col_v[sk*32+:32]&col_we[sk*32+:32]),
                .c_quiet(cq),.h_quiet(hq));
            for(genvar pc=0;pc<32;pc=pc+1)begin:map
                wire [23:0] sec=head_sec[pc*24+:24];
                wire [9:0] j=l2j(sec[16:0]);
                assign wr_bank[pc*5+:5]={j[9:7],j[1:0]};assign wr_col[pc*5+:5]=j[6:2];
            end
        end
    end else begin:off
        assign {d_rdy,fault,quiet,l_v,l_sec,l_row,l_data,w_room,wd_v,wd_tag,
            row_v,col_v,col_we,busy,row_op,row_bank,col_bank,col_col,row_row,
            h_cred_ret,h_desc_commit,h_go_commit,h_desc_ordinal,h_go_ordinal,
            h_cv,h_csec,h_cdata,h_ctag}='0;
    end endgenerate
endmodule
