# SYS_C / SYS3 handback — Codex parked 2026-10-26 04:24 PDT

Stopped starting work on parent notification that Claude reset. No jobs killed. No route/STA authorized: current SYS_C remains FAIL STRUCTURAL.

## Published source fixes
- Native ROM/header/LEC/PHY PG source-only packet `codex/sysc-flow-narrow-1026@71c0780ba`, exact actual-hub main51fe3d1f8 base, merged by root in main8a121b0c8. Eager BB preserves real INSTANCE/VIAMAP; scoped physical canonicalization writes immutable ROM metadata then removes unsupported string cellparams only in physical netlist. LEC known ROM metadata parameters only; unknown params still fail. PHY PDN anchored/escaped ODB instance regex and actual LEF PG layer selection (native PHY M6->M7). 10 focused checks PASS, tiny native ROM formal40/40 EQ, address mutant39/40 NOT_EQ. Six macros unchanged:4xSRAMp288 +ROM64x32 +native7portFDI PHY.
- READY `codex/sysc-keepout-1026@187a4b2a4` on411eae3b9, actual-hub branch published, based main8a121b0c8. Clears only overlapping welltap/endcap/TAP_/PHY_EDGE_ cells under newly added die-clock/PHY PG reservations; EVERY master MTerm must be POWER/GROUND regardless direction/connectivity. INOUT SIGNAL/CLOCK/RESET controls fail closed,11focused tests PASS. Both old B19 and actual B31 native check_placement PASS after removing exactly6602 physical cells across75 blockages, zero logical cells removed. Root has READY tip; no root merge by this worker.
- Do NOT merge broad `codex/native-bb-1026@4a9af7c67`: superseded by narrow source packets and includes already-merged schema/island work. Do NOT merge old physical `codex/kv-sysc-1026@9a0fa1aca`: B19 diagnostic only.

## Current source / live job
- Current B31 source a8c24031c77b7ec882369673e7563d7bda8b3d7a, parent full bound verification PASS2553368. TXDP22->113 is producer capture latency, NOT SRAM depth; reset relay count84->69, depths remain8; exact8868 R8 pad FFs unchanged.
- Current WIP `codex/kv-sysc-b31-1026@b0e2e94d81`, published actual-hub and GitHub. Whole branch has KV batch ancestry: NOT READY for blanket merge. Actual own sparse worktree `intel2:/srv/opentallas-scratch2/claude/wt/codex-kv-sysc-b31-1026`.
- Kit18files / six macros /4987ports /4967face bits PASS;31514registers, fanout>64=0. Synth/ODB preflight PASS.
- LIVE full B31 LEC: intel2 host PID3711494, ~98% CPU, running76min at park. ot-run unit3695060-1793009121, original client971626. Work dir `/srv/opentallas-scratch2/claude/codex-kv-sysc-b31/phys_current/kv3_sys_c`, `lec_run.log` buffered/empty, gold+gate AIGs exist. Stream actual-epyc1 `/srv/opentallas-scratch2/claude/codex-kv-sysc-1026/b31_synth.log`. Leave running, do not call PASS without terminal. Old B19 formal deliberately superseded/stopped by exact guarded own PID; receipts remain `lec_metadata_r2/superseded.json`.

## Current measured geometry / failures
- Actual current placed shape2160x1036.8, native PHY777.6square central wall at691.2,60.48; its supply hard keepout682.56,51.84..1477.44,846.72. Four SRAMs596.16,y17.28/103.68/190.08/276.48,57.912x67.512. ROM302.4,250.56. Accepted74 die island rectangles preserved, no mesh rebuild.
- `/srv/opentallas-scratch2/claude/codex-kv-sysc-b31/current_place_g256` is exact current kit. `-bin_grid_count256` reduces pathological8.4M FFT bins; full shape/timing constraints unchanged. Native DPL first failed physical tap overlaps. Original failed ODB preserved at `run/results/asap7/dp_kv3_sys_c/base/3_5_place_dp-failed.odb`.
- Read-only guarded cleanup created `corrected_placement_diagnostic.odb`, native check_placement PASS: before247092, removed6602 physical-only cells. Logs actual-epyc1 `.../codex-kv-sysc-1026/b31_keepout.log` and stricter `b31_pg_guard.log`; both terminal0. Not a release checkpoint or route permission.
- Full current baseline reach census:41292endpoints /178822arcs /6829endpoints>405 /max2819.826um;4660D endpoints>405. Major KVN output to W rec_rx1832um; RXcalendar control596; rf824; SRAMdq638. Native actual image was viewed: FAIL STRUCTURAL.
- Actual baseline artifacts intel2 `current_place_g256/reach_current`. Local copies `/srv/opentallas-scratch/claude/sysc-b31-current-reach/` incl viewed `actual_failure.png`. Local `cells.tsv` NOW full physical export from corrected baseline; old lean copy `cells_lean_original.tsv` preserved.

## Locality prototype — unfinished, do NOT route/adopt
Parent authorized existing-FF locality, zero cycles; parent separately owns post-producer W/E output pipeline budgets. Parent explicitly delegated internal RXcal ev_*->ecnt/r1/r2 controls to SYS_C. Native identity/stage/latency unchanged by all prototypes.

First reviewed candidate moved6238FF+149ties. DPL failed2947 overlaps because emitter used setOrigin after mirrored row orientation; canonical face_flops.tcl181 explains correct setLocation. Original log `b31_locality.log`, original emitted Tcl retained `current_place_g256/locality_candidate/origin_bug.tcl`.

Corrected setLocation candidate failed137 overlaps/157padding checks, all exact TAP_TAPCELL collisions. Cause: census cells.tsv intentionally filtered TAPCELL masters, so allocator's fixed tap reservation never saw their geometry. Native verbose log `b31_locality_check.log` lists every pair; full fixed-body export now exists `locality_candidate/full_cells.tsv`, log `b31_full_cells.log` PASS. Source allocator now uses all bodies and macro8.64um halos; no new physical attempt after that correction.

The failed setLocation candidate saved `locality_candidate/dpl_candidate.odb`; full native reach diagnostic on it terminal:41292/178822,5613>405,max2819.826. Artifacts `locality_candidate/reach_diagnostic/{hops.tsv,all_arcs.tsv,cells.tsv,summary.txt}`. This is meaningful structural diagnostic only; overlap unresolved in that checkpoint. Unlike old worst-source-only output, all_arcs.tsv preserves every actual fan-in source; hidden alternate sources exposed new broadcast/control paths.

Latest purely static revision is LOCAL only, NOT P&R/visually reviewed/adopted: `/tmp/sysc_locality_candidate.py` (hardcoded current data), `/tmp/sysc_locality_1026.py` (CLI candidate emitter), `/tmp/review_sysc_all_arcs.py`. Latest generated local `/srv/opentallas-scratch/claude/sysc-b31-current-reach/locality_candidate/{sites.json,locality.tcl,all_arc_prediction.json,touched_arcs.tsv}`. Exact previous native sites in `prior_sites.json`. The older `review.png` does NOT represent final static expansion and cannot authorize P&R.

Latest static model10473cells includes:
- Existing last3 ATT pad stages -> q_att capture near430,350; existing last2 EMB pad stages ->q_emb near500,300; existing host-rec pad1 ->q_record near390,430. Every existing stage identity unchanged; all3 payload alternatives must be included.
- TX capture control copies g_dly[*].fc[*] near500,300 and only existing final sr stages g_dly0.sr111 /g_dly1.sr2 /g_dly2.sr1 near500,450; matching reset ties included. dq feeds SRAM DIRECTLY; dqq is bypass history, NOT extra write relay.
- SRAM dq near560,y200..350; dqq near560,y230..380; dout near670,y330..390; existing u_ctl.q_pin near665,700; rf/es near880,850; KVN near1100,900. This is real q_pin/rf pipeline, not unrelated ft1.
- RXcalendar near500,710, reset g_c6.qv0 brought local; r1 near620,790, r2~890,900, ecnt~620,750, native rx_slot/kind/beat/ev2/rs2 near900,850.
- Status near1000,900; existing token epoch pad1~315,850 ->q_status_epoch16~655,850; engine result FFs~1200,900.

Latest all178822-arc projection remains FAIL:4523 DATA endpoints>405 (includes parent output legs now farther from old faces). Hidden remaining internal families: q_kvn_compiled_identity[*] still atE2030,640 feeding relocated KVN ->~1213um; existing u_link.u_ctl.rx_flit[*] (after rf) still1600,412 ->~1165um; q_crom_fault/q_fault captures remain old locations and status outputs need coherent relocation. These are NOT solved. Next steps: finish those existing-stage chains and actual input R8 allocation, compose parent's W/E post-producer pipeline map, full-arc geometry before another native placement; render/look at final image; native DPL must honor all actual tap bodies plus halos; no route until full reach0>405. Additional budget/cycle changes need bind/R8/joint miter, never silently add cycles.

## Worktree leftovers / ownership
- Actual B31 worktree uncommitted tracked census adapter fix `tools/qwen_kv_die/sysc_reach_census_1026.tcl`; untracked `tools/qwen_kv_die/sysc_locality_1026.py` is an EARLIER version, latest expanded version is local `/tmp/sysc_locality_1026.py`. Do not assume remote tool has final static expansion. No final code commit on parking order.
- Actual B31 untracked staging `physical/die_plan/qwen_kvsys/kit_plan_sysc_b31.json` and `sysc_b31/bind/` are complete source generation inputs, not partially applied main edits.
- Local own clean source WT `/srv/opentallas-scratch/claude/wt/codex-sysc-flow-narrow-1026`, branch codex/sysc-keepout-1026@187a4b2a4. Old local physical WT `/srv/opentallas-scratch/claude/wt/codex-kv-sysc-1026` has newer census full-arcs/physical-body export than remote; latest copied census lives there. Shared infra_clock owns mesh, cores sibling owns CORES-KITS; no overlapping plan/core edits by SYS_C.
- No physical jobs remain running/queued; only own B31 full LEC above remains live. All other listed native jobs terminal. No OWNER questions outstanding.
