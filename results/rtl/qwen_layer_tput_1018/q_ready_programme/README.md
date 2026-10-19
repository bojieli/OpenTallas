# Production programme recovery

The hardware image ABI is a measured blocker. `tb_qready_capacity.sv` instantiates
the exact `0d4c9808f` release `qfd_dv_cmd_cal_mu` with NU4, CTX_DW1, UFOLD1,
UVM_STRIDE4096, PIDX_STRIDE128 and its real two SRAM macros and write observer.
It streams all1024 PW and8 DW in legal order, with ME meta_rows30/base480.
The positive descriptor with248 entries seals ready without a fault. The249-entry
mutant and the recovered390-entry full-decode lower bound both fault at seal,
fault_code0x10 (bit4), image_ready0. This does not execute fabricated commands;
the rejected descriptor cannot seal regardless of entry contents.

The release ABI computes `base + 2*nent <= 976` and `base >= 16*meta_rows`.
Thus248 entries is the maximum at base480. The immutable full lowering at
`4e718c010:results/rtl/qlb_c4b_1018/clayer2/layer_s1.json` contains390 decode
entries and estimates21 boot entries,72 PROG+188 BTAB+528 per-layer CROM chunks,
4 per-token RoPE chunks. Even removing all table payloads leaves at least
480+2*390=1260 PW; the complete archived estimate is13910 PW. Its artifact
remains analytic and old-die scoped; these counts are not a performance claim.
Current TLOAD uses a6-bit row in this same store and rejects rows>=61 and overlap
with ME/calendar regions. A compiler cannot emit that lowering into this ABI.

Required RTL owner work (handed to `qwen_programme_capacity`): a distinct static
calendar/payload source with enough actual macro capacity, source identity and
boot/witness ABI; preserve the ME1024-word image and reserved metadata; give each
layer its exact PROG/BTAB/CROM payload and each token its exact RoPE row; fixed
load-to-use edges and exclusive table write ownership; pin/fetch latency passed
to the compiler. Table-only migration cannot solve the calendar overlap.
No seal bound is relaxed by this change.

`recover_q_trace.py` recovers existing full12-slice native stage logs from
`ot-epyc5:/srv/opentallas-scratch/claude/qw-realstg` read-only. L0 andL1 each
contain512 unique Q seats and64 Q words, bit-exact vs the real P8191 ISA golden,
with all96 Q/K/V output edges matching the same compiled lowering origin.
Their exact words, seat writes, per-beat last producer edges, source input SHA256
values and limitations are committed in `L0_q_trace.json` and `L1_q_trace.json`.
This recovers useful actual RTL data, **not production admission**: QKV/r are
bench-landed real operands, direct slice commands bypass controller PW/DW, the
source predates release and no production layer origin/request calendar exists.

Fleet units: capacity1546858 (2GB/2threads), recovery1550873 (1GB/1thread),
Verilator5.050. Both exit0; logs and version committed. No original run modified.

## Actual landing mechanism and physical phase obligation

`tb_qready_landing.sv` replays the64 actual Q words from each recovered layer,
retaining their measured gaps with an explicitly declared64-edge bench offset.
The real26-stage forwarded lane/landing primitives carry all548 bits. Q-slot and
beat each pass through their real FIRST1 landing, K3. Source release edges are
raw1266 (Q) and21 (slot/beat), receiver1596: the GEN G1267/22 already include
HOP0_EN_REG=1, as `reset_calendar_audit.finalize_model` specifies. Native service
and real SRAM are pinned to SAFE2 source9f159ab98. No RTL dependencies are edited.

Under zero-delay related clocks the production Q K2/E19 straps yield16 observed
edges, not the planned20, and the landing asserts its epoch fault. Native service
still emits all33 CMD/Q records,32 results and completion bit-exact; the bench
correctly fails65 transport checks (one sticky epoch-fault rise +64 ages).
This is **not proof of a physical die bug**. The inherited bi routed plan used
by dv2f18dh2 explicitly compensates a large physical timing offset: Q E_sta7,
TT s1=-4515.6ps / FF=-3133.6ps, with positive setup/hold windows after pricing it.
The original full-plan digest, its actual old-bi report paths and selected rows
are in `landing_phase_obligation.json`. The dv2f18dh2 physical chain had not yet
finished its own clock/GRT/STA when recovered; no matching phase trace exists.
The zero-delay bench cannot reproduce that physical compensation by assumption.

A separately labeled lawful zero-delay control (K6/E15, Q age16; slot age2)
passes on **both L0 and L1**: all512 seat values/coverage, all32 requests, all33
CMD/Q records on their unchanged output slots,32 return words, completion and
embedding. It is never a production candidate. Moving only its prefetch one
edge late makes247 checks fail and sets the native fault; witness committed.
All cases use the same full512-seat mechanism; no partial Q model is substituted.
`landing_summary.json` includes all32 ready/request times in this explicitly
local control frame. They are deliberately outside the `events.q_prefetch`
admission schema, with production_bound/advance_admitted/phase_qualified=false.

The compiler inspector now labels age_edges as **GEN planned E+1**, with checked
frame/strap connectivity and phase_qualified=false. Updated full-GEN negative
certificate: `phase_blocked_q_readiness.json`; six focused regression tests PASS.
Previous source-pinned evidence remains historical. No20-edge physical claim is
made from a netlist/metadata inspection.

To reproduce, export every dependency listed in `landing_sources.json` from its
pinned9f159ab98 commit into an isolated fleet source snapshot. Copy this branch's
landing bench/C++ driver to their listed paths, the runner to the build root,
`landing_sources.json` as `sources.json`, and L0/L1 traces under `trace/`.
The runner verifies every dependency and bench hash before compiling.
Run on the fleet with Verilator5.050: `python3 run_landing.py --ideal-control`,
then `--ideal-control --layer 1 --reuse`,
then `--ideal-control --late` for the failing prefetch witness. Default invocation
reproduces the expected production-straps/zero-phase failure. Completed objects
are retained. Per-layer output log names avoid overwriting verdicts.

Remaining production join: programme-capacity owner supplies real source-pinned
PW/DW/new-store ABI and its event origin; die-clock owner supplies actual source,
forwarded and receiver clock phases for the successor GEN. Recompute source
QKV/QK writes under that programme, join all512 seats to32 requests in the same
frame, then admit advance1 only after the complete pin inequality and native
output-slot proof pass. Current traces and zero-delay controls do not admit it.
