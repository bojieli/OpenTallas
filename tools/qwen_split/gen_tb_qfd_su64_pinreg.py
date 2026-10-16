import sys
clk_ports=['ck']+[f'ck_{f}{i}' for f,n in [('head',64),('exp',64),('rcp',64),('rsq',64),('align',16),('lane',64),('red',9)] for i in range(n)]
def inst(name,pinreg,mut):
    c=",".join(f".{p}(clk)" for p in clk_ports)
    cas=",".join(f".ca{g}({name}_ca[{g}]),.cq{g}(cq[{g}])" for g in range(8))
    return f"""    qfd_sp_su64_sfu #(.PINREG({pinreg}),.PRMUT({mut})) {name} ({c},
        .rst_n(rst_n),.external_a_re({name}_ea_re),.external_a_addr({name}_ea_addr),.external_a_q({name}_ea_q),
        .external_vm_a_re({name}_evm_re),.external_vm_a_addr({name}_ea_addr),.external_embed_fault(1'b0),
        .si(si),.sd({name}_sd),.acc({name}_acc),.native_issue({name}_ni),.va({name}_va),.vq({name}_vq),.cp(cp),
        .cp_active({name}_cpa),.cp_done({name}_cpd),.xsw({name}_xsw),.kv_we({name}_kvwe),.kv_waddr({name}_kvwa),
        .kv_wdata({name}_kvwd),{cas});
"""
def decl(n):
    return f"""    wire [63:0] {n}_ea_re; wire [1535:0] {n}_ea_addr; reg [2047:0] {n}_ea_q; wire [63:0] {n}_evm_re;
    wire [107:0] {n}_sd; wire [23:0] {n}_acc; wire [62:0] {n}_ni; wire [2366:0] {n}_va; reg [6143:0] {n}_vq;
    wire {n}_cpa,{n}_cpd; wire [2136:0] {n}_xsw; wire [63:0] {n}_kvwe; wire [1535:0] {n}_kvwa; wire [2047:0] {n}_kvwd;
    wire [205:0] {n}_ca [0:7];
    reg {n}_ea; // the seq_su embedding mask (ot_qfd_su_embed_static embed_active)
    assign {n}_evm_re = {n}_ea_re & ~{{64{{{n}_ea}}}};
    always @(posedge clk or negedge rst_n) if(!rst_n) {n}_ea<=0; else if(si[0]) {n}_ea<=si[457];
    // seq_su decode model: one edge after the strobe (ot_qfd_su_embed_static), a deterministic word per lane address
    integer {n}_l;
    always @(posedge clk) for({n}_l=0;{n}_l<64;{n}_l={n}_l+1)
        {n}_ea_q[32*{n}_l+:32] <= ({n}_ea_re[{n}_l] & {n}_ea) ? hw(32'h5eed0000 ^ {n}_ea_addr[24*{n}_l+:24]) : 32'hdead0000 + {n}_l;
    // banked VM model: every operand answers all 64 lanes 15 edges after the strobe at the va pin (VL 14),
    // lane l word = H(operand, a0 + l*(a1-a0)); no strobe -> a deterministic filler of the pin image
    reg [6143:0] {n}_vp [0:14];
    integer {n}_o,{n}_k;
    always @(posedge clk) begin
        for({n}_k=14;{n}_k>0;{n}_k={n}_k-1) {n}_vp[{n}_k] <= {n}_vp[{n}_k-1];
        for({n}_o=0;{n}_o<3;{n}_o={n}_o+1) for({n}_l=0;{n}_l<64;{n}_l={n}_l+1)
            {n}_vp[0][{n}_o*2048+32*{n}_l+:32] <= {n}_va[50*{n}_o+48] ?
                hw({{8'h40+{n}_o,24'd0}} ^ ({n}_va[50*{n}_o+:24] + {n}_l*({n}_va[50*{n}_o+24+:24]-{n}_va[50*{n}_o+:24]))) :
                hw({{8'h80+{n}_o,24'd0}} ^ {n}_va[150+32*{n}_l+:24]);
        {n}_vq <= {n}_vp[13];
    end
"""
body=f"""`timescale 1ns/1ps
// Q-ELEM-SUC 2026-10-16: qfd_sp_su64_sfu PINREG = 1 (every pin registered) against PINREG = 0, production shape
// (64 lanes, real lane/SFU RTL, all 346 clock entries on one bench clock), each DUT on its OWN fixed-latency VM model
// (answer 15 edges after the va-pin strobe), its own seq_su embedding mask/decode model (answer 1 edge after the
// external_a strobe) and the common random cb (cq) / instruction (si) / copy (cp) stimulus.
// MODE 0 (SU ops, random si; no copy): va, ca0..7 request part (crom_re/addr), kv_*, acc, native_issue, xsw, cp_* must
//   be equal on EVERY edge (0-edge contract); the ca cb_stage field (si[481:476] feed-through, now a pin register) is
//   the PINREG=0 value one edge later, and on every edge a group carries a request its stage equals PINREG=0's on that
//   SAME edge (request/stage pairing unchanged); sd(PINREG=1) = sd(PINREG=0) one edge later (status +1; the idle bit, whose cut mixes the
//   lane write strobes, is checked separately for being at most one edge early/late); external_a_re/addr(1) = (0) one
//   edge EARLIER (embedding request -1; the answers are re-aligned inside).
// MODE 1 (copy only): copy read beats at va + 2, write beats / xsw + 3, cp_done + 2 (same data).
// PRMUT (mutants, must FAIL): 1 old VM/cb edge, 2 copy latency, 3 sd old edge, 4 cp old edge.
module tb_qfd_su64_pinreg;
    parameter integer MODE = 0, PRMUT = 0, OPS = 48, SEED = 11, MAXCYC = 20000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    function [31:0] hw(input [31:0] x);
        reg [31:0] y;
        begin y = x * 32'h9e3779b1; y = y ^ (y >> 15); y = y * 32'h85ebca6b; hw = y ^ (y >> 13); end
    endfunction
    reg [481:0] si; reg [55:0] cp; reg [511:0] cq [0:7];
{decl('d0')}{decl('d1')}
{inst('d0',0,0)}{inst('d1',1,'PRMUT')}
    integer cyc = 0, errs = 0, g, ops = 0, copies = 0, ev0 = 0, ev1 = 0;
    // one-edge history of d0 / d1 for the shifted compares
    reg [107:0] d0_sd_p; reg [63:0] d1_ea_re_p; reg [1535:0] d1_ea_addr_p; reg [5:0] d0_cst_p [0:7]; integer gp;
    always @(posedge clk) begin d0_sd_p <= d0_sd; d1_ea_re_p <= d1_ea_re; d1_ea_addr_p <= d1_ea_addr;
        for (gp = 0; gp < 8; gp = gp + 1) d0_cst_p[gp] <= d0_ca[gp][205:200]; end
    integer n_req = 0;   // group-edges carrying a constant-ROM request (pairing check coverage)
    task automatic bad(input [8*48-1:0] what);
        begin errs = errs + 1; if (errs <= 12) $display("MISMATCH cyc%0d %0s", cyc, what); end
    endtask
    // copy-mode event streams (pin images of the copy beats)
    reg [49:0] r0q [0:4095]; reg [49:0] r1q [0:4095]; integer nr0=0,nr1=0,fr0=-1,fr1=-1;
    reg [2184:0] w0q [0:4095]; reg [2184:0] w1q [0:4095]; integer nw0=0,nw1=0,fw0=-1,fw1=-1,cd0=-1,cd1=-1,ca0r=-1,ca0f=-1,ca1r=-1,ca1f=-1;
    always @(negedge clk) if (rst_n && cyc > 2) begin
        if (MODE == 0) begin
            if (d0_va !== d1_va) bad("va");
            for (g = 0; g < 8; g = g + 1) begin
                if (d0_ca[g][199:0] !== d1_ca[g][199:0]) bad("ca request (0)");
                if (d1_ca[g][205:200] !== d0_cst_p[g]) bad("ca stage (+1)");
                if (|d1_ca[g][7:0]) begin n_req = n_req + 1; if (d1_ca[g][205:200] !== d0_ca[g][205:200]) bad("ca request/stage pairing"); end
            end
            if (d0_kvwe !== d1_kvwe || d0_kvwa !== d1_kvwa || d0_kvwd !== d1_kvwd) bad("kv");
            if (d0_acc !== d1_acc) bad("acc");
            if (d0_ni !== d1_ni) bad("native_issue");
            if (d0_xsw !== d1_xsw) bad("xsw");
            if (d0_cpa !== d1_cpa || d0_cpd !== d1_cpd) bad("cp status");
            if ({{d1_sd[107:11], d1_sd[9:0]}} !== {{d0_sd_p[107:11], d0_sd_p[9:0]}}) bad("sd (+1)");
            if (d1_ea_re_p !== d0_ea_re || d1_ea_addr_p !== d0_ea_addr) bad("external_a (-1)");
        end else begin
            if (d0_va[48]) begin if (fr0 < 0) fr0 = cyc; r0q[nr0] = d0_va[49:0]; nr0 = nr0 + 1; end
            if (d1_va[48]) begin if (fr1 < 0) fr1 = cyc; r1q[nr1] = d1_va[49:0]; nr1 = nr1 + 1; end
            if (|d0_va[2309:2246]) begin if (fw0 < 0) fw0 = cyc; w0q[nw0] = {{d0_va[2309:150], d0_xsw[24:0]}}; nw0 = nw0 + 1; end
            if (|d1_va[2309:2246]) begin if (fw1 < 0) fw1 = cyc; w1q[nw1] = {{d1_va[2309:150], d1_xsw[24:0]}}; nw1 = nw1 + 1; end
            if (d0_cpa && ca0r < 0) ca0r = cyc; if (!d0_cpa && ca0r >= 0 && ca0f < 0) ca0f = cyc;
            if (d1_cpa && ca1r < 0) ca1r = cyc; if (!d1_cpa && ca1r >= 0 && ca1f < 0) ca1f = cyc;
            if (d0_cpd && cd0 < 0) cd0 = cyc;
            if (d1_cpd && cd1 < 0) cd1 = cyc;
        end
    end
    always @(posedge clk) cyc <= cyc + 1;
    // ---- stimulus ----
    integer seed = SEED, k, n, wait_c;
    reg [5:0] stage;
    task automatic issue;
        reg [17:0] nout, nin; reg [23:0] ab, bb, cb, db, rb;
        begin
            nout = 1 + ($urandom % 3); nin = 1 + ($urandom % 200);
            ab = 24'h001000 + ($urandom % 4096); bb = 24'h004000 + ($urandom % 4096);
            cb = 24'h008000 + ($urandom % 4096); db = 24'h00c000 + ($urandom % 4096); rb = 24'h00f000 + ($urandom % 256);
            si = 0;
            si[0] = 1; si[18:1] = nout; si[36:19] = nin;
            si[37] = $urandom % 2; si[61:38] = ab; si[85:62] = nin; si[109:86] = 1;
            si[110] = $urandom % 2; si[134:111] = bb; si[158:135] = nin; si[182:159] = 1;
            si[183] = $urandom % 2; si[207:184] = cb; si[231:208] = nin; si[255:232] = 1;
            si[257:256] = $urandom % 4; si[259:258] = $urandom % 4; si[262:260] = $urandom % 8; si[265:263] = $urandom % 8;
            si[266] = $urandom % 2; si[267] = $urandom % 2; si[269:268] = $urandom % 4;
            si[293:270] = db; si[317:294] = nin; si[341:318] = 1;
            si[343:342] = $urandom % 3; si[344] = $urandom % 2; si[368:345] = rb; si[392:369] = 1;
            si[424:393] = $urandom; si[456:425] = $urandom; si[457] = ($urandom % 4) == 0;
            si[475:458] = $urandom % 151936; si[481:476] = stage;
        end
    endtask
    always @(posedge clk) for (k = 0; k < 8; k = k + 1) cq[k] <= {{$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,
        $urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom}};
    initial begin
        si = 0; cp = 0; stage = 6'd3; k = $urandom(SEED);
        repeat (6) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        if (MODE == 0) begin
            for (n = 0; n < OPS; n = n + 1) begin
                if (($urandom % 8) == 0) stage = $urandom;
                issue; @(negedge clk); si[0] = 0; ops = ops + 1;
                // keep the instruction fields (the SU samples them with go); wait for the op to drain
                wait_c = 0;
                repeat (6) @(negedge clk);
                while ((!d0_sd[10] || $urandom % 3 != 0) && wait_c < 4000) begin @(negedge clk); wait_c = wait_c + 1; end
            end
            repeat (80) @(negedge clk);
        end else begin
            for (n = 0; n < 3; n = n + 1) begin
                cp = {{7'd16 + n, 24'h00a000 + 24'd4096*n, 24'h002000 + 24'd2048*n, 1'b1}}; @(negedge clk); cp = 0; copies = copies + 1;
                repeat (120) @(negedge clk);
                if (nr1 != nr0 || nw1 != nw0) bad("copy beat counts");
                if (fr1 - fr0 != 2) bad("copy read edge (+2)");
                if (fw1 - fw0 != 3) bad("copy write edge (+3)");
                if (cd1 - cd0 != 2) bad("cp_done edge (+2)");
                if (ca1r - ca0r != 1 || ca1f - ca0f != 2) bad("cp_active edges (+1 rise / +2 fall)");
                for (k = 0; k < nr0; k = k + 1) if (r0q[k] !== r1q[k]) bad("copy read beat");
                for (k = 0; k < nw0; k = k + 1) if (w0q[k] !== w1q[k]) bad("copy write beat");
                $display("COPY%0d reads %0d/%0d writes %0d/%0d first_read +%0d first_write +%0d cp_done +%0d cp_active +%0d/+%0d", n, nr0, nr1, nw0, nw1,
                         fr1-fr0, fw1-fw0, cd1-cd0, ca1r-ca0r, ca1f-ca0f);
                nr0=0;nr1=0;nw0=0;nw1=0;fr0=-1;fr1=-1;fw0=-1;fw1=-1;cd0=-1;cd1=-1;ca0r=-1;ca0f=-1;ca1r=-1;ca1f=-1;
            end
        end
        if (MODE == 0 && (d0_sd[107] || d1_sd[107])) $display("NOTE fault bits d0 %0d d1 %0d", d0_sd[107], d1_sd[107]);
        if (errs == 0) $display("PASS qfd_su64_pinreg mode%0d ops=%0d copies=%0d cycles=%0d crom_req_group_edges=%0d", MODE, ops, copies, cyc, n_req);
        else $display("FAIL qfd_su64_pinreg mode%0d errors=%0d", MODE, errs);
        $finish;
    end
    initial begin #(MAXCYC); $display("FAIL qfd_su64_pinreg timeout"); $finish; end
endmodule
"""
open(sys.argv[1],'w').write(body)
