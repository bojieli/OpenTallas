# KV-TOK (epyc2)
## RESUMED 12:15 PDT 2026-10-24 (after 08:50-12:04 usage limit), adopted from Codex:
- root cause (Codex): legacy boot_go launches D2D admission 76 cycles before the boot config is ready (d2d fault cyc 539);
  BO1 opt-in source on main a2757edd53 (merged into claude/kv-tok-1024 @84d6f885b4).
- kv42_o1_perf / kv42_parallel16_perf collected: both reproduce boot_go 453 / fwd_epoch 463 / dcal_fault 539; speed
  O1 1-thread 4500 cyc / 994 s user (16:34 wall), --threads 16 top 4500 cyc in 4:26 wall (~17 cyc/s).
- kv42_bo1 (epyc2 scratch2 codex-qwen/kv42_bo1): top re-verilated with --threads 16 --hierarchical-threads 16 (1:47),
  single-thread binary kept as Vtb_kvslice.bo1_single. RUNNING 12:14: scratch2/claude/kv-tok/bo1tok/{nominal (FAR=1,
  preload, POST 300000), mut_frame (+MUT_FRAME=100)}.
- old O0 sims boot42/tok42 (pids 434532/434535/466382, root disk) left alive per Codex note.
 — branch claude/kv-tok-1024 (= tokj-kvslice-1023 + main), worktree localhost ~/wt/kv-tok, epyc2 ~/wt/kv-tok
## Status 2026-10-24 08:05 PDT
- ROOT CAUSE of the 10-23 top blow-up: Verilator 5.050 never substitutes a hier_block module that HAS parameters
  (minimal test localhost ~/ot-scratch/kv-tok/hiertest) -> strip_default_params.py (header parameter->localparam, drop the
  71 top #() overrides; all 2,582 overrides == defaults, exact). Committed 885afd56bc.
- PV boot item CLOSED as a record: kv42 = kv41 + PV W request-lane pads (8 ports, 900 flops) = bind/bound_kv42 (bb5ffd5b8):
  post-bind INNER-delay edit (netlist binder2-1023/kv_bound lost -> verify/port-bind NOT RE-RUN); bind_post regen PASS
  OK 17 / WARN 3 (VPORT_DQ WARN -> OK); boot image = image_kv41 by construction (literal prep re-run NOT RUN: rtl6 GEN
  inputs lost).
- BUILD epyc2:/srv/opentallas-scratch/claude/kv-tok/kv42_build (kv42 tree, 79 hier blocks, J=64, started 07:33 PDT): running.
- Token-phase bench written (c890c5d071+): compute-die far end on UCIe (real qfd_d2d_static + cal_seq on the kv41 pair image,
  record codec, KVN transport; RESULT vs gold of checkpoint_service_vectors T=256), post-boot observation, HBM preload
  generator (CONTRACT map v2) + HBM address log for the map self-check. NOT RUN yet.
## Next
- boot replay smoke nominal + frame mutant on kv42_build; POST observation of the die's token-start chain; then FAR=1 token.
## OWNER?
(none)

## CODEX notes
- Collected kv42 build: remake2 exit 0; boot nominal/mut_frame and FAR=1 token processes remain live CPU-bound on epyc2:/srv/opentallas-scratch/claude/kv-tok/{boot42,tok42}. No finished verdict yet. Root-disk run dirs are live and cannot be moved; new work will use scratch2. Next collect boot/token verdict, diagnose first fault.

CODEX progress: BO1opt-in source mergedmaina2757edd53, variantdefault0; sixrealbc4modesPASS+fullHOSTclosurelintPASS. ActualHOSTacceptedprogramme eventretainsHBMboot_go. NewdeclaredsourceL643actual35edges=28transport+7pad; wrapper/census/rewirecandidate /srv/opentallas-scratch/claude/codex-qwen/boot_bo1_bound_candidate. CanonicaladoptionHELDfreshrebind/R8/fulltoken/physical. IdenticalO1buildLIVEepyc2scratch2/claude/codex-qwen/kv42_o1 (71+/79hiermodulesdone), old3jobsuntouched.
