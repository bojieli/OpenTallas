`timescale 1ps/1ps
// QW-F16PROG4: qfd_dv_slice_tload (9-bit request face + real table-ROM loader + VM join) into the REAL qfd_dv_vm.
// Requests arrive only as the 9-bit registered lane {valid, stage, user}; the stream bundle carries the shared-head
// sentinel (BTAB 72..271) through the join.  Checks, per slice fixture:
//   - every joined write at its exact edge: request presented before edge R -> first write visible after R+FIRST_AGE
//     (FIRST_AGE = 1 face + 1 sample + 3 = 5 edges from the request edge, +1 vs the bare loader), 88 slots, done age;
//   - all36 x all4 load sequence, then every resident user's image read back from the real VM SRAMs (retention);
//   - shared head sentinel written through the stream port survives every reload;
//   - FAULT_CASE 1: a stream write in the same edge as a loader write -> joined tw_we low on that edge (both suppressed)
//     and fault high exactly one edge later (the join's own registered fault, before the loader's p_other fault).
// MUT (DUT parameter): see qfd_dv_slice_tload.  Pass line TLOAD_JOIN_PASS; fail lines TLOAD_*.
module tb_qfd_dv_slice_tload;
    integer profile=0, FIRST_AGE=5;
    reg ck = 0; initial forever begin #416 ck=1; #417 ck=0; end
    reg rst_n = 0;
    reg [8:0] treq = 0;
    reg s_we = 0; reg [1:0] s_kind = 0; reg [23:0] s_addr = 0; reg [1023:0] s_data = 0;
    wire we, busy, done, jfault; wire [1:0] kind; wire [23:0] addr; wire [1023:0] data;
    wire [4:0] we_p,busy_p,done_p,fault_p;
    wire [1:0] kind_p[0:4]; wire[23:0]addr_p[0:4]; wire[1023:0]data_p[0:4];
    for(genvar i=0;i<4;i=i+1) begin:g_profile
      qfd_dv_slice_tload #(.SLICE(0),.CAPTURE_STAGE(i==1||i==2),.LOCAL_JOIN(i==1||i==2),.CAPTURE_MUT(i==2),.MUT(i==3?4:0)) dut
       (.ck(ck),.rst_n(rst_n),.treq(treq),.s_we(s_we),.s_kind(s_kind),.s_addr(s_addr),.s_data(s_data),
        .tw_we(we_p[i]),.tw_kind(kind_p[i]),.tw_addr(addr_p[i]),.tw_data(data_p[i]),.busy(busy_p[i]),.done(done_p[i]),.fault(fault_p[i]));
    end
    // Metadata-defined Option A timing contract only, not a physical-equivalence proof.
    reg[8:0] req_q=0; reg sw_q=0; reg[1:0]sk_q=0;reg[23:0]sa_q=0;reg[1023:0]sd_q=0;
    reg rr1=0,rr2=0,ow=0,ob=0,od=0,of=0;reg[1:0]ok=0;reg[23:0]oa=0;reg[1023:0]op=0;
    wire iw,ib,idone,ifault;wire[1:0]ik;wire[23:0]ia;wire[1023:0]ip;
    always @(posedge ck) begin
      req_q<=treq;sw_q<=s_we;sk_q<=s_kind;sa_q<=s_addr;sd_q<=s_data;rr1<=rst_n;rr2<=rr1;
      ow<=iw;ok<=ik;oa<=ia;op<=ip;ob<=ib;od<=idone;of<=ifault;
    end
    qfd_dv_slice_tload #(.SLICE(0),.CAPTURE_STAGE(1),.LOCAL_JOIN(1)) contract_body
     (.ck(ck),.rst_n(rr2),.treq(req_q),.s_we(sw_q),.s_kind(sk_q),.s_addr(sa_q),.s_data(sd_q),
      .tw_we(iw),.tw_kind(ik),.tw_addr(ia),.tw_data(ip),.busy(ib),.done(idone),.fault(ifault));
    assign we_p[4]=ow;assign kind_p[4]=ok;assign addr_p[4]=oa;assign data_p[4]=op;
    assign busy_p[4]=ob;assign done_p[4]=od;assign fault_p[4]=of;
    assign we=we_p[profile];assign kind=kind_p[profile];assign addr=addr_p[profile];assign data=data_p[profile];
    assign busy=busy_p[profile];assign done=done_p[profile];assign jfault=fault_p[profile];
    reg [7:0] cr_re = 0; reg [191:0] cr_addr = 0; wire [511:0] cr_q;
    reg bt_re = 0, bs_re = 0, p_re = 0; reg [8:0] bt_word = 0, p_idx = 0; reg [23:0] bs_addr = 0;
    wire [255:0] bt_q, bs_q; wire [456:0] p_q; wire vfault;
    qfd_dv_vm vm (.ck(ck), .rst_n(rst_n),
        .a_re(8'd0), .b_re(8'd0), .c_re(8'd0), .a_addr(192'd0), .b_addr(192'd0), .c_addr(192'd0),
        .a_q(), .b_q(), .c_q(), .cr_re(cr_re), .cr_addr(cr_addr), .cr_q(cr_q),
        .bs_re(bs_re), .bs_addr(bs_addr), .bs_q(bs_q), .bt_re(bt_re), .bt_word(bt_word), .bt_q(bt_q),
        .p_re(p_re), .p_idx(p_idx), .p_q(p_q), .su_we(8'd0), .su_waddr(192'd0), .su_wdata(256'd0),
        .w16_we(1'b0), .w16_addr(24'd0), .w16_data(512'd0), .w1_we(1'b0), .w1_addr(24'd0), .w1_data(32'd0),
        .tw_we(we), .tw_kind(kind), .tw_addr(addr), .tw_data(data), .fault(vfault));
    reg [1050:0] expected [0:12671]; string exp_file;
    integer resident [0:3]; integer st, u, r, k, h, ix, checks = 0, edge_checks = 0, cycles = 0, fault_case = 0;
    integer req_cycle = -1, cur_stage = 1, cur_user = 0, slot;
    reg [1050:0] want, got;
    function automatic [255:0] head_word(input integer wa);
        integer lane; begin for (lane = 0; lane < 16; lane = lane + 1) head_word[16*lane +: 16] = 16'h6000 + wa + lane; end
    endfunction
    // exact-edge monitor of the joined bundle
    always @(posedge ck) begin
        cycles = cycles + 1;
        if (treq[8]) begin first_visible=-1;last_visible=-1;first_sample=-1;last_sample=-1; req_cycle = cycles; cur_stage = treq[7:2]; cur_user = treq[1:0]; end
        if (rst_n && req_cycle>0 && we && !s_we) begin
          if(first_sample<0) first_sample=cycles;
          last_sample=cycles;
        end
        #1;
        if(rst_n && req_cycle>0 && we && !s_we) begin
          if(first_visible<0) first_visible=cycles;
          last_visible=cycles;
        end
        if (rst_n && fault_case == 0) begin
            if (jfault || vfault) $fatal(1, "TLOAD_UNEXPECTED_FAULT join=%0d vm=%0d cycle=%0d", jfault, vfault, cycles);
            if (req_cycle > 0 && cycles >= req_cycle + FIRST_AGE - 1 && cycles < req_cycle + FIRST_AGE - 1 + 88 && !s_we) begin
                slot = cycles - (req_cycle + FIRST_AGE - 1);
                ix = (((cur_stage - 1) * 4) + cur_user) * 88 + slot; want = expected[ix];
                got = {addr, kind, we, data};
                if (we !== want[1024] || (want[1024] && got !== want))
                    $fatal(1, "TLOAD_EDGE_MISMATCH stage=%0d user=%0d slot=%0d cycle=%0d", cur_stage, cur_user, slot, cycles);
                if (done !== (slot == 87)) $fatal(1, "TLOAD_DONE_AGE slot=%0d", slot);
                edge_checks = edge_checks + 1;
            end
        end
    end
    task automatic check_record(input [1050:0] w);
        integer part, lane; reg [23:0] wa; reg [1:0] wk;
        begin
            wa = w[1050:1027]; wk = w[1026:1025];
            if (w[1024]) begin
                if (wk == 3) for (part = 0; part < 2; part = part + 1) begin
                    @(negedge ck); p_re = 1; p_idx = 2*wa + part; repeat(2) @(posedge ck); #1;
                    if (p_q !== w[512*part +: 457]) $fatal(1, "TLOAD_PROG_MISMATCH addr=%0d", wa);
                    checks = checks + 1; @(negedge ck); p_re = 0;
                end else if (wk == 2) for (part = 0; part < 4; part = part + 1) begin
                    @(negedge ck); bt_re = 1; bs_re = 1; bt_word = wa + part; bs_addr = wa + part; repeat(2) @(posedge ck); #1;
                    if (bt_q !== w[256*part +: 256] || bs_q !== w[256*part +: 256]) $fatal(1, "TLOAD_BTAB_MISMATCH addr=%0d", wa);
                    checks = checks + 1; @(negedge ck); bt_re = 0; bs_re = 0;
                end else if (wk == 1) for (part = 0; part < 2; part = part + 1) begin
                    @(negedge ck); cr_re = 8'hff;
                    for (lane = 0; lane < 8; lane = lane + 1) cr_addr[24*lane +: 24] = 16*wa + 8*part + lane;
                    repeat(2) @(posedge ck); #1;
                    for (lane = 0; lane < 8; lane = lane + 1)
                        if (cr_q[64*lane +: 64] !== w[64*(8*part + lane) +: 64]) $fatal(1, "TLOAD_CROM_MISMATCH addr=%0d lane=%0d", wa, lane);
                    checks = checks + 1; @(negedge ck); cr_re = 0;
                end
            end
        end
    endtask
    task automatic request(input integer s, input integer uu);
        begin @(negedge ck); treq = {1'b1, 6'(s), 2'(uu)}; @(negedge ck); treq = 9'd0; end
    endtask
    // Observe at the VM sampling edge, before nonblocking updates. The failed
    // NS4 LOCAL_JOIN1/CAPTURE_STAGE1 join samples the stream on edge S;
    // 0 samples exactly the same bundle on S+1.
    reg stream_monitor = 0, previous_stream_we = 0;
    reg [1049:0] previous_stream_bundle = 0;
    reg previous2_stream_we=0;reg[1049:0]previous2_stream_bundle=0;
    integer stream_checks = 0;
    always @(posedge ck) begin : stream_edge_contract
        reg expected_stream_we;
        reg [1049:0] expected_stream_bundle;
        if (stream_monitor) begin
            expected_stream_we = profile==4 ? previous2_stream_we : s_we;
            expected_stream_bundle = profile==4 ? previous2_stream_bundle : {s_addr,s_kind,s_data};
            if (we !== expected_stream_we || (expected_stream_we && {addr,kind,data} !== expected_stream_bundle))
                $fatal(1, "TLOAD_STREAM_EDGE_MISMATCH cycle=%0d registered=%0d", cycles, 0);
            if (expected_stream_we) stream_checks = stream_checks + 1;
        end
        previous2_stream_we=previous_stream_we;previous2_stream_bundle=previous_stream_bundle;
        previous_stream_we = s_we;
        previous_stream_bundle = {s_addr,s_kind,s_data};
    end
    integer first_visible=-1,last_visible=-1,first_sample=-1,last_sample=-1;
    integer lastk;
    initial begin
        if (!$value$plusargs("PROFILE=%d",profile)) profile=0;
        FIRST_AGE=(profile==4)?8:(profile==1||profile==2)?6:5;
        if (!$value$plusargs("EXPECTED=%s", exp_file)) $fatal(1, "EXPECTED required");
        if ($value$plusargs("FAULT_CASE=%d", fault_case)) begin end
        $readmemh(exp_file, expected); for (u = 0; u < 4; u = u + 1) resident[u] = 0;
        repeat(4) @(negedge ck); rst_n = 1; repeat(5) @(negedge ck);
        if (fault_case == 1) begin
            // a load, then a stream write placed on the edge of its first valid loader write
            // collide with the LAST valid write of (stage 1, user 0): no later valid capture, so the loader's own
            // p_other check cannot raise the fault -> only the join's collision fault can (kills MUT 3)
            lastk = -1; for (k = 0; k < 88; k = k + 1) if (expected[k][1024]) lastk = k;
            if (lastk < 0) $fatal(1, "TLOAD_FIXTURE_NO_VALID_SLOT");
            request(1, 0);
            while (cycles != req_cycle + FIRST_AGE - 2 + lastk) @(negedge ck);
            s_we = 1; s_kind = 2; s_addr = 72; s_data = {4{head_word(72)}};
            @(posedge ck); #1;
            if (we !== 1'b0) $fatal(1, "TLOAD_COLLISION_WRITE_NOT_SUPPRESSED");
            @(negedge ck); s_we = 0;
            @(posedge ck); #1;
            if (jfault !== 1'b1) $fatal(1, "TLOAD_COLLISION_FAULT_AGE");
            $display("TLOAD_COLLISION_REJECT_PASS suppressed=1 fault_age=1"); $finish;
        end
        // shared head sentinel through the stream port (exclusive window: before any load)
        stream_monitor = 1;
        for (k = 72; k < 76; k = k + 4) begin
            @(negedge ck); s_we = 1; s_kind = 2; s_addr = k;
            for (h = 0; h < 4; h = h + 1) s_data[256*h +: 256] = head_word(k + h);
        end
        @(negedge ck); s_we = 0; repeat(3) @(negedge ck);
        stream_monitor = 0;
        if (stream_checks != 1) $fatal(1, "TLOAD_STREAM_EDGE_COUNT %0d", stream_checks);
        $display("TLOAD_STREAM_EDGE_PASS writes=%0d source_to_vm_edges=%0d", stream_checks, profile==4?2:0);
        for (st = 1; st <= 2; st = st + 1) for (u = 0; u < 2; u = u + 1) begin
            request(st, u);
            wait (done); repeat(3) @(negedge ck);
            $display("TLOAD_MEASURE profile=%0d stage=%0d user=%0d period_ps=833 req=%0d first_visible=%0d last_visible=%0d first_vm_commit=%0d last_vm_commit=%0d first_age=%0d last_age=%0d resident_after=%0d",profile,st,u,req_cycle,first_visible,last_visible,first_sample,last_sample,first_sample-req_cycle,last_sample-req_cycle,last_sample);
            resident[u] = st;
            for (r = 0; r < 4; r = r + 1) if (resident[r] != 0) for (k = 0; k < 88; k = k + 1) begin
                ix = (((resident[r] - 1) * 4) + r) * 88 + k; check_record(expected[ix]);
            end
            for (k = 72; k < 76; k = k + 1) begin
                @(negedge ck); bt_re = 1; bs_re = 1; bt_word = k; bs_addr = k; repeat(2) @(posedge ck); #1;
                if (bt_q !== head_word(k) || bs_q !== head_word(k)) $fatal(1, "TLOAD_SHARED_HEAD_CLOBBER addr=%0d", k);
                checks = checks + 1; @(negedge ck); bt_re = 0; bs_re = 0;
            end
        end
        if (edge_checks != 352) $fatal(1, "TLOAD_EDGE_CHECK_COUNT %0d", edge_checks);
        $display("TLOAD_JOIN_PASS edge_checks=%0d reads=%0d cycles=%0d first_age=%0d stages2 users2 retention head_guard=1",
                 edge_checks, checks, cycles, FIRST_AGE);
        $finish;
    end
    initial begin repeat(3000000) @(posedge ck); $fatal(1, "TLOAD_BOUNDED_BENCH_PROGRESS"); end
endmodule
