# Actual F20 installation of the SU sparse programme image

The existing SU collar accepted only consecutive linear programme addresses.
The actual DS layer 0 record 31 programme writes banks and rows: its first
8 words address 0..7, and its next word addresses bank 4 row 0 (linear 512).
The old source rejects that ninth real F20 frame. `original_row512_reject.log`
preserves the measured failure (gold1 unit 118995-1792732504).

The opt-in `SPARSE_SU=1` correction preserves all ports and all dense collar
variants. It accepts only the selected SU source's legal bank apertures:
4 parts, 10 columns/part, 4 index banks and the selected 3/13 dictionary-bank
leaf capacity. Banks increase, and each present bank's rows start at zero and
increase without holes. An address-zero write starts a fresh installation
and invalidates old need and operand ownership. E01 declares the exact number
of writes in that generation. Empty installation, a missing write, duplicate,
reserved bank, skipped first row and stale descriptor cannot launch.
The new state is 23 address bits plus one seen bit; the existing high-water
counter becomes the sparse generation's write counter. No data edge is added.

Final positive and causal tests ran on ep5 unit 3274114-1792732971. Actual
AXI F20/F24 frames install all 462 unmodified image words through the real
source ingress and collar, F28/F2c arm it, and F30 starts the real root_h5 and
SRAM-backed pslice_c5. All 125 emitted commands compare bit-exactly against
the actual compiled `quarter.mem`, including the output index. No programme
memory or producer input is image-injected. Busy, done and fault return from
the producer in the final bench. The measured bench ends at 359050 ns with
a 10 ns stream clock; its conservative per-frame idle gaps are part of this
cold-install measurement, not a production token-rate claim.

`final2.log`: missing final write, count 461/462. `final3.log`: reserved
bank 319. `final4.log`: duplicate address. `final5.log`: valid bank 320 but
first row 1. `final6.log`: new generation cannot reuse old descriptor/operands.
`final7.log`: empty generation. All are refused. Ep9 unit
2637494-1792733045 catches both causal mutants: count-check bypass makes
case 2 improperly ready, and ingress data corruption fails exact word zero.
Their committed fatal witness logs are `mutant_count.log` and `mutant_data.log`.

`l31_su_sparse_install.py` sets the actual contract's `col_su` parameters to
SPARSE_SU=1 and the dictionary aperture derived from each selected producer.
It explicitly requests the new sparse collar view, causing a truthful SYNTH
fallback until that view exists. The old `hdie_col_su_r1` hard view cannot
implement this correction. Source adoption still needs that contract layer,
new view or SYNTH wrapper, normal GEN and the actual manifest check. This
packet proves the source installation mechanism; it does not claim current
die physical closure, host link PMA transport, an IDX installation, or a full
numerical token PASS. Current S10 programmes must be re-emitted and checked.

`prepare_host_su_install.py --repo OWN_WT --rev RELEASE_SOURCE --contract
CURRENT_CONTRACT --programme CURRENT_EMIT/images/su_prog00 --out OUT` prepares
this same minimum vehicle for an actual current programme. It requires the
real contract's SPARSE_SU=1, pins selected source hashes, and copies the actual
compiled image and commands. Run its generated `run.sh` on the fleet.

Default SPARSE_SU=0 preservation: existing `tb_hbm_static_cfg_collar` ran
against the exact old and new sources (gold1 unit 285491-1792733685).
All three entire output logs compare byte-identically: positive 35 checks
(A0=2100/A1=5/B=10), sequence mutant 1 with two expected failures, and need
mutant 2 with four expected failures. This bench covers existing dense
SU/SFU/IDX shapes, XSER=0/1, and reset while stream events are in flight.
The dense row-zero/restart branch is unchanged; clearing need/operand
ownership at a new generation occurs only inside the opt-in sparse branch.
See `legacy_default_identity.json` and the three committed logs.

`coherent_408/` retains the complete immutable prepared source readset,
actual TARGET_MASK and SU_DICT_CAP testbench, input image/commands, run script,
identity, hashes, and seven raw logs from coherent W3+fix export 40861499b.
Gold1 unit 267925-1792733581 exited zero: all 462 words / 125 commands and
all six causal cases passed. The archive can replay without scratch or
unpublished source ancestry. Its source dependencies remain isolated from
main's canonical files. All 28 tracked Verilog instantiations in that source
revision use named parameters; see `parameter_users.json`.
