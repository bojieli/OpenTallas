# OpenTallas design methodology (FROZEN v1, 2026-10-24 21:40 PDT)

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

5.1 Layers: partition signals and feedthrough <= M7; ft stations registered every <= 405 um. M8/M9 reserved for
    die clock spine, die reset and PG. [B#12 10-24] (see 9.3)
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

6.1 Setup at TT, hold at FF, uncertainty 60 ps setup / 25 ps hold, period exactly 833 ps. SS never gates (INFO only).
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
- 9.3 ALL signal routing (partition ft AND die-top nets) on <= M7; M8/M9 only die clock spine / reset / PG (dec. 12 supersedes the 10-22 M9-for-signals record). Tools drop M8/M9 ft; reach = 405 um.
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
