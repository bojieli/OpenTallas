`timescale 1ns/1ps
// Memory-BIST element bench (DS-V4.1 ROM S81, 2026-10-04).
// ref = the pinned ot_v41_rom_elem_q_qp_w10; dut = ot_v41_elem_mbist_top (the generated MBIST successor
// ot_v41_rom_elem_qp_mb_w10 + two KV staging banks behind SRAM collars + one shared ot_mbist_ctrl), both at the
// routed S81 q parameters (NB 2, MTP 1, EARLY 1, FAST 1, PP 1, QTIMING_FIX 1, QPIPE 1).  Both read the same ROM
// contents through the behavioural macro model (+OT_ROM_DIR via maps: r_* for the ref, d_* for the dut).
//
// MODE func (default): the stimulus of tb_dsrom_qpipe_exact (directed + random phases, resets, noise); every
//   cycle the dut's valid / busy / fault bits and every data field under its valid, and the walker / FIFO /
//   issue / drain state, must equal the ref's (no shift).  In the middle, with both elements idle, the dut
//   runs its full memory BIST (ROM signatures + March C- on the KV banks) and must PASS with the expected
//   signatures (+ROMSIG0..3); the comparison continues through the BIST and after it.  The KV banks are
//   written and read back against a bench model before and after the BIST (the March is destructive; the
//   bench rewrites).
// MODE fault (+FAULTS=<file>): faults are injected into the dut's macros (macro index 0..3 = ROM 2*mb+k,
//   4..5 = KV bank 0..1; kinds as tools/mem_compiler/behav.py), the BIST runs alone and its statuses are printed.
module tb_v41_elem_mbist;
 integer SEED = 1;
 parameter integer NRAND = 400;
 reg clk=0, rst_n=0, cfg_v=0, go=0, xs_v=0;
 reg [4:0] cfg_a=0; reg [47:0] cfg_d=0;
 reg [7:0] xs_p=0; reg [2:0] xs_b=0, xs_pos=0; reg [1:0] xs_sv=2'b11;
 reg [255:0] xs_q0=0, xs_q1=0; reg [9:0] xs_e0=10'd127, xs_e1=10'd127;
 always #0.5 clk=~clk;
 reg bist_rst_n=0, bist_start=0;
 reg [1:0] kv_we=0; reg [15:0] kv_waddr=0, kv_raddr=0; reg [511:0] kv_wdata=0; wire [511:0] kv_rd;
 wire bist_busy, bist_done, bist_pass; wire [3:0] bist_sram_status; wire [7:0] bist_rom_status;
 reg [127:0] rom_exp=0; wire [127:0] rom_sig; wire rep_so;
 reg rep_en=0, rep_si=0;
 wire [1:0] av,bv,ae,be; wire [63:0] ad,bd; wire [31:0] ar,br;
 wire [9:0] asg,bsg,an,bn; wire [5:0] ap,bp; wire ab,bb,af,bf;
 ot_v41_rom_elem_q_qp_w10 #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1),
  .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .INSTANCE("r")) ref_dut (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(av), .pval(ad), .prow(ar), .pseg(asg), .pnseg(an), .perr(ae), .ppos(ap), .busy(ab), .fault(af));
 ot_v41_elem_mbist_top #(.NB(2), .MTP(1), .EARLY(1), .FAST(1), .PP(1), .QTIMING_FIX(1), .QPIPE(1), .QP_XS(1),
  .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .NKV(2), .INSTANCE("d")) dut (
  .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_a(cfg_a), .cfg_d(cfg_d), .go(go),
  .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0), .xs_q1(xs_q1), .xs_e1(xs_e1),
  .xs_pos(xs_pos), .pv(bv), .pval(bd), .prow(br), .pseg(bsg), .pnseg(bn), .perr(be), .ppos(bp), .busy(bb), .fault(bf),
  .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .kv_raddr(kv_raddr), .kv_rd(kv_rd),
  .bist_rst_n(bist_rst_n), .bist_start(bist_start), .bist_busy(bist_busy), .bist_done(bist_done), .bist_pass(bist_pass),
  .bist_sram_status(bist_sram_status), .bist_rom_status(bist_rom_status), .rom_exp_sig(rom_exp), .rom_sig(rom_sig),
  .rep_scan_en(rep_en), .rep_scan_in(rep_si), .rep_scan_out(rep_so));
 integer cyc=0, hits=0, issues=0, rows=0, nonzero=0, qadv=0, restarts=0, wraps=0, classes=0, rejected=0;
 integer go_closed=0, go_drain=0, resets=0, compared=0, exempt=0, bist_cmp=0, kv_checks=0;
 integer tcyc=0, last_assert=-1000;
 wire [127:0] ro = {av,ad,ar,asg,an,ae,ap,ab,af};
 wire [127:0] dov = {bv,bd,br,bsg,bn,be,bp,bb,bf};
 wire [159:0] rs = {ref_dut.u_e.hit_q,ref_dut.u_e.issue,ref_dut.u_e.n_run,ref_dut.u_e.n_q,ref_dut.u_e.n_b,ref_dut.u_e.n_c,
          ref_dut.u_e.n_j,ref_dut.u_e.n_pos,ref_dut.u_e.nA,ref_dut.u_e.nB,ref_dut.u_e.f_cnt,ref_dut.u_e.f_wr,
          ref_dut.u_e.f_rd,ref_dut.u_e.w_run,ref_dut.u_e.w_q,ref_dut.u_e.w_b,ref_dut.u_e.w_c,ref_dut.u_e.w_j,
          ref_dut.u_e.w_pos,ref_dut.u_e.a_ctr,ref_dut.u_e.fw_v,ref_dut.u_e.drain};
 wire [159:0] ds = {dut.u_e.hit_q,dut.u_e.issue,dut.u_e.n_run,dut.u_e.n_q,dut.u_e.n_b,dut.u_e.n_c,
          dut.u_e.n_j,dut.u_e.n_pos,dut.u_e.nA,dut.u_e.nB,dut.u_e.f_cnt,dut.u_e.f_wr,
          dut.u_e.f_rd,dut.u_e.w_run,dut.u_e.w_q,dut.u_e.w_b,dut.u_e.w_c,dut.u_e.w_j,
          dut.u_e.w_pos,dut.u_e.a_ctr,dut.u_e.fw_v,dut.u_e.drain};
 function automatic bit oeq(input [127:0] d, input [127:0] r);
   reg [1:0] dv, rv; reg [63:0] dd, rd; reg [31:0] dr, rr; reg [9:0] dsg, rsg, dn, rn; reg [1:0] de, re; reg [5:0] dp, rp;
   reg db, rb, df, rf;
   {dv,dd,dr,dsg,dn,de,dp,db,df} = d; {rv,rd,rr,rsg,rn,re,rp,rb,rf} = r;
   oeq = (dv === rv) && (db === rb) && (df === rf);
   for (int m = 0; m < 2; m++) if (rv[m])
     oeq = oeq && dd[32*m +: 32] === rd[32*m +: 32] && dr[16*m +: 16] === rr[16*m +: 16] && dsg[5*m +: 5] === rsg[5*m +: 5]
               && dn[5*m +: 5] === rn[5*m +: 5] && de[m] === re[m] && dp[3*m +: 3] === rp[3*m +: 3];
 endfunction
 reg fault_mode = 0;
 integer st_ex = 0, st_go = -1;
 always @(negedge rst_n) begin last_assert = tcyc; st_ex = 1; st_go = -1; end
 always @(negedge clk) if (st_ex && rst_n && dut.u_e.go_e && st_go < 0) st_go = tcyc;
 always @(negedge clk) if (!fault_mode) begin
   tcyc = tcyc + 1;
   if (rst_n) cyc = cyc + 1;
   if (tcyc > 2 && tcyc - last_assert > 1) begin
     if (!oeq(dov, ro)) $fatal(1, "output mismatch cycle=%0d bist_busy=%b (dut %h, ref %h)", tcyc, bist_busy, dov, ro);
     if (st_ex && st_go >= 0 && tcyc > st_go + 2) st_ex = 0;
     if (!st_ex && ds !== rs) $fatal(1, "state divergence cycle=%0d bist_busy=%b dut %h ref %h", tcyc, bist_busy, ds, rs);
     compared = compared + 1;
     if (bist_busy) bist_cmp = bist_cmp + 1;
   end else exempt = exempt + 1;
   if (rst_n) begin
     for (integer m=0;m<2;m=m+1) if (av[m]) begin rows=rows+1; if (ad[32*m+:32]!=0) nonzero=nonzero+1; end
     if (ref_dut.u_e.hit_q) begin
       hits=hits+1; classes=classes | (1 << ref_dut.u_e.n_c);
       if (({1'b0,ref_dut.u_e.c_u0[ref_dut.u_e.n_c]} + {3'd0,ref_dut.u_e.n_q,ref_dut.u_e.n_j})>255) wraps=wraps+1;
     end
     if (ref_dut.u_e.issue) issues=issues+1;
     if (ref_dut.u_e.n_step && ref_dut.u_e.n_nx[12] && ref_dut.u_e.n_nx[11:9]!=ref_dut.u_e.n_q) qadv=qadv+1;
     if (ref_dut.u_e.n_rst) restarts=restarts+1;
     if (ref_dut.u_e.xs_v_e && !ref_dut.u_e.hit_q && ref_dut.u_e.n_run) rejected=rejected+1;
     if (go) begin
       if (ref_dut.u_e.walk_busy) ;
       else if (ref_dut.u_e.drain != 0) go_drain=go_drain+1;
       else go_closed=go_closed+1;
     end
   end
 end
 task automatic tick(input integer n); repeat(n) @(posedge clk); endtask
 task automatic cfg(input integer a,input [47:0] d);
   @(negedge clk); #0.01; cfg_v=1; cfg_a=5'(a); cfg_d=d;
 endtask
 task automatic rnd_x;
   for (integer i=0;i<8;i=i+1) begin xs_q0[32*i+:32]=$urandom; xs_q1[32*i+:32]=$urandom; end
   xs_e0=10'd100+10'($urandom%50); xs_e1=10'd100+10'($urandom%50);
 endtask
 task automatic configure(input integer mode);
   integer nu,base,fp4,lo,hi,valid,plast,qlast; reg [47:0] d;
   plast = (mode==0) ? 2 : (mode==3 ? $urandom%3 : 0);
   qlast = 0;
   for(integer c=0;c<8;c=c+1) begin
     fp4 = (mode==3) ? $urandom%2 : (mode!=1);
     lo = (mode==3) ? $urandom%2 : 1; hi = (mode==3) ? $urandom%2 : 1;
     d=48'(c+1) | (48'(1+$urandom%3)<<16) | (48'd1<<21) | (48'(fp4)<<26) | (48'(lo)<<27) | (48'(hi)<<28)
       | (48'($urandom%8192)<<29);
     cfg(c,d); cfg(17+c, (mode==3 && $urandom%4==0) ? 48'h8000 : 48'(c+101));
     if (mode==0) nu=(c==0)?9:((c==3)?3:((c==7)?2:0));
     else if (mode==3) nu=($urandom%3==0) ? 0 : 1+$urandom%12;
     else nu=1;
     valid = (nu!=0);
     base=(mode==3) ? $urandom%256 : ((c==0)?252:(32*c));
     if (nu > 8 && qlast < 1) qlast = 1;
     d=48'(valid) | (48'(base)<<1) | (48'(nu)<<9) | (48'(c)<<16) | (48'(c)<<19) | (48'(mode==2)<<22);
     cfg(8+c,d);
   end
   if (mode==0) qlast=1;
   cfg(16, 48'(qlast) | (48'(plast)<<3) | (48'(2*($urandom%64))<<6));
   @(negedge clk); #0.01; cfg_v=0; tick(4);
 endtask
 task automatic beat(input integer kind, input integer gap);
   @(negedge clk); #0.01;
   rnd_x;
   xs_v=(kind!=4); xs_p=ref_dut.u_e.n_pair; xs_b=ref_dut.u_e.n_b; xs_pos=ref_dut.u_e.n_pos;
   xs_sv = ($urandom%8==0) ? 2'($urandom) : 2'b11;
   case(kind)
     1: xs_p=xs_p+8'd1;
     2: xs_b=xs_b+3'd1;
     3: xs_pos=xs_pos+3'd1;
     5: begin xs_p=$urandom; xs_b=$urandom; xs_pos=$urandom%3; end
   endcase
   tick(1); @(negedge clk); #0.01; xs_v=0; rnd_x;
   tick(gap);
 endtask
 task automatic idle_noise(input integer n);
   for (integer i=0;i<n;i=i+1) begin
     @(negedge clk); #0.01; xs_v=($urandom%4==0); xs_p=$urandom; xs_b=$urandom; xs_pos=$urandom%3; rnd_x;
   end
   @(negedge clk); #0.01; xs_v=0;
 endtask
 task automatic phase(input integer mode, input integer rnd_timing);
   integer sent, k, g;
   configure(mode);
   @(negedge clk); #0.01; go=1; tick(1);
   @(negedge clk); #0.01; go=0; tick(rnd_timing ? $urandom%6 : 4);
   sent=0;
   while(ref_dut.u_e.n_run && sent<3000) begin
     g = rnd_timing ? 5+$urandom%12 : 12;
     if (rnd_timing) begin
       k = $urandom%10;
       if (k==0) beat(1+$urandom%5, 1+$urandom%4);
     end else if (sent%9==0) begin beat(1,12); beat(2,12); beat(3,12); beat(4,12); end
     beat(0, g); sent=sent+1;
   end
   if(sent==3000) $fatal(1,"walker failed to finish");
 endtask
 task automatic random_phases(input integer n);
   for (integer r=0;r<n;r=r+1) begin
     phase((r%5==0) ? $urandom%3 : 3, 1);
     case ($urandom%4)
       0: idle_noise(130 + $urandom%200);
       1: idle_noise($urandom%127);
       2: tick($urandom%3);
       3: begin tick(120 + $urandom%15); end
     endcase
     if ($urandom%25==0) begin
       @(negedge clk); #0.01; rst_n=0; resets=resets+1; tick(1+$urandom%3);
       @(negedge clk); #0.01; rst_n=1;
     end
     if ($urandom%15==0) begin
       @(negedge clk); #0.01; go=1; tick(1+$urandom%2); @(negedge clk); #0.01; go=0; tick($urandom%140);
     end
   end
 endtask
 // ---- KV banks: write a random image and read it back (3-cycle read: boundary, macro, output registers)
 reg [255:0] kvm [0:1][0:255];
 task automatic kv_fill_check(input integer n);
   integer a, b;
   for (a = 0; a < n; a = a + 1) begin
     @(negedge clk); #0.01;
     for (b = 0; b < 2; b = b + 1) begin
       for (integer i = 0; i < 8; i = i + 1) kvm[b][a][32*i +: 32] = $urandom;
       kv_wdata[256*b +: 256] = kvm[b][a]; kv_waddr[8*b +: 8] = 8'(a);
     end
     kv_we = 2'b11;
   end
   @(negedge clk); #0.01; kv_we = 0; tick(3);
   for (a = 0; a < n; a = a + 1) begin
     @(negedge clk); #0.01; kv_raddr = {8'(a), 8'(a)};
     tick(3); @(negedge clk);
     for (b = 0; b < 2; b = b + 1)
       if (kv_rd[256*b +: 256] !== kvm[b][a]) $fatal(1, "KV bank %0d word %0d mismatch %h vs %h", b, a, kv_rd[256*b +: 256], kvm[b][a]);
     kv_checks = kv_checks + 1;
   end
 endtask
 // ---- BIST --------------------------------------------------------------------------------------------------
 integer bist_cycles = 0, bist_runs = 0;
 always @(posedge clk) if (bist_busy) bist_cycles = bist_cycles + 1;
 task automatic run_bist;
   integer t0;
   t0 = bist_cycles;
   @(negedge clk); #0.01; bist_start = 1; @(negedge clk); #0.01; bist_start = 0;
   wait (bist_done); tick(2);
   bist_runs = bist_runs + 1;
   $display("BIST done pass=%b sram=%b rom=%b cycles=%0d sig=%h", bist_pass, bist_sram_status, bist_rom_status,
            bist_cycles - t0, rom_sig);
 endtask
 // ---- fault injection (dut only) -----------------------------------------------------------------------------
 reg [8*512-1:0] fname;
 integer fd, n, fm, fk, fr, fc, far, fac, fv, nf = 0;
 integer slot [0:5];
 task automatic inject(input integer m, input integer k, input integer r, input integer c, input integer ar0,
                       input integer ac0, input integer v);
   case (m)
     0: begin dut.u_e.g_mac[0].g_pp.u_rom0.f_kind[slot[0]] = k[3:0]; dut.u_e.g_mac[0].g_pp.u_rom0.f_r[slot[0]] = r;
              dut.u_e.g_mac[0].g_pp.u_rom0.f_c[slot[0]] = c; dut.u_e.g_mac[0].g_pp.u_rom0.f_ar[slot[0]] = ar0;
              dut.u_e.g_mac[0].g_pp.u_rom0.f_ac[slot[0]] = ac0; dut.u_e.g_mac[0].g_pp.u_rom0.f_v[slot[0]] = v[1:0]; end
     1: begin dut.u_e.g_mac[0].g_pp.u_rom1.f_kind[slot[1]] = k[3:0]; dut.u_e.g_mac[0].g_pp.u_rom1.f_r[slot[1]] = r;
              dut.u_e.g_mac[0].g_pp.u_rom1.f_c[slot[1]] = c; dut.u_e.g_mac[0].g_pp.u_rom1.f_ar[slot[1]] = ar0;
              dut.u_e.g_mac[0].g_pp.u_rom1.f_ac[slot[1]] = ac0; dut.u_e.g_mac[0].g_pp.u_rom1.f_v[slot[1]] = v[1:0]; end
     2: begin dut.u_e.g_mac[1].g_pp.u_rom0.f_kind[slot[2]] = k[3:0]; dut.u_e.g_mac[1].g_pp.u_rom0.f_r[slot[2]] = r;
              dut.u_e.g_mac[1].g_pp.u_rom0.f_c[slot[2]] = c; dut.u_e.g_mac[1].g_pp.u_rom0.f_ar[slot[2]] = ar0;
              dut.u_e.g_mac[1].g_pp.u_rom0.f_ac[slot[2]] = ac0; dut.u_e.g_mac[1].g_pp.u_rom0.f_v[slot[2]] = v[1:0]; end
     3: begin dut.u_e.g_mac[1].g_pp.u_rom1.f_kind[slot[3]] = k[3:0]; dut.u_e.g_mac[1].g_pp.u_rom1.f_r[slot[3]] = r;
              dut.u_e.g_mac[1].g_pp.u_rom1.f_c[slot[3]] = c; dut.u_e.g_mac[1].g_pp.u_rom1.f_ar[slot[3]] = ar0;
              dut.u_e.g_mac[1].g_pp.u_rom1.f_ac[slot[3]] = ac0; dut.u_e.g_mac[1].g_pp.u_rom1.f_v[slot[3]] = v[1:0]; end
     4: begin dut.g_kv[0].u_mem.f_kind[slot[4]] = k[3:0]; dut.g_kv[0].u_mem.f_r[slot[4]] = r; dut.g_kv[0].u_mem.f_c[slot[4]] = c;
              dut.g_kv[0].u_mem.f_ar[slot[4]] = ar0; dut.g_kv[0].u_mem.f_ac[slot[4]] = ac0; dut.g_kv[0].u_mem.f_v[slot[4]] = v[1:0]; end
     default: begin dut.g_kv[1].u_mem.f_kind[slot[5]] = k[3:0]; dut.g_kv[1].u_mem.f_r[slot[5]] = r; dut.g_kv[1].u_mem.f_c[slot[5]] = c;
              dut.g_kv[1].u_mem.f_ar[slot[5]] = ar0; dut.g_kv[1].u_mem.f_ac[slot[5]] = ac0; dut.g_kv[1].u_mem.f_v[slot[5]] = v[1:0]; end
   endcase
   slot[m > 5 ? 5 : m] = slot[m > 5 ? 5 : m] + 1;
 endtask
 initial begin
   for (integer i = 0; i < 6; i = i + 1) slot[i] = 0;
   if (!$value$plusargs("seed=%d", SEED)) SEED = 1;
   void'($urandom(SEED));
   if (!$value$plusargs("ROMSIG0=%h", rom_exp[31:0])) rom_exp[31:0] = 0;
   if (!$value$plusargs("ROMSIG1=%h", rom_exp[63:32])) rom_exp[63:32] = 0;
   if (!$value$plusargs("ROMSIG2=%h", rom_exp[95:64])) rom_exp[95:64] = 0;
   if (!$value$plusargs("ROMSIG3=%h", rom_exp[127:96])) rom_exp[127:96] = 0;
   if ($value$plusargs("FAULTS=%s", fname)) begin
     fault_mode = 1;
     fd = $fopen(fname, "r");
     while (fd != 0 && !$feof(fd)) begin
       n = $fscanf(fd, "%d %d %d %d %d %d %d\n", fm, fk, fr, fc, far, fac, fv);
       if (n == 7) begin inject(fm, fk, fr, fc, far, fac, fv); nf = nf + 1; end
     end
     if (fd != 0) $fclose(fd);
     $display("FAULTS injected=%0d", nf);
     tick(4); @(negedge clk); #0.01; bist_rst_n = 1; rst_n = 1;
     tick(4);
     run_bist;
     $finish;
   end
   tick(4); @(negedge clk); #0.01; rst_n=1; bist_rst_n=1;
   kv_fill_check(64);
   // directed
   phase(0,0); tick(700); phase(1,0); tick(700); phase(2,0); tick(700); phase(0,0); tick(700);
   configure(0); @(negedge clk); #0.01; go=1; tick(1);
   @(negedge clk); #0.01; go=0; tick(4); beat(0,3);
   @(negedge clk); #0.01; rst_n=0; resets=resets+1; tick(4);
   @(negedge clk); #0.01; rst_n=1; phase(1,0); tick(300);
   random_phases(NRAND / 2);
   // memory BIST with both elements idle (gate closed: idle > DRAIN)
   tick(300);
   run_bist;
   if (!bist_pass || bist_sram_status !== 4'b0101 || bist_rom_status !== 8'b01010101)
     $fatal(1, "clean BIST failed: pass=%b sram=%b rom=%b", bist_pass, bist_sram_status, bist_rom_status);
   tick(50);
   kv_fill_check(256);
   random_phases(NRAND - NRAND / 2);
   phase(1,0); tick(400);
   if(hits<2000 || issues<2000 || rows<200 || nonzero<100 || classes!=255 || wraps==0 || qadv==0 || restarts<4 ||
      rejected<50 || go_closed<20 || go_drain<20 || resets<3 || bist_cmp<1000)
     $fatal(1,"coverage incomplete h=%0d i=%0d r=%0d w=%0d q=%0d rst=%0d rej=%0d gc=%0d gd=%0d rs=%0d bc=%0d",
            hits,issues,rows,wraps,qadv,restarts,rejected,go_closed,go_drain,resets,bist_cmp);
   $display("PASS seed=%0d compared=%0d exempt=%0d bist_compared=%0d cycles=%0d hits=%0d issues=%0d rows=%0d nonzero=%0d classes=%0d wraps=%0d qadv=%0d restarts=%0d rejected=%0d go_closed=%0d go_drain=%0d resets=%0d kv_checks=%0d bist_runs=%0d",
       SEED,compared,exempt,bist_cmp,cyc,hits,issues,rows,nonzero,classes,wraps,qadv,restarts,rejected,go_closed,go_drain,resets,kv_checks,bist_runs);
   $finish;
 end
endmodule
