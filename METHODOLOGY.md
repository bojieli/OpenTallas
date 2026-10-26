# OpenTallas design methodology (FROZEN v4.5, 2026-10-26 16:5x; v4.4 06:39; v4.3 06:33; v4.2 06:15; v4.1 06:11; v4 06:07; v3 05:58; v2 earlier 10-26; v1 2026-10-24 21:40 PDT)

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
  restructure their CTS to meet it, shallow cores pad up. No early taps by design. Cores are rebuilt in parallel to it, signed cores included
  (owner 10-26). Early-tap branches are RETIRED (12.8): diagnostic evidence only, never a closure path.
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
  b. CPPR (OWNER 10-26 06:07, 12.8): the GATE number credits CPPR only to the last common H-tree/tree node (region root for same-mesh pairs);
     no credit at the mesh node. The mesh-node-credited number (COORD 10-26 early ruling) is INFO only.
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
  - 10-26 16:5x OWNER: core latency band/window = design target, die related-pair STA decides (12.3a) = CURRENT. Supersedes treating 250+-20/window<=20 as hard core FAIL. Same exchange: bottom-up landed fallback run IN PARALLEL now on every die, first to pass wins.

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
     offsets, post-CTS ECO padding/buffer swaps on the clock, mesh-node CPPR credit, gate-number relaxations.
  d1. (OWNER 10-26 06:11) ALLOWED as design: per-tap driver/stub sizing COMPUTED BY THE PLAN TOOL from plan geometry and loads BEFORE any
     block is built, deterministic, recorded and frozen with the plan. BANNED: any value chosen after a measurement (trims, offsets, ECOs).
     A measured miss goes back to the structure/plan model (12.8e), then the plan is re-frozen as one PLAN-DELTA.
  e. A measured failure goes back to the structure (plan or core architecture), recorded with its root cause before any rebuild.
  f. Existing results obtained with the banned means (QC early-tap 154/143, any stub-trimmed mesh result incl. KV c3t 63.95/54.71) are
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
