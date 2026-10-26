# OpenTallas coordinator handoff — tender-ray (localhost fleet) → rtx-pro

Written 2026-10-24 ~19:10 PDT by the Claude coordinator on tender-ray, at the owner's request ("rtx-pro is back, move the
coordinator back to it"). Covers 2026-10-24 06:30–19:10 PDT. Read this first, then `docs/coordination/coord_state_2026-10-24/`
(a frozen copy of the coordination files) or the live branch `coord/state` (same files, checked out at `~/coord` on tender-ray).

## 0. What the next coordinator must do first
1. Check out `coord/state` as the coordination dir (BRIEFING.md, RELEASE_TREE.md, HANDOFF.md, lanes/*.md).
   Every lane file now ends with a `## PARKED <time>` section: branch@sha, live jobs host:path/pid, results, failures,
   next step, OWNER?. That is the per-lane task list. Section 9 below is a snapshot of them.
2. Read BRIEFING.md fully: merge recipe, disk rules, review-before-route, sign-off corner, owner decisions, no git stash.
3. Fleet jobs are still running on all 5 hosts (they were NOT killed). Collect them; never launch duplicates into a live
   run dir. `ot-run` (on tender-ray, `~/.local/bin/ot-run`) placed them; `ot-run --status` shows host load.
4. Re-dispatch lanes (section 6), one agent per lane, each told: "read your lane file's PARKED section and continue".
5. Re-enable whatever automation you want on rtx-pro (section 7); all of it is OFF on tender-ray now.

## 1. Project and gates (unchanged)
Mask-ROM LLM inference silicon on ASAP7, 833 ps clock (1.2 GHz). Three targets:

| Design | Dies | Plan on main |
|---|---|---|
| DeepSeek-V4.1 ROM | S81 layer-die array + 4 head dies (owner: 4 head dies, no HBM on them) | S81 v4.8 + canonical 26-slot FT405 frames (90fd169e93); head die plan |
| Qwen3-8B ROM | Qwen compute die + KV/system die | QC P6 (+ Codex capacity plan, ACCEPTED, adoption in progress); KV v3.8x (c98b74b466; v3.8w 30fe617bcb) |
| HBM accelerator | B2 die (serves DS + Qwen) | B2l (9c5104bfcc50; rack_macro naming d82817f245) |

Gates: G0 `check.py`, G0C `--completeness`; G1 visual review (GEOM-REVIEW); G2 routing probes `g2.py`; G3 partitions/hard
cores via `gen.py phys` + `run_kit.sh` (+sdc_lint, face_guard), closed only when `signoff.py` says SIGNED; G4 abutted die
via `die_sta.py` (ILM == flat proven 0.000 ps) and `die_ci.py`; G5 token pass. Rules R2–R8 in `tools/die_plan/README.md`.

## 2. Binding rules (all in BRIEFING.md / AGENTS.md)
- **Sign-off:** setup at TT, hold at FF, 60/25 ps uncertainty, pin-flop spread ≤ 80 ps. NEVER SS (SS info only).
- **Owner decisions 2026-10-24 18:4x:**
  1. QC capacity plan ACCEPTED (G0C 56/56; ~434k pads + CB16 alignment pads).
  2. Reset, all dies: ONE root 2-flop synchroniser (its async input is the only false path), then a synchronous release
     through relay flops every ≤ 405 µm, equal depth to every tap; local flops timed normally; no recovery waivers.
  3. Extra die-timing margins (xtalk/IR/OCV) are INFO only; gate is the policy above.
  4. HBM B2l's ~22 % DeepSeek-AR loss vs d4g ACCEPTED; bind B2l natively now, recover speed later.
- **Earlier owner decisions:** elastic seams REJECTED; 4 head dies, no HBM on head dies; copy-A/B reserve SerDes pair on
  every layer die; MTP draft rides copy-B dies (no draft fan-out SerDes); the 10-21 element list is OBSOLETE (open work =
  current plans' G0C failures, types/cores without SIGNED views, GEOM-REVIEW findings, lane next steps).
- **Coordinator rulings today:** S81 FT seam split 0.16 T receiver / 0.84 T sender (adopted on main 90fd169e93); DS BK
  drain sink canonical (profile/bind ON, compiler stops emitting addressed drains as CTL beats, legacy BK bench retired);
  v4.8 R8 landed pads must be priced; S81-CORES per-type leaf macro arrangements accepted (+58 stations, +3 cyc), x-mirrored
  vn/vq/vs views for 13 reach-fail leaf types, internal stations for core bundles > 405 µm; KV hard cores publish their
  clock insertion (core-latency contract, parent uses early taps); missing boundary regs get added in RTL (never relax
  face_guard); HBM host traffic in-band over die links (drop dedicated host UCIe); KV boot bugs A/B/C1/C2 fixed in design.
- **Review before route (owner):** render die + tile, judge like an industry floorplan review (data flow, pin alignment,
  long wires stationed, channel/pin density, macro halos, clock tap balance, PDN, reset distribution), revise before
  P&R/STA, record in `results/geom_review`.
- **Disks:** scratch only (`/srv/opentallas-scratch2` on intel1/intel2/epyc2; md0 on localhost/epyc3). `lsof` misses
  docker bind mounts — never move/delete a dir without `docker inspect` checks.
- **Merge:** central checkout `~/OpenTallas` on tender-ray is the only GitHub pusher: `git checkout -q main`, fetch,
  `merge --ff-only origin/main`, plain `merge --no-ff` (never `-X ours/theirs`), push, verify HEAD == origin/main; under
  `~/coord/merge.lock` (flock). Never `git add -A`, never `git stash` (shared across worktrees; 12:44 incident).
- **Never** pattern-kill fleet jobs (TRIAL-S81 used `pkill -f run_sta.sh` on intel1/2 at ~18:5x; no known victim, noted).

## 3. Fleet (as of 19:00)
| Host | Threads/RAM | Disk notes | Load |
|---|---|---|---|
| tender-ray (localhost) | 256 / 755 GB | md0 root **85 % at 19:00 → ot-run refuses it**; `/srv/opentallas-scratch` is ON the root fs; biggest: claude/wt 508 GB (lane worktrees), elem-s81 143, elem-qk 121, elem-hbm 121, elem-s81-st405 109, codex-clock 80 GB | 26–61 jobs |
| epyc2 | 128 / 1 TB | scratch2 880 GB, **34 GB free → ot-run REFUSES it**; ELEM-S81 (codex-s81/station405_c1 235 GB) and ELEM-QK (codex-qwen 114 GB) were told to prune | 7 jobs |
| epyc3 | 96 / 1 TB | md0 | overloaded (110–410 load) |
| intel1 | 112 / 1 TB | scratch2 3.4 TB (~2.4 TB free) | ~50–90 jobs |
| intel2 | 112 / 1 TB | scratch2 3.4 TB (~2.3 TB free); `~/OpenTallas` is a symlink to `/srv/opentallas-scratch2/claude/moved/home__ubuntu__OpenTallas` | ~20–35 jobs |

Timezone is America/Los_Angeles on all hosts. Tools: `~/.local/opentallas-tools/bin`, docker `openroad/orfs:latest`.

## 4. State per design (19:00)

### DeepSeek ROM (S81 + head)
- **Plan:** v4.8 + canonical 26-slot frame FT405 ledger on main (90fd169e93): 72 in-ROM stations → 0, 72 lanes +3..15 cyc,
  ft_hop_in_share 0.16. **S81 G0 + G0C 174/174 now on main (e94d9bb329)**: leaf/svc/eng hard cores, per-type leaf arrangements, +58 stations. S81-XDIE (`codex/s81-xdie-integ-1024`, held) is back to G0C 91 but must be rebased on
  the 26-slot ledger; reserve-pair corner ESD/bump reuse + pair-B endpoint RTL still held.
- **G3:** frame kits g3k5: 0 reg-reg > 750 µm; blockers = reset (now ruled) and tap/macro clock skew (xa relay→bs2 −368).
  Hard cores: **vq SIGNED** (TT +8.35 / FF +7.58); hrow r13 NOT SIGNED (TT −50.1), r14 running; hcore WPRE routed, signoff
  on epyc2; vs pathfinding (face_guard 130 dropped / 736 shared); c2 canonical kits (10) running localhost/epyc3.
  Station405: t12 SIGNED (variant B, 0.16 T); others in progress; t33 needs stronger repeater; t4/t32 relaunch.
  Head: elemA c7 / elemB c2 routed NOT SIGNED; best_key path pipelined (pk_q); hd_tile r3 / tap160 c7 FAILED review
  (elemA clk pin 24 nm access; source rebuild done, re-route pending).
- **Token:** entry replay fc31 6/6 PASS + mutant; layer control L0/L2/L14/L20 PASS + mutants with BK drain sink
  (9721734fee). Arithmetic exactness blocked on compiler gaps G-COMPILER-ROWS / G-NORMALIZE-SO (main DS token blocker).
  Composed model AR 802.6 tok/s, MTP 2,564 (≈30 % measured on current RTL).
- **Trial die (TRIAL-S81):** die GRT 0 overflow (layer + head); die-tree seam skew S81 50.9/43.8 PASS, head 81.9 TT FAIL;
  in-partition tap spread ~100 ps; IR interior 30 mV PASS, over SerDes windows 235–270 mV FAIL (model may overcount).

### Qwen ROM (compute + KV)
- **QC:** G0C 52/56 on main → 56/56 with accepted capacity plan (QC-A0 + QC-TOK adopting; must name canonical bus-groups
  file: main G0 currently fails one R8 landing-table check, fingerprint e56a2f6f vs committed c56f7e7a). ft_regs.py moved 51
  in-core stations to channels (ab490d1fbb, branch). 6 cbf SerDes TX slots need 5 stations (rebind). A0 kit is bound +7 cyc
  (spec 6): price the extra cycle. coll_ftc g3i routing on intel2. A0 v7 NK/NL routes heavily congested (pathfinding).
- **QC token:** tp8 / xdie / ovl4u / xt1 (64/64 both clusters) PASS; capacity rebind with CB16 pads xt1 64/64 + 64/64.
  R8 padding target < 150k is an optimisation target (trees cut 870k → 588k; CB16 alignment ~0.79M remains).
- **KV:** v3.8w/x on main (G0/G0C PASS; 1,033 stations off hard cores; head_eighth 216). hub_Ei: vJ pair skew 74.8/69.7
  PASS, but GEOM-REVIEW FAIL-to-route (reset not per rule, predicted hotspot ft24 st2 @ clk_t31) → **vK** = pipelined reset
  (shared kit_rsync feature, KV-G3 building) + hotspot spread, GRT-only gate, delta re-review. Codex retry4 still in GRT.
  KV cores: none SIGNED; pv_pair routed NOT SIGNED (FF hold −10.75, insertion 355.6, slew); head_eighth 216 ×8 running;
  hold recipe b fixes FF hold on heads; astk/ectlk variants running.
- **KV token:** BO1 fixed D2D fault; boot stalls at 528/7161 frames — bugs A (kvpc reset on HOST die_rst_n), B (HBM
  calendar sealed after boot), C1 (hub_Wi valid +4 cyc vs data), C2 (host SerDes 0.959→1.2 GHz CDC without synchroniser).
  All ruled design fixes; sub-agents for B and C2 were working at park time.
- **Qwen token (TOK-QW):** stg 527/527, head, attnret 98/98, xhead 4/4+10/10 PASS on main; compose 1u 4,428 tok/s, 4u 11,844.
  s8 bound-row build on intel2 (35/36 units).
- **Trial die (TRIAL-QK):** QC route / IR runs were finishing at park time (see lane file).

### HBM B2
- **Plan B2l:** G0C 49/49; 480 hbm-ds circuits pair (d82817f245); host link → in-band (ruled). Native binding scoped
  (`results/arch/hbm_arch_1024/b2_native_bind_delta.json`): new RTL needed (2-stop VM ring stop, quadrant straps, 2-leg SU
  tree, 2-part SU root, 2-half HC root, 2-list IDX selector); TP-384 may need wider rank/group fields. Fix first: clock
  leaf grid vs taps, trunk split (OCV seam skew 407–594 ps), SerDes IR 4–6× over (a B2l clock MSCTS sub-agent was running).
- **ELEM-HBM:** 89 B2l core kits routing to signoff; 26 FAIL at placement on core clock insertion (→ early core taps).
  GQ land CTS RSZ0060 hold-buffer cap variants.
- **TOK-HBM:** XDIE 10/10, AR-step, transport miters, HC native unit gate 24/24 + mutant PASS; layer gate FAILS on SU/HC
  die transport; price bracket DS 1,561–1,886 / QW 893–943 tok/s.
- **TRIAL-HBM (B2r2):** die GRT 0 overflow vs 1.37M old; H-tree OCV seam FAIL; seam hold pads needed; IR SM 47 mV FAIL,
  SerDes 146–203 mV FAIL; full-die exact IR not completed; `gen_phys.py` `%g` origin-rounding bug (23/88 refused).

### Toolchain lanes
| Lane | State |
|---|---|
| DIE-STA | `die_sta.py` on main (e70305aec7; TT/FF gate). CP1 reach405 seams PASS (TT +432.5 / FF +87.8, spread 56.8/46.2). Trial dies: setup OK all 5, **FF hold FAILS all 5** (−46 … −417 ps) from inter-tap clock skew → clock spine must be rebalanced (hbm NW_sm2 tap +440 ps; KV hub spread 216 ps). Half-period wrap bug fixed on branch `claude/die-sta-1024@97fd4371ec`; v2 reruns on intel2 |
| DIE-CI | merged (bf41c38e32): per-die jobs, G2 OOM ladder, die STA gate TT/FF, margins INFO column; timers DISABLED now |
| CP1-R10 | **CP1 seam PASSES at 833 ps** on reach405L (TT +434.5 / FF +104.9, spread ≤ 60.3 ps; ILM == flat). Partition kits NOT SIGNED (r1 FF hold −6.9 + slew; r0 reset recovery −310). Leaf fix (6435e46354) on `claude/cp1-r10-1024@f5c549e166`, merge it first |
| SIGNOFF | signoff.py final step of run_kit.sh (TT/FF); 138 old modules NEED RE-RUN |
| PART-CAP | OpenROAD scaling n1…n44; n27/n44 running |
| GEOM-REVIEW | die + tile batches merged; checklist includes reset rule |
| FLEET-DISK, TYPE-DEDUP, ELASTIC | done |

## 5. Owner decisions still open
- QC: CB16 alignment method if < 150k padding is pursued (plan equal hops / RTL / compiler offset) — not a gate.
- S81-CORES: constant output pins (hcpl o[15:0], rxsb o_r[31]): drop from plan or add a face_guard constant-pin class.
- S81 vs face_guard (130 dropped / 736 shared).
- S81 head seam skew 81.9 ps TT: accept seam-drop fallback or require a tighter tree.
- Power bumps / separate PHY supply over SerDes windows (S81, head, HBM all fail IR there).
- DIE-STA: whether "margins INFO" also covers the 80 ps spread check (currently still gated, per AGENTS.md).
- S81-XDIE reserve pair corner ESD/bump reuse and pair-B endpoint RTL (held).
- Missing SRAM GDS / LOST archives (full-layout dependency; routed-abstract closure only until then).

## 6. Lanes to re-dispatch
S81, S81-CORES (+kits), S81-HEAD, ELEM-S81, TOK-DS, TRIAL-S81 · QC-A0, QC-TOK, ELEM-QK, KV-G3, KVG3-CORES, KV-TOK, TOK-QW,
TRIAL-QK · HBM-ARCH, ELEM-HBM, TOK-HBM, TRIAL-HBM · DIE-STA, DIE-CI, CP1-R10, PART-CAP, GEOM-REVIEW, SIGNOFF.
Each lane file names its branch and worktree. Priority order for the next shift:
1. Die clock-spine rebalancing (FF hold fails on all 5 trial dies; head seam skew) — shared, blocks every G4.
2. Pipelined reset: TWO implementations exist and must be unified first — KV-G3 `tools/die_plan/reset_tree.py` (branch `claude/kv-g3-1024@6ecd9a39e2`, one root sync per partition, hub_Ei 7 relays, 2 tests to update) and S81 `reset.release: pipelined` (branch `claude/s81-p11-1024@71bed19a4a`, 6 stages/16 taps per frame); S81-HEAD added an element reset relay on main (d456fea42f). Open scope question: one root sync per partition vs per die region (die-level synchronised reset). Then KV hub vK, S81 frames g3k6, stations t13/t30, CP1 kits, S81-CORES kits.
3. QC capacity plan adoption + main G0 R8 landing fix; S81-CORES regen15 merge.
4. Token blockers: DS compiler gaps; KV boot bugs A/B/C1/C2; HBM SU/HC transport.
5. Hard-core closure (hrow, KV cores, HBM 26 insertion fails) with core-latency contracts / early taps.
6. epyc2 scratch prune; then keep all 5 hosts saturated.

## 7. Automation on tender-ray — ALL STOPPED at 19:00 (how to re-create on rtx-pro)
| Item | Where | State | Notes |
|---|---|---|---|
| Claude↔Codex auto-switch | cron `* * * * *` → `~/bin/claude-autocontinue.py` (pane 0:0 Claude, 0:1 Codex) + `~/bin/make-codex-handoff.py` | **removed from crontab** (backup `~/.local/state/claude-autocontinue/crontab.bak`) | Watches only the coordinator pane: it missed the 15:00–18:47 lane-agent limit because the coordinator was blocked in a question dialog. If re-used, also watch lane-agent 429s, and ask owner questions as plain text, never a blocking dialog. Codex role/rules: `CODEX-ROLE.md`; Codex's 08:50–12:04 takeover log: `CODEX-LOG.md` |
| Release-task watcher (Codex) | systemd --user `release-task-watch.timer` | **disabled** | read-only liveness watcher |
| DIE-CI commit + nightly | systemd --user `die-ci-commit.timer`, `die-ci-nightly.timer` (02:30) → `tools/die_plan/die_ci_cron.sh` | **disabled** | results branch `claude/die-ci-results`; re-enable on whichever host is the hub: `systemctl --user enable --now die-ci-commit.timer die-ci-nightly.timer` |
| Coordinator Monitors (HANDOFF tail, fleet load/disk poll) | in-session | stopped | |
| ot-run | `~/.local/bin/ot-run` on tender-ray | **still running** (it is the job launcher; live jobs' clients are its child processes) | v13 scratch-disk placement; refuses hosts with root > 85 % or scratch < 50 GB. The rtx-pro coordinator can keep launching through tender-ray (`ssh tender-ray ot-run ...`) or install a copy |
| Lane agents | Claude sub-agents of this session | **parked** (each wrote `## PARKED` in its lane file) | fleet jobs they started keep running |

## 8. Where things are
- Repo: github.com/bojieli/OpenTallas (SSH). Central checkout + only pusher today: tender-ray `~/OpenTallas` (main). Lane
  worktrees: tender-ray `~/wt/<lane>` and `/srv/opentallas-scratch/claude/wt/<lane>`; branches `claude/<lane>-1024`, Codex's
  `codex/<lane>-1024` (do not whole-merge broad codex branches; cherry-pick what matters).
- Coordination: branch `coord/state` (tender-ray `~/coord`): BRIEFING.md (rules), RELEASE_TREE.md (gate tree), HANDOFF.md
  (milestone log), lanes/*.md (per lane, PARKED sections), lanes/TOPDOWN-PLAN.md, OPEN_ELEMENTS.md, CODEX-*.md, handoff/.
  Frozen copy in this commit: `docs/coordination/coord_state_2026-10-24/`.
- Evidence: `results/geom_review/`, `results/die_sta/`, `results/die_ci/` (branch claude/die-ci-results),
  `results/die_trial_1024/`, `results/token_pass/`, `results/rtl/tokqw_1024/`, `results/elem_qk_1024/`, `results/arch/`.
- Fleet run dirs: `/srv/opentallas-scratch{,2}/claude/<lane>/...` on each host (paths per job in lane PARKED sections).

## 9. Lane PARKED snapshot
(Generated from `~/coord/lanes/*.md` at commit time; the lane files on `coord/state` are authoritative.)
### CP1-R10
## PARKED 2026-10-24 18:57 PDT
- Branch claude/cp1-r10-1024 @f5c549e166 (pushed; includes merge of origin/main 69e173e308). Unmerged to main: pair.py reach
  leaf (6435e46354, validated: r1 TT setup -241.76 -> +192.55) - MERGE REQUEST pending.
- Live jobs: none of mine (reach405L r0/r1 ot-run finished exit 0). Codex reach405 r0 (PID 2130440) finished too: NOT SIGNED TT -314.87.
- RESULTS reach405L (/srv/opentallas-scratch/claude/cp1-r10/reach405L; results/die_sta/cp1_reach405L):
  * DIE SEAM STA (flat, routed SPEF, die_sta.py main): PASS. Ideal spine: TT setup +439.75, FF hold +95.08, 0 neg.
    Branch spine: TT setup +434.46, FF hold +104.93. Face-flop spread TT 48.24/33.81, FF 46.44/32.27; cross-seam
    union (bounds seam skew) ideal 51.7 TT / 50.8 FF, branch 60.3 TT / 59.4 FF (<= 80). SS info: setup +257.5.
  * Kits NOT SIGNED internally: r1 TT +192.55, FF hold -6.88/181, slew 164 TT/99 FF. r0 TT -310.27/1432 (worst =
    arst_n -> 30-buffer chain -> u_rsync_t39 RESETN recovery: per-tap async rsync tree, violates the owner reset rule),
    FF hold -15.06/339, slew 1157/791 TT/FF. DRC 0, sdc_lint/face_guard PASS both.
- NEXT: (1) merge reach leaf; (2) apply owner reset rule (one root 2-flop sync, relays <=405 um, equal depth) to pair kits
  via the KV-G3 kit_rsync / S81-HEAD reset relay tool once on main, rerun r0; (3) root-cause r0 slew 1157 + hold
  -15/-7 (repair_timing hold margin in proof kit), then sign kits.
- OWNER?: none new.

### DIE-CI
(no PARKED section — last 12 lines of the lane file)
- die_sta.py is now ON MAIN (DIE-STA merge e70305aec7): CI uses it directly; --sta-tool only as fallback.
- New-code run started 12:31 on main da5213b0b3 (intel2, 6 per-die jobs incl. hbm_arch_B2 now on main; HBM 136 G,
  others 72 G). Jobs queued by ot-heavy (intel2 admits 34 G now); results -> claude/die-ci-results + HANDOFF LATEST line.

## 12:50 PDT (coordinator 12:4x)
- MERGED bf41c38e32: die STA GATE = agreed policy (TT setup / FF hold, 60/25 ps); margined slack and margined stand-ins
  are INFO columns (SUMMARY: "die STA gate" + "INFO margined"; per die: seam table gate vs INFO). KV pair e5e6 under
  the gate: TT +93.3 / FF +231.0 -> PASS for that pair (margined INFO -20.1 / +170.2). Margin values stay OWNER?.
- intel2: ~/OpenTallas is a symlink (scratch2 clone at 3e05af806b); the runner already fetches hub main every run and
  now fails closed unless the CI worktree HEAD == sha. The 12:31 run on intel2 checked out da5213b0b3 correctly.
- In-flight run da5213b0b3 (started 12:31) uses the pre-bf41c38 gate (margined); the next hourly commit run on bf41c38
  re-gates (G2 CARRIED where the plan is unchanged).

### DIE-STA
## PARKED 18:55 PDT
- Branch claude/die-sta-1024@97fd4371ec (pushed). main has up to 96ce86b63e; branch adds: no half-period arrival wrap,
  empty-pin fix, tests 9/9, results/die_sta/trial (v1). NOT yet merged (merge after v2 results).
- Live jobs (intel2 = tolerant-swine, ot-run, die_sta.py pids): hbm_B2l:1389069 qwen_kvsys:1389720 s81:1389748 s81_head:1390005 qwen_compute:1390007 hbm_B2l:1390279 qwen_kvsys:1390349 s81:1390356 qwen_compute:1390361 s81_head:1390362 hbm_B2l:1390576 hbm_B2l:1390577 hbm_B2l:1390594 qwen_kvsys:1390617 qwen_kvsys:1390618 qwen_kvsys:1390635 s81:1390653 s81:1390654 s81:1390671 qwen_compute:1390680 qwen_compute:1390681 qwen_compute:1390702 s81_head:1390721 s81_head:1390722 s81_head:1390739 
  dirs intel2:/srv/opentallas-scratch2/claude/die-sta/trial/<die>/sta/run_ttff_v2 (logs run_ttff_v2.log;
  ot-run logs ~/coord/part-cap-logs/die-sta-run2-*.log). ~1-2 h (hbm slowest). Cancel: ot-run --cancel <dir>.
- Results: CP1 G4 reach405 ilm == flat 0.000 ps, seam PASS (TT +432.5 / FF hold +87.8 / spread 56.8). Trial dies v1:
  TT setup OK on all 5, FF hold FAIL on all 5 (table below). Capacity: full die 970 GB (no) / 540 GB --reduce (yes).
- Failures: none of the tool; trial dies FAIL FF seam hold (H-tree tap skew).
- Next: when v2 done -> `python3 /tmp/trial_sum.py` on intel2 (copy in ~/wt/die-sta? no: script at intel2:/tmp/trial_sum.py),
  copy run_ttff_v2/die_sta.json to results/die_sta/trial/<die>/v2_die_sta.json, update README.txt, commit, merge.
- OWNER?: hbm_B2l NW_sm2 tap +440 ps and qwen_kvsys hub taps (216 ps spread) need spine rebalancing before any seam
  can close hold; per-partition hold fixing cannot absorb -417/-173 ps.

## 18:50 PDT (resumed after session limit)
- OWNER DECISION ack: gate = TT setup / FF hold at 60/25 ps uncertainty (+ pin-flop spread <= 80 per AGENTS.md L32);
  everything else (SS, TT hold, FF setup, extra margins) INFO only. die_sta.py verdict already does exactly this.
- Trial-die seam STA v1 (current main plans, budget stand-ins, trial H-tree spine), seam slacks valid:
  | die | groups/bits | TT setup | FF hold (neg bits) | verdict |
  | s81 | 2151/1.06M | +654.4 | -52.5 (661k) | FAIL |
  | s81_head | 425/212k | +626.3 | -82.1 (124k) | FAIL |
  | qwen_compute | 2934/1.32M | +661.6 | -46.4 (1.0M) | FAIL |
  | qwen_kvsys | 3939/620k | +501.9 | -173.4 (437k) | FAIL |
  | hbm_B2l | 918/610k | +411.2 | -417.0 (369k) | FAIL |
  Setup is never the problem (stand-in seams are flop-to-flop, >400 ps slack). Hold fails on every die because
  stand-in seams have ~zero data delay (QN -> wire -> D) against H-tree tap skew of 50-440 ps: the capture tap is
  later than launch. Worst: hbm_B2l NW_sm2 single tap +440 ps (FF) vs neighbours ~25-90 ps; qwen_kvsys hub_* taps
  (spread 216 ps > 80 inside hub_Wi/Wo/Eo). Real partitions will add hold buffers inside each seam flop's input
  cone, but -417/-173 ps is beyond per-partition hold fixing (~1 buffer = 10-15 ps): the H-tree tap skew must come
  down (spine balancing / tap re-insertion) - OWNER? / TRIAL-HBM + TRIAL-QK: hbm NW_sm2 tap, kvsys hub taps.
- BUG found + fixed: clock arrivals in launch/capture/FFSPREAD were wrapped by period/2 (hid the 440 ps tap; slacks
  unaffected). v2 rerun of all 5 (correct spreads) running intel2 run_ttff_v2. Also fixed: empty pin connects
  in rewritten tops ('{}'); 'ports' spine == gclk 0.000 ps on routed CP1 reach405 pair.

## 14:20 PDT
- MERGED main 96ce86b63e (CP1 G4 + die-scale fixes + capacity SUMMARY).
- CP1 G4 (root reach405 pair, kits NOT SIGNED internally): ilm == flat 0.000 ps, 2 seam groups / 1533 bits, TT/FF/SS,
  ideal + CP2 branch spine. Seams: TT setup +432.5, FF hold +87.8, spread TT 56.8 / FF 46.2 -> seam PASS.
  Evidence results/die_sta/cp1_reach405.
- Trial s81_head (current plan a00cc383, budget stand-ins, trial H-tree spine): FAIL: TT setup +626 OK, FF hold -82.1 ps
  (123,852 neg seam bits; worst mesh0S->sst4/rx_i, launch 22.8 vs capture 101.6 ps clock), spread 105 ps (tW4b8,
  tW4o8, tE4b8, +1 > 80). => H-tree tap skew alone breaks seam hold; matches TRIAL-S81 OCV finding (shared seam leaf
  fallback = OWNER? item there).
- s81 / qwen_compute / qwen_kvsys / hbm_B2l running (TT ~50 min/corner; hbm ~2 h/corner).

## 13:50 PDT
- Trial dies on CURRENT main plans (die_trial.py kit + clock TT/FF, my dirs; stand-ins = one face flop per pin bit,
  spine = trial H-tree arrival per tap): intel2:/srv/opentallas-scratch2/claude/die-sta/trial/{s81,s81_head,
  qwen_compute,qwen_kvsys,hbm_B2l}/sta/run_ttff (ot-run, 48 GB/8 thr each), logs ~/coord/part-cap-logs/die-sta-run-*.log.
  die_sta fixes on the way (committed): per-bit seam slack (path enumeration too slow at 1M bits; == to 0.001 ps on
  KV), spine as ONE clock + per-tap port source latency (generated clock per tap: 3.8k-8.2k clocks stalled).
- CP1 G4 validation now possible: root's codex-cp1/reach405 pair both routed (NOT SIGNED): ilm + flat TT/FF/SS (+ branch
  spine) running localhost:/srv/opentallas-scratch/claude/die-sta/cp1_reach405 (ot-run 24 GB).
- Capacity SUMMARY committed (results/die_sta/capacity/SUMMARY.json): full die ~970 GB full parasitics (NOT feasible
  on 1 TB), ~540 GB with --reduce (feasible, ~19 h/corner, SPEF reader bound).

## Current step (08:25 PDT)
die_sta.py verdict switched to TT setup / FF hold / spread<=80 (7ba6155209).
die_sta.py v1 committed + pushed (ilm / flat / etm modes, compare, replica). Flat capacity replicas running on intel2.
Waiting for CP1-R10 routed kits (r10a epyc3:~/ot-scratch/cp1-r10/kits at GRT; r10b ~/ot-scratch/cp1-r10b/kits) to
... (38 more lines in lanes/DIE-STA.md)

### ELASTIC
(no PARKED section — last 12 lines of the lane file)
- Longest lanes c_*_bf_00__rsf (7 hops, 514 b, 17/18 cyc) carry 0 pad; 98.6% (P5) / 98.7% (P6) of pad flops on <=6-cycle lanes
  waiting for a slow partner (P5: tw_we/kind 3 b at depth 17 vs tw_data 1024 b at 2 -> pad 15 x12 slices; P6: replica spread, e.g. hw ctl->hc1/hc2 +2).
- Cal: pad stage 0.3353 um2/bit, elastic FIFO entry 0.523-0.538 um2/bit (1.6x). Full-duty elastic/pad = 2.9x (P5), 5.2x (P6), 0 lanes win.
  Elastic on the 12 rsf lanes alone = +0.116 mm2 for 0 pad saved. Pad ceiling = 0.011% die (P6).
- Token latency gain 0 cycles (pad = arrival of slowest joined/locked partner); valid-gated issue would need rework of all static
  consumer leaves + joins; calendar collectives cannot stall. Rate gain <= 0% (1% = 2,291 cyc/token at 5,237 tok/s).
- Task 3 (RTL seam, exactness, 833 ps SS/FF P&R): NOT RUN — no winning lane set.
## Shared with QC-TOK
- Pads come from plan bus splits (P5) and replica depth spread (P6): fix plan-side (ride-along / equal replica hops, as r8b did for tw).
- Unpriced residual idea: rate-aware "sparse landing" for low-duty buses (needs duty measurement + consumer don't-care proof; ceiling <=0.011% die).
## OWNER?
(none)

### ELEM-HBM
## PARKED 2026-10-24 19:00 PDT (ELEM-HBM main)
- Branches:
  - claude/elem-hbm-1024 @9bd0d7c0f8 (pushed, worktree ~/wt/elem-hbm clean).
  - SPLIT2 claude/elem-hbm-split2-1024 @d2d3dc361d (see its park report above). It has 65/70 split modules proven exact; their 91 views generate rc=0 and are not launched yet.
  - Not merged to main yet: no core has SIGNED.
- Live jobs (all mine, running, left alone):
  - B2l core routes, 89 kits, in /srv/opentallas-scratch/claude/elem-hbm/runs/<kit> on localhost, epyc3 and intel1. Containers are hbmcore-<kit>_*.
  - Kit list: /srv/opentallas-scratch/claude/elem-hbm/route_all.txt. Status snapshot: route_status_parked.txt (route_status.sh LIST re-reads it).
  - At park: 70 in GRT, 10 at generate_abstract (finish, signoff next), 1 in DRT.
  - auto_resume.sh is stopped (pid 853443 killed). Its retries are logged in auto_resume.log.
  - SPLIT2 equivalence jobs: localhost pids 2319737-2319742.
- Failures on record (not closed):
  - RSZ-0060 hold-buffer cap. Several first-batch runs started before hold_cap.tcl, and some failed again after resume.
    - Next: check that OT_HOLD_CAP appears in their 5_1_grt.log.
    - If it is there and the cap is still hit, the input-hold demand itself is the problem. That belongs to the same core clock contract question: IO vclk 250 vs measured insertion.
  - GRT-0116/0183 congestion: svc_pc_ctrl_leaf_cfg_h9b (31be7c, 3b586c, a4d8b0, 3ffaa4, 9467d1) and sm_xload cl2 bdring/bfqg.
    - These cores are pin- or macro-dense. Next: try a lower PLACE_DENSITY or a higher layer, or ask HBM-ARCH for a bigger outline.
  - 6_report "LEF Cell ot_sram_* has no matching GDS/OAS": macro GDS is missing in kits with SRAMs (vm_calendar, idx_query, svc_pc_ctrl_leaf 3f2f98/cfc804/684f40).
    - Next: add the macro GDS (ADDITIONAL_GDS) in gen_core_kit_hbm.py, or check whether signoff.py accepts it without GDS.
  - Placed-stage FAIL: 26 kits on the core clock contract (insertion 328-1150 ps). Lists: route_hold.txt and route_hold3.txt.
  - GQ land CTS retry: FAIL.
- Next steps:
  1. Collect the finish runs: physical/die_plan/hbm_arch_cores/collect.py, then record verdicts.
  2. Fix the GDS and congestion items, then re-launch.
  3. Integrate SPLIT2: merge its branch, run plan_records, then place the 91 views.
  4. CTS-probe the 9 unmeasured sfu split3 lanes (cts_probe_result3.txt).
- OWNER? (open):
  - Core clock contract: early core taps for cores whose insertion is over 290 ps (posted to HBM-ARCH 13:27 and 14:11).
  - vmdel re-pin to NPC=2.
  - VM_RT_EXTRA 173 vs 171.
  - coll body pins were cut from the VM_RT=0 master, but the die binds VM_RT=81 (SPLIT2 finding).

### ELEM-QK
## PARKED 2026-10-24 18:56 PDT  (branch tip after sub-agent parks: 2ece7f9a79)
- Branch claude/elem-qk-1024 @de0409474f (pushed; main merged in). NOT merged to main: tools/die_plan pytest shows
  failures in test_g2/test_relay_mid (+ test_bind needs OT_BIND_YOSYS=local yosys); not yet compared against main -> next
  agent: run the same suite on a main checkout, merge only if no new failures. Own changes: bind.py kit-rtl (keep cells,
  `include headers), gen_phys.py (include dirs, escaped macro names), tools/elem_qk/*, results/elem_qk_1024/*, geom_review.
- Live jobs (let finish, then collect):
  * epyc3:/srv/opentallas-scratch/claude/elem-qk/g3qc3/tt_ctlm  run_kit route (unit oth-ubuntu-440481-1792873606; was in
    GRT extra iterations 19/30 = congestion), log localhost .../elem-qk/logs/qc3_tt_ctlm_route.log, KIT/run_route.log;
    signoff runs inside run_kit (KIT/signoff/signoff.json). Pathfinding: bound v5 = P6 main plan, NOT the accepted
    capacity plan.
  * localhost:/srv/opentallas-scratch/claude/elem-qk/rerun/qkd_kvs_ctl  re-run route (log logs/rr_qkd_kvs_ctl.log), then
    resign: cd there; ot-run ... bash ../../resign.sh 24b2da3433; collect: tools/elem_qk/collect_rerun.py.
  * forks ELEMQK-ASTK (ASTK/ECTLK variants) and ELEMQK-KV (KV io/sys/hroot G3) told to park; their blocks follow below.
- Results: 32/33 signoff_1024 re-runs routed at closed commit + main signoff: ALL NOT SIGNED (results/elem_qk_1024/
  README.md, rerun_summary.json): sdc_lint 32 (ref_tile Tcl SDC form), face_guard 26, FF hold 13. -> need die-plan G3
  re-kit to sign. KV heads e1..e7 hold variants (21): none SIGNED; recipe b (FF-only margin 3) fixes hold to <=5 endpoints
  (e2 +0.09 / TT +27.10) but DRV slew, clock insertion 320-363 vs 250+-40, old-kit face_guard remain (re-kit by KVG3-CORES).
  QC tt_ctlm v5: SDC_LINT PASS, FACE_GUARD PASS 3117/3117, placed (review PASS-COND), route pending.
- Failures/blocks: native59 face_guard FAIL = duplicate plan fault lane fltn (asked QC-A0 12:24, still in capacity plan).
  21 re-runs killed 08:33 by fleet-wide docker stop (relaunched OK).
- Next: rebind QC G3 types on the accepted capacity plan once QC-A0 lands it (tt_ctlm, native59 after fltn fix, glue,
  coll_*; coll/glue have bound_only clocks clk_coll/clk_serdes/clk_d2d -> need SDC/plan clock decision).
- OWNER?: (1) ref_tile re-runs can never sign (SDC form + face registers): confirm re-kit as the only path (SIGNOFF lane).
  (2) native59 fltn duplicate lane: drop it (QC plan owner). (3) multi-clock coll/glue types: plan clock per bound_only clock.
- Cleaned epyc2 scratch2 codex-qwen obj trees (~106 GB freed, binaries kept).
- 2026-10-24 18:56 PDT PARK (fork ELEMQK-HOLD): branch claude/elem-qk-1024 @de0409474f (hold work in ed2fcee37e, a0875f8a5f), clean, pushed.
  Live jobs: none (all 21 hold-ECO runs finished; no elemqk-hold containers on localhost/epyc3).
  Results: results/elem_qk_1024/hold/ (README, hold_summary.json, 21 signoff.json): all NOT SIGNED; recipe b (FF-only,
  margin 3) brings FF hold to -1.6..+0.09 ps (e2 passes hold, TT +27.10) but drv slew / clock insertion 320-363 vs
  250+-40 / face_guard fail on the old 285.12 kits. Run dirs localhost+epyc3:/srv/opentallas-scratch/claude/elem-qk/hold.
  Next: apply recipe b (tools/elem_qk/hold_eco) as the post-route hold step of the KVG3-CORES 216x216 head re-kits once
  they route clean on clock insertion/slew/face_guard.
## ASTK/ECTLK parked 2026-10-24 18:56 PDT (fork ELEMQK-ASTK)
- Branch claude/elem-qk-1024 @22cfe74028 (tools/elem_qk/astk_variants.sh, run_variant.sh, results/elem_qk_1024/astk/VERDICTS.md).
- Live jobs of mine: none (all 14 variants finished; ES r4hs NOT RUN: ot-run "no host qualifies" glitch). Watching only Codex
  intel1:/srv/opentallas-scratch2/claude/codex-qwen/astk_WN_r4 (not mine; collect with signoff.py tt,ff into a new dir).
- Results (all NOT CLOSED, no route): ASTK EN/ES/WN/WS hm55 / r4h / r4hs (EN/WN/WS) -> CTS RSZ-0060 max hold-buffer count
  (flat 55 ps TC hold margin too aggressive). ECTLK e1/e2/e3 (-no_insertion_delay, buffer spacing/clusters, BUFx24 tree)
  -> CTS RSZ-0060, ~11.36k hold buffers: late clock is ck pin geometry (E corner of 881 um), not macro balancing.
  Run dirs: epyc3:/srv/opentallas-scratch/claude/elem-qk/astk/<core>/<v>, intel2:/srv/opentallas-scratch2/claude/elem-qk/ectlk/e{1,2,3}.
- Next: ASTK = margin-15 route (+replica RTL r4 for TT) then FF-only post-route hold ECO (root r4b/r4d recipe), signoff tt,ff;
  ECTLK = measure e1 CTS insertion, then OWNER?: centre clock entry / plan pin move (250 ps budget never waived).
- KV kits parked 18:56 PDT (ELEMQK-KV). Branch claude/elem-qk-1024@2ece7f9a79. Verdicts results/elem_qk_1024/kv/*.json (none SIGNED):
  io_ft TT -98.3/FF +9.5; io_ft_v1 TT -85.4 -> -39.8 with repair_design -max_wire_length 120 (slew 0; residual = input->face flop: SPEF tap insertion 204..239 vs plan 250); io_cor TT -244.3/FF -11.0; io_cor_v1 TT -128.7/FF -27.8/spread 89.4;
  hroot TT -139.7/FF -11.1; all DRC 0, GRT 0, pin_audit + face_guard PASS. sys_c g3h GRT FAIL ovf 109 at UCIe PHY bottom corners (W pins y 250..500 under PHY). sys_SD/_v1 NOT RUN (no x6 PHY view).
  Systemic kit-flow findings: (1) run_kit 6_report RCX OOMs at any cap (peak = cap) -> signoff skipped; run signoff.py separately. (2) 635+ um hops need max_wire_length repeaters (flow left 250 um segments, RCX slew 688 ps). (3) tap_balance lands SPEF insertion ~30 ps below plan 250 -> input budget paths fail.
  RESET RULE conflicts: every kit has a per-partition 2-flop sync on raw arst_n (bind u_rst_sync) fanning out by buffer tree (no relay flops) over up to 1900 um; ot_dp_st face flops async-reset; hroot leaf re-syncs (cascaded ot_rst_relay root->bank/main, unequal depth).
  LIVE (mine, keep running, collect then signoff): intel1 /srv/opentallas-scratch2/claude/elem-qk/kvr2/{kv3_hroot,kv3_io_cor,kv3_io_ft}; intel2 .../kvr2/{kv3_io_cor_v1,kv3_io_ft_v1} (r2 = wirelen + OT_TAP_TARGET_PS 280 + HOLD margin 45, signoff chained; logs localhost:/srv/opentallas-scratch/claude/elem-qk/logs/r2_*.log); intel2 .../kvg3h/kv3_sys_c (-allow_congestion pathfinding, log logs/kvh_kv3_sys_c_route.log; run signoff.py by hand after).
  Next: collect r2 signoffs; sys_c PHY move/halo + plan W pins / host-leg stations (propose KV-G3); hroot relay guide; propose wirelen + tap target fix to gen_phys owners; macro overlay physical/die_plan/qwen_kvsys/elemqk/macro_overlay.json -> KV-G3.

### ELEM-S81
## PARKED 18:56 PDT (station405 sub-agent)
- Branch: claude/elem-s81-st405-1024 @ e61ddd9234 (pushed; merged to main by COORD). No WIP and no stash. Worktree /srv/opentallas-scratch/claude/wt/elem-s81-st405.
- Watcher auto_resume.sh (localhost pid 745780) STOPPED by me at park, so it can't launch anything new. No new jobs were started.
- LIVE B jobs: ot-run launcher pid on localhost, container dpkit-slice_station__tN on the host; cold kits; 36 GB / 8 threads. Collect each with:
  grep ^SIGNOFF logs/tN.B.otrun.log
  - epyc3:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__tN:
    - t1 (6_report, pid 2355875)
    - detailed route: t2 (2354717), t23 (2357829), t24 (2359058), t33 (2358944)
    - global route: t3 (2359361), t4 (2352217), t9 (2360299), t25 (2361702), t27 (2362857), t28 (2359247), t32 (2353081)
  - intel1:/srv/opentallas-scratch2/claude/elem-s81-st405/kitsB/slice_station__tN:
    - t31 (6_report, 2386183)
    - t5 (2388643), t6 (2389368), t8 (2390102), t10 (2390720)
  - intel2:/srv/opentallas-scratch2/claude/elem-s81-st405/kitsB/slice_station__tN:
    - t14 (2391131), t18 (2391528), t22 (2391812), t26 (2392084), t29 (2392476)
  - Logs: localhost:/srv/opentallas-scratch/claude/elem-s81-st405/logs/
  - If 6_report dies with Error 247, resume warm from the kit's own 5_route.odb with resume_finish.sh (manual now that the watcher is stopped).
- VERDICTS (B; IR NOT RUN; DIE-STA seam STA pending):
  - SIGNED: t12, t15, t16, t17, t20, t21. Records: localhost:/srv/opentallas-scratch/claude/elem-s81-st405/kitsB/slice_station__tN/signoff/signoff.json. Numbers in the 14:49 and 19:1x lines above.
  - NOT SIGNED:
    - t13: TT -67.37, recovery. localhost:.../kitsB/slice_station__t13/signoff/signoff.json
    - t30: TT -81.43, arst_n -> u_rsync_t13 recovery. intel1:.../kitsB/slice_station__t30/signoff/signoff.json
    - t11: DRV 4 slew, worst 372/320. epyc3:.../kitsB/slice_station__t11/signoff/signoff.json
    - t34: DRV 2 slew (330/320) and TT spread 88.6. intel1:.../kitsB/slice_station__t34/signoff/signoff.json
  - A (0.08 T) runs are diagnostic only: t2, t15 and t33 NOT SIGNED. t19 is the empty type and was NOT RUN. t7 belongs to Root.
- CAUSES:
  - t13/t30: the per-tap async reset synchronisers set up a recovery check across about 2 mm. The owner RESET RULE removes it.
  - t11/t34 slew: after the routing-stage repair at slew margin 50, a BUFx3 placement buffer still drives an INVx1 about 149 um away on the station-0 flop output, and it lands just over the limit.
  - t34 spread: tap balancing is done on the CTS-stage estimate; routed insertion comes out 20-30 ps low, and big taps have large internal skew.
- NEXT:
  1. Collect the 21 running tiles; write verdict lines here.
  2. t11/t34: write a slew-repair hook. ORFS repair_design_helper (util.tcl) passes only CAP/SLEW_MARGIN, with no max wire length. Use a kit tcl that runs repair_design -max_wire_length about 100 um, or a repair after routing on 5_2_route.odb followed by incremental detailed route. Review it, then re-run warm from each tile's own pre-fill route checkpoint.
  3. t34 spread: look at tap_balance on the worst tap.
  4. t13/t30: wait for the shared reset implementation (request with the 5 points is in KV-G3.md at 19:1x), then re-kit from main. If there is no ETA within about 2 h, offer to write the gen_rtl + kit_rsync implementation on a branch for KV-G3 to review.
- OWNER?:
  - Reset rule for a tile that is not its region's root: is rst_n a synchronous input with an input-delay budget, or is there one root synchroniser per tile?
  - Boot-cycle cost of the relay depth.

## PARKED 2026-10-24 18:56 PDT (canonical cores sub-agent)
- Branch claude/elem-s81-cores-1024 @dc52d4a06f (pushed; NOT merged). WT localhost:/srv/opentallas-scratch/claude/wt/elem-s81-cores. Commits: c111758856 generator+recipes, d1852f8f10 implemented-netlist face regs + face_guard `pair IN OUT` (+test), dc52d4a06f const-output flops / pair outputs / core_margin / LEF-contract mode.
- Generator: physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py (+recipes.json, core_face_post_synth.tcl, render_kit.py). VQ r12 recipe (833 ps, vclk 250, 60/25 split, seam hold -40, MCMM tc+bc, post-GRT DRV pass) on plan hard-core pins. rst is a TIMED synchronous input (max 0.5T / min -40 vs vclk, recovery/removal checked), no false path = owner reset rule, same as VQ r12. No RTL edits anywhere.
- Run root <host>:/srv/opentallas-scratch/claude/elem-s81-cores/<round>/<kit> (intel2 symlinked to scratch2); logs + bin/{launch,status,render}.sh on localhost. Only stage 1 (synth+face_guard+place) has run. NO route, NO signoff yet -> 0 SIGNED.
- LIVE (ot-run stage-1 place, all mine, leave running): localhost r2 l0r, l4, l4r, l5f, eg; r5 l1, l3, xrt1, xrt3 (const-flop fix); intel2 r2 l1c, l5_n32 (48 GB); intel1 r2 xfin (will FAIL face_guard: see below). Containers named klegacy-<kit>-<pid>.
- Stage-1 PASS (placed, placed.csv present, ready for review render + route): localhost r2 l0, l2, bk_g, LLd, cfg7_seq_bfp(intel2), r4 qbank_N, qbank_S, rstg, cfg7_seq, sstn_payload536. Reviews done: r2 rstg/cfg7_seq/payload536 (review/*.png): rstg PASS-COND; cfg7_seq REVISED (4.32 margin left an 8.6-um core, bins >0.8 -> core_margin 1.08 in r4); payload536 REVISED (face_flops cloned every 1-station flop -> pair outputs skipped in r4). r4 renders not yet viewed. No geom_review record committed yet.
- FAIL causes: r2 bksel_c face_guard shared 146 (r2 hook predates const-output fix; regenerate like l3 and rerun); nodes LLfd/LLfu/NNfd/NNfu + sstn_base566: RTL ORs a fault/status INPUT (fi / e0,e1,c0,c1,si,nf) into the fault flop -> face_guard 'unregistered' (OWNER?); xfin: main RTL has ENG ports (mode, e_v/e_c/e_hh/kk/dd, ~100 bits) absent from plan pins (OWNER?/S81 plan); cfifo_crs4: 6 clocks (cr, cr_s, xk[3:0]) CDC landing, single-clock SDC invalid (needs multi-clock contract); capc5r, bksel_q: unsigned hard children (generator refuses); spr: ot_s81hd_key.sv not on main (only 3ff002b64c); gunit signoff of legacy runs: 0/9 (sibling, "## gunit signoff").
- NEXT: (1) wait for live stage-1; bin/render.sh <rnd> <kit> <host>, Read PNG, write results/geom_review/elem_s81_core_<kit>.json; (2) route on the SAME host: bin/launch.sh <rnd> <kit> route 32 16 <host> (run_kit.sh continues from place, then do-finish/abstract, pin audit, signoff.py tt,ff -> <kit>/signoff/signoff.json); (3) regen bksel_c (r6) and rerun stage 1; (4) on SIGNED copy LEF/libs/signoff.json into physical/die_plan/s81/cores/views/<module>; (5) l5_n32 uses plan l5 outline 345.6 (n32 kit was 388.8): watch utilization; (6) refresh kit files of r2 survivors from current generator (only core_face_post_synth.tcl/freeze differ; no-op without TIE outputs).
- OWNER?: (a) fault/status inputs ORed combinationally into the fault flop (5 network nodes, sstn_base566): conforming to register-on-every-pin needs +1 cycle on the fault/status chain + bench update; (b) xfin plan pins vs main ENG-mode RTL; (c) cfifo_crs4 multi-clock boundary contract; (d) capc5r/bksel_q: sign children first or flatten; (e) implemented-netlist face registers (output clones / unused-input capture / constant-output flops, all 0-cycle, no RTL) accepted as the face_guard remedy?

## PARKED 2026-10-24 18:56 PDT (ELEM-S81 lane, root agent)
- Branches:
  - claude/elem-s81-1024 @18c5f769c2, merged in main e7c09034ae.
  - claude/elem-s81-st405-1024 @e61ddd9234, merged in main bf6ac37681 (with 460bcf40fd).
  - claude/elem-s81-cores-1024 @dc52d4a06f, NOT merged. Ungated: it changes the shared face_guard.py (pair IN OUT), so it needs review + signoff evidence first.
  - wt-bind48 (localhost elem-s81/wt-bind48, uncommitted v4.8 bind scripts): dead sub-agent, superseded by S81 p11.
  - No stash anywhere.
- Live jobs: none of my own. The sub-agent jobs are listed in the two PARKED blocks above: 21 station B routes on epyc3/intel1/intel2, and stage-1 core places on localhost/intel1/intel2. All watchers are stopped.
- Adopted Codex jobs, now finished:
  - BK drain full-layer replay (epyc3:/srv/opentallas-scratch/claude/codex-s81/bk_drain_layer, own sink-ON kit): build rc 0, run rc 0,
    TB_DV_SLICE FAIL, 2 SCHEDULE_MISMATCH (cycle 6535 port 2244, cycle 6546 port 2248: got 0, want data), fault_cycles 0, 6652 cycles.
    So the addressed-drain candidate is NOT adoptable as is. Default OFF on main stays correct.
  - Head abstract PSM c2 (intel2 scratch2 codex-s81/trial_head_psm_c2): PDN/bumps connected PASS, then the IR analysis crashed with
... (21 more lines in lanes/ELEM-S81.md)

### FLEET-DISK
(no PARKED section — last 12 lines of the lane file)
  bind mounts once no container runs for 3 checks (docker stopped ~1 min then; a docker run in that minute would fail).

## Incident / honesty
- 07:41-07:57 my first ot-mvlink used lsof +D only (blind to docker bind mounts). Checked afterwards: no running container
  mounts any dir I moved; docker events show no container whose life spanned a move with a moved mount except
  intel2 g2part-422678 (07:39-07:42, exit 0) and hd_tile-476609 (07:46:25-28, exit 2, s81-head lane on scratch2 = not moved).
  Moved dirs: intel1 die-sta kv-tok qc-a0 qc-tok s81 claude/part-cap ~/.cache; intel2 qc-a0 kv-tok claude/{kv-g3,part-cap,
  stw-s81d-tok,tok-ds} ~/.cache; epyc2 kv-tok claude/{tok-ds,tokd-hbm2,tokj-1023} ~/.cache ~/wt/{tok-ds-comp,tok-hbm} ~/OpenTallas.
- Not moved (static, small): ~/src-tools 3.4G, ~/.local 0.45G, /var 7G.

## CODEX notes
- 2026-10-24 09:01 PDT: CODEX root collected background movers: no new failure, live-source directories remain unmoved. Removed only own unused interrupted checkout (40GB); no active source moved.

### FLEET-NEW3
(no PARKED section — last 12 lines of the lane file)
- Helpers installed on all 5 hosts via tools/fleet/install_fleet_host.sh (ot-heavy*, die protection, vl-jcap, earlyoom,
  linger, cron reconcile */2, scratch /srv/opentallas-scratch/claude + ~/ot-scratch link). localhost role coord
  (/etc/ot-heavy.conf MIN_AVAIL_FRAC=0.15). ot-sizes-sync cron on localhost */10.
- ot-run --selftest: PASS 5/5 hosts; choose selftest PASS 28; tiny job per host PASS; unpinned placement -> epyc2.
- Tool parity identical on 5/5: verilator 5.050, yosys 0.68 (38e001a6f), sta 3.1.0 (be771a0), orfs sha256:16470cea...
- Tests: test_ot_run_* all OK (spill fixed: tar prefix /usr/bin/tar:). Pre-existing FAIL on main too:
  test_ot_heavy_admit (reconcile selftest v17 HARD_INVARIANT=0 case), test_ot_heavy_v174_replay (1 failure).

OWNER?
- Old-fleet scratch filesystems found on unpartitioned nvme0n1 (signature wiped, backup superblocks intact):
  intel1 3.5T (ex ot-gold1), intel2 3.5T (ex ot-gold2), epyc2 894G (ex ot-epyc9, claude/ I/O errors).
  Mounted READ-ONLY at /mnt/old-nvme0 (not fstab). NOT formatted. Recover 10-23 outputs, then reformat as scratch?

### GEOM-REVIEW
## PARKED 2026-10-24 18:57 PDT
State: all records committed + merged (last GEOM-REVIEW merge main e39037d67f; branch claude/geom-review-1024 clean, nothing ahead of main). No jobs running; sub-agents GR-S81G / GR-KVC parked with NO records written (nothing judged).
Pending reviews (resume here):
- S81 frame kits g3k5 (g3k4 was stopped by S81; no g3k6): 7 kits NOT REVIEWED. ODB copies + dumps ready in localhost:/srv/opentallas-scratch/claude/geom-review/tiles/GR-S81G/{odb,dump,kits}/<kit>; next = layout_review.py on dump.json, look, propagated-clock STA (GR-S81F sta/*.tcl), 7 records. Input-level notes (not visual): ROM lib fixed; elem_q/bf_col early clk_c* taps fixed; ROM macros still get NO early tap (h9_r2 read path -56); tap load imbalance (h9_r2: clk 2541 / t1 1513 / t6 1524 sinks vs 6 taps 0-10); reset_taps.tcl = per-tap async rsync -> FAILS owner reset rule. h9_r0_p1/p3, h9_r1 only 3_place.
- KV cores NOT REVIEWED: qkd_ahub 6_final (epyc3, webp ready) first; kvs_pc / kvs_pc_h_head_p only 09:xx GRT-failed ODBs (no newer run); ectlk: no variant passes CTS (ELEM-QK e1-e3 RSZ-0060 max buffer count) + plan S-face detour unresolved; head_eighth 216 e4 dumped only; pv_pair m7 6_final. Scripts in tiles/GR-KVC/tools (reset_audit.tcl needs fixing: TIEHI counted as reset source, NULL compare crash).
- hub_Ei vK delta re-review (reset rule + ft24 st2/clk_t31 hotspot, GRT-only gate) when KV-G3 builds it.
- slice_station 405c1 t4/t32 (no ODB at last look); regenerated frame kits on the 26-slot ledger.
Open findings per lane:
- KV-G3: hub_Ei vJ FAIL-to-route (reset rule; hotspot (560-600,800-840)); reach405 plan: 8 in-core stations need regs_um, +1..4 cyc re-price.
- S81: 26-slot ledger PASS-COND (canonical regen, latency receipt NOT RUN, frame kits consume bit sites); xdie fe3d259091 needs rebase on ledger; 12 v4.8 frame FAIL stand; frames fail reset rule.
- ELEM-S81: v4.8 slice_station t3/t4/t9/t25/t32 FAIL (405c1 t3/t9/t25 fix them, PASS-COND); t33 NOT SIGNED (weak repeaters, spread 86.75); station-0 insertion >= 250; reset rule.
- CP1-R10: reach405 r0/r1 FAIL (unpinned proof-leaf regs) - stop as timing evidence.
- S81-HEAD: hd_tile tap160c7 FAIL (elemA_cv clock pin 24 nm access -> regen LEF; best_key 14-level path -627 needs RTL stage).
- HBM-ARCH: B2l PASS-COND (RTL relay binding + token re-run; clock root driver off core u_tkm_SW_tile19; root crossing band + q_sm channels as blockages; halos). Earlier bankq0/gq_land/gq_issue FAIL stand.
- QC-A0 / KVG3-CORES: batch-1 PASS-COND conditions stand (A0 clock contract/equivalence; KV cores straps-as-constants).
Checklist now includes "reset distribution matches the owner rule" (TILE_BRIEF.md); margins INFO only.

### HBM-ARCH
## Sub-lane HBM-ARCH-CLOCK (B2l die clock -> MSCTS/mesh) — PARKED 2026-10-24 18:56 PDT
- branch claude/hbm-arch-clock-1024 @ a2decb1018 (= main merge base; pushed; NO commits of my own yet)
- worktree localhost:/srv/opentallas-scratch/claude/wt/hbm-arch-clock (clean)
- live jobs: NONE (no fleet/OpenROAD job started)
- results: none yet; read-only analysis only. Read AGENTS/BRIEFING, B2r2 trial README, clock_htree.py, tools/die_trial/htree_clock.py,
  B2l plan geometry (row faces y = 0,1503.36,3006.72,4510.08,6065.28,8138.88,10212.48,11767.68,13271.04,14774.4,16277.76,18351.36;
  B2l types carry only clock.tap_um, no per-type clock.taps; M8/M9 pitch 0.08).
- failures: none
- planned design (not started): H-tree (ribs on row faces) -> mesh drivers -> die M8/M9 clock mesh (common CPPR point) ->
  k-median tap drivers (<=400 um to every tap, no empty driver) -> partition taps. Measure: OpenSTA for tree + local
  subtrees, Python linear-RC transient for driver+mesh (OpenSTA cannot time multi-driver mesh), plus adversarial +/-5%
  driver-derate step test on the mesh; deliverables a-e per task.
- next step: write physical/die_plan/hbm_arch/clock_msct.py -> B2l/clock_msct.json; extend htree_clock.py with a mesh mode.

## PARKED 18:56 PDT 2026-10-24
- Branch claude/hbm-arch-1024 @ c411a12b86 (pushed). Main has my DIE-CI rack_macro fix (d82817f245).
- Sub-branches (worktrees on localhost scratch): claude/hbm-arch-clock-1024 at /srv/opentallas-scratch/claude/wt/hbm-arch-clock (clock MSCTS subagent, told to park and push WIP); claude/hbm-arch-bind-1024 at /srv/opentallas-scratch/claude/wt/hbm-arch-bind (created at main a2decb1018, unused, no commits).
- Live jobs (not mine, adopted from Codex): epyc3:/srv/opentallas-scratch/claude/codex-hbm/B2l_fabric_buf12_legal_r4 (GRT extra iterations at last look). Collect, don't relaunch.
- Results:
  - intel2 B2j_hub_core_g2_r2 FINISHED FAIL: EXIT 1, DPL-0033. Core-link station flops (cl_*) overlap each other in the hub's narrow channels, about 1k overlaps, padding check 1017. Station site density exceeds the legal sites. This was B2j; the B2l/B2m hub needs a station-site-density fix before its hub G2 is rerun.
  - xdie hbm-ds@B2l: 480/480 paired. Host error is resolved by the OWNER ruling (go in-band); not yet applied.
- OWNER rulings received (18:4x): price loss accepted; host in-band with the UCIe dropped; reset rule; fold the clock and SerDes power fixes into the plan before binding.
- WIP / next step (B2m = B2l + fixes, new dir physical/die_plan/hbm_arch/B2m; B2l stays untouched):
  1. Host in-band: drop u_host_N (ot_pdie_ucie_col) from the NW_io contents and the io_NW_io_u_host_N window; set io_NW_io_u_lk_N0 host:"in_band" with host_route "NW_io -> [L48] -> root" (root holds u_host_cp_ingress); u_host_ep stays but is fed from the u_ep_N0 host VC (RTL delta, for the bind). NW_io area freed (compaction is a follow-up).
  2. Reset: tools/die_plan/reset_tree.py (committed, UNTESTED) adds reset.mode "pipelined" + a tree (one root at the clock root, relays <= 405 um, hop target 364, equal depth, last relay = partition tap) and type reset.mode "delivered". Still to do: schema fields (reset.mode/tree, type reset.mode) and the check.py hook (rule reset_tree, WARN when not adopted). Then run it on B2m and check G0C.
  3. SerDes PG: add die.pg.local (dense M8/M9 over the 5 SerDes windows, about 5x coverage, e.g. width 2.4/pitch 8.64, plus a dedicated bump field) to the schema and plan. Verify with tools/die_trial/hbm_b2_ir.py on the w_io/w_spb0 windows (about 1 min each locally); gate 35 mV.
  4. Clock: merge the subagent's B2m_clock clock block (gate: related-pair skew with 5% OCV after CPPR <= 80 ps TT/FF).
  5. Then G0/G0C, render + G1 review (results/geom_review), G2 die + worst parts incl. hub core nets, then native bind per the RTL delta audit (order of work in the 12:58 entry).
- OWNER?: none new.

### KV-G3
### KVG3-CORES — PARKED 2026-10-24 (coordinator move to rtx-pro)
- claude/kv-g3-1024 @229adce8f2, local commits befed6a747 (signoff hard-core latency contract + labelled kvs_pc clock
  assumption) and 229adce8f2 (WIP leaf PORT_REGS RTL + benches). NOT pushed by KVG3-CORES: my task brief from the user says
  "do NOT push"; KV-G3 (branch owner) please push. Modified tools/die_plan/{face_flops.tcl,gen_phys.py,gen_rtl.py,
  kit_rsync.py,reset_taps.tcl} + untracked reset_tree.py in ~/wt/kv-g3 are KV-G3's WIP, not committed by me.
- Live jobs: none of mine. Codex-adopted, finishing (generate_abstract): intel1:/srv/opentallas-scratch2/claude/codex-qwen/
  {astk_WN_r4,head_e1_hold40}, intel2:/srv/opentallas-scratch2/claude/codex-qwen/head_e2_keep.
- Results: head_eighth 216 x8 routed DRC 0 / ant 0, NOT SIGNED: FF hold -4.3..-7.5 ps all, TT setup e6 -12.1 / e7 -25.0
  (others +1.6..+46.3), face_guard FAIL e0/e2/e4/e6 (RTL; PORT_REGS fix written, not yet in kits). pv_pair NOT SIGNED.
- Next: collect head 216 + Codex runs; FF-hold recipe from head_e1_hold40; wire PORT_REGS=1 into head_eighth cores (+ your
  partition binding, e0 g_f +1 edge); e6/e7 setup; reruns of pv_pair/kvs_pc/ectlk/astk on v3.8w/x geometry.
- OWNER?: kvs_pc HBM clock period + CDC SDC vocabulary (sdc_lint forbids set_clock_groups; 833 ps co-timed labelled
  ASSUMPTION kept); PORT_REGS adoption in shared leaves (S81 ref tiles bind the same r4.sv; defaults unchanged).

## PARKED 18:58 PDT 10-24 (KV-G3)
- Branch: claude/kv-g3-1024 @6ecd9a39e2 (pushed; includes KVG3-CORES befed6a747 + 229adce8f2 WIP). Last merge to main: b1c715bf9a (@09ec38621d).
- Live jobs: none of mine. KVG3-CORES parked (its note above / lanes/KVG3-CORES.md; Codex-adopted astk_WN_r4 + head_e1_hold40 on intel1 and head_e2_keep on intel2 still finishing, to collect).
- Results since last note:
  - hub_Ei vJ 4_cts: pair skew PASS TT 74.8 / FF 69.7 ps; TT WNS -864.0 (reset recovery), TT clk -26.1, WHS TT -84.4 / FF -26.4 (pre hold repair); author review PASS-COND (results/geom_review/kv3_hub_Ei__kvg3_vJ_cts.json). NOT routed, NOT SIGNED.
  - FAILED (recorded, not overwritten): g4 vC GRT-0116, total overflow 8157 (superseded). Codex retry4 (localhost, ot-run PID 2204345, exited) GRT-0116, total overflow 22835 (max H39/V32) -> reach405 + grid200 without per-bit sites does not route; vJ (per-bit sites) is the candidate.
- OWNER RESET RULE (option b) implemented as WIP in 6ecd9a39e2:
  - tools/die_plan/reset_tree.py (shared): one root ot_dp_rsync_s<N> u_rst_root at the arst_n pin, then ot_dp_rrelay u_rrl_<k> with hops <= 405 um, equal depth D to every tap, last relay drives rst_n_t<i>; reset_tree.tcl gives FIRM sites.
  - kit_rsync.py converts both bound u_rst_sync kits and earlier per-tap u_rsync_t kits; gen_rtl.py emits the tree; gen_phys.py copies or generates reset_tree.tcl; face_flops.tcl sources it; reset_taps.tcl skips u_rst_root / u_rrl_.
  - arst_n stays timed under its 166.6 ps input delay into u_rst_root, so there is no false path and sdc_lint is unchanged.
  - hub_Ei price: D = 7 (71 tree + 208 pad relays, max hop 404.4 um), release N+D = 2+7 = 9 clocks, so +7 boot cycles.
  - vK kit RTL built and verilator-clean: ~/scratch/kv-g3/kit_rtl/g5/vK/kv3_hub_Ei (only u_rst_root sees arst_n).
- Failures to fix before merge: test_g2::test_per_tap_reset_synchronisers and test_check::test_gen_rtl_lint_and_bench need updating for the tree. test_bind (12), test_forest, test_relay_mid x2 and test_g2::test_seam_audit_catches_or11810 fail on the baseline too (not mine).
- Next (vK plan):
  1. fix the 2 tests and add test_reset_tree (depth equality, hop <= 405, kit_rsync per-tap conversion), then merge;
  2. gen.py phys vJ plan with --kit-rtl vK (copy ideal_budget/cts_budget_release + the 9 config extras from vJ), rsync to intel2 g5/vK, run to CTS;
  3. measure with ps2.sh TT/FF + pair_skew gate, confirm recovery is closed and look for an async group;
  4. dump/render, author review, then GEOM-REVIEW second review; route only after it.
- OWNER?:
  - (1) ft reach / M8-M9 (open);
  - (3) KV re-bind owner for hub_Eo/Wo + rows (open);
  - kvs_pc HBM clock period + CDC SDC vocabulary (from KVG3-CORES);
  - die-level: the rule says one root synchroniser per die region; the kit has one per partition, so equal release ACROSS partitions needs the die spine to carry a synchronous reset (owner to confirm "region" = partition or die).
- HANDOFF 18:58: KV-G3 parked at 6ecd9a39e2; resume at "Next (vK plan)" step 1; no live jobs of mine.

### KV-TOK
## PARKED 18:56 PDT 2026-10-24
- Branch claude/kv-tok-1024 @5a351c94dd (pushed). main has efd14deb5c (vehicle + sub-benches + root causes).
- Live jobs: none of mine on epyc2 (old O0 sims killed per COORD; bo1tok runs stopped). Forks B (claude/kv-tok-b-1024)
  and C (claude/kv-tok-c-1024) told to park + push; see fork lines below once reported.
- Done: A tool physical/die_plan/qwen_kvsys/bind/kv_kvpc_hbm_reset.py (96 kvpc rst_n -> i_host_hbm_rst_n_q[0]; not yet
  in a build). m2 mutant plusarg +MUT_RL24=<part> in the PHY bench.
- Findings this step: B is bigger than "seal before boot": the calendar only reserves static columns while a layer runs
  (go), and seal is sticky (one image) -> fix must be a controller boot window (static column without reservation +
  raw-return expectation) before the first calendar go (fork B). m4 mutant: re-compiling the boot image from
  die_ages_bound_padded.json + relay_stages_bound.json does NOT reproduce image_kv41 (targets 1/3/11/13 differ) ->
  m4 needs either the original run_rebind.sh inputs or a word patch + re-encode (encoder not yet located). NOT RUN.
- Reset rule: A uses the synchronously delivered HBM lane (rule style); die-wide spine pipelining for KV RTL follows
  KV-G3 kit_rsync (physical) -- functional ot_dp_rsync unchanged in sim. OWNER? whether the bound RTL itself must
  carry the pipelined spine before boot benches.
- Next: collect B/C fork branches -> kv43 = kv42_bo1 + A + B + C(+C1) full hier rebuild (~32 min, 35 GB) -> boot smoke
  nominal + MUT_FRAME, token nominal + m1 (+MUT_CMD_LATE) m2 (+MUT_RL24) m3 (PRELOAD_ARGS --mut-kswap) m4 (image).
- OWNER?: KV bind ownership / bind.py re-run impossible (bound_netlist.json lost); C2 clock plan (sys_SD on core).
## COORD rulings A/B/C1/C2 (received ~19:00) -- IN PROGRESS
- old O0 sims 434532/434535/466382 KILLED (per COORD).
- A: physical/die_plan/qwen_kvsys/bind/kv_kvpc_hbm_reset.py (bind-level edit, bind.py re-run impossible: KV
  bound_netlist.json lost): 96 kvpc instances in 24 pc part types .rst_n -> i_host_hbm_rst_n_q[0] (pipelined synchronous
  HBM reset lane, reset-rule style; slg keeps die reset). DONE (tool), integration pending.
- B (controller boot window, miter+mutant) and C1+C2 (coherent valid/data delay + async FIFOs at HOST adapter, bench PHY
  model CDC) running as KV-TOK forks on branches claude/kv-tok-b-1024 / claude/kv-tok-c-1024.
- Next: kv43 build (kv42_bo1 + A + B + C), boot smoke nominal + frame mutant, token nominal + m1..m4.
## MERGED main efd14deb5c 14:2x (tools + findings; verdicts NOT RUN)
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

## 13:40 BO1 boot findings (whole-die bench + flat sub-benches; all NOT a token verdict yet)
- BO1 removes the D2D fault: no dcal/d2d fault in 20k+ cycles (legacy faulted at 539). D2D admission now waits.
- BOOT STALL (independent of BO1, also in legacy runs): HOST accepts 528/7161 frames, boot_pr never changes, no image
  replayed; die_rst_n stays 0. HBM cold boot: boot_go reaches all 4 chain ends at cyc 506, PHY sees only REFPB
  (row op 6), never a WR; at cyc ~20590 all 128 slices report done, ok 0, fault 1 (qkd_hbm_boot_pc TIMEOUT 20000).
- ROOT CAUSE A (proven, flat pc_part sub-bench tools/qwen_layerbench/kv_dieslice/pcpart): the kvpc reset spine
  ri_kvpc0_rst_n is bound to HOST die_rst_n (x_hub_Wi_rs_host_die_rst_n_*), and the slice boot-window face
... (33 more lines in lanes/KV-TOK.md)

### KVG3-CORES
## PARKED 2026-10-24 (coordinator move to rtx-pro) — KVG3-CORES
Branch claude/kv-g3-1024 @229adce8f2 (local commits befed6a747, 229adce8f2 NOT pushed: lane rule "parent KV-G3 owns
push/merge"; earlier 5637117270/b1acb09077/b494c0dd31 — v3.8x already on main c98b74b466 via KV-G3). Untracked/modified
tools/die_plan/{face_flops.tcl,gen_phys.py,gen_rtl.py,kit_rsync.py,reset_taps.tcl,reset_tree.py} in ~/wt/kv-g3 are
KV-G3's WIP, not mine (left untouched).
Live jobs: none of mine. Codex-adopted, at generate_abstract (collect next): intel1:/srv/opentallas-scratch2/claude/codex-qwen/
{astk_WN_r4,head_e1_hold40}, intel2:/srv/opentallas-scratch2/claude/codex-qwen/head_e2_keep/kv3_head_eighth_e2__285.12x285.12.
Results (signoff.py, all DRC 0 / ant 0, clock PASS under the hard-core latency contract, none SIGNED):
- head_eighth 216 (v3.8x, M7): TT setup e0 +25.3, e1 +36.6, e2 +1.6, e3 +46.3, e4 +10.1, e5 +15.9, e6 -12.1, e7 -25.0;
  FF hold -4.3..-7.5 on all 8; face_guard FAIL e0/e2/e4/e6 (RTL), PASS e1/e3/e5/e7. Kits: intel2:/srv/opentallas-scratch2/
  claude/kv-g3/cores/kits38x/kv3_head_eighth_e{0..3}__216x216, localhost:/srv/opentallas-scratch/claude/kv-g3/cores/kits38x/
  kv3_head_eighth_e{4..7}__216x216 (signoff/signoff.json, views/). Not yet collected into results/ / ref_tile views.
- kv3_pv_pair: NOT SIGNED (FF hold -10.75, DRV, face_guard; clock check was pre-contract) views abstract_only (b494c0dd31).
Done this session: signoff.py hard-core latency contract (COORD ruling 1, test_signoff 22/22); kvs_pc 833 ps labelled
assumption (ruling 4; HBM period asked of KV-G3, no answer yet); RTL ruling 2 WIP 229adce8f2: frontq PORT_REGS=1
(0 cycles; miter PASS 6000 edges, mutant FAIL) and ktree_lk PORT_REGS=1 (g_f +1 edge fault path; bench PASS, mutant
FAIL) — opt-in, defaults unchanged, NOT yet wired into the core kits. (Note: frontq mutant shows port0 unchanged;
check genvar slice in the mutant before relying on it.)
Next: (1) collect the 8 head 216 + 3 Codex runs (collect_core.py -> results/ + ref_tile views); (2) ruling 3: compare
head_e1_hold40 FF hold vs the -4..-7 ps here; if it closes, make FF-hold margin the default core recipe; (3) wire
PORT_REGS=1 into kv_core_rtl.py head_eighth members (+ KV-G3 partition binding, price g_f +1 for e0) and rebuild kits;
(4) e6/e7 TT setup -12/-25 at 216 (review timing paths); (5) pv_pair/kvs_pc/ectlk/astk reruns on v3.8w/x geometry (route goal).
OWNER?: kvs_pc HBM clock period / CDC SDC vocabulary (KV-G3); PORT_REGS adoption in shared leaves (S81 ref tiles bind the
same r4.sv; defaults keep them unchanged).

### KVG3-WI
(no PARKED section — last 12 lines of the lane file)
# KVG3-WI (sub-lane of KV-G3): hub_Wi host-core pins (G0C 22 'no pins listed')
Branch claude/kv-g3-1024 in ~/wt/kv-g3 (commits by explicit path; KV-G3 merges). Scratch localhost:~/scratch/kv-g3/wi.
## Status
07:40 PDT: baseline G0 PASS 0 err / 1811 warn; G0C FAIL 22 (hub_Wi hard_cores). Host leaf elaborated (yosys, obsx decl-hoist reading aid). core_pins_hr.py first run in progress.
08:00 PDT DONE @366980c5d9 (claude/kv-g3-1024, not pushed): plan v3.8u. G0 PASS 0/1788w (was 0/1811w); G0C PASS 0 err 49/49 clean (was FAIL 22). 22 hub_Wi host cores pinned (core_pins_hr.py/post_v38u.py/run_v38u.sh), glue:* stay partition glue, 0 missing members. pytest tools/die_plan: 27 env failures (docker socket denied for bind yosys, verilator 5.050 -Wall, docker-only g2/forest tests), none touch qwen_kvsys files.

## CODEX notes
- DONE: hub_Wi core pins merged a7e29a44ac; no new job. Remaining broad KV binding/host hardening tracked under KV-G3.

### PART-CAP
## PARKED 2026-10-24 18:58 PDT
Branch claude/part-cap-1024 @1381120171 (pushed; includes Codex codex/part-cap-1024 fef34728ce). Not merged to main yet (no README/report yet).
Live jobs (keep running; ot-run clients on localhost, logs ~/coord/part-cap-logs/):
- n14   intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n14          (WC route, tns100) in GRT
- n27   epyc3  /srv/opentallas-scratch/claude/part-cap/pc_rep_n27           (WC, tns100) in 3_4 place_resized
- n44   intel2 /srv/opentallas-scratch2/claude/part-cap/pc_rep_n44          (WC, tns100) in GPL (floorplan took ~7.5 h)
- n44_tt_tns10 epyc3 /srv/opentallas-scratch/claude/part-cap/pc_rep_n44_tt_tns10 (TC, tns10) in GPL (floorplan 37 min)
- n27_tt_tns10 (Codex, adopted) intel1 /srv/opentallas-scratch2/claude/codex-part-cap/pc_rep_n27_tt_tns10 (local PID 1888477) in DPL
Results (runs/*.json via results/arch/part_capacity_1024/collect.py RUN_DIR on the host):
- n1  77.7k placed: 41.5 min, peak 13.1 GB, DRC 0, TT +214.5 / FF +3.6 -> closes (SS -64 info)
- n4  305k: 3.6 h (48 thr, contended) / 2.8 h (16 thr), peak 38 GB, DRC 0, TT +164.0 / FF +1.55 -> closes
- n7  535k: 8.5 h (intel1 load ~540/112), peak 44.8 GB, DRC 0, TT +184.2, FF hold -19.5 (181 pins) -> FAIL hold
Findings: no memory wall (DRT peak ~85 GB/M cells, everything else <15 GB); DRT is the only stage using >10 threads;
floorplan/CTS/GRT repair_timing + 6_report are ~1-3 threads and dominate wall time; floorplan repair_timing -repair_tns 100
at the WC (SS) route corner is superlinear (n1 2 min, n4 20 min, n7 53 min, n27 3h41, n44 ~7.5 h; 26,049 violators at n44)
vs 4.4 min at TC + repair_tns 10 (396 violators). 400k cap origin: COORD 10-23 06:1x "L1-cap study" (closed-run census
or_capacity_runs.csv, never committed) -- no failure behind it.
Next: collect n14/n27/n44/n44_tt_tns10/n27_tt_tns10 when done; check n7 FF-hold cause (vehicle chain flops vs size);
write README (stage table, scaling fits, recommendation, plan_census.py seam/type table, knobs) and merge.
OWNER?: none.

### QC-A0
(no PARKED section — last 12 lines of the lane file)
  kits when it lands.
- coll_ftc g3i RESULT (intel2 .../g3/ftc_g3i, signoff.py): NOT SIGNED. TT setup -126.95 ps (2670 endpoints), FF hold -4.40
  (132), DRV slew 4165 TT / 3675 FF; spread TT 45.5 / FF 38.3 (PASS), insertion TT 214-260 mean 246; DRC 0, antenna 0;
  sdc_lint + face_guard PASS. Worst path = ft station hop crec_rx_s0 s0 -> s1 (N face -> (60,458), ~580 um): 884 ps of data
  incl. one 240-ps wire segment and an INVx1 at 306 ps slew. Images /tmp/qca0/g3i/*.png (congestion: hotspots at the E->S
  control fan and mid-left).
  ROOT CAUSE (flow vs plan): the plan budgets ft hops OVER THE TOP on M8/M9 (die_use ft_reserved, ft_budget, reach M8 1001 /
  M9 1013, stations every <= 750 um), but the partition kit routes everything on M2-M7 (MAX_ROUTING_LAYER M7; M4-M7 reach
  405 um). OpenROAD here has no per-net layer range (only set_routing_layers -signal/-clock). COORD decision (affects every
  ft kit on all dies): (a) ft kits route to M9 with M8/M9 global adjustment = 1 - cut_avail (die PG/spine share), or
  (b) stations every <= 405 um inside partitions (more stations -> more R8 pads / latency), or (c) die-level ft routing.
  Failed verdict kept; no follow-up route until decided.

### QC-TOK
(no PARKED section — last 12 lines of the lane file)
- QC-A0 is building the canonical capacity plan on claude/qc-a0-1024: codex/qc-capacity-1024 (406d3a497a + 72ece79138 +
  f553f73d91 landing) + ft_regs station sites off hard cores (ab490d1fbb) + OWNER-approved +1 station on the 6
  cbf_q0x_s2 serdes TX slots (routed hops 734-804 um with 4) + coll_ftc grid+sinks taps + A0 v7 taps.
  The +1 serdes station changes 3 lanes x 2 types -> needs the SAME rebind (owner: "do it in the same rebind").
- ASK 1: name the canonical bus_groups.json (+ the R8 landing recipe incl. CB16 pads) that your xt1 64/64+64/64 rebind used,
  so the committed r8/bus_groups.json + r8/qwen_compute_r8_landing.json digests match (main 24b2da3433 FAILS G0:
  landing digest e56a2f6f7e7e9337 != committed bus_groups c56f7e7abff4cabb; capacity landing f553 = 5b3a39e809083115,
  qcp_capacity_final_canonical bus_groups = 38322708f76c85be).
- ASK 2: I will post the regenerated capacity plan sha here; please rebind on it (or tell me the recipe + bind dir and I run
  it: base recipe /srv/opentallas-scratch/claude/codex-qwen/qcp_capacity_final_canonical/recipe.json) and re-run xt1 both.
- A0 +1 cycle (owner): priced in the compiler/R8 tables (kit t_out = bound +7, spec +6): needs your compiler/R8 table
  change; receipts results/rtl/qwen_a0_shifted_1024 (on claude/qc-a0-1024).

### S81-CORES
## PARKED 18:55 PDT (kits_repin sub-agent)
- Branch claude/s81-cores-kits-1024 @9fc976f89f (pushed). Kit inputs, reviews and results are under physical/die_plan/s81/cores/kits_repin/.
- Live jobs (ot-run, run_kit.sh route; signoff.py runs as the final step):
  - localhost:/srv/opentallas-scratch/claude/s81-cores-kits/c2/:
    - dsdv_svc_sx_hrow_c (= hrow r14)
    - ot_dsrom_su_hcpost_lane_pr_c (PATHFINDING, face_guard_continue)
    - dsfd_su_t_rxsf_c
    - dsfd_su_t_rxsb_c
    - ot_s81sl_vsw_c
    - ot_s81sl_vn_c
    - dsdv_eng_rr_e_c
    - dsdv_eng_rr_h0_c
  - epyc3:/srv/opentallas-scratch/claude/s81-cores-kits/c2/:
    - dsdv_eng_rr_h1_c
    - ot_s81sl_ve_c
  - Logs: <dir>.otrun.log on localhost, plus KIT/run_route.log and KIT/signoff.log.
- Results:
  - vq: SIGNED (CODEX r12, main 24b2da3433).
  - hrow r13 NOT SIGNED: TT -50.12 / 233 endpoints, on role[1] -> decode fanout tree. FF +8.45. Spread 63.7. Clock balance gave insertion 268 (PASS). DRV 1 slew. Post-GRT estimate +0.5 -> RCX -50, so r14 adds setup margin 40 and a post-GRT setup repair.
  - CODEX r10: NOT SIGNED.
  - vs: PATHFINDING (OWNER).
  - c1 (superseded by c2) FAILED:
    - vsw, rxsf: SYNTH_MEMORY_MAX_BITS (now fixed).
    - ve: wrong spec (now the r5 spec).
    - hcpl: face_guard FAIL.
    - rxsb: face_guard FAIL.
    - vn: stopped as a duplicate.
- Known face_guard RTL blockers (no waiver; OWNER/RTL decision):
  - hcpl o[15:0] constant (ot_dsrom_su_hcpost.sv:129 o <= {hi,16'd0}), plus the sticky fault self-loop.
  - rxsb o_r[31] shares a tie net (constant bit). c2 rxsb will stop at face_guard.
- Pins: closed-view pins are taken from the closed LEF edge rects. The inputs/core_pins tables (largest-rect centre) differ by up to 1.37 um on 13..362 pins/core (kits/*/pins_snapped.json). The plan integrator should know.
- Next: collect c2 with collect.py (signoff authoritative) and iterate on failures, each after a recorded review. eng: verify macro placement and half-cycle SDC in synth/floorplan logs.
- OWNER?: hcpl/rxsb constant output pins (drop from the plan, or allow a const class); vs face_guard.
- Owner rulings for next steps (recorded 19:00, not yet acted on):
  - (a) Internal core bundles of 405-472 um get fixed internal stations; R3 reach applies inside cores.
  - (b) The 13 reach-fail leaf types get x-mirrored pin variants of vn/vq/vs as new core views.
  - (c) Reset: core kits take reset as a synchronous timed input (one root 2-flop synchroniser, pipelined relays every <=405 um at equal depth, no recovery waivers). The current kits_repin SDC models rst as async with recovery checked; the generator must change before the next rekit.

## PARKED 2026-10-24 18:59 PDT (S81-CORES main lane)
- Branch claude/s81-cores-1024 @ eee33cf766 is MERGED to main as e94d9bb329 (plain recipe).
  - Gates: G0 PASS and G0C PASS 174/174 (0 errors), re-run on the merged tree.
  - Plan diff vs main: only the leaf/svc/eng/pvso_entry hard_cores and their ft_slots.
  - Top latency 118439 -> 118442 (coordinator accepted this as S81 decision (a)).
  - tools/die_plan pytest: test_bind fails here (yosys/docker env). My files (gen_plan_v4 + s81 outputs) are not read by those tests.
  - Worktrees removed: ~/wt/s81-cores and ~/scratch/s81-cores/basewt.
- Live jobs (main lane): none. All opt4 searches are finished.
- Sub-agent kits_repin is parked separately (section above).
  - Branch claude/s81-cores-kits-1024 @9fc976f89f, NOT merged.
  - c2 runs keep going on localhost and epyc3 at /srv/opentallas-scratch/claude/s81-cores-kits/c2/.
  - vq is SIGNED. hrow r13 is NOT SIGNED (TT -50.12).
- Results: GEOM self-review at results/geom_review/s81_cores_1024/.
  - 13 leaf types FAIL reach: t5 t6 t8 t11 t15 t28 t30 t36 t40 t49 t50 t54 t72.
  - Internal core bundles are 405-472 um.
- Scratch tools are kept: ~/scratch/s81-cores/{regen.sh, plandiff.py, leaf/opt2.py, opt4.py, pick.py, mkalt.py}, plus regenbase (the no-core baseline).
- Next, per coordinator rulings (14:xx):
  - (2) Add fixed internal stations on core-core bundles over 405 um. R3 applies inside cores. Model this in core_conns and the kit specs.
  - (3) Build x-mirrored pin variants of vn/vq/vs for the 13 reach-fail types (new core views). Then add a "variant" choice to the generator candidate search.
  - Change the kit generator for the reset rule (BRIEFING OWNER DECISIONS #2: synchronous timed reset input, no recovery check). The kits currently model reset as async.
  - Collect the kits_repin c2 results; only SIGNED counts.
- OWNER?:
... (3 more lines in lanes/S81-CORES.md)

### S81-HEAD
(no PARKED section — last 12 lines of the lane file)
- 2026-10-24 18:53 PDT (Claude) after the second resume. Owner decisions (BRIEFING 10-24 18:4x) are applied to the head elements.
  - Status: main 9b1a4d16e0.
  - Done already: builder committed, floorplans reviewed, best_key pipeline register (bundle pk_q).
  - Reset rule: each rebuilt element takes rst_n through one local relay flop (synchronous delivery), and its flops then use timed recovery/removal. Bench CV=1 ALL PASS.
  - elemA c7 routed: NOT SIGNED.
    - Clean checks: DRC 0, ant 0, pin audit 458/458, face_guard / sdc_lint PASS.
    - TT setup -71.32: rst_n recovery only. The clk group is +159.9, vclk +500.
    - FF hold -43.21 (150): output face flops arrive at 122 ps FF against the fixed 250-ps vclk, because the early tap of 200 is too large at FF.
    - Pin-register insertion TT mean 214 / FF 138, spread 54.
  - elemB c2 routed: NOT SIGNED. TT -3.26 (2), FF hold -36.78 (149 outputs), TT slew 5, TT insertion 199.5 (< 210).
  - Relaunched: elemA c8 (early 160 + reset relay) and elemB c4 (early 120 + reset relay), both full route on intel2 scratch2 .../s81-head/elemA_rb/.
  - Margins: INFO only, per decision 3.

### S81
## PARKED 2026-10-24 18:56 PDT (coordinator move to rtx-pro)
Branch claude/s81-p11-1024 @71bed19a4a (worktree ~/wt/s81-p11), pushed. Unmerged on it: af0bfc6361/a6846d534e (s0 move +
revert, net zero), 71bed19a4a WIP pipelined reset (NOT merged: not kit-tested). Everything else is on main (90fd169e93, 1ce2ec31aa).
Live jobs: NONE (all g3k5 place/CTS finished; review watchers stopped). No containers of mine.
Results:
- g3k5 frame kits (main 1ce2ec31aa + ft 0.16; counted reset): all 7 placed + reviewed (review dir
  localhost:/srv/opentallas-scratch/claude/s81/review/g3k5/<type>/review/place.png, <type>.rev.txt). reg-reg > 750 = 0 on 5/7;
  h9_r0_p1 / h9_r0_p3: 2 b u_s0.st -> u_t0.c0 905 um (OPEN, see 14:50). Face pins p90 8.3-9.5 um, max density <= 0.56.
  Kits: localhost/epyc3 /srv/opentallas-scratch/claude/s81/g3k5, intel1/intel2 /srv/opentallas-scratch2/claude/s81/g3k5.
- CTS (goal cts, evidence only) TT WNS: h9_r2 -56.5 (ROM c13_6 -> seq s13), h10_r2 -75.1 (ROM c11_0 -> seq), h10_r1 -256.8
  (arst_n; n13->n12 -240.6), h10_r0_p1 -851.4 (arst_n; xa relay -> bs2 -367.9). See 15:25 for causes.
- Pipelined reset (OWNER RESET RULE): tool + S81 plan switch on 71bed19a4a (D = 6 relay stages + face flop, 16 taps per frame,
  release = arst_n + 7 cycles in each frame). pytest all pass, G0 PASS.
- hcore WPRE re-kit sub-lane (S81-HCORE): stopped by the 15:00 session limit after synth (face_guard PASS 1212/1212 on yosys +
  1_synth.odb); worktree /srv/opentallas-scratch/claude/wt/s81-hcore, branch claude/s81-hcore-1024 (state in its lane notes, if any).
Failures: none new beyond the CTS numbers above.
Next steps (in order):
1. Kit-test the pipelined reset: regenerate the 7 frame kits (g3k6) from 71bed19a4a, check ORFS synth keeps 16 x 6 chains
   (yosys keep), reset_taps.tcl hop report (<= 405), place + review; then merge 71bed19a4a. Die-level: ONE root synchroniser per
   die region + inter-partition reset relays (equal depth to every tap die-wide) are still to be planned (plan/bind/die top).
2. COORD 18:55: turn the DS BK drain sink ON in the S81 die profile/bind (TOK-DS owns compiler + legacy bench; lanes/TOK-DS.md);
   price the v4.8 R8 landed-bundle pads (up to ~13 cycles) in the latency table.  NOT started.
3. Early ROM core taps (~150 ps early; ROM addr setup ~30 ps) for the ROM read path; tap-tree / macro-pin latency skew
   (314-375 ps vs 250) in CTS; h9_r0 u_s0.st -> u_t0.c0 905 um (RTL stage on c0/c1 or move t0).
4. S81-HCORE: its r3 re-kit FINISHED routing on intel2:/srv/opentallas-scratch2/claude/s81/hcore/ot_s81c_attn_hcore__157.68x259.2_r3
   (6_final.*, PIN_AUDIT PASS 1214/1214); signoff.py NOT run yet, review image not checked -> run signoff, record, commit on
   claude/s81-hcore-1024. epyc2 old WPRE dir: both /srv/opentallas-scratch/s81/hcore/..._wpre (ROOT disk) and
   /srv/opentallas-scratch2/claude/s81/hcore_old exist -> verify the copy, then delete the root-disk one.
OWNER?: none new (ROM 833-ps read path: raise only with CTS/route numbers after early ROM taps).

## Run dirs
- epyc2 (ot-run oth-ubuntu-80375-1792850176): /srv/opentallas-scratch/s81/hcore/ot_s81c_attn_hcore__157.68x259.2_wpre route gate
- recovered old scratch: intel2:~/ot-scratch/s81/recovered/{s81-p9-fc-1023,stw-s81d-tok,stw-s81c-cap30,tokj-1023,core-s81-1023,codex-s81-cap30-framecal-1022}, intel1:~/ot-scratch/s81/recovered/{stw-s81d-tok,stw-s81c-cap30,core-s81-1023}
- localhost:~/s81p10/kits/* (place)
## Results
- 07:55 PDT main 4b7b2b3e64 (CP1-R10 sdc_lint/face_guard) merged into claude/s81-p10-1024 @16a1a9a870 (r8.py/test_r8/test_check kept ours: main's df641549 merge DROPPED the v4.8 LANDED BUNDLES r8 rule + tests; my branch restores it; die_plan pytest all pass). COORD: please note main currently lacks r8 LANDED.
- G3: old kits (~/s81p10/kits) = PATHFINDING ONLY (place reviews above; old routes stopped). Regenerated kits g3k2 (gate kit gen: sdc_lint 0 err, SDC now -max + output -min 0): route gates via ot-run (run_kit.sh: sdc_lint -> synth -> face_guard -> route):
  localhost /srv/opentallas-scratch/claude/s81/g3k2: h10_r0_p1, h9_r0_p1, h10_r1 | intel1 /srv/opentallas-scratch2/claude/s81/g3k2: h9_r0_p3, h9_r1 | intel2 (scratch2 same path): h10_r2 | epyc3 /srv/opentallas-scratch/claude/s81/g3k2: h9_r2. ot-run logs localhost:~/s81p10/g3k2_logs/
- S81-HEAD gaps: sub-agent S81-XDIE working in ~/wt/s81-xdie (claude/s81-xdie-1024): reserve pair EN2/3+WS2/3 all dies, in-band host rule, 604-b s_7N_LP->seqhost question.
- G3 place review (own; probe reg-reg>750 / pin->face-reg p90 / render): h9_r2 PASS (0 over, p90 9.13um), h9_r0_p3 PASS (0, 8.33), h10_r2 PASS (0, 9.19); route gates launched localhost (docker s81p10_<type>_route). Note GPL routability 'could not reach target' (RUDY ~19-20% tiles) on all -> judged at GRT.
- entry replay: fork sub-agent running fc31 replays + eks_7N TORN root cause.
## OWNER?

## From S81-CORES (2026-10-24, lane file ~/coord/lanes/S81-CORES.md, branch claude/s81-cores-1024)
S81-CORES owns the hard-core definitions of the G0C hard_cores failures (74 ot_s81sl_leaf__t*, 16 svc_*, eng__t1):
edits limited to gen_plan_v4.py NONFRAME_HC["leaf"/"svc"/"eng"] (+ core placement helpers), inputs/core_pins/<new cores>,
cores/<leaf|svc|eng>/*, a core_conns.json sidecar, and die_plan.json regenerated by run_v4.sh (only those types'
hard_cores[] should change). Please do not edit those NONFRAME_HC entries; if you regenerate die_plan.json, tell me
(lane file) so we rebase. I will post here before merging any die_plan.json change.

## NOTE from TOK-DS (2026-10-24 06:57 PDT) -- recovered old-fleet inputs (old /mnt/old-nvme0 wiped 07:03)
COORD copied to /srv/opentallas-scratch/claude/recovered-1023/ (same relative paths): intel1 + intel2: stw-s81d-tok/fc30 (fc30 cuts/kits, cut_3S_ctl sim),
stw-s81c-cap30/gen-main (cap30 GEN bind/plan/land); intel2: s81-p9-fc-1023/fc31 (fc31 die.v, port_bind, bind_case).
TOK-DS added on intel2 (if the copy finished before 07:03): s81-p9-fc-1023/{K_monfc31,out_monfc31} (built fc31 cut_3S_ctl MON sim; idle run never completed),
tokj-1023/lower (fc30 entry regen: job15/17/22 FAIL only on eks_7N KS word TORN 2307/2308), stw-s81d-tok.ep5/layers (root30, fix, entry_jobs_fc30, layers_fc30).
epyc3:/srv/opentallas-scratch/claude/stw-s81d-tok = full ep5 layers+fc30 copy (TOK-DS). No need to rebuild cap30.
S81-CORES 2026-10-24: I am taking the svc hcore (ot_s81c_attn_hcore) TT -25.29 ps re-close as part of the svc core
kit work (your step 3) -- please drop it from your list unless you already launched it (then say so here and I stop).
Finding: the vp closed view (closed_archive s81sl_vp9_fb LEF/LIB/GDS) is LOST with rtx-pro; only its pins json survives.
S81-CORES 2026-10-24 (correction, per coordinator): I do NOT take the svc hcore -25 ps re-close; S81's WPRE fix 89c161bd5 + route gate on epyc2 stands. I will consume its result. My scope: hard-core definitions for the 91 G0C fails.
... (156 more lines in lanes/S81.md)

### SIGNOFF
(no PARKED section — last 12 lines of the lane file)
- Both closure_loop verdicts list job_spec.verdict.macros = ot_rom_4096x274_m8: memory_macros (elem_q) and memory_macros_v2 (bf_col).
  Each of those dirs has _tt/_ff/_ss.lib, and tools/closure_loop/macro_views.py feeds them to corner_sta --macro. So at spec level the ROM was
  timed with its lib. This is NOT verifiable at run level: routed DBs and logs were lost. The elem_q record also has a ref_gate warning
  (physical/abi3/gen/dsrom_q_cl_signoff.sdc missing at ffacf68cd).
  -> Treat both as UNVERIFIED, not invalid. A re-run through current signoff.py (missing-macro-lib reject) is required either way.
- The untimed-ROM problem GEOM-REVIEW found is in the G3 *frame kits* (generator, owned by S81), not in these old records.
- ELEM-S81 13:30: legacy gunit routes re-routed at closed commit, then signoff.py tt,ff (main e7c09034ae): 0/9 SIGNED.
  - l5f fails only sdc_lint (ref_tile Tcl SDC + 833.333 period).
  - l0r and l4r: also face_guard (1 shared bit each).
  - l0/l1/l1c/l2/l3/l4: also FF hold -12..-22 and face_guard dropped/shared; l1c TT -18.
  - The std overlay was skipped on all 9 (no IO vclk in ref_tile SDCs). That is a signoff.py gap for ref_tile kits: should it be NOT RUN rather than silently skipped?
  - Records: <host>:/srv/opentallas-scratch/claude/elem-s81/hc/<kit>/signoff_tt_ff/signoff.json. Canonical rekit in progress (ELEM-S81).

### TOK-DS
## PARKED 2026-10-24 18:57 PDT
- Branch claude/tok-ds-1024 @81f6107a62 (pushed). main has everything up to 9721734fee (gated). 81f6107a62 is WIP, NOT gated, NOT merged.
- Live jobs: none (epyc3 has no TOK-DS processes). Scratch: epyc3 /srv/opentallas-scratch/claude/tok-ds/{fc31,bk,bk2,verify_sink}; verify_sink = detached worktree of 81f6107a62 + Codex vstop/dsdv_bk_g with BK_DRAIN_SINK default 1 (verification only, never commit).
- Results (merged): BK-sink HOST-cut layer control L0/L2/L14/L20 PASS_CUT_COMPONENT + mutants CAUGHT (results/token_pass/tokds_bk_layers_1024); components 4/4 PASS; composition 1u AR 802.6 / MTP 2,564.0 tok/s (~30% measured-current), MU AR50 40,130 / MTP6 15,384 (model); data cuts 0S/0N/7 fault-free but 0 checks.
- WIP (per COORD ruling 18:55, sink canonical): dv_layer_compile.row_ctl_events drops V CTL rows whose template is an addressed BK drain (p[7:0]=u_bk_sel uid, p[10:8]=1) -> internal BKDRAIN event; lower_bk benches no longer expect the forwarded drain (OT_BK_LEGACY_FWD=1 = old record); tb_dsdv_bk_wrap fwd_b no longer expects slot-0 drain (+define+OT_DSDV_BK_LEGACY_FWD = old record).
- NEXT: (1) in verify_sink run rtl/dsrom_sys/s81_dv/unit/bk/test/run_bk_bench.sh sel/col (canonical expect, must PASS + mutants FAIL) and with +define+OT_DSDV_BK_LEGACY_FWD on main RTL (old record must reproduce); lower_bk bench (run_bk_layer.sh) same two ways; tools/s81_dv/test_dv_cut_replay.py. (2) recompile L0/L2/L14/L20 on tree_fc31 with 81f6107a62 (tools/s81_dv/tokfunc/fc31/compile_fc31.sh into a NEW run dir), prepare_split_control, replay on the BK-sink binary (codex-s81/bk_drain_layer/out/obj) WITHOUT --bk-drain-sink (bk_layers.sh with BK_SINK unset, new out root); expect L2/L14/L20 PASS. (3) merge after (1)+(2) pass. (4) then compiler gaps G-COMPILER-ROWS / G-NORMALIZE-SO (data-cut output checks: off-die RD all-gather, 16-slice NX/XQ norm exchange) = main token-pass blocker.
- Waits on S81: plumb BK_DRAIN_SINK=1 through dsdv_bk_sel/dsdv_bk_col into the profile/bind (canonical RTL default); until then canonical-expectation BK benches FAIL on main RTL by design.
- OWNER?: v4.8 R8 landed-bundle pads not in any latency table (up to ~13 cyc on x/xo/xring/sid lanes).

### TOK-HBM
## PARKED 2026-10-24 18:56
- Branch claude/tok-hbm-1024 @909ec66a01 (pushed). Last main merge 681cc61dab (= @a46de47f7b); 909ec66a01 (transport_gate WIP) NOT merged.
- Live jobs (mine): intel2:/srv/opentallas-scratch/claude/tok-hbm/ld/t_qw_chain_r0, t_qw_chain_r5 (pids 150727 150729 ; exit.txt on finish).
  All epyc2 runs finished; Codex jobs adopted and collected (prog_r8_leafslice build PASS + SU31 diag run; hc_r8 gate).
- Results: XDIE 10/10 + AR-step DS/Qwen PASS; leaf-split slice rec2_kq 287/287 + ls_ds_l14_x4 3822/3822 PASS;
  HC native unit gate XRD=XRU=10 PASS (24/24 mixes + 4/4 outs, HC_MIX 1029, DING2 mutant caught; my rerun
  intel1:/srv/opentallas-scratch2/claude/tok-hbm/hc_r8_t0fix after Codex run infra FAIL).
  Price (P7+leaf-split): DS 1885.7 tok/s (530.3 us), Qwen 942.7 (1060.8 us); SU advance exposed: 1561.2 / 893.4.
- Failures: layer benches FAIL: DS L14 640/1991, _x1 1305/3234, _x2 38/4217; Qwen L0 r0/r5 1424/1424; prog_r8
  padded-programme SU31 diag still FAIL 640/1046 (all 8 banks; fr_SW fault 5722).
- transport_gate (r18h5): HC XRD/XRU bound 0 (need 10, pads 1/2/0/1 + 1/0/2/1, RAW0 185), HC launch skew 16; SU cfg
  we/bank 26 short; SU cmd legs 9-19; SU bank read RT = READ_RETURN 22 OK (write-side trace gap for odd banks);
  SU calendar relation slot-lg-rq per bank -1/-3/6/6/-1/-1/3/3 -> the remaining SU suspect.
- Next: equalize SU calendar relation (pad lg_read/write per slice + rq per bank) on the prog_r8 die, rebuild, rerun
  SU31; then HC die bind (pads + XRD/XRU=10) and HC_MIX replays re-emitted with RAW0; hand transport_gate to HBM-ARCH
  as the B2l native-bind check.
- OWNER?: none new (B2l native bind accepted 18:47).

### TOK-QW
## PARKED 2026-10-24 18:59 PDT
- Branch claude/tok-qw-1024 @5b89da34d8 (pushed, clean). Merged to main: 40e086ead0 + d7bf8a8ba0 (record results/rtl/tokqw_1024).
  5b89da34d8 (tools/qwen_tokfunc/stage_stg_die.sh) NOT yet merged.
- Results (main 8a5d1f3dab assembly, readset == current main): stg PASS 527/527; head PASS 123/123 + 131/131, bmut3 caught;
  attnret PASS 98 == 98 (ddwin/ddbase caught); xhead PASS 4/4 + 10/10 mutants (go_lag -3 / xpf 4 after widening OT_XH_GO_MIN
  to -8). Compose with QC-TOK tp8/xdie/ovl4u + carried xt1/ctx4u/kv/chain: 1u 271,106 cyc = 4,428.1 tok/s, 4u 11,844.1.
  PRICE HELD: IMAGE CAPACITY, TILE DELIVERY, RoPE ROW producer->consumer. xdie_bound F5/F6/F7 have opt-in fixes on main (Codex).
- Failures / not run: stg on the BOUND s8 slice row NOT RUN (vehicle still compiling).
- Live job (mine): intel2 ot-run unit oth-ubuntu-2336359-1792869646 (local ot-run client pid 2606671, log
  localhost:~/wt/tok-qw-logs/s8cal2.otrun.log), script /srv/opentallas-scratch2/claude/tok-qw/s8exp/s8cal2.sh: make -j24 of
  tb_qfd_dv2 FACE 3 obj_n12 (35/36 units done, last Vtb_vm_classes_8.cpp ~6.6 h in), then slice + vec calibrate
  (die/build/slice_calibrate.out, calibrate.out, timing.txt). Leave it running.
- Next step: when s8cal2 shows rc=0 on both calibrates, run on intel2:
  bash /srv/opentallas-scratch2/claude/tok-qw/s8exp/stage_stg_die.sh /srv/opentallas-scratch2/claude/tok-qw/s8exp
  /srv/opentallas-scratch2/claude/tok-qw/s8exp/stg_result.json /srv/opentallas-scratch2/claude/tok-qw/s8exp/pos_runlist.txt --par 24
  (via ot-run; fixtures already in s8exp/stgdie/fx) -> stgdie/result.json; commit to results/rtl/tokqw_1024/stages/stg_die,
  merge, recompose. If calibration fails: record it as a FAIL finding (bound s8 row vs slice2 ages).
- RUNROOTs: intel1 /srv/opentallas-scratch2/claude/tok-qw/{r1024,recovered,xdie_bound} (moved off root fs; symlinks in ~/ot-scratch/tok-qw).
- OWNER?: see OWNER? section (OBS1_COMPAT=1 + F7 ROM pair adoption on bound top; F1 TXDP bind; KV r17 archive regeneration).

### TRIAL-HBM
(no PARKED section — last 12 lines of the lane file)
- Branch: none committed by me (brief: no git in ~/wt/trial-hbm; the lane owner commits). Uncommitted files in ~/wt/trial-hbm:
  tools/die_trial/{hbm_b2_top.py,hbm_b2_power.py,hbm_b2_ir.py,hbm_b2_render.py,ir_run.sh},
  results/die_trial_1024/hbm_b2/top/{README.md,pg_stats.json,die_io.json,real_views.json,trial_flow_summary.log},
  results/die_trial_1024/hbm_b2/ir/{README.md,power_map.json,cases/*.json,*.png}. -> lane owner: commit + push these.
- Live jobs: NONE (all finished/stopped; no thbm_* containers on epyc2/epyc3/intel1/intel2).
- Results: top: 88/88 exact placement (odb), 0 overlaps; gen_phys %g origins refuse 23 (tool bug); check_power_grid VDD/VSS PASS;
  M7-M8 vias 6.197M/6.182M; GRT FAIL overflow 394 (taps under PHY_N + UCIe keep-outs); DRT NOT RUN.
  Power est 642.7 W (SM 395 W; SerDes 12.1 W/mm2). IR exact windows rail sum vs 35 mV: hub 12.7 PASS, PHY+corridor 29.6 PASS,
  SM 47.0 FAIL (interior 31.7), NW_io SerDes 146 FAIL, spb0 SerDes 203 FAIL. Full die exact NOT COMPLETED (pdngen >4h);
  coarse x4 done (880 mV) but invalid as absolute (5-8x over exact windows; relative map only).
- Big outputs: intel1:/srv/opentallas-scratch/claude/trial-hbm/top/kit/die (die_top.odb/def), intel2:.../ir/w_*, epyc3:.../ir/full_s4m, full_exact.
- Next step: exact full-die IR with the grid written as DEF special nets (no pdngen macro grids); plan fixes for F3/F4 (PHY outline, taps out of keep-outs, SerDes at edge); SerDes own supply/dense PG.

### TRIAL-QK
## PARKED 2026-10-24 18:56
- Branch claude/trial-qk-1024 @be5dc2305e (pushed; not yet merged to main).
- Live jobs (own; leave running):
  - intel1:/srv/opentallas-scratch2/claude/trial-qk/qwen_compute (QC v3.8s route_g0, container trialqk-route_g0-1445030, ot-run pid 1635605 on localhost): GRT DONE (ovf 4659: M4 980, M5 2086, M6 227, M7 565, M8 456, M9 345; 4 h 06 m), writing grt_g0_wl.csv/heatmap -> EXIT line.
  - intel1:/srv/opentallas-scratch2/claude/trial-qk/qwen_compute_ir_t4 (QC IR, 138 um tiles, 512 GB, trialqk-ir-3298221): PDN done 1549 s, PSM running (165 GB at 13:5x).
  - localhost: python die_trial.py build of the QC CAPACITY plan (codex/qc-capacity-1024 @72ece79138, plan sha 33c214a3) -> /srv/opentallas-scratch/claude/trial-qk/qwen_compute_cap (log build_qwen_compute_cap.log; local process, not fleet).
  - stopped (own): intel2 trialqk-ir-759266 (old 69 um QC IR, superseded; STOPPED.txt in its dir).
- Results: results/die_trial_1024/qwen_kvsys (summary.json, die_trial*.json, ir.json, PNGs, ILM TT/FF) — KV gate PASS on padded clock (nominal TT/FF, seam max 33/29 ps), GRT ovf 3349 only in hub_Eo/hub_Wo 1118-bit station gcells, IR VDD 67.4 / VSS 71.5 mV worst; INFO 5 % OCV: 544-571 ps seam skew (root split through hub row). results/die_trial_1024/qwen_compute: QC v3.8s clock/pad + Manhattan hop report: seam max TT 34 / FF 52 ps (0 > 80) but hold window (insertion_tol 40) negative on 27,474 hops (FF skew > 40) -> FAIL; INFO OCV 5 %: 854 ps.
- Failures: own KV IR 128 GB EXIT 137 (Codex 256 GB retry used instead); old QC IR (69 um tiles) pdngen > 4 h single-thread -> replaced.
- NEXT: (1) when QC route EXIT: rsync route files to localhost qwen_compute + symlink into qwen_compute_clkpad, report (--g2 physical/die_plan/qwen_compute/g2_report.json --ir-dir ..._ir_t4 after irsum), render, Read images, summary.json; (2) capacity plan: run_clock.sh + clock_pad_probe + run_route_g0.sh 192 16 on intel1 + ir --tile-pitches 4 at 512 GB; (3) share QC findings with QC-A0/HBM-ARCH; merge via flock per BRIEFING.
- OWNER?: plan seam skew rule 80 ps vs kit hold window insertion_tol 40 ps: die skew 40-80 ps passes the seam rule but breaks the kit hold contract (QC FF). Which binds?
- Findings already shared: KV-G3, DIE-STA, HBM-ARCH lane files (FROM TRIAL-QK sections).
  (capacity build pids on localhost: /usr/bin/time 2331863, python 2331864)
- 18:57 capacity-plan build DONE exit 0 (5 m 18 s, 2.6 GB) -> localhost /srv/opentallas-scratch/claude/trial-qk/qwen_compute_cap (plan sha 33c214a3); no clock/route launched (parked).

### TRIAL-S81
## PARKED 2026-10-24 18:56 PDT
- branch claude/trial-s81-1024 @ c2713abad0 (pushed; = main 7d75427c59 + WIP: die_trial.py fabric-latency + irwin, fabric.py
  S81 core_pins fix, results/die_trial_1024/{s81,s81_head}/trial_wip.json). NOT merged (WIP, not gated).
- LIVE jobs (mine, ot-run from localhost; leave running, collect):
  intel1 /srv/opentallas-scratch2/claude/trial-s81/s81/fabric_TT and fabric_FF (s81 die STA budget mode, 2.99M flops, 2.39M nets)
  intel2 /srv/opentallas-scratch2/claude/trial-s81/s81_head/fabric_TT and fabric_FF (head: GRT done 351 s, overflow 0; STA RC stage)
  local ot-run clients: pids 2212244 2213653 2214583 2215541; logs ~/coord/part-cap-logs/trial-s81*_fabric_{TT,FF}.log
  Result files: fabric_TT/sta_grt_TT_max.wns, fabric_FF/*FF_min*; summary.json.
- RESULTS so far:
  GRT on abstracts: s81 455k nets overflow 0 (3m16s/18.8 GB; still 0 at 2.5x less ft share); head 33.6k nets overflow 0 (48 s/5.6 GB).
  Die H-tree (nominal, gate rule): seam skew s81 TT 50.9/FF 43.8 ps PASS; head TT 81.9 ps FAIL(>80)/FF 78.8; in-partition tap
  spread ~100 ps (s81 104.5 TT, head 96.5); insertion s81 6.16 ns TT, head 3.81 ns TT. OCV3% INFO: s81 372, head 224 ps.
  IR (window PDNSim, 0.15 W/mm2, die C4 150 um lattice): interior worst 30 mV (4.3% of 0.7 V) both dies; over SerDes IO
  windows (no power bumps) worst 235 mV s81 (WS0/WS1) and 270 mV head (HOST0/HOST1/WS0) -> FAIL: needs power bumps/
  PHY own supply in IO windows (or the window load is wrong: PHY power not modelled separately).
  Full-die PSM: head (Codex c2) SEGFAULT in psm::IRSolver::solve at 119 GB after 2.4 h -> full-die PSM not viable; window PSM.
- FAILURES/notes: die_sta.py per-tap generated clocks did not finish >4 h (stopped; FYI DIE-STA). I used
  'pkill -u ubuntu -f run_sta.sh' on intel1/2 once (could have matched others' run_sta.sh; none known).
- NEXT: collect fabric TT max / FF min WNS (gate TT setup / FF hold 60/25); render IR window maps + Read them; write
  results/die_trial_1024/<die>/findings.md + geom_review entry; share with S81/S81-HEAD/DIE-STA/PART-CAP; merge.
- OWNER?: (1) head die-tree seam skew 81.9 ps TT > 80 -> accept shared seam drops (Codex proposal) or tighter tree;
  (2) power bumps over SerDes IO windows (IR 235-270 mV there).

### TYPE-DEDUP
(no PARKED section — last 12 lines of the lane file)
Bound kit counts: QC 56 plan types -> 80 bound modules; KV 49 -> 76 (S81 bound tree lost, summary stale).
KV hg cN rotating-chain lockstep miter (results/type_dedup/kv_hg_cn_miter): PASS 200k cycles, mutant caught.
## Proposals (owners decide; nothing applied to live plans)
S81: adopt the 13 merges (or derive port order from type order XOR mirror in gen_plan_v4); leaf ft-population is the
real driver (74 types / 66 populations) -> hard-core leaf, standard slot grid, or station strips.
HBM: mirror-symmetric windows on the listed buses -> 60 -> 53. KV: rotating cN chain (+ R8 acal/o_kg decision) ->
hg kits 5 -> 3. QC: full-width rotating encodings for narrowed-port variants, chain-end ring lanes -> 80 -> ~56 kits.
## OWNER?
- KV: R8 acal/o_kg per-row added delay (1/-1/-3/-5/-7) blocks any hg_v1 merge: make uniform, or exempt as boot-static?
- S81: superset ft slots are tie-offs (forbidden) -> leaf type count needs a lane re-pack decision.
## Scratch
localhost:~/scratch/type-dedup/dd_s81/{die_plan.json,dedup_provenance.json} (the 161-type S81 copy); rest removed.

