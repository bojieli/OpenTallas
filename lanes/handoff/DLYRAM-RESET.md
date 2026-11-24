# DLYRAM-RESET handoff (Opus 5.5, split from KV-PV-CAP 11-23 23:58 PST). ONE job: ot_dp_dly_ram reset behaviour + KV reset-vs-flush.
Lane dir epyc11 /srv/opentallas-scratch2/claude/dlyram-reset (clone = ot-lane-clone of main 8f590b7d24, cones tools,rtl,physical/die_plan + macro dirs).
## Done (posts 01:11 PST 4d0ed371 / af5713a7 / 3946a8d3)
- Step 1 PROVEN: rp <= wp - (D-4) (one counter). ring_bmc.sh / ring_bmc_all.sh: from ANY state, q == D-shift from edge D, D 4..130 127/127; neg lag/indep/window D-1 all FAIL. bmc/all.txt (ot-run unit oth-ubuntu-750380, rc 0).
- Step 2: only kit_dly_ram.py (pad_ram) -> 31 KV pv types of D29; S81/s81_head plans 0; QC/HBM none.
- Step 3: d29/ = copy of epyc8 kv-plan-r6/d29/apply/portable_bind (rtl + bind_reset.json ...). flush.py -> flush_d29.json: longest reset-less core->core line 235; root hold ~21 clk (lockq STABLE 16, PLL por_n = pad); needed hold max 239 on type-max paths; 54/65 types > 21, all 31 pv. Proposal reset.source.lock.stable_cycles 16 -> 400.
## Next (ETAs posted)
- 02:15 row draft for KV-ALLFIX: stable_cycles 400 on the current compose (A5s), reset_tree offsets, boot contract regen; verify host die_rst_n sequencer hold (qkd_host_root_admission in hub_Wi); bound need over ALL pairs, not only type max.
- 02:30 FABLE (d): reset flops 44->0, 135->120 from KV-PV-CAP lec2/k3_ok (read-only), by module + removing pass.
- 03:00 4-state bench per clock domain, pv_v3 real (W,D), reset consumer, random 2-state + 4-state.
- 03:30 opt-in pad_ram.ptr_reset (sim cleanliness only) + LEC + negative control.
- Risk sweep: run flush.py on S81 / HEAD / QC binds (same wavefront hold question).
