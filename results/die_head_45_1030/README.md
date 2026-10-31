# DIE-HEAD-45 (HEAD die owner), 2026-10-30

## l45 = l44 + one-block hd_spn_wshim_rx clock tap event (COORD 18:04 (4))
- l44 wshim_rx kit (main ctlkey + pinslot): clock_reach 235.83 FAIL (lone sink u_srl_43 at (481,284) = a planned run-reset relay site
  (480.6, 284.0) holding 4 relays; nearest density tap clk at (351,178) 235 um).
- Fix: clock.sink_sites_um += [480.6, 284.0, 4] for hd_spn_wshim_rx. Density taps feed the reset tree (reset_tree reads the planning taps),
  so a plain plan edit gives 12 G0 errors; built as a full event with the DIE-HEAD-43 machinery (build_event_stable6 + chain.sh,
  input_l40, edits_l45.json = edits_l43 with that row). Control: the same machinery on edits_l43 reproduces l43 byte-identical.
  Then budgets.cland_pinslot_types copied from l44.
- l45 vs l44 (json compare): only hd_spn_wshim_rx: sink row; taps clk_t5 new at (480.6,284.0), east taps (682.6,783)/(682.6,934) merged
  to (682.6,858.6) (569 sinks, r 165 um); raw START relay pick u_rrl_13 -> u_rrl_30 (landing_contract / landing_local_resets /
  reset_start_raw_exports). RTL: ot_s81hd_spn_wshim_rx.sv (tap comments + re-sited reset relay tree) + start_stages json; top RTL and sidecar unchanged.
- plan source_plan.json sha256 df73603b5abf5eb6efc64b3c8454de864af5d002b6e93a027123583400e51ecf (sidecar 02dececead4a = l44)
- G0C main b2cd2d28d2a check.py --completeness: l44 1 err / 16 warn, l45 1 / 16, 0 new / 0 gone (g0c_l4?_main.json).
- strict bind (DIE-HEAD-40 run_source_portbind.py at b2cd2d28d2a): l44 guard PASS (358 inst, nested 6108); l45 PASS (358, nested 6106 = 2 fewer wshim_rx relays).
- die clock l45a405 (head_l44a405 config, plan path only): GRT TT/FF overflow 0 (90720 nets), spread scaled 122.33/120.14,
  OCV stated 149.78/142.16 (0 > 150), duty 0 outside 45-55 = l44a405.
- wshim_rx l45 kit (main b2cd2d28d2a, head_rekit_current.py): LEC EQUIVALENT, PLACE rc 0, AUTO-GEOM clock_reach 235.83 -> 182.13 PASS,
  r2r 369.4 x0, pin_reg_p90 27.4, GRT 0; left: fill/empty (standing exception), pin_reg_max 179 = START pin (ring_start, COORD 15:44 3A).

## l44 pinslot kits (kits_l44/): LEC EQ all 4, PLACE rc 0, GRT ov 0
turn_a p90 79.6 -> 27.4 PASS; turn_b p90 100.1 -> 92.5 FAIL (upper pin rows: flops smear diagonally, see render); st_str p90 86.2 -> 64.4 FAIL,
r2r 509.8 x506 -> 463.0 x4 (landing control aggregate), clock_reach 220.27 (l40 220.32).

## LEP ECO6 (eco6/) = LEP ECO5 f + 2 data buffers
ECO5 f re-sign at flow-20261030-e-head: NOT SIGNED only on TT slew 1 (beat_tx[157]/D 328.96 vs 320; OAI21x1 -> face flop 121 um);
TT +10.15, FF hold +3.21, pair skew TT/FF 77.0/67.8, DRC 0. ECO6 adds one BUFx4f at each of the two OAI21x1 drivers (gpay[101], gpay[86]).
