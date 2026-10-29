# QC-PG-5-ICG: A0 tile-root ICG, real engine-idle port (OWNER 2026-10-28 19:58 option (c)) -- 2026-10-28 PDT

Base: origin/main 410e940f4f + DIE-QC-16 9ce9c463a5 (cherry-picked, unchanged apart from the items below).

## Change
1. Re-pin of the 4 body modules (additive output only, no logic change): `ot_qwen_rom_tile_logic_w12.idle` (= u_me.idle,
   the registered matvec "engine drained" flag of ot_qwen_w12_matvec_part, 1 in reset), `ot_qwen_rom_tile_w12.idle`,
   `ot_qwen_rom_tile_nk.idle`, `qfd_tile_{nk,nl}_rp2_45.me_idle`.  Files: rtl/physical/a0_rc15_selected_2000/
   ot_qwen_rom_tile_w12_land32.sv (the kit source), rtl/physical/ot_qwen_rom_tile_nk.sv, rtl/physical/a0_rc14_selected_2000/
   qfd_tile_{nk,nl}_rp2_45.sv.  The same additive port is added to the 3 other ot_qwen_rom_tile_w12 definitions
   (rtl/hdc/ot_qwen_rom_tile_w12.sv, a0_rc14 ot_qwen_rom_tile_w12{,_land32}.sv) because ot_qwen_rom_tile_nk.sv now
   connects .idle and is compiled with any of them (verilator lint of rom_tile_nk with each: 0 errors, CHECKED).
   tools/qwen_romleaf/rc14_2000/selected_source_manifest.json: 4 sha256 re-pinned (old value kept as sha256_before_repin).
2. qfd_tile_{nk,nl}_a0c: me_idle now comes from the body port u_g.me_idle in synthesis AND simulation; the hierarchical
   read and the SYNTHESIS fallback me_idle=0 (gate held open) are removed.  ICG parameter default stays 0 (main elaboration).

## Placement / enable (review, CHECKED in RTL)
- One ICGx8DC_ASAP7_75t_R per A0 tile: instance `g_icg.u_icg` in qfd_tile_{nk,nl}_a0c, CLK = tile clock port `ck`, GCLK = `ck_g`.
- Ungated (`ck`): input faces ck_fa4 (tap/go, tile_id, 2-stage rst_n landing), NK ck_fa0/ck_fa1 (n_a/n_b faces), and the
  enable state (go_f, go_h, nv_f, dr).  Gated (`ck_g`): body ck, ck_rp*/ck_tx*/ck_rsw/rnw/dw/de/rs/rn/lsl*/node, output faces
  ck_fa2/ck_fa3 (they hold), ROM macro clocks inside the body.
- The ICG sits at the tile clock root, i.e. BELOW every parent/region/crossing node; no CA counter or crossing capture is in
  a0c, so CA crossings and the start tree are unchanged.
- Enable = !rst_n | go_f | |go_h | !me_idle | n-face valid/fault copies (NK) | drain counter (64).  go_f is the face copy of
  tap[0]: go at edge t opens edge t+1, the first gated capture => 1-cycle lead from existing signals, 0 schedule cycles,
  no new tile port.

## Bench (Verilator 5.050, intel2 capped units, 12,000 cycles, ICG=0 vs ICG=1, synth-equal idle path) -- CHECKED
| mut | NK | NL |
|---|---|---|
| 0 design | PASS qualified 0, gated 6073 (50%) | PASS 0, gated 6647 (55%) |
| 1 no 1-cycle lead | CAUGHT 4156 | CAUGHT 4156 |
| 2 ~me_idle dropped (wrong enable) | CAUGHT 9847 | CAUGHT 10463 |
| 3 drain dropped | CAUGHT 5285 | CAUGHT 6054 |
| 4 n valid/fault dropped | CAUGHT 733 | n/a |
| 5 reset term dropped | CAUGHT 5000 | CAUGHT 801 |
| 6 go hold dropped | PASS (equivalent mutant, dr covers) | PASS |
| 9 control en=1 | strict 0 | strict 0 |
Identical to DIE-QC-16 (expected: same signal, now through ports).  Strict trace mismatch on INVALID data words only
(6908 NK / 6651 NL cycles); gate criterion = valid-qualified (COORD 12:30 principle ruling).

## LEC (yosys 0.68, strap_lec.py recipe) -- CHECKED
| check | NK | NL |
|---|---|---|
| body re-pin: main vs branch rp2_45 flattened through rom_tile_nk/rom_tile_w12/logic_w12 (lec_body.sh), all existing outputs | EQUIVALENT (7242 $equiv) | EQUIVALENT (6210) |
| body mutant tile_id inverted | NOT EQ (16) | NOT EQ (16) |
| a0c main vs branch ICG=0 (lec.sh off) | EQUIVALENT (1030) | EQUIVALENT (516) |
| a0c main vs branch ICG=1 SYNTHESIS (on) | NOT EQ, 1 unproven (gate really closes now; was EQ = gate open before) | NOT EQ, 1 |
| a0c mutant tile_id | NOT EQ (16) | NOT EQ (16) |
lec.sh harness: gold connects the new black-box output to a dangling wire (.me_idle(me_idle_nc)) so the u_g cells have
the same port set; no function added.  ON-vs-OFF sequential equivalence = the valid-qualified bench.

## Open (UNCHECKED)
- Enable timing: u_me.idle (leaf flop on the late gated tree) -> OR -> ICG latch at the early tile root; budget ~833 -
  root-to-leaf insertion (~550 ps est.) -- check in the A0 parent kit STA (clock-gating check on u_icg).
- ICG_DRAIN=64 bench-passing, not a proved minimum.
- Release value of ICG: param default 0 here; the A0 parent kit recipe sets ICG=1 (ASK, DEFAULT ICG=1 in the
  qfd_tile_{nk,nl}_a0c kit recipes/specs at QC-A0-KITS-7).
Data: intel2:/srv/opentallas-scratch2/claude/qc-icg-2.
