`timescale 1ns/1ps
// HBM-BIND B2 (2026-10-24): ot_hbm_su_programme_root_h5 #(PARTS) bench (die su_prog; B2 = PARTS 2, part 0 pgp_NW,
// part 1 pgp_NE). DUT = the edited h5; REF = the unchanged base h5 (4 parts, modules renamed *_ref by run_pgroot_nq.sh).
// One random host stimulus drives both on the same edges: configuration writes (bank uniform over the DUT's bank space
// plus out-of-range banks), starts, lengths, part faults, and three resets (host writes right after each release).
//   PARTS 4: every output of DUT == REF on every edge (r_we, r_bank, r_start, r_len, r_row, r_data, fault).
//   PARTS 2: REF bank = DUT bank for banks < 640, DUT bank + 640 for banks >= 640 (so REF is out of range exactly when
//            the 2-part DUT is); REF p_fault = {0, 0, DUT p_fault}. Every edge: r_start, r_len, r_row, r_data, fault,
//            r_we[1:0] equal; r_bank[k] equal (except the edge after a remapped bank); REF r_we[3:2] never set.
//   Both: model check (independent of REF): r_we[k] one edge after a write to bank 320k .. 320k + 319 (outside the
//         reset windows), r_bank[k] = bank - 320k with it; the sticky fault rises after an out-of-range write.
// Mutants: -P...MUT=1..4 (root5 MUT on the DUT) must FAIL.
module tb_hbm_su_programme_root_h5_nq;
  parameter integer P=4, MUT=0, NCYC=30000, SEED=11;
  localparam integer NB=320*P;
  logic clk=0; always #5 clk=~clk;
  logic rst_n=0, cfg_we=0, start=0;
  logic [15:0] cfg_bank=0, length=0, rbank; logic [6:0] cfg_row=0; logic [255:0] cfg_data=0; logic [3:0] pf=0;
  wire d_start, r_start_r; wire [15:0] d_len, r_len_r; wire [P-1:0] d_we; wire [3:0] r_we_r;
  wire [16*P-1:0] d_bank; wire [63:0] r_bank_r; wire [6:0] d_row, r_row_r; wire [255:0] d_data, r_data_r; wire d_fault, r_fault;
  assign rbank=(P==2 && cfg_bank>=16'd640) ? cfg_bank+16'd640 : cfg_bank;
  ot_hbm_su_programme_root_h5 #(.PARTS(P),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(cfg_bank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),.p_fault(pf[P-1:0]),.r_start(d_start),
    .r_len(d_len),.r_we(d_we),.r_bank(d_bank),.r_row(d_row),.r_data(d_data),.fault(d_fault));
  ot_hbm_su_programme_root_h5_ref ref4(.clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_bank(rbank),
    .cfg_row(cfg_row),.cfg_data(cfg_data),.start(start),.length(length),.p_fault((P==4)?pf:{2'b00,pf[1:0]}),.r_start(r_start_r),
    .r_len(r_len_r),.r_we(r_we_r),.r_bank(r_bank_r),.r_row(r_row_r),.r_data(r_data_r),.fault(r_fault));
  integer t, k, err=0, nchk=0, nwr=0, noor=0, nst=0, seed=SEED, since_rel=0;
  integer oor_t=0; logic mapped_q=0, we_q=0, oor_seen=0; logic [15:0] bank_q=0;
  task automatic bad(input string what); err++; if(err<10) $display("ERR t=%0d %s", t, what); endtask
  initial begin
    for(t=0;t<NCYC;t++) begin
      @(negedge clk);
      // ---- checks of the edge just passed
      if(t>4) begin
        nchk+=6;
        if(d_start!==r_start_r) bad("r_start");
        if(d_len!==r_len_r) bad("r_len");
        if(d_row!==r_row_r) bad("r_row");
        if(d_data!==r_data_r) bad("r_data");
        if(d_fault!==r_fault) bad($sformatf("fault dut=%b ref=%b", d_fault, r_fault));
        for(k=0;k<P;k++) begin
          nchk+=2;
          if(d_we[k]!==r_we_r[k]) bad($sformatf("r_we[%0d] dut=%b ref=%b", k, d_we[k], r_we_r[k]));
          if(!(P==2 && mapped_q) && d_bank[16*k+:16]!==r_bank_r[16*k+:16]) bad($sformatf("r_bank[%0d]", k));
          // model
          if(since_rel>4) begin
            nchk++;
            if(d_we[k] !== (we_q && bank_q>=16'(320*k) && bank_q<16'(320*k+320))) bad($sformatf("model r_we[%0d]", k));
            if(d_we[k] && d_bank[16*k+:16]!==bank_q-16'(320*k)) bad($sformatf("model r_bank[%0d]", k));
          end
        end
        if(P==2) begin nchk++; if(r_we_r[3:2]!==2'b00) bad("ref r_we[3:2] set by a remapped bank"); end
        if(oor_seen && t>oor_t+8) begin nchk++; if(d_fault!==1'b1) bad("sticky fault missing after out-of-range write"); end
      end
      // ---- reset windows: t 0..3, 9000..9003, 18000..18003, 24000..24001
      if(t<4 || (t>=9000&&t<9004) || (t>=18000&&t<18004) || (t>=24000&&t<24002)) begin rst_n=0; since_rel=0; oor_seen=0; end
      else begin rst_n=1; since_rel++; end
      // ---- stimulus for the next edge (host writes also inside the 3 edges after a release: dropped everywhere)
      cfg_we=($urandom(seed)%10)<3; seed=seed+1;
      cfg_bank=($urandom%50==0) ? 16'(NB+$urandom%700) : 16'($urandom%NB);
      cfg_row=7'($urandom); cfg_data={8{$urandom}};
      start=($urandom%50==0); length=16'($urandom);
      pf=(t%3001==1500) ? 4'($urandom) : 4'd0;
      if(t>=4000 && t<9000) cfg_bank=16'($urandom%NB);         // a window without out-of-range writes (fault off)
      mapped_q=(cfg_bank>=16'd640); we_q=cfg_we&&rst_n; bank_q=cfg_bank;
      if(cfg_we && cfg_bank>=16'(NB) && since_rel>4 && !oor_seen) begin oor_seen=1; oor_t=t; end
      if(cfg_we) nwr++; if(cfg_we && cfg_bank>=16'(NB)) noor++; if(start) nst++;
    end
    $display("SU_PGROOT_NQ%0d %s checks=%0d errors=%0d writes=%0d oor=%0d starts=%0d MUT=%0d", P, err==0?"PASS":"FAIL",
             nchk, err, nwr, noor, nst, MUT);
    $finish;
  end
endmodule
