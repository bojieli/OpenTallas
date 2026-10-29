# DIE-QC-35 PROG QC-020 ffh10r: SIGNED OFF (physical sign-off + routed LEC EQUIVALENT + PG census PASS)

Same hooks / config / run script as `../ffh10e` (FF-only post-route hold ECO, margin 10, FF vclk 381.14, clk_freeze),
started from the ROUTED ffh10 `5_2_route.odb` (sha256 ebe156c63c00bb28..) + its 6_final.spef (KV mk_eco default
OT_ECO_FROM=route form), so the ffh10 clock detailed wires stay FIXED. Kit intel2
`/srv/opentallas-scratch2/claude/die-qc-34-kits/prog/kit_ffh10r`; unit **oth-ubuntu-1139601-1793300807** exit 0
(12:03-12:18 PDT); client log intel2 `~/dqc35k/prog_ffh10r.otrun.log`.

CHECKED (kit run_route.log + signoff/signoff.json, copy here):
- ECO: routed-SPEF FF hold before -4.115 ps (= ffh10 sign-off); 196 hold buffers (data paths); OT_CLK_FREEZE ON 333
  clock nets with wire, 333 re-encoded FIXED; assert OK "all 333 clock nets carry their pre-ECO FIXED wire" (17 nets
  touched by GRT updateDirtyNets were restored by the freeze); post (GRT RC) +6.32; DRT 0 violations (no DRT-1231).
- **signoff.py verdict SIGNED**: TT setup **+232.16** | FF hold **+6.67** (measured pin-flop FF vclk reference) |
  related-pair skew TT/FF **79.2 / 71.5** (<= 80; 0.8 ps headroom) | pin-flop spread info 62.51/62.57 | DRV slew/cap 0 |
  fanout PASS | DRC 0, antenna 0 | PG PASS | timing_modes PASS | sdc_lint, face_guard, unconstrained, clock PASS.
- No clock ECO, no pads/trims, no skew targets, no new check; hold cells are ordinary repair_timing data-path buffers
  (12.4a a1) at the 12.19 10-ps margin on measured arrivals.

Not yet done (blocks CLOSED): **routed LEC** (kit RTL vs 6_final.v). The kit has no rtl/ dir (deleted with the s8b kit;
config.mk VERILOG_FILES /work/rtl/qfd_dv_s5_vm8x.sv + 3 SRAM _bb.v, spec 86288faea:physical/ref_tile/qfd_dv_s5_prog);
stage those exact sources into the kit, then main `tools/die_plan/lec.py KIT --netlist .../6_final.v --out
KIT/lec_routed` with OT_LEC_SUPERSET_VEC=1 (autopilot signoff_chain form); also the PG census on 6_final.
Caveat: the related pair has 0.8 ps headroom and moved 78.4-85.6 across three routes of the same tree (ffh10e); any
re-route of this DB must keep the clock wires FIXED, and the tree re-balance of the pcap/p_q and u_hi_wd -> u_hi leaf
groups stays the structural item for the next plan event.

## DIE-QC-35 (KITS round 2) routed LEC + PG census on 6_final (2026-10-29 12:38 PDT) -> QC-020 SIGNED OFF, CLOSED
All numbers CHECKED from the files in this dir (copies of the kit outputs).

**Routed LEC: EQUIVALENT** (`lec_routed/lec.json`, exit 0): main `tools/die_plan/lec.py` (origin/main a62696e61, sha256
c06c2e72..) staged as KIT/lec.py, `OT_LEC_SUPERSET_VEC=1` (autopilot signoff_chain form), `--netlist` the routed
`6_final.v` (sha256 c273e187.., mtime 12:14:48 PDT; proof generated 12:28 PDT, i.e. newer than the netlist).
7221/7221 compare points proved, 0 differ, 0 undecided; 6238 key points by name + 113 register pairs/merges proved
inductively, 0 unmatched; kept registers 1972/1972; superset_vec all_shown true (0 extra bits); 12 SRAM black boxes.
Gold = KIT/rtl staged from **main 66b68bff2 (= current origin/main) rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv** (sha256 6680b721..)
+ the 3 SRAM `_bb.v` of spec 86288faea (d5e85b37 / 9352069d / 35e0905c); config.mk VERILOG_TOP_PARAMS MIF 1.
- Source identification (not a waiver): the kit freeze.json still names spec 86288faea / repo_rev 4151e9fe9f, whose RTL
  (sha256 edd3caca) predates the MIF=1 per-SRAM pre-decoded macro-interface registers (b91cc4b87, PATH-QC-SRAMIF 10-25);
  against it LEC is NOT EQUIVALENT (`lec_routed/lec_86288faea_pre_mif.json`: gate-only g_r.u_hi_ra.* registers,
  u_p1.q[0..3] differ) = the netlist carries the MIF=1 interface. Every MIF=1 version on main or on fleet kits
  (b91cc4b87, 95ddf32dd, 66b68bff2 + 6 staged kit copies) is EQUIVALENT with identical counts (`try_cands.sh`, epyc2 unit
  oth-ubuntu-628547-1793302129 exit 0; the prog top is unchanged across them). The kit rtl/ now holds the 66b68bff2 file.
  Follow-up (kit generator, not this kit): freeze.json spec/repo_rev of the PROG kit lineage is stale vs its netlist.

**PG census on 6_final: PASS** (`pg_census_6final/pg_term_census.json`, script `pg_term_census.py`, OpenROAD 26Q3 in
openroad/orfs:asap7lock on intel2, docker 16 GB, diagnostic probe): master-terminal driven (every POWER/GROUND MTerm of
every instance master, not getITerms) -> 204,445 instances (incl. fill), **408,890 PG terms, 0 open / wrong-type**;
VDD and VSS each special, with SWires, 204,445 ITerms each. Same count as signoff.json pg (408,890 / 0 open).

Verdict: physical sign-off (signoff.json SIGNED) + routed LEC EQUIVALENT + PG census PASS -> **QC-020 signed off**.
Structural item for the next plan event (not a blocker): related-pair headroom 0.8 ps (79.2 vs 80 TT; this pair spanned
78.4-85.6 ps over three routes of the same tree) -> PROG CTS tree leaf re-balance of the pcap / p_q and u_hi_wd -> u_hi
leaf groups.

## DIE-QC-36 KITS: freeze.json provenance corrected (2026-10-29 13:27 PDT)

COORD ruling [DIE-QC-35 KITS update] (1): kit freeze.json now records the RTL actually signed. `fix_freeze_provenance.py`
(run on intel2 kit_ffh10r) added `rtl_signed` = main 66b68bff2 rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv (sha256 6680b721..), MIF=1,
+ the 3 SRAM _bb.v of 86288faea (d5e85b37/9352069d/35e0905c, verified against git), netlist 6_final.v c273e187, lec.json 34f4dfc4.
The old spec/spec_sha256/repo_rev/rtl_patches values are kept verbatim under `superseded[]` (with the reason and the original
file sha256 c6f46503); the untouched original is kept as `freeze.json.pre_provenance_fix` (both copied here). spec 86288faea stays
the physical spec (pins/outline/macros); only the RTL source of record moved. Kit freeze.json sha256 now fdad72b9.
