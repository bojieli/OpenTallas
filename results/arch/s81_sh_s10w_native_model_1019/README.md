# Exact s10w native diagnostic and structural prerequisites

**MODEL HOLD. No RTL, helper, macro-view, clock, schedule or gate changes.**
The existing WARN/GRT-zero result does not qualify this tile. Exact source
`40261329ff8bdcdfb6d8e344937c9f5c9e3a00bb`, archive `36b2f4a7…`,
manifest `87d4b851…`; full values and selected source/view hashes are in model.json.
Read-only frozen run: `ot-epyc6:/srv/opentallas-scratch/claude/ref_gate/dsdv_sh_lk_s10w-20261019-115854`.
Native database: `routes/gate/work/orfs/results/asap7/opentallas_dsdv_sh_lk_asap7_ref_gate/base/5_1_grt.odb`,
SHA256 `efcf6c0da26728a1985168cf98a07c5084591910fc338b0ccbf873906c1b8ded`.
This is a GRT diagnostic database, not final routed closure.

The audit ran in exact image `openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29`
through unpinned ot-run, with the frozen run mounted read-only. Initial extractor
failed on the OpenDB BPin rectangle API; native.log preserves that failure.
Corrected native_retry.log and expanded native_final.log both exited zero.
No original fleet process was stopped or restarted. s10 and s10b remain separate live candidates.

| Checklist | Exact evidence and implication |
|---|---|
| Registered pins | Eight input bits reach combinational logic before any FF: s_jd_w[1:0], s_jd_e[1:0], kd_i[53], j_i[32], f_ks[52], f_host[0]. Sixteen t_host[47:32] outputs are tie-driven; source contract must establish their reserved semantics before any exception. Remaining output drivers are FFs. |
| Reach | 351 logical root/end-point pairs exceed 405 um Manhattan distance; maximum 519.202 um. All are FF roots. Buffers and inverters are transparent; they do not create a new cycle. Full pairs retained in native.json. |
| Fanout | 91,978 native instances, 13,927 FFs; 212 nonclock roots exceed32 =70FF+142comb. FF max794 (dq_rd[0]); comb max890. Input max1, macro-output max1, tie max1. No undriven/multidriven signal nets in this inventory. |
| Reset | At least two reset-related FF roots violate32: u_rsc.reset_pipe[0]41 and root ot_rlv c10 73. Input rst_n landing max1 does not prove downstream reset safety. Inherited assertion/release ages and stopped-clock behavior still need source proof. |
| Depth/timing | Current same-run pc.log uses TT placement RC/signoffSDC: 598 reg→reg paths, worst−52.7ps at sp_iss[30], reg→macro+73.8ps, hold+31.9207ps. Textbook st_row→s_grp690.1ps/19levels remains a separate depth failure. Final ORFS GRT SS/WC setup−135.35ps is sensitivity, not TT; FF/BC min internal+30.07/input+29.78/removal+31.16ps. CTS SS−116.04ps is also retained. |
| Storage | Four actual SRAMs: 2×16x257 +2×16x289, 17,472 total bits, 8clock pins. Additional live stream queues are itemized in model.json. Realigner8×256 is one coherent indexed2048-bit pair-write/read-window store, not eight independent words. A macro replacement requires real bandwidth and lifetime proof. |
| Macro access | 16x257 W392/E391 contacts; 16x289 W440/E439. Both have adjacent local pitch0.096um =10.4167pins/um: FAIL. Full-face averages cannot qualify these legacy masters. |
| Floorplan | Actual masters89.448×39.432 and99.144×44.04um; old 345.6×194.4 outline is not a successor constraint. New macro channels, lattice origins, std-band capacity and endpoint placement must be modeled together. No cost ceiling applies. |
| Clock | Current TT/FF boundary spread46.7/42.2ps meets80, insertion420.2/350.6ps is guidance only. Native macro clocks have no internal child-flop reference, so raw arrival is not a neighbor match or min-delay proof. New registers/macros/regions must price their actual clock load. |
| PG | Complete master universe: 8PGMTerms, 8connectedPGITerms, 432VDD/VSS rectangles across4macros. Net attachment alone qualifies zero rectangles for physical via/OBS/rail connectivity. Real protected access and current-PG connectivity remain open. |
| Static schedule/validity | Existing host FIFOs contain credits/Gray-pointer machinery; this packet adds none and grants no new static-on-chip credit exception. Scope and producer/consumer contract require explicit composition. Cold state must remain unobservable until written/qualified; no arbitrary zero initialization is a proof. |

The first-order fanout floor is **233 additional FF copies and620 additional
combinational copies** before recursive D/enable/reset replication, clock loading,
register placement and reach. Native standard-cell area is11442.25278um²;
plain FF master area0.2916um² (ASR0.37908). The plain-FF floor67.9428um²
is not a final cost or fixed point. Registering eight input bits may change
observable fault/completion ages, so no free-cycle implementation is implied.

For geometry sizing only, preserving margins and using uniform0.192um contact
pitch would require at least76.632um and85.848um heights respectively. Those
numbers omit side-channel lead lengths, OBS/vias/PG, internal cell mapping and
timing roles. They are not generated macro views, valid footprints or permission
to substitute the shared SC2 prototype. No legacy nominal CQ is certified as an
earliest CQ by this model.

Next structural work is a single composed source model: (1) map every unsafe root
and all351far pairs to useful stream operations and legal regional ownership;
(2) derive kept same-age copies to a complete D/enable/reset fixed point, or price
landed regions and every added edge; (3) model actual selected dual-clock SRAM
contact escape, PG/via/OBS and separately bound earliest/latest delays; (4) prove
the exact descriptor/realigner/FIFO cold-read, simultaneous read/write, full/empty,
completion marker, fault and reset calendars; (5) price the resulting outline,
std-band40–60%, macro lattice and native neighbor clock references. Only the
complete model permits a private default-off source choice. No knob retry or
generic helper change follows from this diagnostic.

All source predecessor failures, current TT setup failure, SS sensitivity, gate
WARN and source packet907aa1fc4 remain unchanged. This packet does not submit,
adopt a parent view, claim token qualification, or transfer qualification from
another candidate.
