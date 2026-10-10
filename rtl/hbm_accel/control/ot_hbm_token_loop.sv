`timescale 1ps/1fs
`default_nettype none
// hbm-system 2026-10-08 (T3 gap 7): ON-DIE TOKEN LOOP and STOP CONDITION of the DS-V4.1 HBM accelerator die.
//
// Replaces the per-token host doorbell.  Before: every AR step waited on completion -> host -> doorbell {token,
// position} to each of the 96 dies (unpriced, no fan-out design).  Now the host posts ONE job descriptor
// {job, first token, first position, ngen, eos id, eos enable, max position}; every die runs this identical,
// deterministic loop: all 96 dies hold the same merged argmax (the head's final top-1 collective), so they take the
// same decisions with no inter-die message, and the next step's doorbell is issued on the die
// (cpl -> db in DB_LAT registered cycles).  Only the die strapped post_en (die 0) posts token records to the host;
// posting is through a FIFO and never gates the loop unless the FIFO is full (back-pressure, counted).
//
// Stop rules (tools/hdc_golden_v41.py generate / generate_spec + the HF convention): a generated token equal to
// eos_id (eos_en) is EMITTED and ends the job (status EOS); the job also ends after ngen emitted tokens (LEN) or when
// the next position would reach max_pos (MAXPOS); a cmdproc fault ends it (FAULT); the host may stop it (HOST).
// MTP (DSpark): mtp_v delivers the n (1..6) tokens a verify step commits, in order; the loop emits them up to and
// including the first EOS, and no further than ngen / max_pos, returns mtp_emit (the effective count, which the
// spec state commits) and mtp_stop.  In MTP mode the step sequencing stays in ot_dshbm_dspark_ctl.
// Record to host: {last, status3, job32, pos21 (the emitted token's position; 2^20 for the last of a 1M context), tok17}.  Status: 0 RUN 1 EOS 2 LEN 3 MAXPOS 4 FAULT 5 HOST.
module ot_hbm_token_loop #(
  parameter integer TW = 17, PW = 20, parameter integer DB_LAT = 2, parameter integer HQ_AW = 3,
  parameter integer EXTERNAL_FAULT_EN = 0,
  parameter integer MUT = 0                      // bench negative control: 1 = EOS compare disabled
)(
  input  wire          clk, rst_n,
  input  wire          post_en,
  input  wire          external_fault,
  // host: job descriptor and stop
  input  wire          job_v, output wire job_rdy,
  input  wire [31:0]   job_id, input wire [TW-1:0] job_tok, input wire [PW-1:0] job_pos, input wire [PW-1:0] job_ngen,
  input  wire [TW-1:0] job_eos, input wire job_eos_en, input wire [PW:0] job_maxpos, input wire job_mtp,
  input  wire          host_stop,
  // host: token records (posted)
  output wire          hr_v, input wire hr_rdy, output wire [TW+PW+36:0] hr_d,
  // cmdproc (AR): doorbell out, completion in
  output reg           db_v, input wire db_rdy, output reg [TW-1:0] db_token, output reg [PW-1:0] db_pos,
  output reg [31:0]    db_job,
  input  wire          cpl_v, output wire cpl_rdy, input wire [TW-1:0] cpl_token, input wire [3:0] cpl_status,
  // MTP commit
  input  wire          mtp_v, input wire [2:0] mtp_n, input wire [6*TW-1:0] mtp_tok,
  output reg           mtp_emit_v, output reg [2:0] mtp_emit, output reg mtp_stop,
  // status
  output reg           busy, output reg [2:0] last_status, output reg [31:0] st_tokens, output reg [31:0] st_hq_stall
);
  localparam [2:0] S_RUN = 0, S_EOS = 1, S_LEN = 2, S_MAX = 3, S_FLT = 4, S_HOST = 5;
  localparam [2:0] L_IDLE = 0, L_DB = 1, L_WAIT = 2, L_TURN = 3, L_MTP = 4, L_EMIT = 5, L_DONE = 6;
  reg [2:0] ls;
  reg [31:0] job; reg [TW-1:0] eos; reg eos_en, mtp; reg [PW:0] maxpos; reg [PW-1:0] ngen, nemit;
  reg [PW-1:0] pos;                                   // position of the step in flight (AR) / next to emit (MTP)
  reg [3:0] turn;
  reg stop_req;
  // ---------------------------------------------------------------- host record FIFO
  localparam integer HD = 1 << HQ_AW;
  reg [TW+PW+36:0] hq [0:HD-1]; reg [HQ_AW:0] hw, hr_;
  wire hq_full = (hw - hr_) == HD[HQ_AW:0], hq_ne = (hw != hr_);
  assign hr_v = hq_ne; assign hr_d = hq[hr_[HQ_AW-1:0]];
  reg pv; reg [TW+PW+36:0] pd;                               // one record to push this cycle
  always @(posedge clk) if (pv && post_en && !hq_full) hq[hw[HQ_AW-1:0]] <= pd;
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin hw <= 0; hr_ <= 0; end
    else begin hw <= hw + ((pv && post_en && !hq_full) ? 1'b1 : 1'b0); hr_ <= hr_ + ((hr_v && hr_rdy) ? 1'b1 : 1'b0); end
  // Reserve the registered push before authorizing another emission.
  // MUT=2 restores the overflow bug for the directed negative control.
  wire [HQ_AW+1:0] hq_reserved = {1'b0, (hw - hr_)} + ((pv && post_en) ? 1'b1 : 1'b0)
                              - ((hr_v && hr_rdy) ? 1'b1 : 1'b0);
  wire can_post = !post_en || ((MUT == 2) ? !hq_full : (hq_reserved < HD));
  // ---------------------------------------------------------------- the stop decision of one emitted token
  function automatic [2:0] verdict(input [TW-1:0] t, input [PW-1:0] p_, input [PW-1:0] ne_);
    begin
      if (eos_en && t == eos && MUT != 1) verdict = S_EOS;
      else if (ne_ + 1'b1 >= ngen) verdict = S_LEN;
      else if ({1'b0, p_} + 2'd2 > maxpos) verdict = S_MAX;   // the next step would run at p_ + 1 >= maxpos
      else verdict = S_RUN;
    end
  endfunction
  assign job_rdy = (ls == L_IDLE);
  assign cpl_rdy = (ls == L_WAIT) && can_post;
  // MTP emission: one token a cycle from the committed batch
  reg [6*TW-1:0] mb; reg [2:0] mn, mi;
  wire [TW-1:0] tk_cpl = cpl_token, tk_mtp = mb[TW*mi +: TW];
  wire [2:0] v_cpl = (cpl_status != 0) ? S_FLT : verdict(tk_cpl, pos, nemit);
  wire [2:0] v_mtp = verdict(tk_mtp, pos, nemit);
  always @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      ls <= L_IDLE; db_v <= 1'b0; busy <= 1'b0; last_status <= 0; st_tokens <= 0; st_hq_stall <= 0; pv <= 1'b0;
      mtp_emit_v <= 1'b0; mtp_stop <= 1'b0; stop_req <= 1'b0; turn <= 0; nemit <= 0; pos <= 0; mi <= 0; mn <= 0;
    end else begin
      pv <= 1'b0; mtp_emit_v <= 1'b0;
      if (host_stop && busy) stop_req <= 1'b1;
      if ((ls == L_WAIT || ls == L_EMIT) && post_en && hq_full) st_hq_stall <= st_hq_stall + 1;
      if (EXTERNAL_FAULT_EN && external_fault && busy && ls != L_DONE) begin
        db_v <= 1'b0; mtp_stop <= 1'b1;
        // Reserve room for the previous registered push before posting abort.
        if (can_post) begin
          pv <= 1'b1; pd <= {1'b1, S_FLT, job, {1'b0,pos}, {TW{1'b0}}};
          last_status <= S_FLT; mtp_emit_v <= mtp; mtp_emit <= 0; ls <= L_DONE;
        end
      end else case (ls)
        L_IDLE: if (job_v) begin
          job <= job_id; eos <= job_eos; eos_en <= job_eos_en; maxpos <= job_maxpos; ngen <= job_ngen; mtp <= job_mtp;
          nemit <= 0; pos <= job_pos; busy <= 1'b1; stop_req <= 1'b0; mtp_stop <= 1'b0;
          db_token <= job_tok; db_pos <= job_pos; db_job <= job_id;
          ls <= job_mtp ? L_MTP : L_DB;
        end
        L_DB: begin                                          // AR: doorbell the step on this die's cmdproc
          db_v <= 1'b1;
          if (db_v && db_rdy) begin db_v <= 1'b0; ls <= L_WAIT; end
        end
        L_WAIT: if (cpl_v && can_post) begin                  // AR: the step's merged argmax
          pv <= 1'b1; st_tokens <= st_tokens + 1; nemit <= nemit + 1'b1;
          if (v_cpl != S_RUN || stop_req) begin
            pd <= {1'b1, (v_cpl != S_RUN) ? v_cpl : S_HOST, job, {1'b0, pos} + 1'b1, tk_cpl};
            last_status <= (v_cpl != S_RUN) ? v_cpl : S_HOST; ls <= L_DONE;
          end else begin
            pd <= {1'b0, S_RUN, job, {1'b0, pos} + 1'b1, tk_cpl};
            db_token <= tk_cpl; db_pos <= pos + 1'b1; pos <= pos + 1'b1; turn <= 4'(DB_LAT); ls <= L_TURN;
          end
        end
        L_TURN: if (turn <= 1) ls <= L_DB; else turn <= turn - 1'b1;
        L_MTP: if (mtp_v) begin mb <= mtp_tok; mn <= mtp_n; mi <= 0; ls <= L_EMIT; end
        L_EMIT: if (can_post) begin                           // MTP: emit the committed tokens in order
          pv <= 1'b1; st_tokens <= st_tokens + 1; nemit <= nemit + 1'b1; pos <= pos + 1'b1;
          if (v_mtp != S_RUN || (stop_req && mi == mn - 1)) begin
            pd <= {1'b1, (v_mtp != S_RUN) ? v_mtp : S_HOST, job, {1'b0, pos} + 1'b1, tk_mtp};
            last_status <= (v_mtp != S_RUN) ? v_mtp : S_HOST;
            mtp_emit_v <= 1'b1; mtp_emit <= mi + 1'b1; mtp_stop <= 1'b1; ls <= L_DONE;
          end else begin
            pd <= {1'b0, S_RUN, job, {1'b0, pos} + 1'b1, tk_mtp};
            if (mi == mn - 1) begin mtp_emit_v <= 1'b1; mtp_emit <= mn; ls <= L_MTP; end
            mi <= mi + 1'b1;
          end
        end
        default: begin busy <= 1'b0; ls <= L_IDLE; end      // L_DONE
      endcase
    end
endmodule
`default_nettype wire
