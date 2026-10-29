# FSTART out face flops -- ledger (DIE-HEAD-10, 2026-10-28)

Change (strap form only, `count_aligned.strap_form`; parameter forms and intra-region relay rx partitions unchanged):
every forwarded start pin `cland_fstart_out_<b>` is the Q of its OWN flop `u_cland_fstart_<b>` (ot_dp_landing_relay,
region clock, the region start's raw reset, d = the start's D-side `start_d`).  Before: all pins of a type were
`assign = cland_start`, the strap-mux / chain-flop net shared with the ring readers and monitors (face_guard
`cland_fstart_out_o: net u_cland_origin/start has 15 loads besides the port chain`, DIE-HEAD-9 FACE).

| item | value |
|---|---|
| cycles added per crossing | 0 (q(t) == cland_start(t) every cycle, proof below) |
| K / PAD / DEPTH / origin_cycles change | none (count_align_bind unchanged; the receiver ring and child origin see the same edge) |
| flops added, HEAD (one-entry 450 plan + Codex strap sidecar regen) | 69 (one per forwarded start pin, 16 types) |
| per type | ctl 10, host_ep 7, lep0N 8, mesh_ep 3, serdes 1, spn 10 (strap+root), spn_end 9, st_k5 4, st_m 2, st_n3 4, st_n4 4, st_str 2, st_turn 2, tile_p 1, turn_a 1, turn_b 1 |
| root+child type (hd_spn) | the static strap_ca_root select picks start_d and the raw reset BEFORE the flop (no mux on the port net) |
| removed | DIE-HEAD-9 origin_s `start_o` / keep flop (one flop per type, still shared by all pins of the type) |
| timing | start_d = taps_e[pad] (1 mux level) or the root comparator; the flop sits at the face (OT_FACE_FLOPS pin register); UNCHECKED until the next kit run |
| FSTART in | NOT changed (design note FSTART_DESIGN.md: receiver capture flop + sender early tap + pad-0 senders +1 K -- needs its own ledger) |

Proofs
- fv_start_o.sh (SAT temporal induction, yosys in openroad/orfs:asap7lock): A strap child origin PADW 1..4 x every pad x efall
  (60), B root+child wrapper as emitted, SETTLE 1/3/6 x PADW 1/2 x pads x efall x root 0/1 (72), C root-only SETTLE 1/3/6/64 (4):
  136 PASS; mutants (start_d one tap late / root one cycle early) 136/136 caught.  CHECKED.
- strap_lec.py (HEAD plan_one_entry_450 + Codex strap sidecar, --mutant): strap master vs parameter form per tie variant: see
  strap_lec_summary.txt.
- clock_landing_verify.fstart_net: receiver ring t_rst_n / child origin p_start must be the sender's u_cland_fstart_<bus>.q,
  that flop on the region clock with d = the live origin's start_d and the same raw reset.
- pytest tools/die_plan: test_clock_landings, test_clock_landing_verify, test_count_straps (+test_fstart_out_face_flop_per_pin),
  test_strap_lec, test_face_guard, test_count_align_bind, test_gen_phys_clock_landing, test_landing_sdc_outputs: all PASS (2 skip).
