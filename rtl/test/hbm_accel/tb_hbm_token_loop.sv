`timescale 1ps/1ps
// hbm-system 2026-10-08: bench of ot_hbm_token_loop.  The scenario file (tools/hbm_token_loop_bench.py) lists jobs:
//   J id tok pos ngen eos eos_en maxpos mtp hoststop_after   then the model's token stream:
//   AR: T tok ... (the merged argmax each step returns, in order)   MTP: B n t0 .. t5 (committed verify batches)
// The bench plays the cmdproc (doorbell -> random latency -> completion) and the DSpark commit, prints every host
// record (R last status job pos tok), every doorbell (D tok pos) and MTP emit counts (E n stop), random host stalls.
module tb_hbm_token_loop #(parameter integer MUT = 0);
  reg clk = 0, rst_n = 0; always #417 clk = ~clk;
  reg job_v = 0, host_stop = 0, hr_rdy = 0, cpl_v = 0, mtp_v = 0; reg [31:0] job_id; reg [16:0] job_tok, job_eos, cpl_token;
  reg [19:0] job_pos, job_ngen; reg [20:0] job_maxpos; reg job_eos_en, job_mtp; reg [3:0] cpl_status = 0;
  reg [2:0] mtp_n; reg [6*17-1:0] mtp_tok;
  wire job_rdy, hr_v, db_v, cpl_rdy, mtp_emit_v, mtp_stop, busy; wire [73:0] hr_d; wire [16:0] db_token; wire [19:0] db_pos;
  wire [31:0] db_job, st_tokens, st_hq_stall; wire [2:0] mtp_emit, last_status;
  reg db_rdy = 0;
  ot_hbm_token_loop #(.MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .post_en(1'b1), .job_v(job_v), .job_rdy(job_rdy),
    .job_id(job_id), .job_tok(job_tok), .job_pos(job_pos), .job_ngen(job_ngen), .job_eos(job_eos), .job_eos_en(job_eos_en),
    .job_maxpos(job_maxpos), .job_mtp(job_mtp), .host_stop(host_stop), .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_d(hr_d),
    .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(db_job), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy),
    .cpl_token(cpl_token), .cpl_status(cpl_status), .mtp_v(mtp_v), .mtp_n(mtp_n), .mtp_tok(mtp_tok),
    .mtp_emit_v(mtp_emit_v), .mtp_emit(mtp_emit), .mtp_stop(mtp_stop), .busy(busy), .last_status(last_status),
    .st_tokens(st_tokens), .st_hq_stall(st_hq_stall));
  integer stall_host = 0;
  integer fi, fo, rc, k2, k, n, hsa, steps, seen_last, x0, x1, x2, x3, x4, x5, x6;
  string line, kw;
  reg [16:0] ts [0:4095]; integer nt, it; reg [16:0] bt [0:1023][0:5]; integer bn [0:1023]; integer nb, ib;
  always @(posedge clk) begin
    hr_rdy <= (stall_host > 0) ? 1'b0 : (($urandom % 4) != 0);
    if (stall_host > 0) stall_host <= stall_host - 1;
    if (hr_v && hr_rdy) begin
      $fdisplay(fo, "R %0d %0d %0d %0d %0d", hr_d[73], hr_d[72:70], hr_d[69:38], hr_d[37:17], hr_d[16:0]);
      if (hr_d[73]) seen_last = 1;
    end
    if (mtp_emit_v) $fdisplay(fo, "E %0d %0d", mtp_emit, mtp_stop);
  end
  initial begin
    fi = $fopen("scen.txt", "r"); fo = $fopen("out.txt", "w");
    repeat (5) @(posedge clk); rst_n = 1;
    rc = 9;
    while (!$feof(fi) && rc == 9) begin
      rc = $fscanf(fi, "J %d %d %d %d %d %d %d %d %d\n", job_id, job_tok, job_pos, job_ngen, job_eos, job_eos_en, job_maxpos,
                   job_mtp, hsa);
      if (rc == 9) begin
      k2 = $fscanf(fi, "N %d\n", n);
      nt = 0; nb = 0;
      for (k = 0; k < n; k = k + 1)
        if (job_mtp) begin k2 = $fscanf(fi, "B %d %d %d %d %d %d %d\n", x0, x1, x2, x3, x4, x5, x6);
          bn[nb] = x0; bt[nb][0] = x1; bt[nb][1] = x2; bt[nb][2] = x3; bt[nb][3] = x4; bt[nb][4] = x5; bt[nb][5] = x6;
          nb = nb + 1; end
        else begin k2 = $fscanf(fi, "T %d\n", x0); ts[nt] = x0; nt = nt + 1; end
      @(posedge clk); job_v <= 1;
      @(posedge clk); while (!job_rdy) @(posedge clk); job_v <= 0;
      it = 0; ib = 0; steps = 0; seen_last = 0;
      if (job_id == 1000) stall_host = 100;
      fork : run
        begin   // AR cmdproc / MTP commit
          while (busy || job_v) begin
            @(posedge clk);
            if (!job_mtp) begin
              if (db_v && !db_rdy && ($urandom % 2)) db_rdy <= 1;
              else if (db_v && db_rdy) begin
                db_rdy <= 0; $fdisplay(fo, "D %0d %0d", db_token, db_pos);
                steps = steps + 1;
                if (hsa != 0 && steps == hsa) host_stop <= 1;
                repeat (3 + $urandom % 20) @(posedge clk);
                host_stop <= 0;
                cpl_token <= (it < nt) ? ts[it] : 17'd99; it = it + 1; cpl_v <= 1;
                @(posedge clk); while (!cpl_rdy) @(posedge clk); cpl_v <= 0;
              end
            end else if (dut.ls == 4) begin
              repeat (2 + $urandom % 6) @(posedge clk);
              steps = steps + 1;
              if (hsa != 0 && steps == hsa) host_stop <= 1;
              mtp_n <= bn[ib]; mtp_tok <= {bt[ib][5], bt[ib][4], bt[ib][3], bt[ib][2], bt[ib][1], bt[ib][0]};
              ib = ib + 1; mtp_v <= 1; @(posedge clk); mtp_v <= 0; host_stop <= 0;
            end
          end
          while (!seen_last) @(posedge clk);
          repeat (4) @(posedge clk);
          disable run;
        end
        begin repeat (500000) @(posedge clk); $fdisplay(fo, "TIMEOUT"); disable run; end
      join
      $fdisplay(fo, "X %0d", job_id);
      end
    end
    $fdisplay(fo, "END"); $fclose(fo); $finish;
  end
endmodule
