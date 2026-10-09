# MX1 CP-south native MTP master: registered MTP boundary (mtp-lead, 2026-10-09)

Why: the first loop routes of hfd_cmdproc_s_mtp_native_mx1 (6adb6c001) failed.
- hm15 (EPYC2): GRT-0183 twice, f_mtp[3] boxed in; hm0 (EPYC4): GRT-0183 on f_mtp[8], then EARLY_FAIL_SETUP post-CTS
  TT -656.8 ps, 1,659 endpoints, TNS -585 ns.
- Worst classes: input -> output f_backend[8] -> t_mtp[179] (identity compare -> am_owned, 348 ps cells), input -> reg
  f_backend[72] -> emit_queue.storage (-547.9), rst[0] recovery (-12.4).  The MTP side was combinational pin to pin
  (admit -> t_host[0], controls -> t_mtp, t_emit / t_provider pure feedthroughs); under the die IO budgets (~38 % of the
  cycle outside on each side) any pin-to-pin path fails, even with no logic.
- GRT: f_mtp[0 +: 43] (provider addresses) fed t_provider ~100-160 um away along the dense bottom-edge pin row
  (517 f_mtp pins at 0.192 um pitch, 450-549 um), on nets with both ends in the pin band.  Global utilisation was
  25-32 %: local, not die-level, congestion.

Fix (RTL, physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv, parameter REGB = 1 default):
- every MTP valid/ready channel crosses an ot_sc_pfifo pin FIFO (job, emit, command in, command out, completion,
  host records, host done); level inputs get one pin flop; every output is a flop; MTP reset registered (2-flop).
- native done is held behind the emit FIFO and host done behind the host-record FIFO; the job pin ready carries a
  registered admission-open bit (no job parked while admission is closed until the drained reset).
- REGB = 0 is the original wiring; the MTP side moved unchanged into hfd_cmdproc_s_mtp_native_mx1_mtp.
- Cost: +1 cycle per crossing, ~+4 per command round trip; the provider read loop +2, so the controller waits PRL 4
  (new parameter of ot_hfd_mtp_core_cp_stop / hfd_mtp_x_cp_stop / hfd_mtp_native_cp_stop, default 2 = unchanged;
  hgi_mtp_native default 4).

Gate (gate.json, EPYC4, iverilog): PASS.
| Case | Result |
|---|---|
| R system: hgi_mtp_native (PRL 4) + physical top (AR + REGB) + typed backend, 2 drained-reset jobs x 4 tokens | PASS 26,539 cycles (unregistered composition 25,511) |
| R mutants: host done not held / PRL 2 / backend wrong job | FAIL x 3 |
| D directed pins: 6 owned AM on identity lines, 12 tokens + done behind both pin FIFOs, ACK, drained reset, wrong job | PASS |
| D mutants: native done not held behind the emit FIFO / host done not held | FAIL x 2 |
| L legacy 6adb6c001 cycle-exact top bench on REGB = 0 | PASS |

hgi_mtp_native gate at PRL 4 (hgi_mtp_native_gate_prl4.json): PASS, connected 25,511 cycles (25,486 at PRL 2),
wrong-job mutant FAIL, CP-result stop cases 6/6.

Routes: hfd_cmdproc_s_mtp_native_mx1_rb-{hm0, hm15}-84549d5ee-tc (bench = this gate + the done-overtake mutant).
