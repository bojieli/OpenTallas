# Actual token-link observation source extension

Status: BLOCKED_SOURCE_CONTRACT. No token, arithmetic, native or transport PASS.
Original strict cut7 failures and all stimuli/gold/deadlines remain unchanged.

Use the ORIGINAL run snapshot at revision
`9c2f5fe60ea8a01fa86088768e58b22ec36638e7`, recovered under
`/home/ubuntu/scratch/mu-die-s81/tok/kits/K_cut_7/src/` and hash-matched read-only
against the existing ot-epyc8 fleet snapshot. Its LEP SHA is b4a9e8af...,
matching the contract. The artifact pickup branch b14d4cf87 has different current
RTL and generator bytes; it is not the run's source identity. Both ledgers,
actual generated bench and kit hashes are in `source_provenance.json`.

`tools/s81_dv/dv_link_observation.py` consumes the original replay and compiled
schedule, verifies the original programme manifest, and emits 28 L0 SU or 84
MU012 frame obligations. The latter uses the original user shifts 0, 21312 and
42624; it does not replace them with the independent endpoint bench's calendar.
Each obligation preserves the actual header/mask, destination slice mask,
producer edge, one-edge EPB input register and exact local lane stations/K/age.
Exit 2 is the intended fail-closed result, not a successful qualification.

The exact local mapping is u_s_7N -> lt_lk_EN0/1 -> u_lk_EN0/1, and u_s_7S ->
lt_lk_ES0/1 -> u_lk_ES0/1. All four local lanes have age 6 (three stations,
K=3). Their opposite RX inputs in cut7 are idle. These names stop at the local
PHY; they do not identify a far die. The RD destination masks select sid 1 or
sid 0 within a destination die, not the destination die or its PMA calendar.

The concrete missing producers are:

- Full row data and its golden placement: every compiled RD word currently
  checks only bits 51:0. No full 1104-bit golden or runtime row placement is
  silently reconstructed from zeros or the observed result.
- The actual two far-end PHY/LEP connections, PMA ages, clock/reset contract,
  static copy/user ownership and landing/replay slots. The real paired endpoint
  bench's asymmetric 2/9 PMA ages and six randomized XB users demonstrate an
  independent component; copying those values would fabricate this token path.

`rtl/dsrom_sys/s81_dv/slice/test/s81_link_observation_probe.sv` is a read-only
probe ready for explicit instantiation at each actual source and mapped receiver
core. Connect the existing bench cycle counter and the actual core's named
signals; give every instance a unique output path and exact endpoint name. Add
it to the bench source inventory. It records complete qualified producer frames,
host/key frames, pair/sequence parity, both released halves, SRAM landing writes,
replays, and consumer ri/mu_rt with reset and faults. No DUT pin is driven.

All samples are pre-NBA at the original rising edge. A release sampled at D
must appear as ri or ml_wv at D+1. ml_rv/ml_rd sampled at E reaches ri at E+2.
The inherited ro pin register costs one edge, and reset release is the original
three-edge relay contract. No constant event-to-peer elastic latency is inferred.
The link itself retains its original credits/replay and pairing implementation.

Next: the die/programme producer must provide the missing far-end connection and
calendar (or explicitly include the real paired peer in the bounded vehicle),
then attach these probes while running the unchanged compiled programme. Check
every pushed full frame against both joined halves and sequence parity; check
qualified cutthrough ri, ml_wv storage and ml_rv replay separately. Compare
qualified user0 payload and identity to the original SU reference at identical
edges. Run actual wrong-owner, corrupt, early, late and omitted-consumer mutants
with committed causal witnesses. Retain the old strict failures alongside these
new results; there is no link-lane waiver. No new simulation or gate was launched
without the missing contract. Only the standalone probe syntax lint ran on the
fleet using pinned Verilator 5.050; its receipt is `probe_lint.log`.
The earlier empty-stdin invocation and integer-file-descriptor width warning
are retained as separate lint FAIL receipts; the latter was fixed with an
explicit `fd == 0` test, without suppressing warnings.
