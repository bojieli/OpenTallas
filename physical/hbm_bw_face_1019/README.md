# hdie_pc_ctrl_bw_face_{p540,q648}: SAFE-face HBM PC controller (LEAD2-HBM/L2H-BW, 10-19)

Branch `claude/l2h-bw-safe-1019` (on `claude/lh-bw-n64-1019` 4d71395b0, tools from origin/main).
Top `ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face` (`rtl/hbm_accel/loader/service_native/`), parameters SRAM_P192=1, PURE_FACE=1.
Specs `tools/ref_tile/specs_hbm_bw_safe_1019/hdie_pc_ctrl_bw_face_{p540,q648}.json`. The two variants share the RTL and
differ only in the floorplan. They are gated in parallel; bind the first that closes and cancel the other.

## Why a structural successor (one failed gate = redesign)
- The n64 gate (hdie_pc_ctrl_bw_n64) FAILED on band/fill: a 561.6x367.2 outline at 14% fill, macros up to 150 um from the band, and placement-RC TT -189.64 on macro->reg.
- The Codex c1f1c2c0c audit of the legacy top found 281 of 1228 signal ports with a non-FF first or last contact:
  - kr_data, kr_tag, kr_beat and kr_v came from the legacy same-edge KR collar's ring read mux.
  - kr_rdy fed the ring's pop and count logic.
  - pc_fault was an OR.
  - k_v met 22 synchronous-reset ANDs.
- The same audit found that the 2c 128x64 macro packs 105 contacts per face at 0.096 um, which is 10.5 contacts/um locally.

## What changed
- **Ports.** Every port is now a flop D or Q.
  - KR leaves on the native READY-LATENCY-1 ABI: a beat transfers at edge e when kr_v(e) and kr_rdy(e-1). kr_v and kr_data are skid head flops, and kr_rdy goes to 18 pure D pins.
  - The consumer lands KR in the existing 3-slot RL1 ring (`ot_hbm_svc_kr_ready_bridge`) on its own side of the crossing, as `ot_hbm_svc_vm_kshare` already does for c_kr_rdy.
  - k_v goes to 22 pure D pins. The reset-owned ready_seen and skid valid state still mask every push and pop, so the cycle behaviour is identical.
  - pc_fault is registered.
- **Storage.** The stores are 23 `ot_sram_1r1w_128x64_m1_p192` macros. The generator, area and TT/FF/SS timing are the same as the 2c family (CQ 293.7 ps).
  - There is one clock pin, and the contacts sit at 0.192 um pitch, which is 5.2 per um on each W/E face. The N/S faces are bare.
  - The same family is already used by the reviewed KV kit qkd_hr_core_guard.
- **Cycles.** 0 edges are added end to end. The 831-flop KR collar moves from the PC to the consumer, so tile area falls and consumer area rises by the same flops.

## Floorplans (macro origins on the M4/M5 track lattice; abutted N-S banks of arrays)
- Stacks alternate R0 and MX orientation and abut, with a 0.024 um gap after every MX. This keeps every W/E contact on the 0.048 M4 track (residue 12 nm).
- No signal pin sits on a touching N/S face, so the stacks qualify as abutted banks under `abutted_stack`.
- **p540**: 349.92x213.84 um (aspect 1.64), predicted fill 36.5%.
  - 12 PAIR stacks (55.08 um tall) in 6 columns at 54.0 um pitch, which leaves 20.3 um channels and about 288 escape nets per channel.
  - Two rows. The top row holds the response payload, head and post b0/b1 stores (KR to N). The bottom row holds the write payload, post b2/b3, queue, pending and response identity stores (col_data to S).
  - Full-width central band at y78.84..133.92. The clock enters W/M4 at y106.368, the band centre.
- **q648**: 209.52x324.0 um (aspect 1.55), predicted fill 40.3%.
  - 6 QUAD stacks (110.18 um tall) in 3 columns at 64.8 um pitch, which leaves 31.1 um channels. The two rows hold the same stores as p540.
  - Band at y133.94..190.08. The clock enters W/M4 at y162.0.

## SAFE-DESIGN checklist (owner 10-19)
1. **Pins: fixed.** Every port is a flop D or Q in RTL. The tool's pin wrappers are disabled, with the reason in the spec, because they would add a second stage and break the RL1 contract.
   Reset lands in 2 kept face stages, followed by the native relay, for 5 release edges as before. The gate's textbook.boundary check (the n64 run had 38 input endpoints deeper than 3 levels) is the check of record.
2. **Reach: PASS by construction.** Both outlines are below 350 um in their long dimension and below 330 um face to face. A pin flop is at most about 175 um from its pin, and no macro is more than 110 um from the band. The gate's reach audit is the check of record.
3. **Fanout: OPEN, measured by the gate synthesis census.** The PURE_FACE captures give k_v 22 loads and kr_rdy 18. The n64 map6 nonreset roots of 33-42 loads were addressed by the cc723735d regional muxes.
4. **Depth: measured at the gate.** The previous synthesis worst stage was 528 ps. The n64 macro->reg miss was wire, which the compact floorplan addresses.
5. **Storage: PASS.** Every runtime-indexed store over 2 kb is SRAM, and the 831-flop KR collar now lives in the consumer. No flop delay lines were added.
6. **Floorplan: fixed.**
   - Macro faces are 5.2 contacts/um.
   - Channels are 20.3 um (p540) or 31.1 um (q648) wide, with a 5.4 um halo.
   - There is one full-width central band with rows in the channels and no fence.
   - Fill is 36-40%, so no fill_reason or lattice exception is needed.
   - Aspect is 1.64 (p540) or 1.55 (q648).
   - Deviation from the strict 43.2-multiple origins: origins sit on the M4/M5 track lattice at a regular pitch. A pitch of 86.4 with origins on 43.2 multiples cannot reach 35% fill with 23 macros of 0.93k um2 (it reaches at most 27%).
7. **Clock: OPEN, measured at the gate CTS.** A W-face M4 spine enters at the band centre beside the register mass, with macro leaves. The n64 run measured spread 60.3/63.8 ps at TT/FF and insertion 735 ps (a WARN, which is guidance). io_hold_margin is 0.03.
8. **Schedule: PASS.** The schedule is static and no edges are added. The only ABI change is that the KR consumer must land RL1 in a 3-slot ring, which the parent already does for VM. BW stays at the 90.67 B/edge/SM stream floor (pricing_lhbw.json).

## Evidence owed before submit
- Production full96 with HBM_SAFE_FACE (`run_smb_unit.sh ... bwsafe_face`), which must give PASS 66/154 END45260, identical to n64.
- A positive control with the 2c macros (FACE_MUT_P192_OFF).
- Mutants FACE_MUT_ID (identity tag) and FACE_MUT_SAMEEDGE (consumer ignores RL1), each with a committed fail witness.
