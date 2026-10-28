# DIE-HEAD-11 compose start-pin slice (2026-10-28 10:49 PDT)

Opt-in by a --start-tree clock bind (count_aligned.start_ports). A child region start arrives on ONE dedicated pin
cland_tstart_in of its origin partition; the parent origin drives ONE cland_tstart_out (= cland_start, fanned out at
the die top). Ends at a virtual region (st:) are die-level start stages (start_stage_emit.py): die-top ports
rs_<region> (out, to the stage) and pst_<region> (in, from the stage), like clk_region_*. The ring write-count start
(cland_fstart beside each bus) is unchanged. Bind without start_ports: byte-identical paths.

Fixes DIE-KV-13 KeyError start:hg_EN_1->hg_EN_0 (strap_ties looked a start port up as a plan crossing).

CHECKED (tool runs, no builds):
- KV ev1 bind (intel1 die-kv-13-1028/ev1/bind.json, kv_compose.py): compose OK, 56 types / 160 parts, straps
  types_after_straps 56, residual split 0, tsel 0; start ports 189 = 65 partition->partition + 62 -> stage + 62
  stage ->; Landings() OK (3595 rows, 0 type splits).
- HEAD inv2 r200 measured-stage bind (ca_g5st, head_compose.py, region monitor): compose OK, 16 types / 326 parts,
  0 splits, 517 start ports = 26 -> stage (20 nets) + 326 stage -> partition (HEAD root is a stage).
- tests: test_start_pins_compose.py 6 new + test_clock_landing_verify 2 new; landing/count/strap suites 183 PASS.
OPEN: root_p_start of a stage root (HEAD) still needs its die-level ot_dp_landing_root (next emitter slice);
die-top hookup of ot_die_start_stages + ctree tap ports happens in the die clock emission.
