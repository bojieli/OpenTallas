# CLAUDE WFC (dsrom-wfc-split) STATUS
## 2026-10-06 03:46 PT: started. Worktree local /home/ubuntu/wt-wfc-split, branch claude/dsrom-wfc-split-20261006.
## 03:54 PT: RTL 0bfdac8f0 (REC_SRAM, UPOS_LWR) exact: eq/s1_all PASS 27712, eq/s0_all_r2 STREAM PASS, negatives FAIL. lat_all 4806721 vs lat_off 4805921 (ref 4804444).
Routes r1/src_* here (src-361c1387a), r1/stg_* on ot-epyc2 /srv/opentallas-scratch2/scratch/claude/dsrom-wfc-split/r1. Stage bench stage_w1_all (wt-361c1387a).
## 04:45 PT (resumed agent): r1 CTS probes (in-context STA on 4_cts.odb, placement parasitics): src incontext -574 / reg2reg -242, stg -98.
  Root cause #1: routed SDC timed IO against the IDEAL clock while insertion is ~520 ps (src) / ~330 (stg) -> repair_timing hold-padded EVERY input with 300-500 ps of BUFx2 chains, which then fail setup in context (cfg->steps -574, in_data->res_v -549, in_valid->hdr_* -309).
  Root cause #2 (reg2reg): rippled +1 / compares: hdr_pos+1 -> 28 upos copies -242, o_p -> b_rec -110, next_u<cfg_users -> pr_pos -104, pos_c+WIN -> proto_fault -98, txq_n -> counters -88; job_done->txq_d fanout -40.
  Fix dea71c1bd: SDC io_clk (source latency 480/600 src, 290/410 stg); CFG_Q (registered static cfg, KS steps pipeline); PRECOMP (EX compares from earlier registers, KS increments/compares, registered hdr_pos+1).
  Exact eq (src-dea71c1bd): s1_all PASS 27712 (cycles 926458 = r1), seed7 PASS, s0_all STREAM PASS, pre-only PASS both, lat_all 4806721 (= r1, 0 cycles), negatives FAIL as required.
  r2 routes (EPYC1): r2/src_u45,u50,u55 r2/stg_u45,u55,u60 started 04:42. r1 routes left running (comparison).
## 06:25 PT
  r2 stg (dea71c1bd) ROUTED: u45 incontext +2.6 / FF hold +7.7, u55 +6.0 / +10.0, u60 -1.4 / +10.5 (SS hold +50); DRC 0 / antenna 0; BUT 8 SS max-slew violators (hdr_user->upos lo net) on u45/u55 -> not closed. rec_r2_stg.json.
  r2 src CTS: u45 -88 (in_data type -> sww / in_ready), u50 -2.4; r3 (d7eecd4ce IN_DEC + TXQ_SLICE) src CTS: u45 -80 / u50 -71 / u55 -1.3 all txh -> vm_we/in_ready (rx word < txh ripple).
  54ab6b313 RDY_LT (log-depth compare): eq r5 all PASS (same cycles), negatives FAIL; stage bench r5 running.
  Running: r2 src u45/50/55 (route), r3 src u45/50/55 + stg u55, r4 stg u50sm/u55sm (r3 RTL + SLEW/CAP_MARGIN 20), r5 src u50sm/u55sm/u55 + stg u55sm (54ab6b313).
  Closure rule (record cmd): SS setup + SS/FF hold >= 0 incontext & reg2reg, DRC/antenna 0, slew/cap/fanout violators 0 at SS & FF. block mode (IO vs io_clk estimate) reported only.
## 07:30 PT -- OWNER MARGIN-FIRST RULE applied (OWNER_RULE_MARGIN_FIRST_20261006.txt)
  Routed so far (none margin-closed): r4/stg_u50sm (d7eecd4ce) CLOSED at +12.4 incontext / FF hold +9.9 / slew 0 (below +60/+15 margin target); r2 stg +2.6..+6 (slew viols); r2 src_u55 +8.2 / FF -2.2 / 64 slew; r3 src_u55 -3.1 / 38 slew.
  c5e4394c9 (= ca09d1a68 + NEG_ROW2): MARGIN knob = core_done/token/value pin flops (+1 cycle/completion, launch hold-off +1), upos read strobe per-group copies, registered conservative word-free compare; plus FANOUT_COPY / RDY_LT / TXQ_SLICE / IN_DEC / PRECOMP / CFG_Q.
  Exact eq (Verilator 5.050): s1_all PASS 27712, seed7 PASS, s0 STREAM PASS 940000 flits; negatives neg_s0_upos FAIL, NEG_ROW2 FAIL (NEG_ROW ring-slot corruption self-heals via rewind under MARGIN timing -> PASS; NEG_ROW2 is the SRAM-row control now).
  Cycle cost (MARGIN): realistic lat bench (CLAT 12000) 4806721 -> 4807121 (+0.008 %); stress benches (CLAT 6) s1 +1.55 %, s0 +1.2 % (per-completion +1 cycle).
  r7 routes (EPYC1, route 770 ps, signoff 833, SLEW/CAP 20 %, HOLD margin 20): src u50 / u55 / u50 aspect 0.8, stg u45 / u50 / u55. Records report incontext, reg2reg, die150 (IO vs die clock +-150 ps), margin_closed (+60 setup / +15 hold).
  NOT done (protocol change, reported): fully registered element boundary. in_ready is combinational from the inbound type bits, vm_we / out_data from internal state; a registered valid/ready boundary needs a skid/credit link (Turing routers) and a +2 VM read-latency pipeline. die150 shows the cost.
  r6 stopped before CTS (superseded); r5 src (past CTS) left running.
