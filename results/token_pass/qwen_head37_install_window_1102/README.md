# Stage37 HEAD table-install window (TOK-QW-4, 11-02/03)

Ledger item (a), HEAD_TABLE_INSTALL_START: MEASURED on main RTL with the genuine rank0 HEAD37 ROMs.

- `slice/`: 12 x `qfd_dv_slice_tload #(HEAD_STAGE37 1)`, treq face driven directly. It runs a stage36->stage37
  spacing sweep, single-load occupancy, a stream-write collision sweep, and a 148-load boot install.
- `e2e/`: the actual `qfd_dv_cmd_cal_mu_head37` with the nent1021 calendar image, then treq_q, then the 12 slices.
  It runs the same sweep through CTLM range starts and a 148-range boot install at spacing 65 / 89 / 90.

Result:
- Loader occupancy is 90 edges. Any two LOCAL4/LOCAL37 range starts must be >= 90 edges apart. At 89 all 12 slices fault.
  The CTLM itself does not fault, so the CTLM-only gate's 65-edge spacing is not a valid schedule.
- The native image has no TLOAD (LOCAL kind 3) entries, so `s_we` never asserts and the stream exclusive window is
  vacuous. As a control, stream writes on loader edges (offsets 3..84) fault as designed.
- Stage37 tables are disjoint from every transformer stage row. They therefore install at BOOT, after stage 36, and
  stay resident. There is no runtime install and no overlap with stage36 traffic.
- Boot install of 4 users x 37 stages at spacing 90 has 0 faults and exact write counts. The last write is 13,324 edges
  after the first range start (T_die = 0).

Details: `receipt.json`. Re-run with `bash slice/run.sh` and `bash e2e/run_e2e.sh` (Verilator 5.050). Each needs the
ROMs under `rom/`.
