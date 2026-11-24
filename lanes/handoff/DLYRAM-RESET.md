# DLYRAM-RESET handoff (updated 2026-11-24 01:45 PST)

Lane dir: epyc11 /srv/opentallas-scratch2/claude/dlyram-reset/ (clone = lane clone of main).

## Done
- Step 1: case (a) PROVEN (ring_bmc_all.sh, bmc/all.txt): rp derived from wp; from any state q == D-flop line from edge D, D 4..130; 3 negative controls refuted. SRAM init irrelevant. 4-state X = sim pessimism.
- Step 2: only kit_dly_ram.py emits the ring: 31 KV pv types of D29. S81/HEAD/QC/HBM: none.
- Step 3 (post be3903cd): flush2.py on D29 bound RTL, H=21: 46 wavefront pins in 10 parts get line garbage after release (worst +79 pv_v12/pv_v7 u_vport_W.pr_valid); spine cores need die_rst_n release >= 254; START >= 35. bind_reset.json pv join taps 286/287 dangling (RTL uses die_rst_n spine).
- FABLE (d) (post b8d49880): 135->120 = synthesis opt_merge in qkd_pv16_vport_b (qv[w]==sv[w]); 44->0 = ot_dp_rtail .a(1'b1) synchronous relay copies. No reset lost.
- HOLD row draft (post 9ca315e0): hold/ROWS_DLYRAM-RESET-HOLD.py IN OUT -> reset.source.lock.stable_cycles 16 -> 256 (releases +240). flush2 --hold 261 --rshift 240: 0 wave violations. Sent to KV-ALLFIX.
- Bench + sim-only fix (post cf56cdb3, main 84ccd7f50f): OT_DLY_RAM_PTR_INIT (sim only), rtl/test/dp_dly_ram/run_reset.sh per-domain 4-state + 2-state random; PASS D+2, FAIL D-5. Netlist byte-identical.

## Open
- When KV-ALLFIX composes the HOLD row: rerun flush2.py (`--reset <new bind_reset.json> --hold 261`) on the new bind; then post "pv reset clean" to KV-PV-CAP, FABLE-RC-KV, COORD.
- die_rst_n sequencer in hub_Wi host (ot_qwen_sys_rst_seq?) unverified; HOLD row makes it moot (hub_Wi release 281 >= 254).
- Optional risk sweep: flush2.py on S81 / HEAD / QC binds (no ring there; generic reset-less line class).
- Caveats of flush2: name-level graph, cores black boxes, noreset cores optimistic.
