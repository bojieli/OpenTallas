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
