Actual ML5/RD2 native head recovery, 2026-10-19

The failed historical qfd_dv_lane_h is ML1 and remains unchanged. The current
production prototype uses ML5/RD2, inner ML11. The measured +6 edges in
safe_qw_slice_w_1019/su8_timing.json belong to the complete landed SU loop;
the banked TLS candidate adds zero data edges and zero reset-release edges.

Fleet Yosys0.68 baseline:46,859generic cells/10,434FF/one legacy128x256 SRAM;
root rt has1,686 reset loads. Generic SRAM banking census:46,860cells/sameFF,
two actual128x64 dualclock native macros, both clocks tied to the same actual
clock. Each33.72x27.576um; total1,859.72544um2 hard area. No mapped standard
area, floorplan, CTS, timing or physical qualification is asserted.

TLS data is126bits, proven by TT62 plus B/C64. The legacy256-bit store padded
upper130zero and observed low126 only. The new two-bank store retains126,
pads two zero, disables those two write-mask bits, and observes low126.
Pointer, read/capture pipeline, finite128slots and class depths are unchanged.
The native compiler dependency is byte-exact e26d92503; its external PG/via
escape qualification remains open. Unique master/top:
qfd_dv_lane_h_native_b64 (same ports as qfd_dv_lane_h_landed). This is an
isolated, unadopted source fork; the generator/parent must explicitly select
its identity after exactness and native closure.

Production run bank64_r3 uses actual final4ec4aa5f2 bank64/CFG source composed
with helper5753e895b, regenerated landed slice, full eight lanes and four users.
It runs a/c/f/g/k/q/m/o/n, then wrong-bank and wrong-TLS-slot mutants with5.050.
Root's scalar16boot guard plus two existing landed release edges is18;
that boot guard is outside steady timing. Initial staging failures (missing
hdc_golden; missing required SAFE_STORAGE define) launched no RTL and remain
in scratch logs. Preserve the live r3 directory and compiled objects.

Next: collect real positives/mutants; commit each actual fail witness. Replace
>=3-edge delay shifts (ML11 tags, LM5/LA4 data, TAP0 and valid lines) with finite
ring/SRAM preserving exact ages; balance reset and control fanout. Existing
qfd_dv_reset_bank/reset_tree may preserve data-reset semantics. DRST0 requires
actual consumer-valid qualification/reset proof and is not adopted here.
Only then map real standard area, create a 40–60percent fullwidth band within
the helper's provisional216x172.8 maximum, actual43.2-lattice macro placement,
complete native clock/fanout/pin audit, and launch a distinct kit. No critical
REVIEW/submit before root PNG approval. xs_leaf remains a distinct actual
storage/native blocker; no qualified hard view was recovered.
