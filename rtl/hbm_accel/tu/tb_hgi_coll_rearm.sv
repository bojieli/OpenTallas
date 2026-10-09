`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// tb_hgi_coll_rearm: ONE die's switched-tier collective endpoint
// (ot_hbm_accel_tu_endpoint, RTL) at DS-V4.1 TP-96 shape, its far side a
// BEHAVIOURAL Tomahawk-Ultra-tier stub (minimum component, owner rule).
//
// The stub stands for: the die's Ethernet PHY/FEC (Tx and Rx), the cable and
// the switch -- ONE labelled budget +BUDGET (ns) from a flit leaving this
// die's serializer to the same flit reaching the destination die's RX CDC
// (default 377.6 = uarch_model.TU endpoint_phy 100 + switch 250 + cable
// 27.6, VENDOR BUDGET).  It multicasts results, and replays the other ranks
// SYMMETRICALLY: every die runs the same RTL on the same schedule, so peer
// j's flit for us leaves its serializer when our corresponding flit leaves
// ours (partials: our flit to owner s <-> peer 2J - s's flit to us, the
// rotated injection order makes it exact; results / gather segments: our
// result m <-> every other owner's result m).  Egress to this die is paced
// per port at the die's own serializer rate (the RX PHY's line rate) and
// spends this die's receive-buffer credits; credits (both directions) return
// after +CRED ns (labelled reverse-link latency).
// Data: partials from the fixture (part.hex), results / gather words from
// the golden image (expected.hex).  Every delivered word is checked; for an
// all-reduce the die's OWN slice is computed by the RTL tree from real
// operands (bit-exact proof), the rest is placement.
// ---------------------------------------------------------------------------
`ifndef TU_NC
`define TU_NC 8
`endif
`ifndef TU_NOG
`define TU_NOG 12
`endif
`ifndef TU_PFMAX
`define TU_PFMAX 64
`endif
`ifndef TU_BF16
`define TU_BF16 1
`endif
`ifndef TU_INJ
`define TU_INJ 2
`endif
`ifndef TU_DEL
`define TU_DEL 4
`endif
`ifndef TU_NPT
`define TU_NPT 8
`endif
`ifndef TU_DUT
`define TU_DUT ot_hbm_accel_tu_endpoint_psg   // hbm-coll-rtl: +define+TU_DUT=ot_hbm_accel_tu_endpoint_sr
`endif
`ifndef TU_RXAW
`define TU_RXAW 8
`endif
module tb_hgi_coll_rearm #(
    parameter integer NC = `TU_NC, NOG = `TU_NOG, PFMAX = `TU_PFMAX, BF16 = `TU_BF16,
    parameter integer INJ = `TU_INJ, DEL = `TU_DEL, NPT = `TU_NPT, RXAW = `TU_RXAW,
    parameter integer LANES = 16, HUBW = 35, WSTG = 14, BITS_X100 = 72000, PWB = 545, LAT = 7,
    parameter real    T_CORE = 0.833333, T_PHY = 1.0
);
    localparam integer FW = 32 * LANES, PWT = FW + 33, NR = NOG * NC;
    localparam integer MAXL = NR * PFMAX;
`ifdef TU_REDUCE
    localparam integer IS_REDUCE = 1;
`else
    localparam integer IS_REDUCE = (NC > 1);
`endif
    integer seed, seed0, pf, rank, samecol, npdep = 0;
    integer duplicate_last=0; integer NA=8, gs=15, cmd=0; reg active=0, dr=0, fa=0; wire sr, done;
    integer total_commands=45, delayed_credit_observations=0, stall_observations=0;
    real budget, cred;
    string vecdir;
    reg [FW-1:0] part [0:MAXL-1];      // AR: contributor partials; gather: every rank's segment
    reg [FW-1:0] expw [0:MAXL-1];      // AR: result image (BF16 packed)
    reg go_clk = 0, go = 0;
    real ph0, ph1;
    integer OF, ROF, TOT, OG, J;
    initial begin
        seed=20261009;seed0=seed;ph0=0;ph1=0;budget=12;cred=50000;samecol=0;
        if (!$value$plusargs("VEC=%s",vecdir)) $fatal(1,"missing VEC");
        void'($value$plusargs("DUPLICATE_LAST=%d",duplicate_last));go_clk=1;
    end
    reg clk = 0, pclk_r = 0, rst_n = 0, prst_n = 0;
    initial begin wait(go_clk); #(T_CORE * ph0 + 0.001); forever #(T_CORE/2) clk = ~clk; end
    initial begin wait(go_clk); #(T_PHY * ph1 + 0.001);  forever #(T_PHY/2) pclk_r = ~pclk_r; end
`ifdef TU_PCLK_IS_CLK
    wire pclk = clk;      // hbm-coll-rtl: the hfd_coll die view wires pclk = clk (SYNCPHY = 1 endpoints)
`else
    wire pclk = clk;
`endif
    always @(posedge clk)  rst_n  <= ($realtime > 40.0);
    always @(posedge pclk) prst_n <= ($realtime > 40.0);


    wire [INJ*16-1:0] ii;
    wire [INJ-1:0] ir;
    reg  [INJ*FW-1:0] idata;
    always @* for (integer i = 0; i < INJ; i = i + 1) idata[FW*i +: FW] = part[rank * pf + integer'(ii[16*i +: 16])];
    wire [NPT-1:0] txv, rxc, fault_v;
    wire [NPT*PWT-1:0] txf;
    reg  [NPT-1:0] crr = 0, rxv = 0;
    reg  [NPT*PWT-1:0] rxf = 0;
    wire [DEL-1:0] dv;
    wire [DEL*PWT-1:0] dfl;
    wire flt;
    wire [31:0] cst;
`ifdef TU_GSZ                // hbm-forks: the group-size fork (NC 8 hardware, n = 2^TU_GSZ active); the stub models NC = n
    localparam integer DNC = 8;
`else
    localparam integer DNC = NC;
`endif
    `TU_DUT #(.ENABLE(1), .REARM(1), .NC(DNC), .NOG(NOG), .PFMAX(PFMAX), .LANES(LANES), .BF16(BF16), .NPT(NPT),
        .INJ(INJ), .DEL(DEL), .HUBW(HUBW), .WSTG(WSTG), .BITS_X100(BITS_X100), .PWB(PWB), .RXAW(RXAW),
        .SWCRED(1 << RXAW), .LAT(LAT)
`ifdef TU_SYNCPHY
        , .SYNCPHY(1)
`endif
        )
      dut (.clk(clk), .rst_n(rst_n), .pclk(pclk), .prst_n(prst_n), .rank(8'(rank)), .pf(16'(pf)), .go(go),
`ifdef TU_GSZPORT
           .gsz(4'(`TU_GSZPORT)),
`endif
           .inj_idx(ii), .inj_rd(ir), .inj_data(idata), .ph_tx_v(txv), .ph_tx_flit(txf), .sw_cr_ret(crr),
           .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(rxc), .del_valid(dv), .del_flit(dfl), .fault(flt),
           .stat_credit_stall(cst),.gsz(4'(gs)),.mcast_all(1'b0),.start_ready(sr),.done_valid(done),.done_ready(dr),.fault_ack(fa));
`ifdef TU_LOCKSTEP
    wire [INJ*16-1:0] ref_ii;wire[INJ-1:0]ref_ir;
    wire[NPT-1:0]ref_txv,ref_rxc;wire[NPT*PWT-1:0]ref_txf;
    wire[DEL-1:0]ref_dv;wire[DEL*PWT-1:0]ref_dfl;wire ref_flt;wire[31:0]ref_cst;
    ot_hbm_accel_tu_endpoint_ps #(.ENABLE(1), .NC(NC), .NOG(NOG), .PFMAX(PFMAX), .LANES(LANES), .BF16(BF16), .NPT(NPT),
        .INJ(INJ), .DEL(DEL), .HUBW(HUBW), .WSTG(WSTG), .BITS_X100(BITS_X100), .PWB(PWB), .RXAW(RXAW),
        .SWCRED(1 << RXAW), .LAT(LAT)
`ifdef TU_SYNCPHY
        , .SYNCPHY(1)
`endif
        )
      reference (.clk(clk), .rst_n(rst_n), .pclk(pclk), .prst_n(prst_n), .rank(8'(rank)), .pf(16'(pf)), .go(go),

           .inj_idx(ref_ii), .inj_rd(ref_ir), .inj_data(idata), .ph_tx_v(ref_txv), .ph_tx_flit(ref_txf), .sw_cr_ret(crr),
           .ph_rx_v(rxv), .ph_rx_flit(rxf), .rx_credit(ref_rxc), .del_valid(ref_dv), .del_flit(ref_dfl), .fault(ref_flt),
           .stat_credit_stall(ref_cst));
    always @(negedge clk) if(rst_n) begin
      if({ii,ir,txv,rxc,dv,flt,cst} !== {ref_ii,ref_ir,ref_txv,ref_rxc,ref_dv,ref_flt,ref_cst})
        $fatal(1,"DS_LOCKSTEP control mismatch");
      for(integer p=0;p<NPT;p=p+1)if(txv[p] && txf[p*PWT+:PWT]!==ref_txf[p*PWT+:PWT])$fatal(1,"DS_LOCKSTEP TX mismatch");
      for(integer d=0;d<DEL;d=d+1)if(dv[d] && dfl[d*PWT+:PWT]!==ref_dfl[d*PWT+:PWT])$fatal(1,"DS_LOCKSTEP DEL mismatch");
    end
`endif


    // ---- stub: egress queues per port, credits ------------------------------------------------------------
    real          eq_t [NPT][$];
    reg [PWT-1:0] eq_f [NPT][$];
    real          cr_eg [NPT][$];     // egress credits returning to the switch (from rx_credit)
    real          cr_in [NPT][$];     // ingress credits returning to the die (from departures)
    integer       eg_cred [0:NPT-1];
    integer       eacc [0:NPT-1];
    real t_issue = -1, t_fdep = -1, t_ldep = -1, t_farr = -1, t_larr = -1, t_done = -1, t_fres = -1, t_lres = -1;
    integer ndep = 0, narr = 0, nres = 0;
    initial for (integer p = 0; p < NPT; p = p + 1) begin eg_cred[p] = 1 << RXAW; eacc[p] = 0; end
    always @(posedge clk) if (go && t_issue < 0) t_issue = $realtime;

    task automatic sched(input integer p, input real t, input [PWT-1:0] f);
        eq_t[p].push_back(t); eq_f[p].push_back(f);
    endtask

    // departures (die PHY clock): record, schedule symmetric arrivals, ingress credit return
    always @(posedge pclk) begin
        for (integer p = 0; p < NPT; p = p + 1) if (txv[p]) begin : dep
            reg [PWT-1:0] f;
            integer kind, dst, src, idx, sl, jp, m;
            real ta;
            f = txf[p*PWT +: PWT];
            kind = integer'(f[PWT-1]); dst = integer'(f[FW+24 +: 8]); src = integer'(f[FW+16 +: 8]);
            idx = integer'(f[FW +: 16]);
            if (t_fdep < 0) t_fdep = $realtime;
            t_ldep = $realtime; ndep = ndep + 1;
            ta = $realtime + budget;
            cr_in[p].push_back($realtime + cred);
            if (kind == 0 && samecol != 0) begin          // +SAMECOL=1 (hbm-coll-rtl directed test): hold every peer
                npdep = npdep + 1;                         // partial, then release them all at once, flit idx of every
                if (npdep == (NA - 1) * OF)                // peer on port idx % NPT: each pclk all ports carry partials
                    for (integer q = 0; q < NA; q = q + 1) // of the SAME contributor -> same-column collisions
                        if (q != J) for (integer x = 0; x < OF; x = x + 1)
                            sched(x % NPT, ta, {1'b0, 8'(rank), 8'(q), 16'(x), part[(OG * NA + q) * pf + J * OF + x]});
            end else if (kind == 0) begin                  // partial to owner dst: peer 2J - s sends us its slice-J flit
                sl = dst - OG * NA;
                jp = ((2 * J - sl) % NA + NA) % NA;
                sched(p, ta, {1'b0, 8'(rank), 8'(jp), 16'(idx), part[(OG * NA + jp) * pf + J * OF + idx]});
            end else if (IS_REDUCE) begin                     // our result m: every other owner's result m
                m = idx - (OG * NA + J) * ROF;
                if (t_fres < 0) t_fres = $realtime;
                t_lres = $realtime; nres = nres + 1;
                for (integer o = 0; o < NR; o = o + 1) if (o != rank && (gs==15 || o / NA == OG))
                    sched((o + m) % NPT, ta, {1'b1, 8'hFF, 8'(o / NA), 16'(o * ROF + ((duplicate_last && cmd==2 && m==ROF-1)?0:m)), expw[o * ROF + ((duplicate_last && cmd==2 && m==ROF-1)?0:m)]});
            end else begin                                 // gather segment flit m: every peer's flit m
                m = idx - rank * pf;
                for (integer q = 0; q < NR; q = q + 1) if (q != rank)
                    sched((q + m) % NPT, ta, {1'b1, 8'hFF, 8'(q), 16'(q * pf + m), part[q * pf + m]});
            end
        end
    end
    // egress (die PHY clock): head ready, credit, line-rate pacing
    always @(posedge pclk) begin
        for (integer p = 0; p < NPT; p = p + 1) begin : eg
            integer a;
            while (cr_eg[p].size() > 0 && cr_eg[p][0] <= $realtime) begin void'(cr_eg[p].pop_front()); eg_cred[p] = eg_cred[p] + 1; end
            a = eacc[p] + BITS_X100;
            if (a > PWB * 100) a = PWB * 100;
            rxv[p] <= 1'b0;
            if (eq_t[p].size() > 0 && eq_t[p][0] <= $realtime && eg_cred[p] > 0 && a >= PWB * 100) begin
                rxv[p] <= 1'b1;
                rxf[p*PWT +: PWT] <= eq_f[p][0];
                void'(eq_t[p].pop_front()); void'(eq_f[p].pop_front());
                eg_cred[p] = eg_cred[p] - 1;
                a = a - PWB * 100;
                if (t_farr < 0) t_farr = $realtime;
                t_larr = $realtime; narr = narr + 1;
            end
            eacc[p] = a;
        end
    end
    // credits (core clock side)
    always @(posedge clk) begin
        for (integer p = 0; p < NPT; p = p + 1) begin
            if (rxc[p]) cr_eg[p].push_back($realtime + 12.0); // Independent fast egress credits; ingress credits remain deliberately late.
            crr[p] <= 1'b0;
            if (cr_in[p].size() > 0 && cr_in[p][0] <= $realtime) begin void'(cr_in[p].pop_front()); crr[p] <= 1'b1; end
        end
    end

`ifdef TU_GSZ
    initial begin
      wait(go_clk); #700;
      $display("GSZDEBUG rank=%0d gs=%0d started=%0d k=%0d NA=%0d OF=%0d ptr=%0d pres0=%h col=%h rv=%b",rank,dut.gsz,dut.g_on.started,dut.g_on.k,dut.g_on.NA,dut.g_on.OF,dut.g_on.rptr,dut.g_on.pres[0],dut.g_on.col,dut.g_on.r_v);
    end
`endif
    // ---- checker ------------------------------------------------------------------------------------------
    integer got = 0, mism = 0, own_ok = 0;
    reg seen [0:MAXL-1];
    initial for (integer i = 0; i < MAXL; i = i + 1) seen[i] = 0;
    always @(posedge clk) begin
        for (integer i = 0; i < DEL; i = i + 1) if (dv[i]) begin : chk
            integer gi;
            reg [FW-1:0] want;
            gi = integer'(dfl[i*PWT + FW +: 16]);
`ifdef TU_GSZ
            if (gi < OG * NC * ROF || gi >= (OG + 1) * NC * ROF)
                $fatal(1,"GROUP_ISOLATION rank=%0d gi=%0d OG=%0d",rank,gi,OG);
`endif
            want = (IS_REDUCE) ? expw[gi] : part[gi];
            if (gi >= MAXL || seen[gi] || dfl[i*PWT +: FW] !== want) begin
                mism = mism + 1;
                if (mism < 10) $display("TUMISMATCH gi=%0d", gi);
            end else if (IS_REDUCE && gi / ROF == rank) own_ok = own_ok + 1;
            if (gi < MAXL) seen[gi] = 1;
            got = got + 1;
            if (got > TOT) $fatal(1,"REARM extra delivery");
            if (got == TOT) t_done = $realtime;
        end
    end
    wire [31:0] credits [0:NPT-1];
    for(genvar p=0;p<NPT;p=p+1)assign credits[p]=dut.g_on.g_port[p].u_port.credit;
    // One externally coordinated command at a time. Completion is local, not a transport barrier.
    function automatic integer queue_words();
        integer n; n=0;for(integer p=0;p<NPT;p=p+1)n+=eq_f[p].size();return n;
    endfunction
    always @(negedge clk) if(active)begin
        if(done && (got!=TOT || ndep!=pf-OF+ROF || queue_words()!=0 || narr!=(NA-1)*OF+((gs==15?NR:NA)-1)*ROF))
            $fatal(1,"PREMATURE_DONE cmd=%0d got=%0d/%0d tx=%0d/%0d pending_external=%0d rx=%0d",cmd,got,TOT,ndep,pf-OF+ROF,queue_words(),narr);
        if(done && sr)$fatal(1,"DONE start_ready overlap");
        if(cst>0)stall_observations++;
    end
    initial begin : commands
        integer mode, cr_before[0:NPT-1];
        wait(rst_n); repeat(8)@(negedge clk);
        for(cmd=0;cmd<total_commands;cmd=cmd+1)begin
            mode=cmd<6?(cmd==0?0:cmd-1):4;
            case(mode)
                0:begin gs=0;NA=1;pf=8;rank=37+cmd;end
                1:begin gs=1;NA=2;pf=16;rank=13;end
                2:begin gs=2;NA=4;pf=16;rank=62;end
                3:begin gs=3;NA=8;pf=32;rank=95;end
                4:begin gs=15;NA=8;pf=64;rank=(cmd*13)%96;end
            endcase
            OF=pf/NA;ROF=OF/2;OG=rank/NA;J=rank%NA;
            TOT=(gs==15?NR:NA)*ROF;
            $readmemh($sformatf("%s/c%0d/part.hex",vecdir,mode),part);
            $readmemh($sformatf("%s/c%0d/expected.hex",vecdir,mode),expw);
            got=0;mism=0;own_ok=0;ndep=0;narr=0;nres=0;npdep=0;
            t_done=-1;t_issue=-1;t_fres=-1;t_lres=-1;
            for(integer i=0;i<MAXL;i=i+1)seen[i]=0;
            wait(sr);repeat(3)@(negedge clk);active=1;go=1;
            @(negedge clk);go=0;
            if(duplicate_last && cmd==2)begin
                wait(flt);repeat(12)begin @(negedge clk);if(done)$fatal(1,"duplicate replaced missing result");end
                $display("REARM_DUPLICATE PASS missing_result_not_completed fault=%0d got=%0d/%0d",flt,got,TOT);$finish;disable commands;
            end
            wait(done);@(negedge clk);
            if(got!=TOT || ndep!=pf-OF+ROF || queue_words()!=0 || narr!=(NA-1)*OF+((gs==15?NR:NA)-1)*ROF)
                $fatal(1,"PREMATURE_DONE consuming checker cmd=%0d got=%0d/%0d tx=%0d pending=%0d",cmd,got,TOT,ndep,queue_words());
            if(flt || mism || own_ok!=ROF)$fatal(1,"REARM exact/fault cmd=%0d got=%0d mismatch=%0d fault=%0d own=%0d",cmd,got,mism,flt,own_ok);
            // Done stays sticky, descriptors remain captured, late ingress credits are preserved.
            for(integer p=0;p<NPT;p=p+1)begin
                cr_before[p]=credits[p];
                if(cr_in[p].size()>0)delayed_credit_observations++;
            end
            repeat(3)begin @(negedge clk);if(!done || sr)$fatal(1,"DONE not sticky");end
            $display("REARM_COMMAND PASS cmd=%0d gs=%0d rank=%0d pf=%0d got=%0d tx=%0d rx=%0d stall=%0d",cmd,gs,rank,pf,got,ndep,narr,cst);
            // The stub has sent every old scheduled RX before acknowledgment. Credit-only traffic may remain.
            if(queue_words()!=0 || |rxv)$fatal(1,"external old traffic remains at ack");
            active=0;dr=1;@(negedge clk);dr=0;
            repeat(2)@(negedge clk);
            if(cmd<6)for(integer p=0;p<NPT;p=p+1)
                if(credits[p]!=cr_before[p])$fatal(1,"ingress credit reset at rearm p=%0d prior=%0d now=%0d",p,cr_before[p],credits[p]);
            if(done || !sr)$fatal(1,"rearm handshake failed");
        end
        if(delayed_credit_observations==0 || stall_observations==0)$fatal(1,"credit-delay/stall coverage missing");
        $display("REARM PASS commands=%0d delayed_credit=%0d stalls=%0d reset_count=1 external_quiescence=stub_contract",total_commands,delayed_credit_observations,stall_observations);
        $finish;
    end
    initial begin #400000; $fatal(1,"REARM timeout cmd=%0d got=%0d/%0d tx=%0d rx=%0d done=%0d fault=%0d",cmd,got,TOT,ndep,narr,done,flt);end
endmodule
