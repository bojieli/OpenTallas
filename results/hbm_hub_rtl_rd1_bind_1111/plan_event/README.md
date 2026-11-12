# rd1 bind recipe (HBM-HUB-RTL-1, 11-12)

Canonical input: the CACHED elaboration epyc8 die-hbm-92-su/exp/bind_e0/asbuilt.json (DIE-HBM-100 ruling).
The recipe reproduces it; it does not switch to current manifest versions.

Steps (bind_rd1.sh, ctl/bind_ctl.sh; same recipe, control = base netlist t11_top without rd1 pin cycles):
1. bind.py elab (base = tip2 + branch RTL: SU slot registers, ot_hgi_qdq_transport_r5.sv)
2. tools/hbm_b2/fused_lower_tree_splice.py splice
3. fused_close.py CACHED SPLICED OUT RECEIPT: FUSED closing step (finding B)
4. prune_dead_latches.py (3 dead $adlatch per idx scorer quarter, fail-closed)
5. cache_names.py CACHED FRESH OUT RECEIPT: cached cell names (finding A)
6. remap3.sh: remap_splits.py (cached bind_e0 -> fresh) + map_fill.py (new SU slot glue cells)
7. bind.py bind --strict pass 1 -> hbm_lat_pads.py -> pass 2

Final results (run_final_both.out):
- rd1: 90 partitions / 420 crossings / 0 errors, LC REGEN 38 / 0 errors
- control: 90 / 420 / 0, LC REGEN 23 / 0 errors
- control vs bind_t19 bound RTL, file by file (cmp_final_ctl_vs_t19_loose.txt):
  36 identical + 40 identical after Yosys auto-index renumbering ($NNN / _NNNN / hash suffix) = 76;
  8 differ = q_su00/10/20/30 (+__physical_v1): the SU injection-slot form (4 registers + 2:1 mux tree instead of
  a memory; EMIT cannot place $memwr/$pmux in a dissolved parent), proven equivalent
  (../su_slot_eq: 187271 proven, 0 unproven). Strict (no renumber): cmp_final_ctl_vs_t19_strict.txt.
- rd1 vs control (cmp_final_rd1_vs_ctl.txt): 72 identical + 12 differing only by rd1 values (bound top, root
  rootctl CR_RT/VM_RT +1, q_hub_ne/nw: coll VM_RT 3->4, dbk RR_RT 80->81, fused lane RR 10->11, fvp BANK_RR 7,
  xload RD_LAT bytes +1, xp_ctl r4 -> ctl_r5 rl_cfg 126 -> 127; q_su* READ_RETURN +1).

## Separate finding: cached elaboration vs current manifest (not part of this event)

A. rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv (q_b000..b011): the cached cell names carry older source line
   numbers than the manifest file (e.g. :171 vs src :182); src attributes and cell counts (55/13) are the same,
   so the difference is names only. cache_names.py renames the fresh cells to the cached names; no file pin needed.
B. FUSED lanes (q_hub_ne/nw, bound top): the cached top wires the lower FUSED lanes into hb_fvp (lane rr from
   hb_fvp a_rr) and ties pad_k/pad_b as constant straps. The repo splice leaves fvp_in__*/rr_* die inputs and
   native pad straps; that closing step is not in the repo. fused_close.py does it from the cached top
   (receipt: 280 ports removed, fvp_in 9280 / pad_k 168 / pad_b 28 / rr_v 32 / rr_d 8192 bits; top port set ==
   cached, 491 ports).
Later ASK to COORD: should the manifest versions win (chunk_rt line drift, FUSED splice with the closing
step moved into the repo)? That would re-sign unrelated cores, so it is outside the rd1 event.
