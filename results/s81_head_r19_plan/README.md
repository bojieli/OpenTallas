# HEAD-R19 plan delta (HEAD-CORE-R19 / HEAD-R19-PLAN) 2026-10-27 11:06 PDT

Base origin/main 60b5ddf523 (already holds the head-r17-plan snap_inside islands 2b67cdc6c3 / ROOT-MERGE-34; its s81_head plan
dir is byte-identical to 2b67cdc6c3, plan sha256 d84d7778ce5f). Ports the dead HEAD-R18 lane's uncommitted delta
(intel2 wt/head-r17-plan-1027, branch claude/head-r18-plan-1027; patch preserved at
intel2:/srv/opentallas-scratch2/claude/tmp/head_r18_dead_wt.patch) and fixes what it missed.

Applies the two COORD 07:47 (HEAD-CORE-R17 ruling 4) APPROVED items, nothing else (delta self-check: dict-equal after undo):
(a) hd_mesh u_core (ot_s81hd_mesh_ep_core) params BQ=2 (one type -> mesh0S, mesh7N, mesh7S); RTL default 7 unchanged.
(b) hd_tile core taps u_core.u_b.g_cv*.u_e*.clk -> .ft_mstrap_i at the real built-LEF pin position; hard-core outlines =
    built SIZE (A 317.672 -> 319.68, B 277.652 -> 285.12).

Main had NOT yet: the BQ param, the ft_mstrap_i tap rename, or LEF-derived pin files (main pins = old closed-LEF files with
`clk`). Main's Codex head_native_plan_delta.py (opt-in 40FT) already assumes functional clock port ft_mstrap_i and reads
ft_* pins from the same pins_file -> compatible with these pin files.

## Fixes vs the dead R18 lane (its G0C 0 was STALE: g0c.log 08:04 predates its final pins/delta 08:08-08:10)
On main the R18 output gave G0C FAIL 30 errors (hard_cores: pins off the plan tracks). Two causes, both fixed structurally:
1. track_offset_um of the mirrored axes was derived for the old 317.672 outline (mod 0.048 = 0.008 -> 0.028); for 319.68
   it must be 0.036. head_r18_plan_delta.py now recomputes track_offset_um per axis from the pins' core-frame track
   residue (fails closed if not unique), and the tap xy now includes it (origin + track_offset + orient(pin)).
2. head_pins_from_lef.py: USE POWER/GROUND pins (VDD/VSS strap combs) are excluded (`excluded_pg`; old closed-LEF files
   never listed PG); multi-track pins (9 centre FT pads 0.192 um + rst_n) are represented by their on-track access
   point inside the RECT (core residue 0.012), centre kept as `rect_centre` (10 pads per core).
Pin sources (sha256 in files): A intel1 head-core-r16/elemA_m2 routed abstract LEF (17786be2...); B epyc2
head-core-r16/elemB routed generate_abstract LEF 08:20 (da3694b4...; pin set canon-identical to the 08:08 GRT abstract
the dead lane used).

## Commands (repo root, intel2) and results
    python3 tools/s81_head/head_pins_from_lef.py <A.lef> physical/die_plan/s81_head/cores/elemA_pins.json --source-label ...
    python3 tools/s81_head/head_pins_from_lef.py <B.lef> physical/die_plan/s81_head/cores/elemB_pins.json --source-label ...
    python3 tools/s81_head/head_r18_plan_delta.py physical/die_plan/s81_head/die_plan.json --report results/s81_head_r19_plan/delta_report.json
    python3 tools/die_plan/check.py physical/die_plan/s81_head/die_plan.json --out results/s81_head_r19_plan/g0
    python3 tools/die_plan/check.py physical/die_plan/s81_head/die_plan.json --completeness --out results/s81_head_r19_plan/g0c
    python3 tools/s81_head/head_die_portbind.py physical/die_plan/s81_head/die_plan.json --out results/s81_head_r19_plan/portbind

- Plan sha256 5a61dd5eb9a7021d92c8130c5b8988e5085c635bd7803257d5dda7adca105ceb (before d84d7778ce5f) CHECKED
- G0  PASS 0 errors / 6 warnings (g0/g0_report.json) CHECKED
- G0C PASS 0 errors / 6 warnings, 16/16 types clean (g0c/g0_report.json) CHECKED
- Strict portbind HEAD_DIE_PORTBIND PASS: module_missing 0, DIE_PORT_BIND PASS (326 inst, params_not_in_rtl 0), tie audit
  PASS 528/0, nested PASS 2203 inst (portbind/) CHECKED
- gen_rtl emits BQ: portbind/gen/ot_s81hd_mesh_ep.sv:325 `ot_s81hd_mesh_ep_core #(.BQ(2)) u_core (`; the one module
  ot_s81hd_mesh_ep is instantiated by mesh7N, mesh0S, mesh7S in the generated top. No gen_rtl change needed. CHECKED
- master_plan.core_clock_entry_check (main's actual-named-native-pin check) on the 5 hd_tile cores: 5/5 PASS,
  tap_to_native 0.000 um (clock_entry_check.json) CHECKED
- Tests: tools/s81_head/tests/test_head_r19_pins.py 6 PASS (PG exclusion, pad snap, fail-closed residue, track offset
  for R0/MX/MY/R180); tools/die_plan -k 'bootstrap or clock_entry or schema or master_plan or native': all pass except
  test_native_istations (needs iverilog, absent in the python:3.12 container: env, UNCHECKED).

## UNCHECKED / open
- Insertion stays PENDING (250 ps target) until the signed centre-entry views publish theirs; no core is signed off yet.
- elemB pin source is the R16 routed abstract, not a signed-off view; regenerate pins if a later B view re-pins.
- No render: no geometry moved beyond <=0.036 um track shifts and the outline growth already in the R18 delta (outlines
  grow inside the same origins; G0C box-inside-outline check PASS).
