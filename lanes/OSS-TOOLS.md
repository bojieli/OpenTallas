# OSS-TOOLS: generic open tools (OWNER 10-27 ~19:1x/19:2x), branches claude/oss-*-1027, dir opentools/
2026-10-27 19:06 PDT COORD: OWNER: also start OSS-MSCTS-1 (macro-aware multi-source clock tool + circuit-sim verification), OSS-METAL-1 (top-metal planner), OSS-HIER-1 (macro-aware hierarchical flow).
  - Interface rule: ONE shared plan schema in opentools/common/ (macros, internal clock insertion, streets, PG stripes, regions, budgets), owned by OSS-CLKPLAN-1; every tool reads and writes it.
  - Split of duties:
    - OSS-CLKPLAN-1 = streets + budgets + predictor + track demand COUNT.
    - OSS-METAL-1 = actual track ALLOCATION (clock rows/shields/PG interleave) on that count.
    - OSS-MSCTS-1 = builds the tree/mesh on the allocated tracks.
    - OSS-MESO-1 = region crossings.
    - OSS-HIER-1 = region grouping + abstraction + top-down pin/budget + die STA on abstracts.
  - No publishing without owner OK.
2026-10-27 19:11 PDT COORD (OWNER "yes"): scope additions, binding for this lane and its successors:
  - OSS-MSCTS-1: REGION MODE FIRST. Build and verify one landed region (a QC slice) end to end before any die-wide demo, verified with ngspice vs STA and a skew report.
  - OSS-MESO-1: a FORMAL proof of deterministic start-up latency (ring pointer init under reset/start broadcast, every allowed phase |d|<P/2) is a REQUIRED deliverable, not optional; simulation alone is not enough.
  - Guidance for OSS-HIER-1 / OSS-CLKPLAN-1: aim for 1 clock region == 1 hierarchical partition in the shared schema.
2026-10-27 19:15 PDT OSS-CLKPLAN-1 START (Claude). Branch claude/oss-clkplan-1027 (from main abbbffac9), dirs opentools/common/ (shared plan schema 'opentools.plan/1', owned here; first push soon, other OSS lanes read it) + opentools/clkplan/. Run data intel2:/srv/opentallas-scratch2/claude/oss-clkplan. Public demo input: ORFS asap7 swerv_wrapper floorplan (ot-run on intel2, running).
2026-10-27 19:15 PDT COORD (OWNER: "the open tools are important"): planning-time check added, from the LAND-HEAD-2 failure.
  - Measured failure: HEAD's landed crossings hang off a 6.1 ns die tree and carry 4-6 ns of unshared clock. Derated margin -209 TT / -121 FF.
  - OSS-CLKPLAN-1: the predictor must compute the UNSHARED clock delay per crossing pair, apply the shared AOCV + droop model, and give each crossing a derated phase margin. A plan FAILS if any pair has margin <100 ps. Reuse the model in tools/s81_head/landed_phase_ocv.py (claude/land-head-2-1027@be648cbdd7) and generalize it into opentools/.
  - OSS-MESO-1: crossing insertion takes that margin as an input and refuses crossings below the margin.
  - OSS-MSCTS-1: region mode must support a "late split" objective (minimize unshared delay for the listed crossing pairs) and neighbour-forwarded region clocks.
