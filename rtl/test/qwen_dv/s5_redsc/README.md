Smallest-mechanism extraction review and fleet bench
==================================================
The generator reads the recovered s5 leaves without changing them. The red
reference extracts the original qfd_dv_su8_entries input masking/registers and
reducer instantiation, with independent reset landing. The sc reference unpacks
configuration as a concatenation and calls original qfd_dv_scalar2 directly.
Tests cover full 16-vector SUM/SQ/MAX segments, directional scalar passing,
a four-input root sum, and same-user argmax. Each mechanism has a data-path
mutant (red square control inversion, scalar incoming data corruption).
Run only on fleet Verilator 5.050: bash rtl/test/qwen_dv/s5_redsc/run.sh OUT LEAF.
Generated benches/references and run/build logs live under OUT.

Static review (production MUT=0, SU_LT=1, MU_NU=4)
------------------------------------------------
No production zero-edge discrepancy identified in red/sc/lrly/suvm extraction.
Reset depths match: slice two stages; SU control/group/lane one extra stage;
lane IREG/OREG reset another stage. LTD AC=1/AQ=1 relay depths and both packed
lane bundles match original source. This is source review, not simulation proof.
Compatibility defect: recovered sc hardcodes MU_MUT=0, losing original
OT_DV_AMAX_MUT=6/7 witnesses; ctl likewise hardcodes amax MUT=0. Restore original
macro-to-parameter mapping before reusing those witness benches.

Safe-design checklist: NOT READY FOR GATE
1 PIN BLOCKED: sc input dn/up decode and own-word selection occur before first
  flop; red input lane mask occurs before rd_x. Upstream face launch registers
  do not constitute local raw pin landing registers.
2 REACH UNMEASURED: no dimensions/placement evidence reviewed.
3 FANOUT UNMEASURED: reset and cfg/source fanout need synthesized kept-copy census.
4 DEPTH UNMEASURED: no synthesis/STA; no combinational input-output path observed
  except reset output h_rst_n, intentionally the lane reset forwarding net.
5 STORAGE BLOCKED: original red uses data delay lines D>=3, notably per-element
  chain alignment up to D18 and tag D21. Requires safe SRAM/ring implementation
  or explicit owner disposition. Scalar production root slots are only 1024 bits;
  its long sequential-fold data delays occur only in MUT1, not production.
6 FLOORPLAN UNMEASURED: no kit recommended.
7 CLOCK UNMEASURED: local reset landing exists, no spread/native boundary result.
8 SCHEDULE production extraction adds zero edges by source review; all hardened
  ctl command/write additions require separately priced integration verification.
No gate/submission authorization is implied by this packet.
