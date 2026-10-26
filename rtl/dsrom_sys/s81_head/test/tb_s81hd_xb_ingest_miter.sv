`timescale 1ns/1ps
// HD-CTL 10-21: minimal smoke bench of ot_s81hd_ctl (Verilator 5.050 --binary --timing).
//   CSR writes on host lane 1 -> 80 tagged XB beats on ri (shuffled gidx order, gaps) -> bus B stream on sn_o / ss_o:
//   go + null best, slice m (xa word m mod 256, xb word m mod 64) at G + 5 + m for every m, xv window exact ->
//   fake N / S returns -> own BEST frame on the 6 mesh lanes -> fake peer BEST frames (both copies of each pair) ->
//   merged token flit through dsfd_mtp_seq -> ro (kind K_TOK) + host lane 0 RESULT frame; no fault.
//   Position 0: a peer wins strictly.  Position 1: all four logits equal -> the lowest row id wins.
// Verdict line: "PASS hd_ctl" / "FAIL hd_ctl <reason>".
module tb_s81hd_ctl;
 parameter integer MUT=0;
 parameter integer TAGGED=1;
 localparam[9:0]USER_ID=TAGGED?10'd777:10'd0;
    wire xgo,xxv,xbusy,xdone,xfault,xready,xactive,xlv,xfwd;
    wire[6:0] xidx;wire[1023:0] xdata;wire[31:0] xtag,xmessage;
    wire[1103:0] xfstage;wire[255:0] xxa,xxb;wire[7:0] xevents;
    reg load_permission=1,allow_invalid=0,expected_active=0,last_retire=0;
    wire retire_token=ro[0]&&ro[3:1]==3'd5;
    wire[30:0] retire_identity={ro[21+40+:21],ro[21+151+:2],ro[21+32+:8]};
    ot_s81hd_xb_ingest #(.SK(8),.MUT_MODE(MUT)) probe(
      .ck(ck),.rst_pin_n(dut.rr[0]),.rst_meta_n(dut.rr[1]),
      .rst_job_n(dut.rr[3]),.rst_replay_n(dut.rr[2]),
      .stage_i(ri),.stage_tag_i(mu_rt),.untagged_position_i(dut.upos),
      .admit_load_i(load_permission),.issue_i(dut.go2),
      .retire_i(retire_token),.retire_identity_i(retire_identity),
      .load_valid_o(xlv),.load_index_o(xidx),.load_data_o(xdata),.load_tag_o(xtag),
      .forward_valid_o(xfwd),.forward_stage2_o(xfstage),.message_tag_o(xmessage),
      .loaded_ready(xready),.job_active(xactive),.go(xgo),.xv(xxv),
      .replay_busy(xbusy),.replay_done(xdone),.xa(xxa),.xb(xxb),
      .fault(xfault),.fault_events(xevents));
    integer ingest_words=0,paired_slices=0,protected_tail=0;
    always @(negedge ck) if(rst_n&&dut.rr[0]&&dut.rr[1]&&dut.rr[2]&&dut.rr[3]) begin
      if(xlv!==dut.wv2 || xfwd!==dut.f2v) $fatal(1,"XB landing valid mismatch");
      if(xlv)begin
        if({xidx,xdata,xtag}!=={dut.wa2,dut.wd2,dut.t2})
          $fatal(1,"XB landed index/data/tag mismatch");
        ingest_words=ingest_words+1;
      end
      if(!allow_invalid)begin
        if(probe.count!=0 && xmessage!=={dut.mt_v,dut.mt_tag})
          $fatal(1,"XB identity mismatch");
        if(xgo!==sn_o[512] || xxv!==sn_o[513])$fatal(1,"XB public GO/stream age mismatch");
        if(xxv)begin
          if({xxb,xxa}!==sn_o[511:0])$fatal(1,"XB indexed payload mismatch");
          paired_slices=paired_slices+1;
        end
        if(xgo)expected_active=1;
        if(last_retire)expected_active=0;
        if(xactive!==expected_active)$fatal(1,"XB job retired before token identity");
        last_retire=retire_token;
        if(expected_active&&!xbusy)protected_tail=protected_tail+1;
        if(xfault)$fatal(1,"XB unexpected protocol fault");
      end
    end

    localparam integer FW = 553, NSL = 8192 + 7 * 8;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rst_n = 0;
    reg [1103:0] ri = 0; reg [31:0] mu_rt = 0; reg [10:0] lw = 0; reg lep_f = 0;
    wire [1103:0] ro; wire [33:0] mu_c; wire [10:0] mu_rc; wire ctl_f;
    wire [564:0] sn_o, ss_o; reg [564:0] sn_i = 0, ss_i = 0;
    wire [5:0] mtx_v; wire [6*FW-1:0] mtx_d; reg [5:0] mrx_v = 0; reg [6*FW-1:0] mrx_d = 0;
    wire [1:0] htx_v; wire [2*FW-1:0] htx_d; reg [1:0] hrx_v = 0; reg [2*FW-1:0] hrx_d = 0;
    wire [4:0] dtx_v; wire [5*FW-1:0] dtx_d; reg [4:0] drx_v = 0; reg [5*FW-1:0] drx_d = 0;
    ot_s81hd_ctl dut (.ck(ck), .rst_n(rst_n), .ri(ri), .mu_rt(mu_rt), .lw(lw), .lep_f(lep_f), .ro(ro), .mu_c(mu_c),
        .mu_rc(mu_rc), .ctl_f(ctl_f), .sn_o(sn_o), .ss_o(ss_o), .sn_i(sn_i), .ss_i(ss_i),
        .mtx_v(mtx_v), .mtx_d(mtx_d), .mrx_v(mrx_v), .mrx_d(mrx_d), .mflt(24'd0),
        .htx_v(htx_v), .htx_d(htx_d), .hrx_v(hrx_v), .hrx_d(hrx_d), .hflt(8'd0),
        .dtx_v(dtx_v), .dtx_d(dtx_d), .drx_v(drx_v), .drx_d(drx_d), .dflt(20'd0));
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
        if (ctl_f && !allow_invalid) fail("ctl fault");
    end
    // ---------------------------------------------------------------- token / RESULT monitor
    integer ntok = 0, nres = 0;
    reg [16:0] exp_row; reg [31:0] exp_bits; reg [20:0] exp_pos;
    always @(negedge ck) if (rst_n) begin
        if (ro[0]) begin
            if (ro[3:1] != 3'd5) fail("ro beat is not a token");
            if (ro[21 +: 16] != 16'h0201 || ro[21+16 +: 4] != 4'd2) fail("token flit header");
            if (ro[21+61 +: 21] != {4'd0, exp_row} || ro[21+82 +: 32] != exp_bits || ro[21+40 +: 21] != exp_pos)
                begin $display("  got row %0d bits %h pos %0d exp row %0d bits %h", ro[21+61 +: 21], ro[21+82 +: 32], ro[21+40 +: 21], exp_row, exp_bits); fail("token value"); end
            ntok = ntok + 1;
        end
        if (htx_v[0]) begin
            if (htx_d[3:0] != 4'd9 || htx_d[16+61 +: 21] != {4'd0, exp_row}) fail("host RESULT frame");
            nres = nres + 1;
        end
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
                mu_rt = {1'(TAGGED), 10'd777, pos};
                tick; ri = 0; mu_rt = 0;
                if (b % 3 == 0) tick;
            end
            g0 = nstream;
            while (nstream == g0) tick;
            repeat (NSL + 200) tick;
            sn_i = 0; sn_i[514] = 1; sn_i[531:515] = nrow; sn_i[563:532] = nbits; tick; sn_i = 0;
            repeat (37) tick;
            ss_i = 0; ss_i[514] = 1; ss_i[531:515] = srow; ss_i[563:532] = sbits; tick; ss_i = 0;
            while (mtx_v == 6'd0) tick;
            if (mtx_v != 6'h3F) fail("BEST not on all mesh lanes");
            ownrec = mtx_d[16 +: 81];
            if (mtx_d[3:0] != 4'd1 || mtx_d[5:4] != 2'd1 || ownrec[0] != 1'b1 || ownrec[80:60] != pos || ownrec[59:50] != USER_ID)
                fail("own BEST frame header / tag");
            for (k = 1; k < 6; k = k + 1) if (mtx_d[k*FW +: FW] != mtx_d[0 +: FW]) fail("mesh lanes differ");
            // peers: pair p lanes 2p / 2p+1, copies at different delays
            for (k = 0; k < 6; k = k + 1) begin
                repeat (3 + k) tick;
                mrx_v = 0; mrx_v[k] = 1;
                mrx_d[k*FW +: FW] = {1'b1, 455'd0, pos, USER_ID, (k < 2) ? b0 : (k < 4) ? b1 : b2, (k < 2) ? r0 : (k < 4) ? r1 : r2, 1'b1, 8'd0, 2'd0, 2'(k/2 + 2), 4'd1};
                tick; mrx_v = 0;
            end
            repeat (300) tick;
        end
    endtask
    initial begin
        repeat (10) tick; rst_n = 1; repeat (20) tick;
        csrw(8'd0, 64'd4); csrw(8'd1, 64'd8); csrw(8'd2, 64'd1); csrw(8'd3, 64'h4); csrw(8'd4, 64'd1000);
        csrw(8'd5, 64'h0201); csrw(8'd8, 64'd1);
        repeat (20) tick;
        // position 0: local best = N row 5 (tie with S row 9 at 2.5 -> lowest id) + base 1000 = 1005; peer pair 1 wins (3.0)
        exp_row = 17'd50000; exp_bits = 32'h4040_0000; exp_pos = 21'd0;
        position(21'd0, 17'd5, 32'h4020_0000, 17'd9, 32'h4020_0000, 17'd2000, 32'h4020_0000, 17'd50000, 32'h4040_0000,
                 17'd7, 32'hC000_0000);
        if (ownrec[17:1] != 17'd1005 || ownrec[49:18] != 32'h4020_0000) fail("local best (N/S final + row base)");
        // position 1: all equal logits (S wins N/S on -0 == +0 tie? no: S row 3 < N row 8) -> own 1003; peers 1200, 1004, 1002
        exp_row = 17'd1002; exp_bits = 32'h0000_0000; exp_pos = 21'd1;
        position(21'd1, 17'd8, 32'h8000_0000, 17'd3, 32'h0000_0000, 17'd1200, 32'h0000_0000, 17'd1004, 32'h8000_0000,
                 17'd1002, 32'h0000_0000);
        if (ownrec[17:1] != 17'd1003) fail("local best tie (lowest id)");
        if (nstream != 2) fail("stream count");
        if (ntok != 2) fail("token count");
        if (nres != 2) fail("host RESULT count");
        if(ingest_words!=160 || paired_slices!=2*NSL || protected_tail==0)
          $fatal(1,"XB missing complete ingestion/stream/token-tail witness");
        $display("XB_NATIVE words=%0d pairs=%0d protected_after_replay=%0d",ingest_words,paired_slices,protected_tail);
        // Invalid duplicate address cannot count as a complete80-beat vector.
        allow_invalid=1;rst_n=0;repeat(10)tick;rst_n=1;repeat(20)tick;
        for(k=0;k<2;k=k+1)begin
          ri=0;ri[0]=1;ri[3:1]=3'd2;ri[20:13]=8'd0;
          mu_rt={1'b1,10'd777,21'd2};tick;ri=0;mu_rt=0;repeat(3)tick;
        end
        if(!xevents[3] || xready)$fatal(1,"XB duplicate accepted as full vector");
        // A changed live identity in a partial message must fault, not alias.
        rst_n=0;repeat(10)tick;rst_n=1;repeat(20)tick;
        for(k=0;k<2;k=k+1)begin
          ri=0;ri[0]=1;ri[3:1]=3'd2;ri[20:13]=8'(k);
          mu_rt={1'b1,10'd777,21'(3+k)};tick;ri=0;mu_rt=0;repeat(3)tick;
        end
        if(!xevents[2] || xready)$fatal(1,"XB identity corruption not rejected");
        $display("XB_INVALID duplicate and mixed identity rejected");
        if (errs == 0) $display("PASS hd_ctl streams %0d tokens %0d slices/stream %0d", nstream, ntok, NSL);
        else $display("FAIL hd_ctl errors %0d", errs);
        $finish;
    end
    initial begin #2000000; $display("FAIL hd_ctl timeout"); $finish; end
endmodule
