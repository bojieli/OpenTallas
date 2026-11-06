# S81 handback — Claude reset, 2026-11-06

No new manual launches after root's handback message. Keep healthy bounded jobs.
Core helper's authoritative BKSEL/ENGRR/IDX details are in CODEX-S81-CORES.md;
types/stations are in CODEX-S81-TYPES.md. No final gate or same-flow child rule waived.
Owner setup0/FFhold25 applies;60ps margin is INFO per latest owner12.24b/c.

## Current jobs and next actions

- COLLE E/W: both on **epyc2 dedicated scratch2**, root
  `/srv/opentallas-scratch2/claude/codex-s81-colle-compact-1106`.
  Original `e`,`w` completed fullroute/abstract, sourceEQ35784/35784,
  DRC0/ANT0/PGopens0, TT40.69/FF-16.03 (SDC-50.41), DRV579/27 TT,
  235/30 FF. Actual compact295.92x444.96,55SRAM,2143pins,realPG6.
  Current pinned **ad** canonical late-ECO loops `e_eco_ad`,`w_eco_ad`,
  intel2 clients1580635/1760689; E admitted unit3484765, W unit3606931.
  Both reached i2 at handback, healthy, max3 already authorized.
  **i1 both**: TT35.66, FF-8.12/49endpoints (SDC-52.75), DRV81/1 TT,
  74/1 FF, DRC0/ANT0/PG0; exact frozen-clock PASS. Loop continues normally.
  Client logs intel2 `~/coord/tmp/codex-coll-{e,w}-eco.log`.
  Residual local hold/DRV and real-parent IO receipt remain; no SIGNED claim.
- COLLE pin audit original FAIL2142/2143 is intentional approved DIE-S81-62
  ck0 landing extension: M5[147.924,236.232,147.972,236.760], anchor
  [147.948,236.520] remains inside; bboxcenter moved24nm. n4_logic exact
  `native_rects` capability269803c93d2 passed actual read-only E audits+
  wrongrect/layer/anchor/name mutants. Preserve original FAIL receipt.
  E declared copy E2 `codex-native-pin-rect-1106/declared.json`; W needs its
  OWN pins copy + `compact_coll_form.declare_clock_pin`, never E's table.
- ROMQ HE: **epyc5 dedicated scratch2** root
  `/srv/opentallas-scratch2/claude/codex-romq-safe-route-1106`.
  Current **AT** bounded late-ECO `he_eco2_at/i1` (max2 further iterations,
  so3 HE total), client2521147, unit960081. Current native repair measured
  TT27.92/FF+.04 before reroute; actual final still owed. Public canonical
  `OT_ECO_REROUTE_DATA=1`, all data rerouted/PA reset, clocks frozen.
  Source `he_eco2_seed` is865MB; original config restored, private obsolete
  PA/PRE chain removed only in this fresh seed. Tools `tools_at` pins AT.
  Log intel2 `~/coord/tmp/codex-romq-he2-at.log`.
- ROMQ previous safe routes: HW **epyc5** `.../hw`, HE **epyc6** `.../he`.
  Both all-DATA DRT0/ANT0 and exact clock geometry PASS: HW1508clocknets/
  32466attachedinstances, HE1500/32425. DRT14m32s/19.8GB HW,
  16m50s/19.0GB HE. Corrected dependency-free do-finish+abstract EXIT0.
  `SAFE_ROUTED_CLOCK_CHECKED.odb` protects exact completed5_2 DB in each base.
  First finish driver mistakenly used `make finish`, followed absent upstream
  stages; stopped ONLY own E5ff9d90e4040b/E6 2faee6ae5e61. No completed
  route was lost. Use do-finish only; no repeated repair/SPEF replay.
- ROMQ actual fresh ac signoffs `hw_resign_ac` on E5, `he_resign_ac` E6:
  HE TT27.92/FF-7.75/14endpoints, TTDRV1data slew, DRC0ANT0;
  HW TT5.34/FF-11.28/100endpoints, TT54/FF51 slew, cap0, DRC0ANT0.
  Both NOT SIGNED; routed EQ correctly NOT RUN. HE advances above.
  HW needs explicit NEW clock repair event before more frozen-clock ECO:
  21TT/22FF slew failures are clock inputs; read-only actual ODB diagnosis
  `hw_clock_diag/clock_drivers.json` finds just3 CLOCKnets, drivers
  clkbuf_6_{14,22,12}_0... all **BUFx24 strongest available**, fanout8/9/9.
  Thus simple upsizing cannot cure it; needs clock net split/local buffering
  or re-CTS before a new freeze, actual reviewed geometry, unchanged SDCs.
  No clock repair or new HW physical launch has been made.

## Parent composition and source queue

- ROMQ OLAT1 is negedge **0 added pin cycles**. New unreferenced shell8289
  merged AJ: whole605input/reset +131output/status captures, +2 interface
  cycles/+1 child-reset edge. Existing11934word+2400reset-age proof,4mutants.
- Original twohalf union536.76x221.4 has0 parent cellrows. Old +8.64 outline
  proposal is now explicitly REJECTED:0usable rows after4.32core inset/halo,
  55/104 new FT/monitorband conflicts. Wider row-aware proposals hit actual
  other contents (62/104 or100/104), not only hardcores. Do not adopt old
  growth artifact or claim736FF fits from outline-minus-macro area.
- Prefer direct twohalf hard composition in enclosing COL, keeping original
  union, with736FF+OR/clock/buffers explicitly reserved in host rows.
  No physical reservation/activation yet. Private intel2 root
  `/srv/opentallas-scratch2/claude/codex-s81-romq-parent-1106` contains
  `row_halo_budget_candidates.json`, `direct_composition_contract.json`,
  actual COLp4 original/adapted source + receipt. Twelve native calls captured;
  remaining type-base/native-name aliases need existing resolver, not guessing.
- **READY 9451a6a397b**, branch`codex/s81-romq-parent-adapter-1106`, ATbase,
 3NEWfiles only, no callsite/plan/binder/RTL changes. Explicit byte-sealed
  source adapter: selectedGB->existingShell, NB2 sealed/removed, selected
  IOREG/OUTPUT_NEG/OLAT/IFN1, all other parameters and INSTANCE expression
  preserved verbatim (including literal/symbolic per-partition defaults).
  Four focused tests PASS, actual COLp4 four-call prep PASS. Root approval
  pending. Receipt PREPARATION_ONLY; no physical/parent qualification.
- Public AT already includes bcb66 full-DATA reroute (merge5b96e86d153),
  plus clock-overpass5551/52aea81dac1 (defaultoff clock_top=M6 withPG6/OBS6/
  childOBS<6/dataM5/nativewireaudit; only reviewed IDX recipe opts in).
  Keep active IDX K11 pinned ad. No child re-sign or physical rerun needed
  for already SIGNED ad child unless a genuinely different parent tag is chosen.
- Native-C four CTS SIG11 forms: busfit7d merged AP fixed narrow Liberty
  declared bus ranges, actual423MiB failed DB all_registers78787PASS.
  Independent Slang4000 frontend failure:25d92e198a6 merged AT, explicit
  finite32912 fresh captures only; nonterminating negative stillfails.
  Actual full routed/source EQ for the fresh C cohort remains owed.

## Storage and preserved work

- User-authorized cleanup unique total30,068,822,123B (~28.0GiB): corehelper
  manifest `CODEX-S81-CORE-RELEASE-1106.json`24.949GiB and ownE2 ROOT
  3,279,777,899B. Compact source/log/failure + useful checkpoints kept;
  exact SIGNED ad IDX child backing E6 and completed proof I1 protected.
  No progressing core worker was killed for age. Two wrong finish workers
  above were stopped for dependency restart, not age or memory.
- Intel1scratch3 and E2scratch3 are ROOT devices, not dedicated volumes;
  no new heavy work there. Current COLLE E2scratch2 and ROMQ E5/E6scratch2
  are actual dedicated filesystems. E6 last known68GB, avoid bulk staging.
- Own source clone intel2
  `/srv/opentallas-scratch2/claude/wt/codex-s81-plan1105` is clean/pushed on
  `codex/s81-romq-parent-adapter-1106@9451a6a397b` (~1.3GB).
  Protected localhost `/home/ubuntu/OpenTallas` never edited or git-used.
