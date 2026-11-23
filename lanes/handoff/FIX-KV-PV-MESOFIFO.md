# FIX-KV-PV-MESOFIFO handoff (Opus, started by FIX-LEDGER 11-23 01:4x PST; ledger rc128 pv pad-delay column)

## Goal
VIS-KV ruling: pv pad-delay register column -> pad FIFO (named ot_meso_fifo). D29 row ROWS-READY to KV-PLAN-R6 by 13:00 (host:path+sha12);
go/no-go by 10:00 (fallback = SINKSPREAD-R2 trunk window + cut-leg stations rows, reason to FABLE-RC-KVHEAD a2afa1acb28fd2355).

## Ruling (mine, posted 02:1x)
ot_meso_fifo is a 4-slot mesochronous CDC ring (flops); it cannot hold a 46-67 cycle pad. Form = ot_dp_dly_ram: SRAM ring
(ot_sram_1r1w_128x256_m1_r2c2, as kv3_pc_v3), cycle-exact to ot_dp_dly; kit post-pass at GEN (tools/die_plan/kit_dly_ram.py),
opt-in plan key partition_types[t].pad_ram. Bind / bind_latency / LATCHECK / R8 untouched (pass runs on the kit's staged bound RTL).

## Work
- Lane clone epyc7 /srv/opentallas-scratch2/claude/fix-kv-pv-mesofifo/clone (main f7d6888bcc + my edits), tmp .../fix-kv-pv-mesofifo/tmp
- Files: tools/die_plan/ot_dp_dly_ram.sv, kit_dly_ram.py, test_kit_dly_ram.py, gen_phys.py hook (after pinband_macros: plan +
  macros; before dly_lockup: apply + stage cell + SRAM bb), schema.py pad_ram key; rtl/test/dp_dly_ram/{tb_dp_dly_ram.sv,run.sh}.
- Bench PASS (8 W/D corners, 3 seeds, random pointer power-up); D-2 mutation FAILS as it must.
- Base D28 seal bind (44c3cbf51e50, epyc8 kv-plan-r6/d28/isolated_seal_takeover/rh12_rebind/selected_candidate): 17 pv types
  1,247,833 pad flops; trunk candidates ~1.11 M. Dry run v6n: 5 RAMs absorb 57.6k of 74.4k; v8: 7 RAMs 68k of 88k (centre keepout
  x W/2+-170).
## Next
pytest -> ot-push-main -> row ROWS_FIX-KV-PV-MESOFIFO-PADRAM.py (sets pad_ram on every kv3_pv* type, incl. row-B split pieces:
applies after row B) -> fork base_d28 (ot-tree-fork) -> plan_gate_pre + G0 + strict bind + LATCHECK -> ROWS-READY. Probe: GEN of
one pv kit (v6n) to see the RAM macros staged/placed.
