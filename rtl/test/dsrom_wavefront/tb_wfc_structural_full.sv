`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_wf_ctrl_equiv: equivalence bench of a wavefront package controller
// implementation (`WF_DUT`, e.g. ot_rom_pkg_ctrl_wfc) against the reference
// rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv, each in its own copy of the same
// deterministic environment, at WAVE = 1.
//
// SOURCE = 1: the environment is the source package's core (level done after a
//   per-job latency), the rest of the array as an in-order pipeline that turns
//   every outbound HIDDEN header into a RESULT (argmax) after a delay, and the
//   known-token table (prompt + draft blocks, some drafts corrupted).  A job's
//   argmax is the golden next token when its whole lineage (its input token and
//   the job of the previous position it extends) is golden, a wrong token
//   otherwise -- so a wrongly verified draft would surface as a wrong committed
//   token.  Checks: every committed token (tok_valid) equals the golden next
//   token, positions commit in order per user, every user finishes, no
//   proto_fault.
// SOURCE = 0: the environment sends HIDDEN messages per user with positions that
//   advance and REWIND by up to WIN (re-issue after a rejection), plus rare
//   illegal rewinds (fault expected), payload flits, link back-pressure.
// LOCKSTEP = 1: additionally every output port of the two controllers is
//   compared on every cycle (cycle-identical implementations).
// Pass: "EQUIV PASS" line; any mismatch prints "EQUIV FAIL" and stops.
// ---------------------------------------------------------------------------
`ifndef WF_DUT
`define WF_DUT ot_rom_pkg_ctrl_wf
`endif
module tb_wfc_structural_full;
    parameter integer SOURCE   = 1;
    parameter integer LOCKSTEP = 0;       // SOURCE = 1 with ot_rom_pkg_ctrl_wfc: 0 (its engine retimes events)
    parameter integer MAXU     = 16;
    parameter integer USERS    = 12;
    parameter integer USER_W   = 10;
    parameter integer NW       = 21;
    parameter integer AW       = 30;
    parameter integer VWA      = 15;
    parameter integer FLIT     = 512;
    parameter integer KVW      = 32768;
    parameter integer XWORDS   = 3;
    parameter integer RXWORDS  = 2;
    parameter integer WIN      = 6;
    parameter integer PLEN     = 3;
    parameter integer GEN      = 30;
    parameter integer CLAT     = 20;      // core latency base (cycles)
    parameter integer PDLY     = 60;      // array round trip base (cycles)
    parameter integer SEED     = 1;
    parameter integer MAXCYC   = 2000000;
    parameter integer NJOBS    = 3000;    // SOURCE = 0: HIDDEN messages to send
    parameter integer FDLY     = 4;       // the DUT may latch a header-position fault this many cycles later
    parameter integer RSTD     = 1;       // the DUT releases reset this many cycles after rst_n (the reference is fed it delayed)

    reg clk = 1'b0, rst_n = 1'b0;
    always #0.5 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    initial begin
        repeat (5) @(posedge clk);
        rst_n <= 1'b1;
    end

    localparam integer UCW = (MAXU > 255) ? $clog2(MAXU+1) : 8;
    localparam integer HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32, HDR_POS = 40, HDR_IDX = HDR_POS + NW,
                       HDR_VAL = HDR_IDX + NW, HDR_TOK = HDR_VAL + 32, HDR_ADDR = HDR_TOK + NW,
                       HDR_USER_HI = HDR_ADDR + 16;
    localparam integer NOUT = 2 + FLIT + 1 + 1 + NW + NW + USER_W + AW + 1 + VWA + FLIT + 1 + VWA + 1 + USER_W
                              + NW + 4 + 1 + 1 + USER_W + NW + NW + UCW + 1 + 3;

    // deterministic hashes
    function automatic [31:0] h32(input [31:0] a, input [31:0] b, input [31:0] c);
        reg [31:0] x;
        begin
            x = a * 32'h9E3779B1 ^ (b + 32'h7F4A7C15) * 32'h85EBCA77 ^ (c + SEED) * 32'hC2B2AE3D;
            x = x ^ (x >> 15); x = x * 32'h2C1B3C6D; x = x ^ (x >> 12); x = x * 32'h297A2D39; x = x ^ (x >> 15);
            h32 = x;
        end
    endfunction
    function automatic [NW-1:0] gold(input integer u, input integer p);   // golden token at position p
        gold = NW'(h32(u, p, 32'h601D));
    endfunction

    wire [NOUT-1:0] o0, o1;
    wire [UCW-1:0] d0, d1;
    integer ok_n [0:2];
    integer err_n [0:2];
    integer rej_n [0:2];
    integer sq_n [0:2];
    integer iss_n [0:2];
    integer fin_cyc [0:2];
    integer sent_n [0:2];
    integer lead_q[0:2];
    initial for(integer n=0;n<3;n=n+1)lead_q[n]=0;
    always @(negedge clk)for(integer n=0;n<3;n=n+1)lead_q[n]=sent_n[n];

    genvar gi;
    generate for (gi = 0; gi < 3; gi = gi + 1) begin : g
        // ---- controller
        wire in_ready, out_valid, out_last, core_start, core_busy, tok_valid, proto_fault, vm_we, vm_re, pr_re;
        wire wf_issue, wf_reject, wf_squash;
        wire [FLIT-1:0] out_data, vm_wdata;
        wire [NW-1:0] core_token, core_pos, pr_pos, tok_pos, tok_id;
        wire [USER_W-1:0] core_user, pr_user, tok_user;
        wire [AW-1:0] kv_base;
        wire [VWA-1:0] vm_waddr, vm_raddr;
        wire [3:0] pr_blk;
        wire [UCW-1:0] users_done;
        reg in_valid = 1'b0, in_last = 1'b0, out_ready = 1'b0, core_done = 1'b0, pr_qk = 1'b0;
        reg [FLIT-1:0] in_data = 0, vm_rq = 0;
        reg [NW-1:0] pr_q = 0, core_next_token = 0;
        reg [31:0] core_next_val = 0;
        wire [UCW-1:0] cfg_users = USERS;
        wire [NW-1:0] cfg_prompt_len = PLEN, cfg_gen_len = GEN;
        reg [RSTD:0] rsh = 0;
        always @(posedge clk) rsh <= {rsh[RSTD-1:0], rst_n};
        wire rst_n_ref = rsh[RSTD-1];
        if (gi == 0) begin : r
            // Qualify the reference's admission by its actual delayed reset.
            // All active-cycle observations/checkers below remain identical.
            wire raw_in_ready;
            assign in_ready = rst_n_ref && raw_in_ready;
            ot_rom_pkg_ctrl_wf #(.WAVE(1), .WIN(WIN), .PKG_ID(0), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(VWA),
                .USER_W(USER_W), .MAXU(MAXU), .KVW(KVW), .XWORDS(XWORDS), .RXWORDS(RXWORDS), .SOURCE(SOURCE),
                .SEND_HIDDEN(1), .HID_DEST(1), .FWD_TOKEN(1)) c (.rst_n(rst_n_ref), .in_ready(raw_in_ready), .*);
        end else begin : d
            ot_rom_pkg_ctrl_wfc #(.DECODED_READ(gi==2),.CONTROL_PIPE(gi==2),
                .QUEUE_SHIFT(gi==2),.HEADER_LOCAL(gi==2),.PREFIX_INC(gi==2),.WAVE(1), .WIN(WIN), .PKG_ID(0), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(VWA),
                .USER_W(USER_W), .MAXU(MAXU), .KVW(KVW), .XWORDS(XWORDS), .RXWORDS(RXWORDS), .SOURCE(SOURCE),
                .SEND_HIDDEN(1), .HID_DEST(1), .FWD_TOKEN(1)) c (.*);
        end
        wire [NOUT-1:0] obs = {in_ready, out_valid, out_data, out_last, core_start,
                               core_start ? core_token : {NW{1'b0}}, core_start ? core_pos : {NW{1'b0}},
                               core_user, kv_base, vm_we, vm_we ? vm_waddr : {VWA{1'b0}}, vm_wdata, vm_re,
                               vm_re ? vm_raddr : {VWA{1'b0}}, pr_re, pr_re ? pr_user : {USER_W{1'b0}},
                               pr_re ? pr_pos : {NW{1'b0}}, pr_re ? pr_blk : 4'd0, core_busy, tok_valid,
                               tok_valid ? tok_user : {USER_W{1'b0}}, tok_valid ? tok_pos : {NW{1'b0}},
                               tok_valid ? tok_id : {NW{1'b0}}, users_done, 1'b0,
                               wf_issue, wf_reject, wf_squash};   // proto_fault: checked below (FDLY)

        // ---- core: level done, per-job latency
        reg [FLIT-1:0] vm_mem[0:XWORDS-1];
        initial for(integer m=0;m<XWORDS;m=m+1)vm_mem[m]=0;
        integer cbusy = 0;
        always @(posedge clk) begin
            if (SOURCE) vm_rq <= {FLIT/32{h32(vm_raddr, cyc, 32'h77)}};
            else begin
                if(vm_we) begin
                    if(vm_waddr>=XWORDS)$fatal(1,"VM write outside real fixture word store");
                    vm_mem[vm_waddr] <= vm_wdata;
                end
                if(vm_re)begin
                    if(vm_raddr>=XWORDS)$fatal(1,"VM read outside real fixture word store");
                    vm_rq <= vm_mem[vm_raddr];
                end
            end
            if (core_start) begin
                core_done <= 1'b0;
                cbusy <= CLAT + (h32(core_user, core_pos, 32'hC0) % 13);
                core_next_token <= NW'(h32(core_user, core_pos, 32'h11));
                core_next_val <= h32(core_user, core_pos, 32'h12);
            end else if (cbusy > 1) cbusy <= cbusy - 1;
            else if (cbusy == 1) begin cbusy <= 0; core_done <= 1'b1; end
            out_ready <= (h32(cyc, 0, 32'h0B) % 7) != 0;
        end

        // ---- known-token table (SOURCE): prompt, then per draft block a range of drafts
        always @(posedge clk) if (pr_re) begin
            if (pr_pos < PLEN) {pr_qk, pr_q} <= {1'b1, gold(pr_user, pr_pos)};
            else if (pr_blk < 4'd12 && pr_pos < PLEN + 4 * (pr_blk + 1) + (h32(pr_user, pr_blk, 32'hB1) % 5)) begin
                pr_qk <= 1'b1;
                pr_q <= (h32(pr_user, pr_pos, {28'd0, pr_blk}) % 5 == 0) ? gold(pr_user, pr_pos) ^ 21'h1
                                                                          : gold(pr_user, pr_pos);
            end else begin
                pr_qk <= 1'b0; pr_q <= NW'(h32(pr_user, pr_pos, 32'hDEAD));
            end
        end

        if (SOURCE) begin : src
            // ---- outbound: HIDDEN headers into the array pipe (in order)
            integer ox = 0;                         // payload flits still to skip
            reg [USER_W-1:0] pu [0:1023];
            reg [NW-1:0]     pp [0:1023];
            reg              pok [0:1023];
            integer          pt [0:1023];
            integer pw = 0, prd = 0;
            reg okmap [0:MAXU-1][0:255];           // lineage golden: last issue of (user, pos)
            reg [USER_W-1:0] hu; reg [NW-1:0] hp, ht; reg lineage;
            integer lastt = 0;
            always @(posedge clk) if (rst_n && out_valid && out_ready) begin
                if (ox == 0) begin
                    hu = USER_W'(out_data[HDR_USER +: 8]) | (USER_W'(out_data[HDR_USER_HI +: (USER_W-8)]) << 8);
                    hp = out_data[HDR_POS +: NW]; ht = out_data[HDR_TOK +: NW];
                    lineage = (ht == gold(hu, hp)) && (hp == 0 || okmap[hu][hp-1]);
                    okmap[hu][hp] = lineage;
                    pu[pw % 1024] = hu; pp[pw % 1024] = hp; pok[pw % 1024] = lineage;
                    lastt = (cyc + PDLY + (h32(hu, hp, 32'hD1) % 40) > lastt) ? cyc + PDLY + (h32(hu, hp, 32'hD1) % 40) : lastt + 1;
                    pt[pw % 1024] = lastt;
                    pw = pw + 1;
                    ox = out_last ? 0 : XWORDS;
                end else ox = ox - 1;
            end
            // ---- inbound: RESULT headers
            always @(posedge clk) begin
                if (in_valid && in_ready) begin in_valid <= 1'b0; prd <= prd + 1; end
                else if (!in_valid && prd < pw && pt[prd % 1024] <= cyc) begin
                    in_valid <= 1'b1; in_last <= 1'b1;
                    in_data <= 0;
                    in_data[HDR_TYPE +: 4] <= 4'd2;
                    in_data[HDR_USER +: 8] <= pu[prd % 1024][7:0];
                    in_data[HDR_USER_HI +: (USER_W-8)] <= pu[prd % 1024] >> 8;
                    in_data[HDR_POS +: NW] <= pp[prd % 1024];
                    in_data[HDR_IDX +: NW] <= pok[prd % 1024] ? gold(pu[prd % 1024], pp[prd % 1024] + 1)
                                                              : gold(pu[prd % 1024], pp[prd % 1024] + 1) ^ 21'h155;
                    in_data[HDR_VAL +: 32] <= h32(pu[prd % 1024], pp[prd % 1024], 32'hA1);
                end
            end
        end else begin : stg
            // ---- inbound: HIDDEN messages, per-user positions with rewinds
            integer upn [0:MAXU-1];
            integer sent = 0, left = 0;
            reg [USER_W-1:0] su; integer sp;
            initial for (int k = 0; k < MAXU; k++) upn[k] = 0;
            always @(posedge clk) if (rst_n) begin
                if (in_valid && in_ready) begin
                    if (left == 0) in_valid <= 1'b0;
                    else begin
                        in_data <= {FLIT/32{h32(sent, left, 32'hF1)}};
                        in_last <= (left == 1);
                        left <= left - 1;
                    end
                end
                if ((!in_valid || (in_ready && left == 0)) && sent < NJOBS && sent < lead_q[(gi+1)%3]+2 && sent < lead_q[(gi+2)%3]+2 && (h32(cyc, 1, 32'h5E) % 3 != 0)) begin
                    su = h32(sent, 0, 32'h05) % USERS;
                    sp = upn[su];
                    if (sp > 0 && h32(sent, 2, 32'h06) % 6 == 0) sp = sp - 1 - (h32(sent, 3, 32'h07) % WIN);
                    if (sent > NJOBS - 50 && h32(sent, 4, 32'h08) % 8 == 0) sp = sp + 3;   // illegal (fault)
                    if (sp < 0) sp = 0;
                    upn[su] = sp + 1;
                    in_valid <= 1'b1; in_last <= 1'b0; left <= RXWORDS;
                    in_data <= 0;
                    in_data[HDR_TYPE +: 4] <= 4'd1;
                    in_data[HDR_LEN +: 8] <= RXWORDS;
                    in_data[HDR_USER +: 8] <= su[7:0];
                    in_data[HDR_USER_HI +: (USER_W-8)] <= su >> 8;
                    in_data[HDR_POS +: NW] <= sp;
                    in_data[HDR_IDX +: NW] <= h32(sent, 5, 0);
                    in_data[HDR_VAL +: 32] <= h32(sent, 6, 0);
                    in_data[HDR_TOK +: NW] <= h32(sent, 7, 0);
                    sent = sent + 1; sent_n[gi] = sent;
                end
            end
        end

        // ---- checks: committed tokens (SOURCE)
        integer nextp [0:MAXU-1];
        initial begin
            for (int k = 0; k < MAXU; k++) nextp[k] = 0;
            ok_n[gi] = 0; sent_n[gi] = 0; err_n[gi] = 0; rej_n[gi] = 0; sq_n[gi] = 0; iss_n[gi] = 0; fin_cyc[gi] = 0;
        end
        always @(posedge clk) if (rst_n) begin
            if (wf_reject) rej_n[gi] = rej_n[gi] + 1;
            if (wf_squash) sq_n[gi] = sq_n[gi] + 1;
            if (core_start) iss_n[gi] = iss_n[gi] + 1;
            if (SOURCE && tok_valid) begin
                if (tok_pos != nextp[tok_user] || tok_id != gold(tok_user, tok_pos + 1)) begin
                    err_n[gi] = err_n[gi] + 1;
                    if (err_n[gi] < 5) $display("EQUIV FAIL inst %0d cyc %0d: user %0d pos %0d tok %0d (exp pos %0d tok %0d)",
                                               gi, cyc, tok_user, tok_pos, tok_id, nextp[tok_user], gold(tok_user, tok_pos + 1));
                end else ok_n[gi] = ok_n[gi] + 1;
                nextp[tok_user] = tok_pos + 1;
            end
            if (SOURCE && users_done == USERS && fin_cyc[gi] == 0) fin_cyc[gi] = cyc;
        end
    end endgenerate

    assign o0 = g[0].obs;
    assign o1 = g[1].obs;
    integer mism = 0;
    always @(posedge clk) if (rst_n && !SOURCE && o0 !== o1) begin
        mism = mism + 1;
        if (mism < 4) $display("EQUIV FAIL lockstep cyc %0d: outputs differ (xor %h)", cyc, o0 ^ o1);
    end

    // Finite exact event joins: packet lead <=2, one pending packet and
    // one active packet imply <=4*(XWORDS+1) flits. No digest-only checker.
    localparam integer JOIN_CAP=1 << $clog2(4*(XWORDS+1)+1);
    localparam integer EW=FLIT+VWA+1;
    reg [EW-1:0] write_ev[0:2][0:JOIN_CAP-1];
    reg [EW-1:0] output_ev[0:2][0:JOIN_CAP-1];
    reg [EW-1:0] launch_ev[0:2][0:JOIN_CAP-1];
    integer wn[0:2],on[0:2],ln[0:2];
    integer wc=0,oc=0,lc=0;
    integer header_n[0:2],first_fault_header[0:2];
    integer fault_cyc[0:2];
    integer pipe_internal_launch=-1,pipe_qual=-1,last_write=-1;
    integer launch_checks=0,completion_checks=0,received_plus2=0;
    integer received_wait_max=0,reset_root=-1,reset_rx=-1;
    initial for(integer n=0;n<3;n=n+1)begin
        wn[n]=0;on[n]=0;ln[n]=0;header_n[n]=0;first_fault_header[n]=0;fault_cyc[n]=0;
    end
    generate for(gi=0;gi<3;gi=gi+1)begin: g_exact_events
        if(!SOURCE)begin:g_header_count
          always @(posedge clk)if(rst_n&&g[gi].in_valid&&g[gi].in_ready&&g[gi].stg.left==RXWORDS)header_n[gi]=header_n[gi]+1;
        end
        always @(posedge clk) if(rst_n)begin
            if(g[gi].proto_fault && fault_cyc[gi]==0)begin
                fault_cyc[gi]=cyc;first_fault_header[gi]=header_n[gi];
            end
            if(!SOURCE)begin
                if(g[gi].vm_we)begin
                    if(wn[gi]-wc>=JOIN_CAP)$fatal(1,"finite VM event join overrun");
                    write_ev[gi][wn[gi]%JOIN_CAP]={g[gi].vm_waddr,g[gi].vm_wdata,1'b0};wn[gi]=wn[gi]+1;
                end
                if(g[gi].out_valid&&g[gi].out_ready)begin
                    if(on[gi]-oc>=JOIN_CAP)$fatal(1,"finite output event join overrun");
                    output_ev[gi][on[gi]%JOIN_CAP]={{VWA{1'b0}},g[gi].out_data,g[gi].out_last};on[gi]=on[gi]+1;
                end
                if(g[gi].core_start)begin
                    if(ln[gi]-lc>=JOIN_CAP)$fatal(1,"finite launch event join overrun");
                    launch_ev[gi][ln[gi]%JOIN_CAP]={g[gi].core_user,g[gi].core_pos,g[gi].core_token,g[gi].kv_base};ln[gi]=ln[gi]+1;
                end
            end
        end
    end endgenerate
    // Calendar checks bind to actual qualified RTL events, including stalls.
    always @(posedge clk)if(rst_n)begin
        if(g[2].d.c.start_i)pipe_internal_launch=cyc;
        if(g[2].core_start)begin
            if(cyc-pipe_internal_launch!=1)$fatal(1,"fullshape launch capture must add exactly one edge");
            launch_checks=launch_checks+1;
            if(!SOURCE)begin
                if(cyc-last_write<2)$fatal(1,"received launch preceded +2 edge minimum");
                if(cyc-last_write==2)received_plus2=received_plus2+1;
                if(cyc-last_write>received_wait_max)received_wait_max=cyc-last_write;
            end
        end
        if(g[2].d.c.completion_qual && !g[2].d.c.g_control_completion.v)pipe_qual=cyc;
        if(g[2].d.c.job_done)begin
            if(cyc-pipe_qual!=1)$fatal(1,"fullshape completion must add exactly one edge");
            completion_checks=completion_checks+1;
        end
        if(!SOURCE && g[2].vm_we && g[2].vm_waddr==RXWORDS-1)last_write=cyc;
    end
    always @(negedge clk)begin
        if(g[2].d.c.rst_q && reset_root<0)reset_root=cyc;
        if(g[2].d.c.rx_enable && reset_rx<0)begin
            reset_rx=cyc;
            if(reset_rx-reset_root!=1)$fatal(1,"fullshape RX reset admission must add exactly one edge");
        end
        if(!SOURCE)begin
            while(wc<wn[0]&&wc<wn[1]&&wc<wn[2])begin
                if(write_ev[0][wc%JOIN_CAP]!==write_ev[1][wc%JOIN_CAP]||write_ev[0][wc%JOIN_CAP]!==write_ev[2][wc%JOIN_CAP])$fatal(1,"fullshape exact VM write mismatch ordinal%0d",wc);
                wc=wc+1;
            end
            while(oc<on[0]&&oc<on[1]&&oc<on[2])begin
                if(output_ev[0][oc%JOIN_CAP]!==output_ev[1][oc%JOIN_CAP]||output_ev[0][oc%JOIN_CAP]!==output_ev[2][oc%JOIN_CAP])$fatal(1,"fullshape exact outbound flit mismatch ordinal%0d",oc);
                oc=oc+1;
            end
            while(lc<ln[0]&&lc<ln[1]&&lc<ln[2])begin
                if(launch_ev[0][lc%JOIN_CAP]!==launch_ev[1][lc%JOIN_CAP]||launch_ev[0][lc%JOIN_CAP]!==launch_ev[2][lc%JOIN_CAP])$fatal(1,"fullshape exact launch tuple mismatch ordinal%0d",lc);
                lc=lc+1;
            end
        end
    end
    initial begin
        wait(rst_n);
        while(!(SOURCE ? (fin_cyc[0]!=0&&fin_cyc[1]!=0&&fin_cyc[2]!=0):
            (sent_n[0]>=NJOBS&&sent_n[1]>=NJOBS&&sent_n[2]>=NJOBS&&
             !g[0].in_valid&&!g[1].in_valid&&!g[2].in_valid&&
             !g[0].core_busy&&!g[1].core_busy&&!g[2].core_busy&&
             !g[0].out_valid&&!g[1].out_valid&&!g[2].out_valid)))@(negedge clk);
        repeat(50)@(negedge clk);
        for(integer n=0;n<3;n=n+1)begin
            $display("STRUCTURAL_STATS source=%0d inst=%0d MAXU=%0d USERS=%0d cycles=%0d fin=%0d issues=%0d committed=%0d errors=%0d rejects=%0d squash=%0d fault_cycle=%0d fault_header=%0d",SOURCE,n,MAXU,USERS,cyc,fin_cyc[n],iss_n[n],ok_n[n],err_n[n],rej_n[n],sq_n[n],fault_cyc[n],first_fault_header[n]);
            if(err_n[n] || (SOURCE && (fin_cyc[n]==0||fault_cyc[n]!=0||ok_n[n]!=USERS*(PLEN+GEN-1))))$fatal(1,"fullshape committed token oracle failed");
        end
        $display("STRUCTURAL_CALENDAR source=%0d launch_checks=%0d completion_checks=%0d received_plus2=%0d received_wait_max=%0d reset_release_delta=%0d VM_exact=%0d flit_exact=%0d launch_exact=%0d default_off_cycle_mism=%0d",SOURCE,launch_checks,completion_checks,received_plus2,received_wait_max,reset_rx-reset_root,wc,oc,lc,mism);
        if(mism || launch_checks!=iss_n[2] || completion_checks!=iss_n[2] || reset_rx-reset_root!=1)$fatal(1,"default-off or fullshape calendar checks failed");
        if(!SOURCE && (wc!=NJOBS*RXWORDS||oc!=NJOBS*(XWORDS+1)||lc!=NJOBS||
            wn[0]!=wn[1]||wn[1]!=wn[2]||on[0]!=on[1]||on[1]!=on[2]||
            first_fault_header[0]!=first_fault_header[1]||first_fault_header[1]!=first_fault_header[2]||
            received_plus2==0))$fatal(1,"fullshape finite exact join/count/fault ordinal failed");
        $display("STRUCTURAL_FULL PASS");$finish;
    end
endmodule
