# Owner directives for final closure

Confirmed by the project owner on 2026-10-07 after reviewing the instructions given to Claude during the preceding day. The owner approved the recap and requested that it be saved, committed, pushed, and followed. These directives govern the continuation of Qwen ROM, DeepSeek ROM S81, and the HBM accelerator.

Finish the actual implementations as quickly as practical, using parallel computation and decisive structural changes. Accept the measured cost, preserve correctness, and report what the evidence supports. Read these directives with [AGENTS.md](../AGENTS.md) and the [integrated physical plan](INTEGRATED_PHYSICAL_PLAN.md). Where earlier project instructions conflict with these later owner decisions, these decisions take precedence; unrelated requirements remain in force.

## Autonomy and ownership

1. **Finish all three targets autonomously.** Make technical decisions, resolve problems, and continue without repeatedly asking the owner for permission. Restore stopped work from its actual sources, transcripts, artifacts, and live processes. The earlier transfer from Codex to Claude is now reversed: Codex carries Claude's unfinished work.

2. **Every open element needs an owner and an actionable fallback.** Check for orphaned work and missing elements. Resume agents whose jobs remain active, deliver handoffs promptly, and make sure proposed fallbacks enter execution when their prerequisites are ready. Preserve useful progressing jobs and partial builds instead of duplicating them.

3. **Communicate efficiently.** Technical coordination, repetitive status reports, and token-heavy polling must not replace engineering progress. Make decisions within the authorized scope, report material findings and measured costs, and keep the owner informed of real blockers.

## Closure policy

4. **Physical closure takes priority over performance cost.** The owner's latest instruction is: “Go with the closure regardless of what cost on performance.” Earlier roughly two-to-three-percent allowances are no longer ceilings for closure fixes. Measure every added cycle, compose the total performance, area, die-count, communication, and energy costs, and report them honestly. This does not authorize speculative performance credit or bypass correctness and physical qualification.

5. **Accept SS setup slack of at least +15 ps and FF hold slack of at least +15 ps, with DRC 0**, under the agreed clock, uncertainty, and interface budgets. The streaming sign-off clock remains 1.2 GHz, with 60 ps setup and 25 ps hold uncertainty. Design with generous margin, but do not redesign a passing block merely to reach the older +40 or +60 ps targets. A distinct slower or enabled domain must be implemented, verified, and priced; changing an SDC alone does not establish it.

6. **Fix difficult blocks structurally.** Add sufficient pipelining, simplify logic, partition into smaller hardened blocks, replicate high-fanout control, and improve boundaries. Do not repeatedly squeeze the last few picoseconds through layout settings. Assemble dies hierarchically from real hardened block views rather than relying on an enormous flat implementation.

7. **Plan timing from the floorplan and clock distribution.** Use top-down budget sheets for every block and a die clock plan. Input/output budgets and clock arrival must agree with that plan. Calibration checks the assumptions. Hold repair must use the correct corner model, and final timing must include the real boundary obligations.

8. **Launch structural alternatives immediately and in parallel.** Once candidate RTL builds and elaborates, start its admitted place-and-route while exactness testing runs alongside it. Do not wait for a small-change route to fail before launching an aggressive fallback. This later instruction supersedes the earlier single-variant preference. Exactness and negative controls still gate adoption; a failed exactness gate makes the candidate route ineligible for adoption. Model sizing and resource admission remain prerequisites.

## Interfaces, arithmetic, and area

9. **Use registered die interfaces and adequate flow control.** Put relay stations beside block pins, targeting a final die-wire segment of approximately 100 micrometres or less. Where a same-cycle ready response cannot meet timing, use credit-based flow control sized for the actual round trip. Price every added hop. Stations, queues, and protocols must exist in the implementation rather than only in a diagram or timing abstraction.

10. **Keep bit-exact accumulation as the first choice.** For difficult feedback loops, use half-rate operation plus additional pairs, copies, or area where needed. Changing accumulation order is allowed only if the exact approach proves impossible for the specific element, with a quality check and explicit disclosure. Half-rate qualification includes production clocking, enables, crossings, and interface behavior; it cannot be established by a relaxed timing constraint alone.

11. **Spend area or add dies instead of squeezing congestion.** Plan corridors and regions around 55–60 percent utilization. A hub with twice the area and investigation of doubled BF pairs are approved. Move problematic pins and rerun affected implementation. Include the resulting silicon, die-count, communication, latency, and energy costs in the model. Continue to use legal die outlines; add dies when necessary.

## Fleet and execution

12. **Keep the fleet busy; memory is the hard constraint.** Use all three EPYC hosts, smaller servers, and localhost subject to measured capacity. Higher CPU load is acceptable; artificial admission limits must not leave hosts idle. Check actual headroom rather than assumptions. Use NVMe scratch, retain useful partial builds, and safely reclaim obsolete intermediates while preserving unique sources and evidence. Keep EPYC3 in the monitor. Maintain the requested key-based SSH access, including the owner's MacBook Pro key, with password login disabled; never store credentials in project evidence.

13. **Follow through on persistent problems.** Execute the HBM VM split fallback in parallel, pursue a simpler design for the HBM norm-engine synthesis bottleneck, and resolve the route-time hold-corner issue. Maintain ownership through terminal results and integration rather than leaving these as proposals.

## Target scope and publication

14. **Qwen ROM is reopened for full closure.** The owner's “Yes, reopen for Qwen” supersedes the earlier freeze. Produce real routed views for previously assumed masters, repair blocks below the current acceptance line, and complete full-die detailed routing, SS/FF timing, layout checks, and IR analysis. Interim views may exercise integration early, but cannot establish final closure. The same final physical obligations apply to DeepSeek S81 and the HBM accelerator. Existing research-scope limits in the integrated plan remain unchanged.

15. **Publish numbers supported by committed evidence.** The owner approved the measured approximately 430.56-micrometre Qwen relay spacing and requested consistent updates to the documents, Architecture Atlas, Chip Explorer, and energy tool. The owner also requested a new Qwen speculative-decoding evaluation including those relay costs. Recompose subsequent closure changes before updating claims, retain evidence scope, and do not leave stale performance headlines. Keep failed verdicts and historical records intact.

## Superseded instructions

| Earlier instruction | Current instruction |
|---|---|
| Qwen ROM is finished and frozen | Qwen ROM is reopened for complete physical closure. |
| Closure costs must stay near an earlier small percentage ceiling | Close regardless of performance cost; measure and report the cost. |
| Every block must achieve the older +40 or +60 ps acceptance target | Accept at least +15 ps SS and +15 ps FF with DRC 0 and valid constraints. |
| Run only one variant or wait for exactness before starting route | Launch built structural candidates and aggressive fallbacks in parallel; exactness gates adoption. |
| Repeatedly tune a congested layout to fit | Add area, move pins, partition, or add dies, and price the change. |
| Conservative CPU-load assumptions can keep the queue idle | Schedule from measured capacity, keep hosts busy, and protect memory headroom. |
| Claude is the sole active coordinator after Codex stopped | Codex restores and continues Claude's work with its subagents. |

The microarchitecture-model-before-build requirement, immutable source and failure evidence, appropriate exactness and quality gates, resource admission, and honest qualification remain binding. Optional speedups do not displace mandatory closure work.
