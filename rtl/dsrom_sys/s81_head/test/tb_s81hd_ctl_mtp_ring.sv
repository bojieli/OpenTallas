`timescale 1ns/1ps
// Real historical controller reference; independent extracted RESULT landing.
// HD-CTL 10-21: minimal smoke bench of ot_s81hd_ctl (Verilator 5.050 --binary --timing).
//   CSR writes on host lane 1 -> 80 tagged XB beats on ri (shuffled gidx order, gaps) -> bus B stream on sn_o / ss_o:
//   go + null best, slice m (xa word m mod 256, xb word m mod 64) at G + 5 + m for every m, xv window exact ->
//   fake N / S returns -> own BEST frame on the 6 mesh lanes -> fake peer BEST frames (both copies of each pair) ->
//   merged token flit through dsfd_mtp_seq -> ro (kind K_TOK) + host lane 0 RESULT frame; no fault.
//   Position 0: a peer wins strictly.  Position 1: all four logits equal -> the lowest row id wins.
// Verdict line: "PASS hd_ctl" / "FAIL hd_ctl <reason>".
module tb_s81hd_ctl_mtp_ring;
 parameter integer MUT=0;parameter integer MUT_RING=0; parameter integer SK=11;
    wire result_v,result_p,result_cr,result_ov;
    wire [511:0] result_d;
    wire[16:0] fault_state;wire fault_summary;reg allow_fault=0;
    wire merged_v;wire[48:0]merged_rb;wire[30:0]merged_id;
    ot_s81hd_ar_control_hsf0 #(.MUT_MODE(MUT))probe(
      .ck(ck),.rst_rank_pin_n(dut.u_logic.rr[5]),.rst_rank_hold_n(dut.u_logic.rr[6]),.rst_result_n(dut.u_logic.rr[7]),
      .rst_fault_n(dut.u_logic.rr[22]),.rst_fault_output_n(dut.u_logic.rr[23]),
      .own_valid(dut.u_logic.ov_p),.own_record(dut.u_logic.orec_d),.peer_valid(dut.mrv),.peer_frames(dut.mrd),
      .destination_header(dut.u_logic.c_hds),.sequencer_grant(dut.u_logic.t_rg),
      .lep_fault_i(lep_f),.external_fault_events({dut.u_logic.fset[16:11],dut.u_logic.fset[5:4],(dut.u_logic.bv&&(dut.u_logic.isnan(dut.u_logic.n_bits)||dut.u_logic.isnan(dut.u_logic.s_bits))),dut.u_logic.fset[2:0]}),
      .result_pending(result_p),.result_ready(result_cr),.result_overwrite(result_ov),
      .flit_valid(result_v),.flit_data(result_d),.merged_valid(merged_v),
      .merged_row_bits(merged_rb),.merged_identity(merged_id),.fault_vector(fault_state),.ctl_fault(fault_summary));
    always@(negedge ck)if(rst_n&&dut.u_logic.rr[6])begin
      if(merged_v!==dut.u_logic.mg4)$fatal(1,"composed rank valid mismatch");
      if(merged_v&&{merged_rb,merged_id}!=={dut.u_logic.mg_rb,dut.u_logic.mg_t})$fatal(1,"composed rank payload mismatch");
    end
    always @(negedge ck) if(rst_n && dut.u_logic.rr[22] && dut.u_logic.rr[23])
      if({fault_state,fault_summary}!=={dut.u_logic.fv,ctl_f})
        $fatal(1,"fault miter live LEP state mismatch");
    always@(negedge ck)begin
      if(dut.u_logic.tk_pop)$display("TOKTRACE pop row%0d bits%h word%h",dut.u_logic.tk_q[81:61],dut.u_logic.tk_q[113:82],dut.u_logic.tk_q);
      if(dut.u_logic.t_tv)$display("TOKTRACE seq row%0d bits%h",dut.u_logic.t_td[81:61],dut.u_logic.t_td[113:82]);
      if(dut.u_logic.f_rv)$display("TOKTRACE in row%0d bits%h",dut.u_logic.f_rd[81:61],dut.u_logic.f_rd[113:82]);
    end
    integer result_miter_count=0,merge_edge=-1;
    always @(negedge ck) if(rst_n && dut.u_logic.rr[7]) begin
      if({result_v,result_p,result_cr,result_ov} !==
         {dut.u_logic.f_rv,dut.u_logic.rpend,dut.u_logic.r_cr,dut.u_logic.fset[9]})
        $fatal(1,"result miter control edge mismatch");
      if(dut.u_logic.mg4) merge_edge=cyc;
      if(result_v)begin
        if(result_d!==dut.u_logic.f_rd) $fatal(1,"result miter full512-bit payload mismatch");
        if(result_d[152:151]!=0 || result_d[39:32]!=0)
          $fatal(1,"result miter lost high user identity");
        result_miter_count=result_miter_count+1;
        $display("RESULT_EDGE position=%0d merge_to_flit=%0d",result_d[60:40],cyc-merge_edge);
      end
    end

    localparam integer FW = 553, NSL = 8192 + 7 * SK;
    reg ck = 0; always #0.4165 ck = ~ck;
    reg rst_n = 0; reg start_i=0;wire job;
    reg [1103:0] ri = 0; reg [31:0] mu_rt = 0; reg [10:0] lw = 0; reg lep_f = 0;
    wire [1103:0] ro; wire [33:0] mu_c; wire [10:0] mu_rc; wire ctl_f;
    wire [564:0] sn_o, ss_o; reg [564:0] sn_i = 0, ss_i = 0;
    wire [5:0] mtx_v; wire [6*FW-1:0] mtx_d; reg [5:0] mrx_v = 0; reg [6*FW-1:0] mrx_d = 0;
    wire [1:0] htx_v; wire [2*FW-1:0] htx_d; reg [1:0] hrx_v = 0; reg [2*FW-1:0] hrx_d = 0;
    wire[0:0]dtx_v;wire[FW-1:0]dtx_d;reg[0:0]drx_v=0;reg[FW-1:0]drx_d=0;
    wire[63:0]txlane[0:2],rxlane[0:2];wire[275:0]host_in;wire[276:0]host_out;
    wire[44:0]unit_bus;
    ot_s81hd_ctl_core #(.SK(SK),.MUT_DRAFT_EARLY(MUT_RING))dut(.ck(ck),.rst_n(rst_n),.start_i(start_i),.lep_fault_i(lep_f),.lw_i(lw),
      .lepk_i0(ri),.lepk_o0(ro),.lepf_o0(ctl_f),.unit_o0(unit_bus),.ctrl_i0(mu_rt),.x_o(sn_o),.b_i(sn_i),
      .h_tx_o(host_out),.h_rx_i(host_in),.a_tx_o(txlane[0]),.b7_tx_o(txlane[1]),.n_tx_o(txlane[2]),
      .a_rx_i(rxlane[0]),.b7_rx_i(rxlane[1]),.n_rx_i(rxlane[2]));
    assign job=host_out[276];assign ss_o=sn_o;assign mu_c=unit_bus[44:11];assign mu_rc=unit_bus[10:0];
    wire host_txf,host_rxf,hword_v;wire[552:0]hword;
    ot_s81hd_host276_tx host_source(.ck(ck),.rn(rst_n),.v(|hrx_v),.frame(hrx_v[1]?hrx_d[1105:553]:hrx_d[552:0]),.lane(host_in),.fault(host_txf));
    ot_s81hd_host276_rx host_sink(.ck(ck),.rn(rst_n),.lane(host_out[275:0]),.v(hword_v),.frame(hword),.fault(host_rxf));
    assign htx_v={hword_v&&hword[3:0]==8,hword_v&&hword[3:0]==9};assign htx_d={hword,hword};
    genvar p;
    generate for(p=0;p<3;p=p+1)begin:g_emulate_peer
      wire bv,bf;wire[552:0]fr;
      ot_s81hd_best64_rx own_sink(.ck(ck),.rn(rst_n),.lane(txlane[p]),.v(bv),.frame(fr),.fault(bf));
      assign mtx_v[2*p+:2]={bv,bv};assign mtx_d[p*1106+:1106]={fr,fr};
      wire v=mrx_v[2*p]||mrx_v[2*p+1];wire copy_b=mrx_v[2*p+1];
      wire[552:0]rec=copy_b?mrx_d[(2*p+1)*553+:553]:mrx_d[(2*p)*553+:553];wire tf;
      ot_s81hd_beat_tx #(.W(110),.N(2),.P(62))peer_source(.ck(ck),.rn(rst_n),.v(v),.d({12'd0,copy_b,rec[96:0]}),.o(rxlane[p]),.fault(tf));
      always@(negedge ck)if(rst_n&&(bf||tf))$fatal(1,"physical mesh codec fault");
    end endgenerate
    always@(negedge ck)if(rst_n&&(host_txf||host_rxf))$fatal(1,"physical host codec fault");
    integer cyc = 0; always @(posedge ck) cyc <= cyc + 1;
    reg [15:0] xv [0:5119];
    integer errs = 0;
    task fail(input [8*64-1:0] msg); begin if (errs < 10) $display("FAIL hd_ctl %0s (cycle %0d)", msg, cyc); errs = errs + 1; end endtask
    task tick; @(negedge ck); endtask
    task csrw(input [7:0] a, input [63:0] d);
        begin hrx_v[1] = 1; hrx_d[FW +: FW] = {1'b1, 464'd0, d, a, 8'd0, 2'd0, 2'd0, 4'd6}; tick; hrx_v[1] = 0; tick; tick; end
    endtask
    // ---------------------------------------------------------------- stream monitor
    integer G = -1, P = 0, nstream = 0;
    integer m, j;
    always @(negedge ck) if (rst_n) begin
        if (sn_o !== ss_o) fail("sn_o != ss_o");
        if (sn_o[512]) begin
            G = cyc; nstream = nstream + 1;
            if (!sn_o[514] || sn_o[563:532] != 32'hFF80_0000 || sn_o[531:515] != 17'h1FFFF) fail("null best missing at go");
        end else if (sn_o[514]) fail("rv without go");
        if (G >= 0) begin
            m = cyc - G - 5;
            if (m >= 0 && m < NSL) begin
                if (!sn_o[513]) fail("xv low inside the slice window");
                for (j = 0; j < 16; j = j + 1) begin
                    if (sn_o[16*j +: 16] != xv[16*(m % 256) + j]) fail("xa slice mismatch");
                    if (sn_o[256 + 16*j +: 16] != xv[4096 + 16*(m % 64) + j]) fail("xb slice mismatch");
                end
            end else if (sn_o[513]) fail("xv outside the slice window");
        end
        if (ctl_f && !allow_fault) fail("ctl fault");
    end
    always@(negedge ck)if(rst_n)begin
      if(dut.u_logic.qpend||dut.u_logic.f_qv)$display("QTRACE cyc%0d pend%b cr%b hold%h f_qv%b f_qd%h",cyc,dut.u_logic.qpend,dut.u_logic.q_cr,dut.u_logic.q_hold,dut.u_logic.f_qv,dut.u_logic.f_qd);
      if(dut.u_logic.fset!=0&&dut.u_logic.fv==0)$display("FAULTTRACE cyc%0d set%h fv%h ej%0d expectj%0d eu%0d",cyc,dut.u_logic.fset,dut.u_logic.fv,dut.u_logic.u_seq.u_seq.ej,dut.u_logic.u_seq.u_seq.r_j,dut.u_logic.u_seq.u_seq.eu);
    end
    integer ntok=0,ndraft=0,ndh=0,nseed=0,nres=0,reply_due=-1;
    reg fixture_active=0;reg[3:0]reply_type;reg[33:0]reply_data;integer jj;
    reg[16:0]exp_row;reg[31:0]exp_bits;reg[20:0]exp_pos;
    always@(negedge ck)if(rst_n)begin
      if(fixture_active)begin
        ri=0;
        if(cyc==reply_due)begin ri[0]=1;ri[3:1]=7;ri[16:13]=reply_type;ri[54:21]=reply_data;end
      end
      if(ro[0])begin
       if(ro[3:1]==7)begin
        if(ro[16:13]==2)begin
         nseed=nseed+1;fixture_active=1;reply_due=cyc+10;reply_type=5;reply_data=0;
         if(ro[21+4+:21]!=50000 || ro[21+25+:21]!=1 || ro[21+46+:21]!=0 || ro[21+67+:10]!=0)$fatal(1,"SEED ring payload mismatch");
         $display("MTP_RING SEED cycle%0d",cyc);
        end else if(ro[16:13]==3)begin
         jj=ro[21+80+21+:3];ndh=ndh+1;
         if(jj!=ndh||ro[21+80+24+:10]!=0||ro[21+80+:21]!=(jj==1?50000:99+jj))$fatal(1,"DHSTEP ring payload mismatch step%0d",jj);
         reply_due=cyc+10;reply_type=4;reply_data={10'd0,3'(jj),21'(100+jj)};
         $display("MTP_RING DHSTEP j%0d cycle%0d",jj,cyc);
        end else $fatal(1,"unexpected outgoing draft ring type");
       end else if(ro[3:1]==5)begin
        if(ro[21+16+:4]==4)begin
         ndraft=ndraft+1;
         if(ro[21+248+:3]!=5)$fatal(1,"DRAFT count mismatch");
         for(integer q=0;q<5;q=q+1)if(ro[21+256+21*q+:21]!=101+q)$fatal(1,"DRAFT token mismatch");
        end else if(ro[21+16+:4]==2)begin
         ntok=ntok+1;
         if(ro[21+61+:21]!=50000||ro[21+82+:32]!=32'h40400000||ro[21+40+:21]!=0)$fatal(1,"held RESULT changed after draft chain");
        end else $fatal(1,"unexpected token flit type");
       end else $fatal(1,"unexpected stage kind");
      end
      if(htx_v[0])nres=nres+1;
    end
    // ---------------------------------------------------------------- one position
    integer b, k, perm [0:79], t, tmp;
    reg [80:0] ownrec;
    task position(input [20:0] pos, input [16:0] nrow, input [31:0] nbits, input [16:0] srow, input [31:0] sbits,
                  input [16:0] r0, input [31:0] b0, input [16:0] r1, input [31:0] b1, input [16:0] r2, input [31:0] b2);
        integer g0;
        begin
            for (k = 0; k < 5120; k = k + 1) xv[k] = $urandom;
            for (k = 0; k < 80; k = k + 1) perm[k] = k;
            for (k = 79; k > 0; k = k - 1) begin t = $urandom % (k + 1); tmp = perm[k]; perm[k] = perm[t]; perm[t] = tmp; end
            for (b = 0; b < 80; b = b + 1) begin
                ri = 0; ri[0] = 1; ri[3:1] = 3'd2; ri[8:4] = 5'd1; ri[20:13] = perm[b][7:0];
                for (k = 0; k < 64; k = k + 1) ri[21 + 16*k +: 16] = xv[64*perm[b] + k];
                mu_rt = {1'b1, 10'd0, pos};
                tick; ri = 0; mu_rt = 0;
                if (b % 3 == 0) tick;
            end
            g0 = nstream;
            while (nstream == g0) tick;
            repeat (NSL + 200) tick;
            sn_i=0;sn_i[514]=1;
            sn_i[531:515]=(nrow<srow)?nrow:srow;sn_i[563:532]=(nrow<srow)?nbits:sbits;
            tick;sn_i=0;
            while (mtx_v == 6'd0) tick;
            if (mtx_v != 6'h3F) fail("BEST not on all mesh lanes");
            ownrec = mtx_d[16 +: 81];
            if (mtx_d[3:0] != 4'd1 || mtx_d[5:4] != 2'd1 || ownrec[0] != 1'b1 || ownrec[80:60] != pos || ownrec[59:50] != 10'd0)
                fail("own BEST frame header / tag");
            for (k = 1; k < 6; k = k + 1) if (mtx_d[k*FW +: FW] != mtx_d[0 +: FW]) fail("mesh lanes differ");
            // peers: pair p lanes 2p / 2p+1, copies at different delays
            for (k = 0; k < 6; k = k + 1) begin
                repeat (3 + k) tick;
                mrx_v = 0; mrx_v[k] = 1;
                mrx_d[k*FW +: FW] = {1'b1, 455'd0, pos, 10'd0, (k < 2) ? b0 : (k < 4) ? b1 : b2, (k < 2) ? r0 : (k < 4) ? r1 : r2, 1'b1, 8'd0, 2'd0, 2'(k/2 + 2), 4'd1};
                tick; mrx_v = 0;
            end
            repeat (300) tick;
        end
    endtask
    initial begin
        repeat(10)tick;rst_n=1;repeat(20)tick;
        csrw(0,1);csrw(1,8);csrw(2,1);csrw(3,4);csrw(4,1000);csrw(5,16'h0201);
        csrw(9,{32'd0,16'd200,16'd12000});csrw(10,10000);csrw(8,1);
        repeat(20)tick;start_i=1;
        exp_row=50000;exp_bits=32'h40400000;exp_pos=0;
        position(0,5,32'h40200000,9,32'h40200000,2000,32'h40200000,50000,32'h40400000,7,32'hc0000000);
        repeat(1500)tick;
        if(nstream!=1||nseed!=1||ndh!=5||ndraft!=1||ntok!=1||nres!=2||job||ctl_f||errs)
          $fatal(1,"MTP ring incomplete streams%0d seed%0d dh%0d draft%0d token%0d host%0d job%b fault%b err%0d",nstream,nseed,ndh,ndraft,ntok,nres,job,ctl_f,errs);
        $display("PASS hd_ctl_mtp_ring realSEQ seed1 DHSTEP5 DHRES5 DRAFT1 heldRESULT1; fixtureDHRES only, not Markov numeric proof");$finish;
    end
    initial begin #2000000; $display("FAIL hd_ctl timeout"); $finish; end
endmodule
