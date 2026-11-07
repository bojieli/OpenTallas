# Rules for per-core lanes (COORD 2026-11-05 19:xx). Read this fully before acting.

Project: OpenTallas, ASAP7 five-die closure at 833 ps (1.2 GHz). Dies are S81, HEAD (s81_head), QC (qwen_compute), KV (qwen_kvsys) and HBM. Your job: get ONE hard core signed off and counted.

Shell / git
- FIRST `cd /` in every shell. Your shell starts in the owner's checkout /home/ubuntu/OpenTallas. Never run git or edit files there; a hook blocks mutating git there.
- Work in your own clone or worktree on a fleet host, e.g. `git clone` the central repo intel2:/home/ubuntu/OpenTallas into scratch. Use git -C only on your own trees. No `git add -A`, no force-push, no stash. Commits end with "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>". Push branches named claude/<lane>-1105.
- Disk (COORD 11-06 12:2x): never make a fresh full repo copy (~50 GB each filled epyc4). Use `git clone --filter=blob:none --sparse` + `git sparse-checkout set <dirs you need>`, or a `git worktree add` off a clone you already own. Prefer `git worktree add` off a clone already on that host. A blob:none partial clone must use --sparse and set the sparse dirs BEFORE any checkout; a full checkout of a blob:none clone fetches blobs one by one and wrote 44 GB on epyc4 (12:5x). Delete your own clones/kits when you park unless they hold a result someone must collect.
- main changes only through ROOT-MERGE-46 (the current merge lane): post READY with branch@sha.
- OWNER 11-06 21:2x: "do not wait for them to merge before rebuild." Build any READY fix at once from its branch head on the host with the most free memory and disk (COORD 22:1x: epyc2 scratch3, intel1, intel2 first; epyc5/epyc6 scratch is nearly full, check df); re-sign on the main tag after the merge to count.
- Hosts: intel1, intel2 (= "localhost" in ot-run), epyc2, epyc4, epyc5, epyc6. Use `ssh -n -o ControlPath=none <host>`. ot-run lives on intel2: `~/.local/bin/ot-run` (--status, --hosts, --mem, --threads). Builds go through ot-run. Small probes may run directly in docker with a memory cap. No heavy jobs on localhost.
- Scratch: /srv/opentallas-scratch2/claude/<lane> on any host; root-disk scratch3 is also allowed.
- Kill only exact PIDs/containers you started. Never pkill -f. Never print keys. Never touch ~/.codex, ~/.claude (except your own job tmp), /archive, /home/ubuntu/closed_archive, Codex files or owner VMs. Never delete data you did not create.
- Timestamps: always $(date). Use python3 -I.

Method (OWNER rules)
- Use safe forms, not retries or knob tweaks. After 2 failed attempts on a form, RE-FORM to the conservative OpenROAD form: <=150k cells, util <=0.45, registered faces (in/out flops at the pins). Perf loss is OK.
- Adding cycles at core pins is cheap (compiler + token only). Use it freely, and declare it in the post as "PIN CYCLES".
- RTL changes must be proved: yosys equiv or lock-step bench vs the old RTL, with mutants caught. The kit LEC must be EQUIVALENT, so do not waive differs.
- Late-stage ECO (eco_loop on the routed DB) is OK for understood local near misses.
- Only sign-off blocks; pre-build checks are advisory. Sign-off = TT setup >= 0, FF hold >= 0, DRV/DRC clean, LEC EQUIVALENT. A hold miss that sits only on io ports is NEEDS_PARENT, which counts.
- Counting: the routed DB must be re-signed on a current flow tag (resign.py, PROVENANCE kind:resign with LEC EQUIVALENT). Then post READY-COUNT with the path.
- 2-h rule: a job with a flat log for 2 h is hung. Check that the CPU is busy before stopping it.
- Estimate before you build. If your estimate shows the form cannot close, say so and propose the next form.

Posting
- Append to ~/coord/lanes/COORD-REVIEW-QUEUE.md (branch coord/state) in this format: `- $(date '+%Y-%m-%d %H:%M') PST STATE|READY|READY-COUNT|ASK|RESULT|PARKED [<LANE> -> COORD, <die owner>] ...`, with [CHECKED host path] evidence for every claim.
- Commit with `timeout 280 ~/coord/bin/coord-commit.sh "<lane>: msg" lanes/COORD-REVIEW-QUEUE.md`, then verify on origin/coord/state.
- Post at least every ~60-90 min while builds run.
- ASK only on real forks, and always state a DEFAULT that applies after 30 min.
- Plain short English; no invented jargon.
- When done (counted, or parked with a clear next step), post PARKED/RESULT and return a short report.

## OWNER 19:3x: parallel safe-by-construction versions
For every failing core, run at least 2 versions at the same time: version A (the targeted fix) and version B (safe by construction). B means: registered input AND output faces (pin cycles OK); util <=0.45; <=150k cells (split if larger, proved by equiv/bench); short-reach placement (macro corridors / regions); a reset tree instead of one high-fanout reset. Build them in parallel via ot-run, never one after the other. The first to sign off wins; then stop only your own other containers. Name the kit dirs <core>_vA / <core>_vB so the counter sees both.

## OWNER 11-06 21:5x: conservative fixes + visual layout inspection (ALL lanes)
OWNER verbatim: "it is important to make conservative fixes and visually inspect the layout for all your subagents to remove congestion".
- Every failing core/type gets a CONSERVATIVE version IN PARALLEL with the targeted one:
  - registered faces (flop at every pin, fanout <=8 per face flop);
  - util <=0.40 for cores and <=0.35 for types;
  - <=100-150k cells;
  - signals <=M6;
  - memories on the edge with a fixed channel;
  - feedthrough flops every <=450 um;
  - +1 PIN CYCLE for setup-reach paths;
  - a pipelined local reset tree.
  Performance loss and extra cycles are accepted. Declare added cycles as PIN CYCLES.
- VISUAL CHECK at three points for EVERY build you launch:
  1. after placement (3_place);
  2. after GRT (congestion map);
  3. after route.
  At each point, render PNGs (cell density + GRT congestion/overflow heatmap + macro/pin layout) and LOOK at them with the Read tool on the image.
  - In your post, name every hotspot: location, layer, cause (macro channel, pin clump, station clump, long fanout).
  - Remove a hotspot by a structural change: move logic out of the corridor, spread pins, add a channel, lower util, split the block.
  - Never remove it with router knob retries.
  - Post [CHECKED host path.png] for each render.

### OWNER 11-06 22:0x: bad-smell checklist for every visual check (find AND fix)
OWNER verbatim: "the visual layout checks should also find the fix obvious bad smells in physical design, for example pins on opposite sides, congestions in pins, too narrow channels, long diverged clock paths, etc."
At every visual check (place / GRT / route), look for each smell below. In your post, write SMELLS: <list or none>, with [CHECKED path.png]. Fix each smell structurally before the next stage; never pass it on.
1. Pins on opposite sides: a signal enters on one face and its logic or partner pin sits on the far face, so the wire crosses the block. Fix: move the pins to the side of their logic or partner, mirror the block, or register at the face.
2. Pin clumps: many pins packed on a short edge, causing congestion at the pins. Fix: spread pins along the face (<=50% track use on the pin layer), use two layers, or put the bus over a longer edge.
3. Narrow channels: a gap between macros, or between a macro and the edge, too narrow for the wires that must pass. Fix: widen to the track budget, move the macro, or route around it.
4. Long or diverged clock paths: a clock entry far from its sinks, branches serving sinks far apart (launch and capture on separate long branches), or clock wires over macros. Fix: move the clock entry to the sink centroid, build a local tree per region, or register the crossing.
5. Long single-driver fanout: one driver feeding sinks spread more than 100 um apart. Fix: replicate or register the driver.
6. Crossing data flow: buses crossing each other or doubling back (spaghetti in the flight lines). Fix: reorder pins, block placement or lanes.
7. Logic far from its pins: flops sitting deep in the block, away from the pin they serve. Fix: register at the pin, add region constraints.
8. Density hotspots: local util >0.7 next to empty areas. Fix: spread the logic, add a blockage, or lower util.
9. Macros blocking the pin edge or the clock entry. Fix: move the macro so pins and the clock have a clear path.
10. Feedthrough wires crossing the block with no repeater or flop within 450 um.
Not on this list but obviously wrong? Fix it too.
- NEVER run git reset in the shared ~/coord (KW-FIX-25 11-06): it drops other lanes' commits before they push; 9 commits, 20 queue lines lost on 11-06. Just append, then coord-commit.sh, which merges origin itself.

## COORD 11-07 03:4x: why conservative forms still fail, and what conservative means from now on
Evidence: 82 failed forms from the last 30 h, plus views of opsa_rest, q2nf_qout, q3_vm_core, split3_ctl_rest_1c, n12, hd_spn. All numbers are targets, not gates: only sign-off blocks.
Settings like util 0.40 do not make a form safe. They were often met by making the die bigger, which adds distance and clock depth. Judge a form by what the placed DB shows.

1. COMPACT, NOT EMPTY (corrected 04:4x: low fill alone is not the fault; S81 leaf has real staged feed-through and fails on one macro pin bus, so check where the logic spreads and where overflow sits). Fill = cell area / die area. Seen: opsa 4%, rest_1c 5%, q3vm 6%, qout 14%, with logic in clumps and face flops on far edges. If fill is under about 25%, say why the outline is that large (slot, pin count, or habit) and shrink it, fold it, or split it. Wide buses: use more pin layers or tighter pin pitch, so pin count does not set the outline. Local 0.40 density stays.
2. BUDGET BY DISTANCE AND DEPTH. Before route, take far-pin-to-far-pin distance and stage count from the placed DB, and ps/um from your own routed paths. If a path cannot reach in one cycle, add a stage or a pin cycle along the long side. Pin cycles are cheap. Do not wait for sign-off to find this.
3. SHALLOW CLOCK. Contract target at the core: about 250 ps TT, FF reference 202.5 ps on HBM kits. Of 58 forms with the 202.5 ps reference, the 39 with FF insertion over 300 ps have median FF hold -144 ps; the 19 at or under 300 ps have median -10 ps. In 20 port-dominated forms, hold miss tracks (insertion - reference), correlation 0.93. Sink span sets depth, not flop count: opsa has 5.5k flops and 359 ps; n12 has 26k flops and 259 ps. Root the tree at the sink centroid, do not cross empty area, and keep it out of macro stacks. Read the post-CTS insertion and estimated hold before spending route time.
4. SPLIT HOLD BY WHERE IT STARTS. Read std_min_start in signoff/ff/corner.json. "port" = starts at an input port, the parent's obligation. "other" = any other start, the core's job. "reg" is only a 0/1 flag: it stays 1 when any register-launched path violates. Do not pad port-start misses. Fix "other" with hold ECO on those endpoints. Port-only + setup + DRV + LEC clean = LOCAL_PASS_NEEDS_PARENT, which counts. The in-core tap spread stays a real parent cost, so rule 3 still applies.
5. DRIVE AND WIRE, NOT JUST FANOUT. Fanout <=8 does not catch wire load. 49 of 74 distinct failed results have more than 100 slew violations; single gates reach 186-462 ps. Limit buffered wire length, resize drivers, and replicate high-fanout control in RTL per group.
6. MACROS: size channels from track demand, keep the clock spine outside stacks. Seen on bksel (red channels) and eng_rr_e (700 um double-back, 120 ps tap spread).
7. NAME THE CLASS BEFORE THE NEXT FORM. SPARSE (rules 1-3), DEPTH (logic stages, e.g. n12: no macros, 33 stages), CHANNEL (rule 6), or PORT-ONLY (rule 4, no rebuild). Post "CLASS: ..." with "SMELLS: ...".

## OWNER 11-07 05:1x: pin cycles and redesign, never retries (ALL LANES)
OWNER verbatim: "use pin cycles on the hard cores. never use more place and route retries. queue the untried cores now. move the cores of KV, QC and S81 to critical list. If no conversative forms are running or it is still failed, you should visually inspect the geometry and redesign"
- HARD CORE = PIN CYCLES FIRST. Add cycles at the pins for setup reach and depth, declared in the kit (added_rx_clk_PIN_cycles), proved by LEC/bench, reported for compiler and token rescheduling. Do not hold back to save cycles.
- NO RETRIES. No new place-and-route run of a form whose RTL, pin cycles, macros, outline or clock structure are unchanged: no seeds, knobs, density tweaks or repeat runs. Every new build's post names what changed and which measured problem it fixes. Running builds finish and are read.
- LATE ECO stays only for a real near miss: small, understood, local misses (a few endpoints, a few ps, a small slew count). A large or failing-again ECO is a redesign case.
- NO CONSERVATIVE FORM RUNNING, OR IT FAILED: render place, clock, congestion and route, Read the images, name the geometry problem, and redesign (pins, macro positions, outline/fold/split, clock root and spine, RTL stages). Post "GEOMETRY:" and "REDESIGN:" lines. Do not rebuild before that.

## OWNER 11-07 05:3x: late-stage fixes, one iteration, near misses only (ALL LANES)
OWNER, verbatim: "real near misses should still use late stage fixes, but do not use multiple iterations of late stage fixes and do not use it to fix large misses"
- One late-stage ECO iteration per routed form. If it does not sign off, no second iteration: GEOMETRY + REDESIGN, pin cycles first.
- Near miss, COORD's working numbers: setup/hold worse by no more than 30 ps on no more than 100 endpoints, no more than 20 slew violations and worst slew under 200 ps at the limit-relative report, DRC under 50, and the cause understood and local. Above that = large miss: no ECO. Port-only hold needs no ECO; it goes to the parent.
- An iteration already running finishes and is read. Nothing starts after it.
