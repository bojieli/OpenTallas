# OpenTallas design methodology (FROZEN v5.1, 2026-10-26 18:5x; v5.0 18:4x; v4.9 17:3x; v4.8 17:4x; v4.7 17:3x; v4.6 17:0x; v4.5 16:5x; v4.4 06:39; v4.3 06:33; v4.2 06:15; v4.1 06:11; v4 06:07; v3 05:58; v2 earlier 10-26; v1 2026-10-24 21:40 PDT)

One rule set for every lane (Claude, Codex, sub-agents) on all four release dies (S81, Qwen compute, Qwen KV, HBM).
Build to these rules; do not re-derive them per lane. Precedence: latest OWNER decision > this file > AGENTS.md >
tools/die_plan/README.md > lane notes. Where sources disagree, the conflict is listed in section 9 and the rule
stated here applies until the coordinator rules. Changes to this file go through change control (7.11) only.
Sources: B = ~/coord/BRIEFING.md "OWNER DECISIONS 2026-10-24" #n; A = AGENTS.md (origin/main); P = tools/die_plan/README.md
(origin/main a11334b98); M:<name> = owner memory record. Dates are 2026.

## 1. Architecture

1.1 Static cycle schedule: the compiler assigns every compute, memory-port, link-slot, buffer and visibility cycle.
    No credits, ready-driven issue, arbitration or backpressure on die. [M:static-cycle-scheduled 10-14]
1.2 Flow control (credits / elastic buffers) exists ONLY at off-die boundaries: HBM PHY, SerDes/d2d (incl. cross-die
    collectives, CRC retry as exception), host link. [M:hbm-static-onchip 10-14/15]
1.3 Neighbour-only pipelined hops, each <= 405 um per cycle (plan reach); latency of every hop known to the compiler.
    Collectives are trees/chains, never a star hub. [M:accelerator-design-principles 10-16, M:reach-405 10-17]
1.4 Co-locate vector work and memory with matrix compute (per-column-group slices); no die-wide central vector unit.
    [M:accelerator-design-principles 10-16]
1.5 Hardened once, replicated: one partition type = one netlist/view; mirrored/shifted copies share it via the die
    lattice. A per-instance variant is a new type. Quantize widths; no new type without measured need.
    [A design method 2, P conventions, M:pin-registers-and-few-tiles 10-15]
1.6 Top-down: die_plan.json (floorplan, pins, ft, clock, reset, latency table, cut budget) comes first; partitions are
    built to budget and assembled by abutment. Never bend the plan to fit a stale block. [M:owner-topdown-workflow 10-23]
1.7 Model before build: block sized in tools/uarch_model.py (MACs, bytes/port, bits/boundary, tracks, area, latency)
    and cut analysis (bits per cut / tracks <= 0.55-0.60) before RTL. [A design method 1, M:cut-analysis-before-rtl 10-12]
1.8 No stubs, shells, tie-offs, open inputs or bench glue in any die target; only test/debug ports may be tied. A
    port-bind check (bind.py) gates every die revision; unbound bus = G0 ERROR. [M:no-stubs 10-14, P "Bus", R7]
    NOTE R7 amendment, ID straps only (owner 10-25, option B): ID straps (tile/lane/head/variant IDs) may be INPUT pins
    of ONE hardened design tied to constants at the parent: (1) declared in the plan core/type entry as "straps",
    named strap_*; tie-off audits accept ties only on declared straps; (2) quasi-static inside the block: no pin
    register, kit SDC set_false_path -from [strap ports], block works for all values (no case analysis); (3) the
    parent ties each with TIEHI/TIELO next to the pin; (4) LEC/lockstep per master vs every constant variant.
    Every other input stays driven. [COORD-REVIEW-QUEUE OWNER DECISION 10-25 07:01; tools/die_plan/straps.py]
1.9 Register every partition pin: one boundary flop at the source pin and one at the destination pin of every port
    (R2 face flops, FIRM at the pin, pin-to-reg p90 <= 30 um). [P conventions "Port"/budgets, M:pin-registers 10-15]
1.10 No constant output pins: an output that is constant is removed from the plan and RTL, not exempted.
    [B#8 10-24]
1.11 R8 bus coherence: every as-built bus lands as one group with equal added delay; replicas padded equally;
    as-built valid/data order kept. LANDED bundles padded to one group depth while skew < window margin. [P r8.py, B rec. 10-23]
1.12 Exact arithmetic: golden rounding points and reduction order are mandatory; no level-6/7 dataflow changes.
    [A objective, dataflow levels]
1.13 Throughput qualification: a unit is done only when bit-exact + SIGNED + production-shape bench within 10% of
    its simulator price. [A throughput qualification 10-10]
1.14 Area is cheaper than closure: target 40-60% utilisation, aspect <= ~2:1, outline derived from the parent slot
    (fill < 60% needs a stated reason); die may grow to full reticle. [M:safe-tile-design 10-19, M:tile-outline 10-23,
    M:full-reticle 10-21, M:dont-pack-to-the-routing-limit]

## 2. RTL coding

2.1 Explicit widths on every port, signal, constant and concatenation; no implicit truncation/extension.
    [B 10-24 anti-rework, M:owner-avoid-back-and-forth]
2.2 No out-of-range bit/part selects, even in dead generate iterations: yosys-slang silently drops the bits
    (csa31: a[31:24] at k=3 tied csa31[30:24] to 0 in every netlist, found only after signoff; fix 16241c6cb).
    SELRANGE lint must pass (Verilator -Wall SELRANGE/WIDTH as errors). [HANDOFF 21:38, S81-KITS-RTLA]
2.3 Synthesisable subset accepted by Yosys 0.68 + slang and Verilator 5.050 (fleet toolchain); benches run on the
    same Verilator version as the daemon. [BRIEFING fleet, M:bench-verilator-version-skew 10-18]
2.4 Parameterised modules: keep/dont_touch must match renamed paramod names; face registers carry face_keep so
    neither Yosys nor ORFS eliminate_dead_logic removes them (face_guard checks 1_synth.odb). [M:yosys-keep-paramod 10-18,
    HANDOFF 08:27 0ce45ab03c]
2.5 Watch ROM inference: MEMORY_BMUX2ROM may fold registers into a ROM read; classify paths before blaming clocks.
    [M:yosys-rom-inference 10-17]
2.6 Reset only control state (FSMs, valid/sequence bits, epoch bits); datapath and ft flops carry no reset.
    [B#13d 10-24, M:owner-rules-relax 10-20]
2.7 Safe-design structure: <= ~20 logic levels / ~600 ps per stage; fanout <= ~32 per register (replicate); wide
    selects as registered one-hot; storage > ~2 kb in SRAM macros; no long flop delay lines. [M:safe-tile-design 10-19]
2.8 One synchronous core domain per die (1.2 GHz, 833 ps). The only clock crossings live inside PHY macros (HBM DFI
    async FIFO, SerDes). Fallback for KV kvs_pc only if the PHY cannot run a 1.2 GHz DFI side: async FIFO at the PHY
    edge + one sdc_lint exception. [B#14 10-24] (see 9.6)
2.9 Every RTL change re-runs lint + unit benches + mutants (bench catches a seeded fault) + token runs on the current
    RTL source assembly. [M:token-runs-on-every-rtl-change 10-21, M:owner-token-on-rtl-first 10-21]

## 3. Clock (industry multi-source CTS) [B#5 10-24, M:owner-clock-industry-practice 10-23]

3.1 Gate: related launch/capture flop-pair skew with CPPR credit <= 80 ps at TT AND FF, intra-partition and seam
    pairs. Max-min pin-flop spread is INFO only.
3.2 Global: structured symmetric binary H-tree/spine on M8/M9 with NDR to the taps, balanced by construction; root in
    a reserved gap, never on a hard core. [B#5a, CLOCK lane]
3.3 Taps on a pruned grid sized by sink density: ~1000-1500 sinks/tap, extra taps at dense clusters, no taps or
    drivers over macros, hard cores, PHY/SerDes windows or empty area. [B#5b]
3.4 Sinks assigned to taps by distance + load. [B#5c]
3.5 Every local tree balanced to the common latency (250 ps) within a <= 20 ps window, measured on GRT/routed RC,
    never placement RC. [B#5d, P clock.common_latency_ps]
3.6 Core-latency contract: a hard core's clock pin is fed early by its internal latency I:
    early_tap = max(0, I - 250). I = the core's signed pin-to-register mean insertion (signed kit early + 250), not
    lib max_clock_tree_path. [B#5e, CLOCK RULING 21:20] (see 9.7)
3.7 Seam neighbours hang on the same spine branch (maximal common path). [B#5f]
3.8 Sign-off is propagated-clock STA (section 6); FF hold with real trees decides seam hold, insertion_tol is
    guidance. [B#5]

## 4. Reset [B#13 10-24, supersedes B#2 "equal depth"]

4.1 Exactly one root 2-flop synchroniser per die, at the die rst_n pin; its async input is the only reset false path.
4.2 Neighbour wavefront: each partition registers its incoming reset and re-drives a registered reset out to its
    abutted neighbours (uniform per type: +1 reset in, registered reset out); relays every <= 405 um inside.
4.3 Release cycle per partition is deterministic and published by the plan tools; the compiler/static schedule uses
    the offsets. No global reset tree, no die-top relay hosting, no per-instance variants.
4.4 Schedule start = explicit start broadcast after reset, not the reset edge.
4.5 Assertion is synchronous (clock runs at boot); local flops use the delivered reset with timed recovery/removal;
    no recovery waivers. Boot benches price the release clocks. [B#2 kept parts]
4.6 Hard cores take rst_n as a timed synchronous input; an internal relay adds to its recorded reset depth. [RESET recipe 5]

## 5. Physical

5.1 Layers: SUPERSEDED by 12.1 (v2, owner 10-26). Partition signals + pushed-down ft <= M7; die-top signal nets may
    use M8/M9 left after the PG/clock/reset pre-routes. [B#12 10-24 -> D-INFRA-FIRST 10-26]
5.2 Pin faces: H layers (M4/M6) on E/W faces, V (M5/M7) on N/S; <= 2 layers per face; pins on die lattice tracks
    (grid 8.64 um); pin/track <= 0.6; <= 6 pins/um per 10-um window. [P conventions, budgets]
5.3 Repeaters every <= 450 um on die-layer nets (600 breaks the 320-ps slew limit); repeaters inside a registered hop
    are normal. [M:owner-repeater 10-22/23, M:reach-405 10-17, P rep_um]
5.4 <= 400k std cells per OpenROAD run (never > 500k); bigger partitions need planned hard cores (G0C). Budget
    32-48 GB per job. [M:openroad-cell-cap-400k 10-23, P G0C]
5.5 PHY supply: separate PHY supply + dedicated bump rows over every SerDes window (S81, head, HBM). [B#7 10-24]
5.6 PG grid continuous across abutted seams; macros on the lattice with halos on pin faces. [P pg, M:safe-tile-design]
5.7 Vt: RVT default; LVT only on near misses, <= ~2% of cells; > ~10% needed = structural RTL fix. [M:rvt-default 10-07]
5.8 Hold-only miss with setup room: deterministic delay stage at the failing inputs, constraints unchanged; no ECO
    loops. [M:easiest-deterministic-fix-first 10-10]

## 6. Sign-off

6.1 Setup at TT, hold at FF, uncertainty 0 ps setup (OWNER 12.24c 10-31; was 60) / 25 ps hold + 10 ps kit hold-repair margin, period exactly 833 ps; setup and clock gates nominal (no spice x1.05, no droop derate, no clock OCV/AOCV, optimistic width-aware clock RCX), margins reported by tools/die_plan/margin_report.py (lanes/MARGIN-REPORT-<die>.tsv), not gated. SS never gates (INFO only).
    [A sign-off corners 10-24, M:signoff-corner-tt-option-b]
6.2 Margined slack (xtalk/IR/OCV) is an INFO column; gate = policy slack. [B#3 10-24]
6.3 A block counts only when tools/die_plan/signoff.py reports SIGNED: TT setup, FF hold under the std boundary-hold
    overlay (NOT RUN blocks SIGNED), slew/cap, no unconstrained/unclocked/loops, clock gate (3.1), sdc_lint, face_guard,
    DRC 0, antenna 0, every macro timed with its lib. [lanes/SIGNOFF.md, Codex overlay fix 21:09]
6.4 sdc_lint: one real clock + one virtual IO clock with latency, max+min IO delay on every port, no relaxed periods,
    no exceptions except ruled ones. [HANDOFF 07:30 4b7b2b3e64]
6.5 face_guard: every planned face register survives synthesis and route as its own flop (none dropped/merged/shared).
    [P face_guard.py]
6.6 LEC (being added, lanes/LEC.md): RTL vs synthesised netlist at exact parameters must be equivalent before P&R and
    is the receipt with strict bind (no native formal proofs on routed netlists). [M:owner-avoid-back-and-forth 10-24,
    M:owner-rules-relax 10-20 #4]
6.7 SELRANGE lint (being added, lanes/RTL-SELRANGE.md): 2.2 as a fail-closed gate. [M:owner-avoid-back-and-forth]
6.8 Die: G4 = die_sta.py (ILM continuous, flat --reduce signoff) TT setup >= 0, FF hold >= 0 on every seam + 3.1 on
    real spine; die GRT overflow 0. [P die_sta, M:die-standard-five 10-16]
6.9 No clock/uncertainty relaxed without pricing; failed verdicts are never overwritten; a gate that did not run is
    NOT RUN. [A engineering rules, BRIEFING reporting]

## 7. Flow and gates (in order; each must PASS before the next)

7.1  SPEC: uarch model + cut analysis + throughput budget (1.7, 1.13).
7.2  G0 / G0C: check.py --completeness on die_plan.json: geometry, abutment, layers, densities, cuts, reach, latency
     table == formula, census coverage (R5 bit-level), R3 stations, R8, reset/clock completeness, hard cores for
     types > 400k cells. 0 errors. [P]
7.3  G1 GEOM plan review: render.py PNG looked at; data-flow-driven floorplan, aligned faces, no unstationed long
     wires, macro/channel sanity; verdict PASS / PASS-COND / FAIL recorded in results/geom_review/ and the lane
     file; independent second review by GEOM-REVIEW. [B "Review before you route" 08:05, M:owner-geom-review 10-23]
7.4  RTL: generated wrappers + leaf RTL; lint (Verilator -Wall incl. SELRANGE/WIDTH), unit + composition benches
     bit-exact, mutants caught, token runs on RTL source (2.9). Port-bind check PASS (1.8).
7.5  SYNTH + LEC: yosys synth per type; face_guard on netlist; LEC equivalent (6.6). sdc_lint on the kit SDC.
7.6  G2 PROTOTYPE: place + GRT + STA (TT/FF, real CTS taps per section 3) for every unsigned type; plus the G2 die and
     ft probes (g2.py: overflow 0, all pins accessible). No detailed route before this passes. [M:owner-avoid-back-and-forth,
     lanes/PROTO.md, P g2]
7.7  GEOM tile review: placement + density + congestion + clock-tree render of the prototype; fill, pin-register
     distance, macro placement, outline vs slot. PASS required; FAIL = structural fix, not retry. [M:owner-tile-visual-review 10-23]
7.8  ROUTE (ot-run, kit run_kit.sh), then SIGNOFF (6.3). Only SIGNED counts as closed.
7.9  G4 die: abutted die STA + die clock (pair skew) + die GRT overflow 0 + reset tree check (6.8, 4).
7.10 G5 token pass: per-layer runs + inter-die co-sims on the die netlist, bit-exact, real cycles, rate vs price.
     [M:token-pass-release-gate 10-18]
7.11 CHANGE CONTROL:
     a. A change to a SIGNED partition's interface (pins, widths, latency, clock/reset contract, outline) needs a written
        impact analysis (affected types, neighbours, latency table, compiler, re-sign list) in the lane file and
        coordinator approval before any edit. [M:owner-avoid-back-and-forth]
     b. Rule/contract changes are batched: the coordinator collects requests in COORD-REVIEW-QUEUE and issues them as
        one numbered METHODOLOGY revision; lanes do not adopt one-off rules from chat.
     c. Owner questions go as plain text under OWNER? in the lane file; continue other work meanwhile. [BRIEFING]
     d. Plan-first: a failing element is never re-routed without a recorded geometry PASS; a failed route means a
        structural fix first. [M:owner-geom-review 10-23, M:safe-tile-design 10-19]

## 8. Operations

8.1 Builds/routes/synth/STA/big lints via ot-run (`ssh epyc1 ot-run`); diagnostic probes run directly in docker with
    --memory = --memory-swap on a fleet host, never queued. [M:owner-decisions-1024-rtxpro, M:owner-checks-bypass-admission 10-23]
8.2 No heavy jobs on the coordinator host (rtx-pro, hostname ubuntu): agents + coordination only. [M:owner-no-heavy-on-localhost 10-23]
8.3 Scratch disks only: /srv/opentallas-scratch2/claude/ (intel1/intel2/epyc2, and epyc1/epyc3 since the RAID split),
    never root disks; worktrees there too. [B disks 07:30, M:owner-scratch-not-root 10-24]
8.4 Admission by memory only; no CPU/load caps; no swap, no growth reservation; saturate the fleet. [M:memory-is-the-only-admission-limit,
    M:owner-no-swap 10-22, BRIEFING utilisation]
8.5 Delete failed/superseded/cancelled job bulk data at once (keep small logs/json/verdicts); only CLOSED/SIGNED
    routes are archived. Nothing runs > 48 h; folders untouched > 24 h are deleted. [M:delete-failed-jobs 10-13,
    M:nothing-runs-over-48h, M:owner-scratch-not-root 10-24]
8.6 Git: own worktree per lane (sparse checkout), branch claude/<lane>-1024; stage explicit paths, never `git add -A`;
    never `git stash`; never run git in another agent's worktree; push branches often. [BRIEFING git, M:sparse-worktrees 10-21]
8.7 Merge: flock ~/coord/merge.lock, --ff-only main then --no-ff branch, own gate passed, no deletions of others' work;
    NEVER -X ours/-X theirs (conflict: abort, merge main into the branch, re-gate). Delete the worktree after merge.
    Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. [BRIEFING git] (see 9.1)
8.8 Kill only exact pids you started or `ot-run --cancel <own dir>`; never pkill -f patterns. [A workflow habits]
8.9 Report: lane file per milestone; one HANDOFF line per milestone with `TZ=America/Los_Angeles date '+%F %H:%M'`.
    [BRIEFING reporting, M:use-date-for-timestamps]
8.10 Simulate the minimum component; compose analytically; whole-system sims only when the owner asks. [A workflow habits]

## 9. Open contradictions / gaps (coordinator to rule; rule stated above applies meanwhile)

9.1 AGENTS.md "Merge finished work": `-X ours` on conflicts vs BRIEFING: NEVER -X ours/theirs (dropped DIE-CI README
    10-24). AGENTS.md needs the update.
9.2 AGENTS.md sign-off still lists "pin-flop spread <= 80 ps" as a gate; B#5 made it INFO. main signoff.py and
    die_sta FFSPREAD still FAIL on spread > 80; pair-skew signoff is WIP (codex/kit-clock-1024, claude/kit-clock-1024).
9.3 B#12 reserves M8/M9 for clock/reset/PG, but P still allows M8/M9 ft (`ft_reserved`, `ft_budget` over-the-top ft,
    reach table M8 1001/M9 1013 um, die.reach_um S81 1500 / KV 1200 / QC,HBM 1000) and 10-22/10-23 memory opened M9
    for die signals. Tools must drop M8/M9 ft routes; reach must use the M4-M7 405 um figure.
9.4 R3 station spacing: check.py ft_station_max_um = 750 um (COORD 10-23) vs B#12 <= 405 um. Default must become 405.
9.5 P reset section still specifies B#2 "equal depth K to every tap" + die relay tree hosted in partitions; B#13
    replaces it with the neighbour wavefront. reset_tree.py needs the wavefront mode (RESET lane).
9.6 AGENTS.md clock domains: 0.9 GHz serial-chain domain (SU/SFU/softplus/Sinkhorn/reducers, 2026-09-30) vs 2.8
    "CDC only in PHY macros" (B#14 is stated for KV). Is the 0.9 GHz domain retired on all release dies?
9.7 Core-latency contract formula: requested early_tap = max(0, I - 250); CLOCK ruled I = signed pin-register mean,
    not lib max (S81-HEAD elemA/B: 191/185 vs signed early 160/120). Confirm I's definition per core type.
9.8 P clock still says insertion 250 +/- 40 and kit SDC seam-hold min input delay = -insertion_tol; B#5d wants a
    <= 20 ps local window. Keep -40 as hold padding or tighten to the measured window?
9.9 Region-crossing landing rings (owner 10-20 clock-ring rule; landed-regions 10-18; P face_xing
    `forwarded_landing`) vs B#5 one synchronous MSCTS die with seam pair skew. Only R8 LANDED bundles are still
    explicitly kept. Are new seams always `budgeted` synchronous?
9.10 Pin registers: owner 10-20 relaxed "register every pin" to region crossings / > 405 um wires; P R2 (10-23)
    registers every partition port both sides. Rule 1.9 applies at partition level; intra-partition tiles may connect
    directly when timed.
9.11 G2 is defined in P as die + ft routing probes; the owner-requested "G2 prototype" (place+GRT+STA per type,
    lanes/PROTO.md) is not yet in the tools or the P gate list.
9.12 LEC (lanes/LEC.md) and SELRANGE (lanes/RTL-SELRANGE.md) lanes are named in HANDOFF 21:38 but no lane files
    exist yet; neither gate is fail-closed in run_kit.sh/signoff.py.
9.13 ref_tile legacy kits cannot be SIGNED (sdc_lint vocabulary, no IO vclk overlay): re-kit in die-plan form (G3) or
    accept? (SIGNOFF OWNER?). Rule here: only die-plan kits are signable.
9.14 Release freeze (owner 10-22: frozen release designs) vs top-down rework of all frozen designs (owner 10-23).
    10-23 is later and is taken as superseding the freeze where they conflict.
9.15 Host naming: BRIEFING "localhost" (84.32.71.203, written during the epyc1 period) vs rtx-pro coordinator
    now; host shares in BRIEFING give "localhost" 256 threads of lane work, which conflicts with 8.2.

## 10. Coordinator rulings on section 9 (2026-10-24 21:42 PDT) -- binding until the owner says otherwise
- 9.1 Never -X ours/theirs; AGENTS.md updated to match.
- 9.2 Spread > 80 ps is INFO; signoff.py/die_sta switch to related-pair skew + CPPR when the kit-clock branches merge (CLOCK lane).
- 9.3 SUPERSEDED 10-26 by 12.1 (owner D-INFRA-FIRST step 5): die-top signals may use leftover M8/M9; partition ft stays <= M7; reach = 405 um on every layer.
- 9.4 ft_station_max_um default 405.
- 9.5 Wavefront reset (RESET lane); README reset section rewritten when the tool lands.
- 9.6 RULED by owner decision 16: single 1.2 GHz domain if FP32 add fits LAT4 at 833 ps (check running).
- 9.7 I = signed pin-register mean insertion of that core type's SIGNED view (lib max only before first signoff).
- 9.8 Keep -40 ps hold padding until the spine is measured; then set it to the measured related-pair window + 10 ps.
- 9.9 New seams are budgeted synchronous under MSCTS; LANDED only for R8 bundles and off-die links.
- 9.10 Register every partition port (R2); tiles inside one partition may connect directly when timed.
- 9.11/9.12 G2 prototype, LEC and SELRANGE gates are being added (lanes/PROTO.md, LEC.md, RTL-SELRANGE.md).
- 9.13 Only die-plan kits are signable; ref_tile legacy kits are re-kitted in die-plan form.
- 9.14 10-23 top-down rework supersedes the 10-22 freeze.
- 9.15 "localhost" in BRIEFING = epyc1 period; the coordinator host is rtx-pro and runs no heavy jobs.

## 11. Die method: infrastructure first [OWNER D-INFRA-FIRST 2026-10-26 01:37 PDT; COORD additions 01:4x; tool lane lanes/INFRA-FIRST.md]
Per die, in order (supersedes "route signals, then fit the clock"; amends 7 and 3 where they differ):
- 11.1 PG first: die grid on M9 + part of M8, sized from per-region IR (PDNSim per region; published PHY power, owner 10-26 4.37 W per 112G macro; core power per type). Report the % of M8/M9 tracks taken.
- 11.2 Clock: equal-length H-tree feeding one mesh per clock region; LANDED (forwarded-clock) crossings at region seams (COORD 01:22); mesh drivers / H-tree buffers in reserved driver islands (12.2): in partition channels, or INSIDE a hard core where no channel site exists (owner 10-26, cores rebuilt with the island).
- 11.3 Reset: die wavefront (B#13): rst_n -> root partition; parent rst_o_<k> -> child arst_n die hops; START beside it.
- 11.4 PG, clock and reset are frozen as FIXED pre-routes (special nets / fixed wires + NDR footprint obstructions in the die kit) so die GRT sees the exact leftover capacity; skew gate (like-edge related pairs, CPPR, TT+FF, <= 80 ps) on the pre-routed clock alone.
- 11.5 Die signal GRT on the leftover, >= 50 iterations: M4-M7 + leftover M8/M9 per 12.1.
- 11.6 Die plan freezes per 12.4a (die STA with real clock on related pairs; 80 ps skew = target).
- 11.7 THE DIE ABSORBS RESIDUALS: a tile's measured clock insertion that differs from plan is compensated at die level (per-tile mesh stub trim / declared core-latency offset in the die clock tool), not by a tile rebuild -- EXCEPT the owner 10-26 core-latency rebuild (12.3). Boundary timing rests on registered pins + channel repeaters. A tile is rebuilt only for its own internal failures.
- 11.8 PRE-FREEZE TRIAL PLACEMENT: every tile type gets a quick place with its clock islands and pre-route keep-outs in, showing fit, pin access and an r2r reach census, before the die plan freezes.
- 11.9 Order: QC (prototype) -> S81-HEAD -> KV / S81 / HBM inside their current batches.

## 12. PHYSICAL INFRASTRUCTURE RULES -- CANONICAL (v2, OWNER 2026-10-26). Read this before ANY layer / feedthrough / island / clock-latency proposal.
Any lane, sub-agent or coordinator message that contradicts 12.x is wrong; 12.x changes only by a new OWNER decision
recorded in 12.6. Never re-impose a superseded line from 12.6 from memory or chat.
- 12.1 LAYERS.
  a. Tiles / partitions / hard cores route their own logic on <= M7 (new tiles default M5 ceiling, M:m5-cap). They never use M8/M9.
  b. Die order (section 11): PG (M9 + part of M8, sized from IR) -> clock (H-tree + regional mesh, M8/M9, NDR) -> reset -> FROZEN pre-routes.
  c. Die-top signal nets then route on M4-M7 PLUS whatever M8/M9 is left after the pre-routes (owner 10-26 01:1x). M4-M7 is preferred; the
     router may use the leftover M8/M9 freely, subject to 12.4 gates.
  d. Partition feedthroughs are PUSHED DOWN: ft stations/repeaters are partition logic (partition netlist, FT slots, <= M7), timed + signed
     off with the partition. Partitions abut; no die-level std cells for signals.
  e. Reach: plan 405 um per registered hop on EVERY layer (M8/M9 included; the measured 1001/1013 um M8/M9 figures are not used for planning).
     Repeaters <= 450 um. A die-top net on M8/M9 drops to a partition repeater bay at least every 405 um.
- 12.2 SITES.
  a. INFRA ISLAND = top-owned placement hole + M9->M1 via stack, used ONLY for die clock drivers (H-tree / mesh) and the regional reset register +
     repeaters. Location: the partition channel cross where one exists (QC: the A0 channel cross); otherwise INSIDE the hard core (core rebuilt
     with it).
  a1. IN-CORE ISLAND = PUSHDOWN (OWNER 10-26 06:39; OpenROAD cannot place parent cells inside a hard-core outline): the island's clock/reset
     driver cells are instantiated IN THE CORE NETLIST at plan-fixed coordinates, identical for every instance of the type, connected only
     through dedicated feed-through ports (in from the M9->M5 stack, out to the die mesh/tree/reset net). The core build places/routes them
     (fixed, dont_touch); the core is signed with them; LEC/bind treat them as die-owned feed-throughs (no core logic on those ports). The
     master plan fixes the island coordinates per core type BEFORE the core is built; every instance's island is used (tree node or mesh
     driver), so the die tree/mesh lattice is chosen to coincide with the per-type island lattice. No parent cells inside core outlines;
     cut-out macros are not used.
  b. REPEATER BAY = partition- or core-owned reserved site rows for pushed-down ft stations/repeaters, along ft corridors / under die-top routes,
     <= 405 um apart, sized from measured demand. In-core bays only where a core longer than reach blocks a corridor and leftover M8/M9 + a
     bay outside the core cannot close the gap.
  c. The die H-tree lattice is snapped to the partition lattice so tree nodes land on island sites (report max node displacement).
- 12.3 CLOCK LATENCY. One common per-die clock-latency target at every hard-core clock pin (default 250 ps TT; FF stated per die); deep cores
  restructure their CTS to meet it, shallow cores pad up. v5.0 (OWNER 10-26 18:4x, "remove the ban rule and keep aligned with industry
  flows"): EARLY TAPS ARE ALLOWED as standard macro insertion-delay balancing. A hard core's clock insertion delay is taken from its
  signed-off (or current real) view, annotated as the core clock pin's latency, and the die CTS taps that core earlier by exactly that
  delay. The core's internal tree is then unshared clock path and is charged by the 12.4a b1 AOCV table like any other clock path. The
  common target stays a DESIGN TARGET for new/rebuilt cores (it keeps unshared delay small), but a signed core is no longer rebuilt only
  for latency; the die related-pair STA (12.4a) decides.
  12.3a (OWNER 10-26 16:5x) The core band (250 +-20 TT / 202.5 +-20 FF, tap window <= 20 ps) is a DESIGN TARGET, not a pass/fail gate:
  every core is planned and predicted to it, but a core measured slightly outside it proceeds to sign-off and the die related-pair STA
  (12.4a, real core numbers) decides. Still banned: trims/pads/post-measurement edits (12.8); a core far out of band is restructured.
- 12.4 GATES (all dies, die_infra.py).
  a. Freeze (OWNER 10-26 06:33) = die GRT0 incl. clock (>= 50 it) AND DIE STA WITH THE REAL CLOCK on related pairs: TT setup >= 0 and FF hold >= 0
     for every related launch/capture pair (intra-partition, seam, die links), propagated clock arrivals from the routed die clock (routed RC, CPPR to
     the last common tree node), blocks as interface timing models (pin-register clock latency + clk->q/setup/hold from the kit; declared 12.3 budget
     until a kit exists, labelled). Related-pair skew <= 80 ps TT/FF is the CLOCK DESIGN TARGET and a reported diagnostic, NOT a pass/fail gate.
     Hold is made safe by STRUCTURE (zero-logic register pairs share a clock leaf; die crossings are landed/forwarded hops), never by post-measurement
     padding (12.8). Release gate stays die STA on real (signed) views + token pass.
  a1. (OWNER 10-26 ~17:3x) HOLD BUFFERS ON DATA PATHS ARE ALLOWED (industry standard): the router/timing repair (OpenROAD repair_timing -hold
     or equivalent) inserts delay cells on short DATA paths at tile and die level until FF hold passes under 12.4a. The clock network
     is never touched (12.8 d still bans clock pads/trims/ECOs). The flow inserts the cells; no hand edits. Setup at TT must still pass
     after insertion, and the inserted cell count/area is reported per die. Structure (shared leaf / landed crossings) remains preferred
     where it is cheap.
  b. CPPR (OWNER 10-26 06:07, 12.8): the GATE number credits CPPR only to the last common H-tree/tree node (region root for same-mesh pairs);
     no credit at the mesh node. The mesh-node-credited number (COORD 10-26 early ruling) is INFO only.
     EXCEPTION (12.8e, OWNER 10-26 17:0x): a regional mesh SIGNED OFF by variation circuit simulation counts as a common point; its
     worst simulated mesh skew is added as explicit clock uncertainty on every pair through it; flat OCV applies only below the mesh.
  b1. (OWNER 10-26 17:4x) CLOCK OCV = depth- and distance-based derate table (AOCV-style, industry practice when no LVF/POCV), replacing
     the flat clock-path cell 1.05/0.95 + net 1.03/0.97 of die_ci_margins.json. Derate per clock path = f(stage count from the last
     common point, bounding-box distance of launch/capture), random part scaling ~1/sqrt(depth) plus a non-averaging systematic part.
     The table is built from ASAP7 device-model Monte Carlo if the models carry variation statistics, else from cited published 7 nm
     data; every assumption documented. Owner reviews the table before it gates. (OWNER 10-26 18:4x: table APPROVED to gate,
     distance gradient g = 0.21 %/mm interim, until a published FinFET within-die gradient replaces it; claude/clk-aocv-1026@b0c11ff91e,
     NUMBER-CHECK-AOCV CHECKED.) Data paths keep flat derates. IR droop (OWNER
     10-26 17:5x): droop is SHARED between launch and capture clocks -- the stated 5 % drop (+5.1 % late) still applies to the data
     path, but on the clock only the DIFFERENTIAL droop between the two clock branches is charged: 0 for branches in the same mesh /
     PDN region; for branches in different regions the full one-sided +5.1 % stays until a PDNSim/region-droop result gives the
     real differential. PDNSim replaces the stated values when it exists.
  b2. (OWNER 10-27 ~18:1x, LIB-VDROOP-CHECK) DATA DROOP DERATE at 35 mV budget: die-level STA charges data paths per class --
     RVT logic cells + flop clk->Q +10 % late, wire/repeater segments (M8/M9 repeated stages) +5 % late (FF: +8 % / +4 %); replaces the
     flat +5.1 % data term. PG budget stays <=35 mV. CORE level (option i): core sign-off is unchanged -- the 60 ps setup uncertainty
     covers jitter + core-internal droop, provided the die PG holds <=35 mV; cores with TT setup slack < 25 ps get a 0.665 V
     sign-off rerun (information + fix if it fails) at their next re-sign. Option (b) (19 mV budget, keep +5.1 %) REJECTED.
  c. Site sufficiency: max gap between legal station/repeater sites along each die net corridor <= 405 um; corridor track use <= 0.6;
     via-field porosity + per-gcell pin-stack limit on every M8/M9 -> bay drop and every island stack; bay fill <= 60 %; mesh-driver
     power density / EM in islands.
  d. Signals adjacent to clock mesh/spine on M8/M9 keep the clock NDR spacing/shield; the skew gate is re-run after signal GRT (not only on
     the clock alone).
  e. PG IR is closed BEFORE signal GRT; any later PG growth re-runs signal GRT.
- 12.5 Known risks (watch, do not re-litigate): pin-stack hot spots on M8/M9 drops (HBM FT-M89: 108k stacks, max 168/gcell); signal-to-clock
  coupling on M8/M9; PG growth after signal routing (QC UCIe IR open); tool paths that still drop M8/M9 ft from the 9.3-era code
  (must be switched by the infra tool lane, then one tool for all dies).
- 12.6 DECISION HISTORY (M8/M9 + ft). Superseded lines are listed so nobody revives them:
  - 10-20 M9 = PG/clock only. SUPERSEDED 10-22.
  - 10-22 M9 opened for die signals M2-M9 (21M GRT overflow from vertical starvation). SUPERSEDED 10-23.
  - 10-23 ft pushdown into blocks + M8/M9 reserved budget (channel-only relays starved routing; M8 relay pins 24.6M vs 269k). KEPT (pushdown).
  - 10-24 B#12: all signals <= M7, M8/M9 = clock/reset/PG. SUPERSEDED 10-26 for die-top nets only.
  - 10-25 proposal of over-tile ft (type count) withdrawn: no measured failure. Lesson: no layer change without a measured failure.
  - 10-26 01:1x OWNER D-INFRA-FIRST: PG/clock/reset first, die signals on M4-M7 + leftover M8/M9 = CURRENT (12.1).
  - 10-26 05:38 OWNER: common core clock-latency target + in-core islands on all dies, rebuilt in parallel = CURRENT (12.2a, 12.3).
  - 10-26 05:58 OWNER: master plan first (city-planning model, 12.7) on all dies; leftover M8/M9 stays free for the router, entry via planned M7 pins = CURRENT.
  - 10-26 06:07 OWNER: root-cause clock structure, no tweaks (12.8): plan-defined centre clock entry + structured core trees; early taps, stub trims, clock ECOs, mesh-node CPPR credit banned as closure means = CURRENT.
  - 10-26 06:11 OWNER: 12.8 d1 plan-computed per-tap sizing before build ALLOWED (post-measurement values banned); core split = last resort after internal H-tree = CURRENT.
  - 10-26 06:15 OWNER: 12.9 execution rules (one owner per die clock/plan, QC critical path, rule freeze, predict-before-build, per-die flow releases, independent number check) = CURRENT.
  - 10-26 06:33 OWNER: freeze gate = die STA with the real clock (TT setup, FF hold) on related pairs; 80 ps related-pair skew becomes design target/diagnostic (12.4a) = CURRENT. Supersedes the 10-26 01:0x skew-gate form.
  - 10-26 06:39 OWNER: in-core islands built by PUSHDOWN (12.2a1); no parent cells inside core outlines = CURRENT.
  - 10-26 16:5x OWNER: core latency band/window = design target, die related-pair STA decides (12.3a) = CURRENT. Supersedes treating 250+-20/window<=20 as hard core FAIL. Same exchange: bottom-up landed fallback (IF.FALLBACK) run IN PARALLEL now on S81, s81_head, KV; first to pass wins (QC/HBM stay master-plan, fallback costs 8-12%).
  - 10-26 17:0x OWNER: MSCTS die clock (12.8e) = CURRENT: M8/M9 global H-tree + regional meshes signed off by variation sim (mesh = common point, sim skew as uncertainty) + short local trees; landed crossings only for remaining seams. Supersedes the 06:07 blanket ban on mesh-node CPPR credit for SIGNED meshes only (unsigned: still banned).
  - 10-26 17:3x OWNER: "if continuous mesh can work, switch to it" (12.8e1) = CURRENT: continuous die mesh cut only at landed crossings is the preferred form; per-region meshes = fallback when the continuous mesh fails its evaluation. Reason: seam pairs between separate regional meshes still see unshared global-tree delay (~1.5-2 ns, UNCHECKED estimate).
  - 10-26 17:4x OWNER: "replace the flat clock margin with a depth- and distance-based table, the standard practice" (12.4a b1) = CURRENT. Supersedes flat 5 %/3 % clock derates (die CI lane choice 10-24, never an owner decision). Gates after owner review of the table.
  - 10-27 18:1x OWNER: data droop derate per class (RVT logic +10 %, wires +5 %) at 35 mV die level; cores keep 60 ps uncertainty (12.4a b2) = CURRENT.
  - 10-26 17:5x OWNER: supply droop treated as SHARED between the two clocks (12.4a b1) = CURRENT: clock charged only differential droop (0 within one mesh/PDN region; full +5.1 % one-sided across regions until PDNSim); data path keeps +5.1 % late. (COORD first misread the owner as keeping the one-sided margin; corrected same minute.)
  - 10-26 ~17:3x OWNER: "approve automatic hold-buffer insertion on data paths" (12.4a a1) = CURRENT. Supersedes reading "hold safe by structure, never padding" as a ban on data-path hold buffers; clock padding stays banned. Trigger: QC-MP-REGION-2 zero-logic seam hold budget 10.9 ps FF < >=29.5 ps flat-OCV pessimism (UNCHECKED).
  - 10-26 18:4x OWNER: "use 0.21% per mm" (12.4a b1) = CURRENT: AOCV clock table approved to gate with distance gradient 0.21 %/mm (interim; the 0.42 %/mm corner-derived bound was global variation, NUMBER-CHECK-AOCV).
  - 10-26 18:4x OWNER: "remove the ban rule and keep aligned with industry flows" (12.3, 12.8d/d1/f) = CURRENT: early taps allowed as macro insertion-delay balancing from the core's own signed/real view; unshared core-internal delay charged by the AOCV table. Supersedes 12.8 (06:07) early-tap ban and 12.3 "no early taps by design". Still banned: per-tap trims, useful-skew offsets, post-CTS clock ECO padding, mesh-node CPPR on unsigned meshes.
  - 10-26 18:5x OWNER: "trims, useful skew and clock fix-up padding are all allowed, but you need to use these techniques sparsely. do principle level fixes whenever applicable" (12.8 d2, v5.1) = CURRENT. Supersedes the 12.8d (06:07) and d1 BANNED lists and my 18:4x narrow reading of "remove the ban rule"; residual tools allowed sparse + ledgered after the structural fix; meander that dominates a tree (QC-SU-F4C 51 %) is not sparse.

- 12.7 MASTER PLAN FIRST -- CITY-PLANNING MODEL (OWNER 2026-10-26 05:58, "yes, do all of them on all dies"). Supersedes/extends 12.1-12.4 where stricter.
  Utilities (PG) -> transit (clock, reset, with islands as stations) -> roads (die-level routing corridors) with rest stops (repeater bays) and
  on-ramps (entry pins) -> only then buildings (partitions / hard cores). Nothing is carved into a finished block afterwards.
  a. ONE MASTER PLAN PER DIE, produced by one shared tool (die_infra.py master-plan mode) for all five dies:
     - traffic census: every die-level path with its bit count (die_plan ports + census);
     - roads: corridor + layer per path (M4-M7, leftover M8/M9 free per 12.1c), track use <= 0.6;
     - rest stops: repeater bays <= 405 um apart along every path (any layer, incl. M6/M7 feedthroughs over hard cores), sized from the
       bits passing at <= 60 % fill; in-core bays where a core longer than reach lies on a path and no channel route exists;
     - on-ramps: every M8/M9 die net enters a partition/core only at a pre-declared M7 entry pin beside a bay (one M8->M7 via), pins spread
       so pins per gcell stay below the pitch-derived limit;
     - infra: PG sized for WORST-CASE power per region (peak activity + margin; PHY hot spots locally reinforced, published PHY power),
       clock H-tree snapped to the partition lattice, islands (clock/reset only), every clock strap/segment shielded by PG stripes on both
       sides, no signal track adjacent/parallel to clock within the shield spacing, reset;
     - one common core clock latency per die (12.3).
  b. STATIC PLAN GATES before ANY block (partition/core) build: reach gap <= 405 um on every path; bay fill <= 60 %; corridor tracks <= 0.6;
     entry pins per gcell <= limit; clock shielding complete; static IR PASS per region at worst-case power; every hard core fits its lot
     with its islands/bays. These run on the plan in minutes; a FAIL is fixed in the plan, never in a block.
  c. BUILDINGS FOLLOW THE PLAN: every partition/core kit consumes its slice of the master plan (outline, keep-outs, islands, bays, entry
     pins, latency target). The kit generator refuses a kit without a slice from the current frozen master plan; GEOM-REVIEW checks the
     kit against its slice. LEF/abstracts expose islands/windows and their PG rails.
  d. ONE FREEZE PER DIE: the master plan freezes when 12.7b passes; later changes only as one batched PLAN-DELTA (7.11b); no local fixes.
  e. MARGINS so routing confirms rather than discovers: 60 % fill/tracks, 405 um plan reach (measured repeated 600-750), worst-case power.
  f. ORDER: QC first (all 68 types held), then S81-HEAD, S81, KV, HBM in parallel lanes on the same tool; running core rebuilds and
     early-tap work feed in. In-flight trials may finish, but sign-off kits must carry a master-plan slice.

- 12.8 ROOT-CAUSE CLOCK STRUCTURE, NO TWEAKS (OWNER 2026-10-26 06:07, "fix the root cause and structurally redesign. do not use tweaks and tricks").
  Root cause: hard cores were closed bottom-up before the die clock plan existed -> clock pins on edges/corners, each core its own latency,
  die compensating afterwards. Structural rule for ALL dies:
  a. The master plan (12.7) defines, per hard-core type, the CLOCK ENTRY (a clock/reset island at/near the core's geometric centre, M9->M5 stack)
     and the die's ONE latency target (12.3). Kits must place the clock pin exactly there; kit generator + GEOM review reject any other location.
  b. Inside every core the clock is a STRUCTURED tree from that entry: symmetric (H-tree/fishbone) trunk to equal-load leaf clusters, stage
     count fixed by geometry, same structure for every instance of the type. A core whose longest entry-to-sink distance exceeds ~200 um, or
     that cannot meet 250 +-20 TT with a centre entry, is restructured -- FIRST an internal H-tree with in-core islands; splitting into smaller
     cores is the LAST resort (adds types and links; OWNER 10-26 06:11) -- never padded/trimmed into range.
  c. Shallow cores reach the target with a designed fixed trunk delay at the entry (same cell chain per type), not per-sink padding.
  d. The die clock is balanced by construction: H-tree snapped to the partition lattice, equal-length branches, equal load per tap (density
     taps), regional meshes with landed seams. NOT allowed as closure means: early-tap offsets/branches, per-tap stub trims or useful-skew
     offsets, post-CTS ECO padding/buffer swaps on the clock, mesh-node CPPR credit, gate-number relaxations. (v5.0: early-tap
     offsets/branches REMOVED from this list -- allowed per 12.3 v5.0 as macro insertion-delay balancing.)
  d2. (OWNER 10-26 18:5x, v5.1, "trims, useful skew and clock fix-up padding are all allowed, but you need to use these techniques
     sparsely. do principle level fixes whenever applicable") The 12.8d list is no longer a ban. Per-tap trims, useful-skew offsets,
     post-CTS clock ECO padding/buffer swaps and meander/detour balancing are ALLOWED as RESIDUAL tools, under three conditions:
     (1) PRINCIPLE FIRST: the structural/plan fix (12.8a-e, d1 sizing, early taps) is applied wherever it applies, and the root cause
     of each remaining miss is recorded before any residual tool is used;
     (2) SPARSE: residual tools touch a small minority of taps/edges/paths (guideline <= ~5 % of a tree's edges or a die's clock taps,
     and never the dominant balancing mechanism -- e.g. 51 % of tree wire as meander is NOT sparse);
     (3) LEDGER: every use is listed per die (what, where, how much, why the structural fix did not apply) in lanes/CLOCK-RESIDUAL.md
     and reported with the die STA. GEOM flags any tree whose residual share exceeds the guideline.
     Still not allowed: mesh-node CPPR on an UNSIGNED mesh, and gate-number relaxations.
  d1. (OWNER 10-26 06:11) ALLOWED as design: per-tap driver/stub sizing COMPUTED BY THE PLAN TOOL from plan geometry and loads BEFORE any
     block is built, deterministic, recorded and frozen with the plan. BANNED: any value chosen after a measurement (trims, offsets, ECOs).
     Exception (v5.0): a hard core's annotated insertion delay from its own signed/real view (industry macro latency annotation) is an
     input to die CTS, not a trim.
  e. (OWNER 10-26 17:0x, MSCTS die clock) Die clocks are built as industry MSCTS: (1) top-metal (M8/M9) shielded global H-tree with
     large drivers, equal branches by construction, NO balance-detour padding; (2) one regional mesh per lattice region, driven at many
     points from islands (12.2a1); (3) short local trees from the mesh to each partition/core entry. Mesh sign-off = circuit simulation
     (SPICE-class, ASAP7 models, routed RC) with driver/wire variation; the worst simulated skew is a declared uncertainty, and the signed
     mesh is a common point for CPPR (12.4a b exception). Unsigned meshes get NO credit. Landed crossings (IF.FALLBACK) only for seams
     that still fail after this. QC first; KV and HBM follow the same pattern.
     e1. (OWNER 10-26 17:3x) PREFERRED form = ONE CONTINUOUS mesh across all region boundaries (straps joined at seams), driven at many
     points by the global tree, cut ONLY where a landed/forwarded crossing sits; every related pair then shares the mesh as common point.
     Adopt it on a die when its measured evaluation works (variation sim tractable + signed, power, M8/M9 tracks, EM within budget);
     otherwise per-region meshes (e) are the fallback.
     A measured miss goes back to the structure/plan model (12.8e), then the plan is re-frozen as one PLAN-DELTA.
  e. A measured failure goes back to the structure (plan or core architecture), recorded with its root cause before any rebuild.
  f. Existing results obtained with the banned means (any stub-trimmed mesh result incl. KV c3t 63.95/54.71; v5.0: QC early-tap 154/143
     is no longer banned-means but still needs the 12.4a real-clock related-pair gate) are
     re-measured on the 12.8 structure with the 12.4b gate number before they count.

- 12.9 EXECUTION RULES (OWNER 2026-10-26 06:15, "yes, go with them").
  a. ONE OWNER per die clock and ONE per die plan (table lanes/OWNERS-DIE.md); no other lane edits that die's clock/plan; shared tools have one
     tool owner each (die_clock_mesh.py = CLOCK-128; master-plan mode = MASTER-PLAN; pg/clock/reset modes of die_infra.py = INFRA-FIRST).
  b. QC = critical path, end to end: 12.7b plan gates -> core rebuilds (12.8) -> die clock (12.8) -> die GRT0 -> skew gate -> die STA (real
     views). Other dies follow the same template without pulling QC resources.
  c. RULE FREEZE: section 12 changes only when a MEASURED failure shows a rule is wrong (cite the run), recorded with an OWNER decision; never
     mid-flight on coordinator initiative.
  d. PREDICT BEFORE BUILD: the master-plan gate includes a plan-level analytic model of clock insertion/skew and path reach so a FAIL appears in
     minutes, before CTS/GRT.
  e. PER-DIE FLOW RELEASES: a flow tag is released per die when that die's canaries are NO-REGRESSION; route holds lift per die. A die whose
     canary is pending keeps the previous tag.
  f. INDEPENDENT NUMBER CHECK: every gate number reported to the owner as PASS/FAIL (skew, GRT overflow, IR, STA WNS, sign-off counts) is
     recomputed from run artifacts by the NUMBER-CHECK reviewer before it is reported; unchecked numbers are labelled UNCHECKED.
- 12.10 SAFE-FORM PARALLEL BUILDS (OWNER 2026-10-27 ~18:4x, "yes, start now"). Replaces the 10-29 12:00 "no fallback builds" hold.
  a. KV: the LANDED form (per-group clocks + landed crossings, lanes/FALLBACK-LAND.md FALLBACK-PLAN-PREP-2, claude/fallback-plans-1027@1b7d068ad8)
     is BUILT NOW in parallel with the top-down form. First form to pass the freeze gate (die GRT0 incl clock + die STA on real views) wins.
     KV seam-shell / real seam HB4 work is held while the landed build runs.
  b. QC: a PER-SLICE clock variant (one clock domain per slice, landed crossings only between slices, related pairs inside a slice) is
     planned and built now in parallel with INFRA-FIRST-QC. It is priced by the TOK tools before adoption; first to pass the gate wins.
  c. HBM: STREET RULE is a hard plan check (G0C). Hard cores sit on a channel grid with every core <= ~400 um from a channel; channels
     are sized for clock repeaters, hold buffers and FT; no clock or die-level leg crosses a hard core. The plan generator obeys it.
  d. SUPERSEDED by 12.11 (S81/HEAD were to stay top-down until the 10-29 check).
- 12.11 LANDED/PARTITIONED CLOCKS = MAIN PATH ON ALL DIES (OWNER 2026-10-27 ~19:0x, "yes, do it immediately").
  a. Every die (S81, s81_head, qwen_compute, qwen_kvsys, hbm) is built as regional clock domains joined by LANDED crossings
     (+K cycles, K=2/3, ot_dp_clk_landing contract). The die-wide related-pair skew requirement, die-wide continuous mesh and die-level
     seam hold apply only INSIDE a region. QC uses the coarser per-slice form (12.10b).
  b. Core clock latency must match only within its region (region tree target); cross-region core latency matching is no longer required.
  c. Gate per die = die GRT0 incl clock (regional trees) + die STA on real views for intra-region related pairs + landing contract checks
     + token pass with the landed cycles. The cost goes in the ledger; the 5 %/15 % targets stay guidance.
  d. The top-down lanes continue only until the landed form of the same die passes the gate (first to pass wins), then stop.
  e. The 10-29 12:00 trigger is no longer a decision point; it becomes a status check.
  f. Not taken: modelling a thick clock/PG layer ASAP7 lacks (would misstate the PDK); allowed only as a labelled what-if.
  g. TERMINOLOGY (OWNER 10-27): "landed form" / "landed crossing" is the INTERNAL name for MESOCHRONOUS CLOCKING. All regions run at one
     frequency from one source with unknown but bounded phase (|phase difference| < P/2), and every region crossing is a
     FIXED-LATENCY MESOCHRONOUS SYNCHRONIZER (ot_dp_clk_landing ring, +K cycles, no handshake/credits). In the paper and in external
     text, say "mesochronous regions with fixed-latency crossings"; never "GALS" or "async FIFO". Tool, lane and plan-field names keep "landed".
- 12.12 (OWNER 2026-10-27 ~19:1x) droop INFO rerun extended: every signed core with TT setup slack < 70 ps gets the 0.665 V INFO rerun
     (12.4a b2 had < 25 ps). An INFO FAIL is fixed structurally at the core's next re-sign; it is not a sign-off gate. Measured basis:
     VQ 2.48 -> -60.90, NNfd 8.23 -> -65.12 (DROOP-DERATE-1, UNCHECKED).
- 12.13 LOCALITY FIRST (OWNER 2026-10-27 ~20:3x: "all of the non-closing dies must be reworked to use locality as the first principle").
     Applies to every die that has not passed the 12.4a freeze gate, which today is all 5. It overrides any earlier die-wide clock
     form (12.7/12.8 MSCTS die mesh/H-tree as the release clock). Top-down PLANNING (12.7 master plan, PG first, streets, budgets,
     pins) stays: it is how locality is made.
  a. Regions from connectivity. Cluster cores/tiles by measured traffic (bit-mm from the plan/RTL), so that heavy traffic stays inside a
     region. Size regions so the region clock stays shallow (guidance about 3-4 mm span, about 1-1.5 ns insertion). The gate is the
     derated margin in d, not these numbers.
  b. Clock follows data. Each region has its own local tree/spine. Region clocks are fed along the inter-region link graph
     (neighbour-forwarded, or from a shared spine running along the links). No region hangs off a deep die-wide tree.
  c. Links. Neighbour links are registered hops placed along the clock spine. Far links are chains of neighbour hops that cross
     regions through fixed-latency mesochronous crossings. The crossing design follows the MESO-COUNT-1 verdict: count-aligned if
     proven, otherwise the current ring with a per-crossing margin. The 10-14 static schedule stays: no runtime credits/backpressure on
     production paths.
  d. Gates unchanged: die GRT0 incl clock; die STA related pairs inside regions; landed_phase_ocv derated margin >=100 ps TT and FF on
     every crossing; token pass. NUMBER-CHECK before quoting.
  e. Rework order per die: traffic matrix -> region map with a locality score (bit-mm inside vs across, crossings, worst unshared
     clock per crossing) -> re-plan event (one source for the die) -> region clocks -> crossings -> gates. Existing closed cores are
     reused; only partition/plan glue changes, unless a core straddles a region cut.
  f. Lanes that build a die-wide clock as the release form stop. Their reusable parts (M8 row reservations, streets, PG) move to
     the locality form.
- 12.14 FASTER CLOSURE (OWNER 2026-10-27 "agree with your changes to close faster" + "I don't agree with working on one die first.
     work 5 dies in parallel"). Changes to how we work; no gate threshold changes.
  a. RULE FREEZE. The binding set is: locality first (12.13); fixed-latency mesochronous crossings + static schedule; crossing margin
     counted after OCV + droop (landed_phase_ocv >=100 ps TT/FF); one plan source per die; NUMBER-CHECK on headline numbers; die gates
     (12.4a freeze gate, release = die STA real views + token pass). No new rule or hard check is added unless a MEASURED failure forces
     it; proposals are batched to the owner, never added by a lane or by COORD alone.
  b. ESTIMATE BEFORE BUILD. Every architecture choice (region map, clock feed, crossing form, plan event) gets a one-page analytic
     feasibility estimate first (delay/mm x span x derate, track demand vs supply, crossing margin). Build only if the estimate passes.
  c. ALL 5 DIES IN PARALLEL, one DIE OWNER lane each (S81, HEAD, QC, KV, HBM). The die owner holds the plan, the region map, clocks,
     crossings and gates for that die and may merge die-local changes (die plan/results/die-specific scripts) to main itself via the
     intel2 merge.lock with tests passing. Shared tools/flow/rtl/common go through the shared merge lane.
  d. ~10 LANES total: 5 die owners + shared merge/flow + locality/estimate tool + crossing (MESO-COUNT/OSS-MESO) + open clock tools
     + open hierarchy tool. Current short lanes finish; their follow-ups go to the die owner.
  e. COORD answers every ASK within 30 min; with no answer the lane's stated default applies.
  f. GATES THAT EARN THEIR PLACE. Keep checks that have caught real failures; flow canaries run in the background and do not block
     a row unless they show a regression; no serial gate chains where checks can run in parallel.
  g. Once OSS-HIER works, regions become hierarchical partitions to cut the number of hard cores.
- 12.15 OWNER DECISIONS 2026-10-27 ~23:2x ("1.(a) 2.(a) 3.(a) for now, the top priority is closure. accept performance reductions and
  keep safe clocking and routing").
  a. COUNT STRAPS. The 1.8 strap rule is extended from ID straps to crossing-configuration straps: count K, PAD and related
     count-aligned constants may be strap_* input pins tied at the parent. They follow all four 1.8 conditions: declared, quasi-static
     with false_path, TIEHI/TIELO at the pin, and LEC per master against every constant variant used. Ring DEPTH stays a per-type
     parameter, set to the largest any instance needs. Do not type-split per K signature; the KV 119 variants are dropped.
  b. SPICE-CALIBRATED CLOCK IN DIE STA. Die STA gates scale clock-network arrivals by the measured OpenSTA-vs-ngspice factor
     (data/asap7_bufx24_spice_cal.json: x1.0485 TT, x1.0552 FF; plan tools may use x1.05). Data-path derates (droop (a)+(i)) are
     unchanged. A crossing that fails only with the factor is fixed structurally (PAD+1 or D8).
  c. CLOSURE OVER PERFORMANCE. The release takes the throughput the safe locality form gives. HBM may land below the 1906 tok/s floor
     (about 1700-1770 tok/s priced). Never trade safe clocking or routing (in-region spread <=150 ps incl. OCV+droop, CA margin
     >=100 ps, GRT0 incl. clock) for throughput. Latency hiding is optional and only where it costs no closure risk. The same applies
     to all dies: added crossing latency is accepted, and the static schedule absorbs it.
  d. (OWNER 2026-10-27 ~23:5x "yes to both") QC SMALLER REGIONS IN PARALLEL. QC tries smaller regions, each with a plain balanced
     CTS tree, at the same time as the clock-builder bug fixes. Whichever first reaches in-region spread <=150 ps (incl. OCV+droop,
     x1.05 clock) wins. Added crossing latency is accepted under (c). The clock mesh (12.8e) is now third choice.
  e. DETAILED-ROUTE TRIAL PER DIE (estimate run, not a gate). Once a die's region map is stable, route one representative region
     with real core views through detailed route (DRT), plus global route with clock. Report DRC count, overflow and pin access.
     Limit 400k cells per run. The results feed the freeze gate early; they never block a row on their own.
- 12.16 COUNT-ALIGNED CROSSINGS, SAFE BY DESIGN (OWNER 2026-10-28 07:29 PDT: "maybe we need to go with count aligned buffer. make sure the design
     is safe by design rather than tweaks"; context: CA-OCV-1 showed every earlier CA pass lacked clock OCV/droop).
  a. Every clock-region crossing on a production path is a count-aligned (CA) landing buffer with a fixed latency. No async/elastic
     FIFOs on production paths; the 10-14 static schedule is unchanged.
  b. Safety comes from the plan, not from tuning:
     (i) Bounded unshared clock by construction. Crossings follow the clock-forwarding graph (12.13b/c): a data link is a clock-tree
         edge (a tree node at the crossing), or it closes a SHORT tree loop. The plan reports the unshared clock per crossing; far links
         are hop chains of neighbour crossings, never one crossing between distant tree branches.
     (ii) The uncertainty bound per crossing is computed at plan time with the ONE shared model (STA phase + 0.21 %/mm AOCV + shared
         droop + spice scale, clock_variation=table) on the unshared clock only.
     (iii) Depth comes from a small standard set (DEPTH 8 or 16, each with an RTL proof), chosen so the window covers the bound plus
         the >=100 ps margin on both sides. Count K comes from the planned arrival centre.
     (iv) Reset release to both counters is planned and checked with the same model; reset is a crossing.
  c. NOT a primary fix: hand-tuned per-crossing PAD/K, per-pair tree-parent overrides that rescue a failing crossing, or clock trims
     or pads for a crossing. Allowed only as ledgered residuals (<= 5 %, v5.1) after (b) passes. A tree-parent choice the planner
     derives from the clock tree is part of (b), not a tweak.
  d. Proof: the plan-time check gates the plan event; the same check reruns on built clock arrivals before freeze; NUMBER-CHECK on
     headline margins. No new gate threshold: the gate stays CA margin >= 100 ps TT/FF incl. OCV + droop.
  e. OWNER 2026-10-28 07:33 PDT: "I suggest fixing the unshared paths of the clock trees for all the 5 dies. this is the root cause." On ALL 5 dies
     the release clock form is the LOCAL form (12.13b): region clocks forwarded from a neighbour, or fed from a spine along the
     data links, so each crossing shares its clock up to a tree node at the crossing. Die-wide trees, H-trees and deep landed
     roots that leave multi-ns unshared clock on crossings STOP as release forms. Deeper buffers (D8/D16) are chosen only after
     the local form, from its computed bounds. CLK-LOCAL-EST-1 gives the per-die estimate; each die owner turns it into its plan
     event.
