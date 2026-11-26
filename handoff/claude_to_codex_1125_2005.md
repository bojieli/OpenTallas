# Claude → Codex handoff, 2026-11-25 20:05 PST

Written ahead of time in case Claude COORD hits a rate limit. Follow ~/coord/CODEX-ROLE.md. The lane table is in lanes/COORD-LANES-1125-2005.tsv. Each Claude lane writes `bash ~/coord/bin/post.sh <LANE> ...` posts to lanes/posts/<LANE>.md; read those for live state.

## New OWNER rulings (11-25), binding
1. **Twice-daily cuts** (OWNER "yes" at 19:4x). Each die integrator cuts its plan at 09:00 and 21:00 PST: S81-ALLFIX-INT, KV-ALLFIX, QC-ALLFIX, HEAD-ALLFIX.
   - Adopt every ROW-READY row that passes PRE plus the scoped strict bind.
   - A failing row goes back to its owner.
   - Running kits keep running.
   - Append adopted, probe-confirmed and route-confirmed counts to lanes/CLOSURE.tsv.
   - The first cut is 21:00 tonight: QC C1q, HEAD W10, S81 R11.
2. **Probe immediately.** A place-only probe goes on kit hosts as soon as a row is ROW-READY.
3. **Progress answers to the owner** lead with problems found / resolved / open per die. The signed count goes last, as one line.
4. **Reviews.** Lanes self-launch Fable reviews, with no top-N cap. Known-problem types are place-only. One route pilot per family.

## Reviews this evening (all dispatched, all owned)
- **Deep reviews** (lanes/posts/FABLE-RC-{S81,KV,QC,HEAD}.md): 70 causes, 27 with no fix drafted when found.
- **Flow review**: epyc7:/srv/opentallas-scratch2/claude/FABLE-FLOW-1920/FABLE-FLOW-1920.md, 53 problems.
- COORD rulings are posted at 6b053486, 10c6353a, 2a770de5 and 0ac1e7a6.

## Key rulings to keep enforcing
- **QC xhead3 RTL fix** (branch claude/qc-xhead3-lec-1125, 56fb2ac979b3) is HELD. Merge it only if the sle_hc0 pv48712631 LEC rerun on lec.py e6d2675979 (epyc11) comes back NOT EQUIVALENT on a_pr/b_emin. Merging rebuilds 8 hc families.
- **QC ECO.** Stop ECO after pass 1 if WNS is still worse than -42 ps, and send the type to a structural row.
- **HEAD C18 die clock.** Use variant A, which re-attaches the core taps to the planned early arrivals. B is data only.
- **KV ESTRIP.** 5 types are ROW-READY: v2, v2n, v6, v6n, v5ne. v3e, v4 and v7e were retracted; the gate is ADV-FP-STREET.
- **KV R7 promotion.** r6_hg4, r6_hg6 and r6_pcwn6 can't gen on R6, so those three use absolute place gates. pc_es4 keeps its R6 baseline.
- **S81 R10.** The 343 kits keep running, and no more batch launches go out. R11 (a3778552) must carry:
  - col_h9 pin-EOL views (from ABSTRACT-EXACT);
  - SVC-BANDFOLLOW, which is ABSENT in R10;
  - the xo, source-stage and seqhost ops;
  - the col_h10 p4 row f01318a7fcc7, which adds latency (+4 / +2 cycles, so re-ack it).
- **Unproven PROVEN-HAND rules** (SITE-IN-MACRO etc.) are demoted to advisory (FP-CONVERGE-S81).
- **Two systemic tool causes found tonight:**
  - **(a) clock_taps.tcl copy trap.** Copying the file from main drops the kit's `source vpw_bank_clock.tcl` and `source landing_exports.tcl` lines, which gives CTS-0114. This is CONFIRMED: serdes t4 hold went from -391 to -21 ps. FLEET-OPS-R2 is fixing the copy step and running a census.
  - **(b) reset_tree.py ignored plan relay_sites.** The fix `reset.relay_sites_win` was pushed by HEAD-SERDES-REFLOOR. Make it the default after the R7b probe confirms it, then run a per-die census.
- **Host rules.** epyc12 is for die jobs only. epyc9 gets no new work. Kits go to epyc10, epyc11, epyc7, intel1 and epyc8. epyc2 gets no new kits while root is above 90%.

## Watch items
- sle_hc0 LEC rerun (epyc11), hd_mesh full routed LEC (epyc10).
- S81 serdes LA probe on epyc10, which feeds the LA LEC and the encoder -314 decision.
- KV-SINKBINS job F on epyc7. Its row must exclude hgi_v6.
- KV-HGI-WGATE gate8/gate9 (pv_v_pads stale-cause control).
- kv_leaf v19/v20 GRT verdicts at 06:00. HEAD lep0N_w 2 probes and the host_w r14 probe.
- Auto-export: eco_*/i<n> ingest, and rtx-pro reserve (hd_spn held).
- Count: 605 any / 487 current, flat for 16 h. n4 and mesh_e are archived.

## Hygiene
- The concurrent-subagent limit (48) was hit. Reuse finished agents by resuming them rather than spawning new ones.
- Remove any autopilot.service.d codex-takeover drop-ins on intel2 when handing back.

## OWNER 11-25 ~20:1x: track CLASSES, not items. This binds Codex too.
- VIS-REOWN owns lanes/CLASSES.tsv (class_id, die, DESIGN or PROCESS P-, static check, owner, count per cut, status) and lanes/CLASS-MAP.tsv (item -> class).
- When you review or dispatch, map every finding onto a class_id. Report only deltas: NEW classes, classes whose count rose, and items with no owner.
- At each 09:00/21:00 cut, refresh the per-die class counts and append the trend.
- Convergence means NEW goes to about 0 and the counts fall. Two cuts in a row without that is a LOOP: report it to the owner.
- Progress answers to the owner give the class trend per die first, then the closure counts, then the signed count as one line.

## Update 20:2x PST: HANDOFF NOW (owner: Claude rate limit)

**Class owners.** OWNER ruling: close each class in the GENERATOR, by construction, across all dies. Each owner calibrates its check against routed results and posts per-cut counts to VIS-REOWN.

| Class | Owner lane | Notes |
|---|---|---|
| C-STREET | FP-CONVERGE-S81 (a66e75f3dc9c8f564) | metric is ADV-FP-STREET |
| C-LEG405 | REF-SITE lane (a6235aed7e541ba95) | |
| C-TAP-LOAD | S81HEAD-TAPSPLIT (adcd46c71cbf7e3ae) | |
| C-RST-RELAY-REACH | shift-in-place lane (a40ee3e661fb1394c) | |
| C-XTAP-HOLD | QC-DRT-ECO (ae50cb7de3567ae22) | steps: C0 census, C1 metric, C2 generator flag (default off), C3 blocking |

- VIS-REOWN (a8d3b2a5bc9130a3e) is building lanes/CLASSES.tsv and CLASS-MAP.tsv.
- FIX-LANDED audit: OWNERS-SWEEP lane (aebc50e908e14276a) writes lanes/FIX-LANDED.tsv. The first version is report-only, due around 21:00, and may slip.

**Corrections. Do not repeat these.**
- The serdes hold fix (-391 to -21 ps) applies to c8 only. Row SERDES-CLKT43-STATION-GROUPS is WITHDRAWN. An R11 proxy probe is running on epyc7 (probe_r11).
- The reset_tree relay_sites overwrite is NARROW: 3 of about 800k seats, mostly hd_serdes R6.
  - The fix is on main c92ea14ae6b1; rt/current is 194a63c2ad51.
  - Make it the default only after the R7b probe on epyc10 confirms it.
  - The census is still missing KV and epyc7.
- The clock_taps.tcl copy trap (CTS-0114) still stands. FLEET-OPS-R2 (ad2d76f087a78c03e) is fixing the copy step and running a census.
- KV ESTRIP: 5 types are ready (v2, v2n, v6, v6n, v5ne). v3e, v4 and v7e are in rework.

**21:00 cuts.** Append the results to lanes/CLOSURE.tsv.
- S81 R11 (INT):
  - col_h9 pin-EOL views from ABSTRACT-EXACT;
  - SVC-BANDFOLLOW;
  - the col_h10 p4 row f01318a7fcc7 (latency +4/+2 needs re-ack);
  - leaf_grow R6, if ready.
- QC C1q (QC-ALLFIX).
- HEAD W10 (HEAD-ALLFIX): spn a26fbca09de0, TAPSPLIT e6ad704d3a29.
- KV (KV-ALLFIX): the 5 ESTRIP types.

**Pending.**
- The QC xhead3 merge waits on the sle_hc0 LEC on epyc11.
- The batch re-LEC of 118 records is in flight (LEC-AUTOFILL ae5f6b068f6cf934e). Two records are already NOT-EQ and need triage.
- Signed count: 605 any / 487 current.
