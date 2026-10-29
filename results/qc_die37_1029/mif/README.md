# DIE-QC-37 / QC-020: PROG MIF1 plan event (2026-10-29)

Task: COORD ruling [DIE-QC-36-PARK] (1), 14:18 10-29. Adopt the default-off MIF1 candidate (codex/qc-mif-1309@c9cdec9e23) as
one fix-only plan event, after pricing the extra programme/SU edge in tok/s. If the price is above 5 %, it goes to the owner.

**Outcome:** the price is at most 0.94 % tok/s (≤ 5 %), so this is not an owner question. The native QC bind with MIF1
passes the strict bind with 0 errors, and `u_pg` is bound as `qfd_dv_s8x_prog #(.MIF(1))`. The PROG view matches on that
bind: the ports match 9/9, and the hashes of the LEC gold sources are identical. **One blocker:** MIF is a single
parent-wide switch. Turning it on also flips VMR and BTAB to MIF1. The signed VMR view (f4k) is MIF0, and the live BTAB
A/B builds are MIF0. COORD must rule on this before ROOT-MERGE (options below). This branch is not merged into main.

## 1. Candidate vs main

- The 11 commits of c9cdec9e23 are not ancestors of main. However, their source is already in main through
  **6864c4b08** ("QC MIF1: restore opt-in current-source parent profile without enlarging flop rings") and
  **66b68bff2** (MIF1 timed reset profile). Main's `qfd_dv_s8_flat.sv`, `qfd_dv_s8_suvm_rp1.sv`,
  `qfd_dv_s8_vm8q_rp1.sv`, `gen_slice8_*`, `tools/qwen_dv/mif1309/*.sv/.sh` are byte-identical to c9cdec9e23.
  `qfd_dv_head_safe1.sv`, `qfd_dv_s8_ce.sv`, `qfd_dv_s8_crh_rp1.sv`, `latency_contract.json` and `uarch_model.py`
  are newer successors in main: a separate 133-bit reply stage instead of the 2128-bit ring, and the timed CRH reset.
- Cherry-picking c9cdec9e23 would therefore **regress** main. No pick was made. The plan event is to turn the switch on.
  The switch is `OT_QC_SRAM_MIF` → `qfd_dv_s8_flat.S8_SRAM_MIF=1` → `suvm_rp1/vm8q_rp1 MIF=1`.
- What MIF=1 changes, per `tools/qwen_dv/mif1309/latency_contract.json` and `uarch_model.qwen_sram_if_mif_model`:
  - each SRAM read and write gets +1 edge (VMR a/b/c, BTAB, PROG, CRH lo/hi);
  - the SU start relay `wf_st` goes from 3 to 4 edges (programme fetch +1);
  - head `MEMORY_READ_EXTRA=1` adds one common 133-bit reply stage.
  - Priced at **2 serial edges per SU command**, plus 1 boot edge after a table write. MACs, port count and issue width
    are unchanged.
  - Codex gates on c9cdec9e23, cited from qualification.json and not rerun here: group 4096 cycles / 48,768 checks PASS;
    head 2,272 checks PASS; fetched programme 1,335 checks / 1,293 live edges PASS; 3 missing-edge mutants caught.

## 2. Token price (estimate before build)

Base: QC+KV pair period **293,376 cycles = 4,092.0 tok/s @ 833 ps** (TOK-QWEN-6, CHECKED there,
results/token_pass/tok_qwen_6_1029).

QC layer programme: results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex, decoded with
`hdc_qwen_fullshape_isa_w12.decode_instruction`. It has **25 instructions: 17 SU (unit 2), 5 unit 1, 3 unit 0**
[CHECKED-own]. The QC ops sit on the token critical path in every layer (token_path_compiled critical_path), across 36 layers.

| case | formula | +edges/token | period | tok/s | Δ |
|---|---|---|---|---|---|
| contract model | 2 edges × 17 SU cmds × 36 layers | 1,224 | 294,600 | 4,074.9 | **−0.42 %** |
| conservative bound | 3 edges (fetch + read + write) × all 25 instr × 37 (36 layers + 1 layer-equivalent for embed/LM head) | 2,775 | 296,151 | 4,053.6 | **−0.94 %** |

- The arithmetic and the instruction counts are **CHECKED** (recomputed here).
- The +2 (or +3) edges per command come from Codex's contract and its measured fetch bench. They are not a compiled MIF1 token.
- The bound assumes no command overlaps, so the real value lies at or below it.
- **Both values are far below 5 %, so there is no OWNER? line.**
- **Not claimed:** a compiled MIF1 token. `tools/qwen_layerbench/dv_lower.py check_memory_profile` refuses to compile with
  MIF0 ages under MIF1 RTL, so the token pass still needs a fresh MIF1 age calibration. That is
  `qualification_remaining[0]` in the candidate and is owned by TOK / the QC programme.

## 3. Native bind with MIF1 (epyc2, ot-run)

- Recipe: `results/qc_die37_1029/bind_mif1/run.sh`. It is the DIE-QC-33 chain (prepare_paired → latency → probe →
  R8 → base → CB16 → strict final) with two additions:
  - after prepare, `defines += OT_QC_SRAM_MIF` is added to the manifest of record `bind_mif1/asbuilt.json`;
  - a fresh `bind.py elab` runs (DIE-QC-33 had reused the Codex elab2).
- Tree: main fb1fc79593.
- **MIF1 run:** unit oth-ubuntu-1564384-1793310118, exit 0. Run dir `epyc2:/srv/opentallas-scratch2/claude/die-qc37-mif1-bind`.
  - ELAB PASS: 84 modules; 13 files read with `-DOT_QC_SRAM_MIF`.
  - **final --strict: 377 parts / 119 types / 1921 crossings / 790,393 bits, errors 0, unbound/tied/undriven/multiply 0,
    11,568 straps** [CHECKED-own, evidence/status_mif1.txt, bind_report_mif1.json].
- **MIF0 control on the same tree:** unit oth-ubuntu-1469768-1793309473, `epyc2:.../die-qc37-mif0-ctl`. Strict 0 errors,
  same counts. This reproduces DIE-QC-33 on current main.
- **u_pg MIF=1 confirmed:**
  - In the elaboration, `$paramod\qfd_dv_s8_vm8q_rp1\MIF=1` has `u_pg qfd_dv_s8x_prog {MIF: 1}`. In the control it is `{MIF: 0}`.
  - The bound partition RTL `final/rtl/qfd_qc_sle_su_c.sv:1986` reads `qfd_dv_s8x_prog #(.MIF(1)) u_u_suvm_u_vm8q_u_pg`.
  - Evidence: evidence/elab_mif_params_*.txt, bound_su_c_mif_lines.txt.
- **Inputs unchanged vs DIE-QC-33:** plan.json, sidecar, R8 table, latency, CA/strap deltas and pair_rule are
  byte-identical. cb16_pads differs only in its own r8_table path.
- **Bind outputs vs MIF0:** bind_latency, bus_groups, param_regen and bind.f are IDENTICAL. Only the intra sink count
  changes, from 1,998,567 to 1,998,579 (+12 = one extra `wf_st` fetch-relay FF per slice).
- **What changes physically** (bound RTL diff vs MIF0, 12 of the partition files differ, evidence/bound_rtl_diff_vs_mif0.txt):
  - `qfd_qc_sle_su_c` and 2 `slw_su_c` classes: leaf MIF params plus the +1 fetch relay;
  - 9 `sle/slw_su_l0/l1` classes: 36 `qfd_dv_lane_h_safe2` instantiations (across the 9 class files) now `MEMORY_READ_EXTRA(1)`.
  - None of these types is signed (OWNERS: sle_su_* PLAN-STRUCTURAL, slw_su_l* KIT-PLACED, slw_su_c FIX), so no
    partition sign-off is lost. Their kits must be built from the MIF1 RTL.

## 4. PROG view re-verified on the MIF1 bind

- **Interface:** the bound `qfd_dv_s8x_prog` ports in the MIF1 elaboration (lib stub) and the module ports of the signed
  `6_final.v` (intel2 die-qc-34-kits/prog/kit_ffh10r, sha256 c273e1872c1c...) are **identical: 9/9 names, directions and
  widths** (ck, p_re, p_idx[9], p_q[457], tw_we, tw_kind[2], tw_addr[8], tw_d0[457], tw_d1[457])
  [CHECKED-own, evidence/{bind,signed}_prog_ports.json].
- **Function:** the routed LEC (EQUIVALENT, 7221/7221 compare points, kept 1972/1972; DIE-QC-35) used as gold
  `66b68bff2:rtl/qwen_dv/s5/qfd_dv_s5_vm8x.sv` top_params MIF=1, plus 3 SRAM `_bb.v` (freeze.json 4513968c1 `rtl_signed`).
  The MIF1 bind elaborates `u_pg` from exactly those 4 files and with MIF=1: sha256 6680b721…/d5e85b37…/9352069d…/35e0905c…
  are identical to freeze.json [CHECKED-own, evidence/prog_sources_sha256.txt]. vm8x.sv has no `ifdef` on
  OT_QC_SRAM_MIF; its only defines are OT_S8_MUT_*, all unset. So the bound PROG RTL is the LEC gold, and the
  equivalence carries over without a rerun. A literal LEC rerun would compare the same files and was not spent.
- => **QC-020 closure condition met on this bind** (native binds MIF1 and the PROG view is re-verified), once the event is
  adopted (merged).

## 5. Blocker for adoption: one switch flips 4 leaf types

The signed views and live runs use a mix of MIF settings (CHECKED from kit config.mk `VERILOG_TOP_PARAMS`):

| leaf | view | MIF | effect of global MIF1 |
|---|---|---|---|
| qfd_dv_s8x_prog | ffh10r SIGNED | 1 | matches (QC-020 closes) |
| qfd_dv_s8_crh_rp1 | f62 SIGNED (autopilot closed …crh_rp1__f62__d965a9aada) | 1 | **now matches** (the native MIF0 bind was also mismatched here; this was not on the CLOSURE-LIST) |
| qfd_dv_s8x_vmr | f4k SIGNED-UNVERSIONED (QC-015), kit "MIF0 … no top params" | 0 | **invalidated**: needs a MIF1 VMR view (source exists, 95ddf32dd) |
| qfd_dv_s8x_btab | QC-014 V1d / A / B live, no top params | 0 | **A/B results are invalid for MIF1**: the next variant must be built with `VERILOG_TOP_PARAMS = MIF 1` |

Options for COORD:

- **(a) Global MIF1 (this branch, recommended).** It matches PROG and CRH and closes QC-020. The source has been
  qualified by Codex. MIF1 is also the GEOM-REVIEW F6 macro-pin-anchored form. Cost: re-sign VMR at MIF1, and switch BTAB
  to MIF1 at its next variant (A/B are not signed yet, both expected DRC>0). The su_c/su_l kits take MIF1 RTL (they are
  not signed). Token −0.42 % model / −0.94 % bound. A MIF1 age calibration is still needed for the token pass.
- **(b) Per-leaf split.** A new parameter would set PROG and CRH to MIF1 and keep VMR and BTAB at MIF0, with parent relays
  re-aligning the head reply age. This keeps the VMR sign-off, but it is a NEW RTL delta, not the qualified candidate,
  so the group/head/fetch benches and mutants would have to be redone. Not recommended.
- **(c) MIF0 everywhere.** Harden MIF0 PROG and CRH views (two re-routes plus LEC). This is the rejected option (b) of the
  14:17 OWNER?, now extended to CRH.

DEFAULT if no ruling within 30 min: (a) stays prepared on this branch; nothing is merged; QC-020 stays OPEN. Do not put
new effort into MIF0 BTAB variants beyond the live A/B collection.

## Files

- `results/qc_die37_1029/bind_mif1/`: run.sh, asbuilt.json (MIF1 manifest), prepare_paired.py, pair_rule.json, cores
  link. Not committed, because they are regenerated and identical to DIE-QC-33 (sha256 in evidence/big_inputs_sha256.txt):
  plan.json (18 MB), sidecar.json, r8/, lat0/, *_asbuilt.json, cb16_pads.json.
- `results/qc_die37_1029/mif/evidence/`: statuses, bind_report, provenance, elab param dumps, bound-RTL diff list,
  port lists, source hashes.
