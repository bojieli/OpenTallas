# HEAD-BIND-4 2026-10-27: s81_head bind gaps (ID straps + hd_serdes binding), plan delta

Base claude/infra-first-head3 77ae153cac + merge of claude/head-core-r13-1027@148ff6a840 (adopted head bind contract,
COORD ~03:25). Runs on intel2 (python directly under a 16 GB scope; yosys in docker -m 16g). Numbers CHECKED = recomputed
from the json in this directory / the plan, not from log lines.

## Plan delta (tools/s81_head/head_bind4_plan_delta.py, applied in place to physical/die_plan/s81_head/die_plan.json)
Touches only partition_types.hd_tile.{contents, nets, sources, id_straps}, partition_types.hd_serdes.{contents, buses,
pads, sources}, partitions[hd_tile].id_straps. Clock / islands / pg untouched (merges with the INFRA-FIRST-HEAD-4 delta).
1. ID straps (OWNER 10-25 option B). u_strap (ot_s81hd_strap #(ROW0 0, TEN 1), hard-coded in all 264 tiles) removed;
   hd_tile declares id_straps strap_row0[16:0] + strap_ten, bound to u_core.row0 / u_core.ten; each hd_tile instance
   carries partitions[].id_straps; gen.py rtl ties them as literals at the die top; kit SDC
   `set_false_path -from [get_ports {strap_row0 strap_ten}]` (sdc_lint straps context).
   Values: tools/s81_head/head_row_map.py build(plan) (directed 565-b chain walk, 6 spines x {W,E} x 22 = 264 slots):
   slot k -> strap_row0 = 128 k (LOCAL row; global = + c_rbase), strap_ten = 1 for k < active(rank).
   Plan carries rank 0: 253 used + 11 dark (row0 0 / ten 0), max row0 32256 (CHECKED). Ranks 1 = identical;
   ranks 2/3 differ at exactly one tile, tE5o10 (slot 252): (32256, 1) -> (0, 0) (CHECKED,
   physical/die_plan/s81_head/bind/row_map.json, all 4 ranks; coverage 1010 bundles / 129280 rows, 0 dup / 0 missing;
   c_rbase 0/32384/64768/97024). `--rank R` re-applies the delta for rank die R.
2. hd_serdes: u_phy = ot_s81hd_serdes_link (coll_o0[513:0] = {st, rx}, 0 added cycles), ck = clk, rst_n = rst_n;
   PMA pins are type pads (new plan field `pads`: no boundary flop, die-top ports <part>_pma_tx[543:0] / _pma_tck /
   _pma_rx[543:0] / _pma_rck; 12 x 1090 = 13,080 die-top pad bits, CHECKED from the generated top). The link closure
   (ot_pdie_serdes + 8 KP4 + 2 v1 macro models, 11 files) moved from head_portbind_extra.f into hd_serdes sources, so
   gen.py rtl --rtl-root checks every u_phy port.

## Tool changes
- schema.py: partition_types.*.id_straps, partition_types.*.pads, partitions[].id_straps (+ semantic check: approved
  strap name/width from parent_id_straps.PHYSICAL_ID_WIDTHS (+ strap_row0 17, strap_ten 1), exact per-instance set, fit).
- gen_rtl.py: strap:/pad: bind keys, strap input ports, pad ports without flops, die-top strap literals + pad ports,
  DIR/parent_id_straps.json (straps.audit_top_ties manifest form).
- gen_phys.py / sdc_lint.py: strap false path + lint context.
- port_bind_gate.py nested_check (+ `port_bind_gate.py nested GEN -f FILELIST`): walks every instance INSIDE every
  generated wrapper vs its master header (all ports bound, no unknown port, widths equal under instance params,
  unresolvable width = FAIL).
- head_die_portbind.py: --strap-file to die_port_bind, tie audit (tie_audit.json), nested check (nested_portbind.json);
  verdict needs all four.
- test_port_bind_nested.py (5 tests): FAILS the committed old form results/arch/head_rtl5_1026/cand/gen/ot_s81hd_serdes.sv.

## Results
- G0/G0C canonical plan after delta: PASS 0 errors, 6 warnings (g0_die_plan/). CHECKED.
- Old form: the committed HEAD-RTL-5 PASS wrappers (results/arch/head_rtl5_1026/cand) FAIL the nested check: hd_serdes
  u_phy (ot_pdie_serdes) clk/rst/st/pma_tx/pma_tck/pma_rx/pma_rck unbound + rx 512 b <- coll_o0_d 514 b. CHECKED.
- cand/ = results/arch/head_rtl3_1026/candidate.json (provider candidate, NOT adopted) + this delta
  (candidate_bind4.json): HEAD_DIE_PORTBIND PASS: module check 0 missing, die_port_bind PASS (strap_ports 2,
  undriven 0, input_tied 0), tie audit PASS 528 = 2 x 264 literals all declared straps, nested PASS 2217 instances.
  CHECKED. (Its G0C has 10 errors only because the copy sits outside physical/die_plan/s81_head: plan-relative
  cores/*_pins.json not found.)
- canon/ = canonical plan after delta: FAIL only from the known 4 missing providers (ctl / host_ep / mesh_ep x3 self-
  instantiating STUBs, HEAD-RTL-3): nested failures are all in ot_s81hd_ctl / host_ep / mesh_ep, none in hd_tile /
  hd_serdes. Tie audit PASS 528. CHECKED. Needs the provider PLAN-DELTA (head_provider_plan_delta) to pass.
- LEC (lec/): see lec/lec.txt.

## LEC (tools/s81_head/head_strap_lec.py; yosys equiv_make/equiv_simple/equiv_induct in openroad/orfs, docker -m 16g)
gold = OLD hd_tile wrapper (u_strap ot_s81hd_strap with TIEHI/TIELO cells, SYNTHESIS form, tie cells = liberty
functions) per instance at that instance's row-map values; gate = NEW wrapper + the die top's literal for that
instance; ot_s81hd_tile = identical observer stub on both sides (o = i ^ {ten, row0}) so tile input pins are compare
points (a plain blackbox made them unobservable: the mutant control passed; fixed before any verdict).
- negative control `--limit 4 --mutant` (gate row0 + 1 on one instance): NOT EQUIVALENT, 4 unproven. CHECKED.
- all 264 instances (254 distinct variants, 253 ten=1): see lec/lec.txt if present; at commit time it was still running:
  OT_YOSYS="docker run --rm -m 16g -v $T:$T -w $T openroad/orfs:latest yosys" python3 tools/s81_head/head_strap_lec.py
  --old $T/old --new $T/new --top $T/new/s81_head_top.sv --out $T/all   (T=/srv/opentallas-scratch2/claude/hb4_lec on
  intel2; old/new = gen.py rtl --types hd_tile of the plan before/after the delta), ~1.1M $equiv cells.
