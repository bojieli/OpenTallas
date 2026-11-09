# Private KV PHY dead forwarded-clock event

The maxwire PHY pilot's worst d3 q[8..11] endpoints capture fh3, not rising-edge pi3 payload. The native PHY model explicitly describes fh/rh as combinational forwarded clocks. All six current generated PC variants use the declared core clock directly and never read these 32 packed face-data bits. They read exactly the 1,156 native PI payload bits.

event.py creates a private plan and asbuilt overlay. It reduces the six PHY-to-PC bundles to12/281/285/285/281/12 bits, preserving epochs, latency tables and every other type. An existing supported asbuilt.clocks rule identifies only the actual PHY fh/rh source pins as the existing core clock. It never classifies pi payload. No new clock domain, period, constraint, RTL default, plan of record or existing file is changed.

Scope: two PHY types and six unsigned PC types,192 direct crossings. It removes1,024 redundant wires and2,048 face flops over32 PHY instances. Data/reset cycle delta0. Every native PI bit still crosses the same two face-register edges.

Checks completed on the actual old and newly emitted private wrappers:
- All six PC variants: exact 32-bit dead set, no unindexed or hidden use.
- Graph rule:1,024 forwarded-clock source bits classified;36,992 PI bits remain payload. Mutant classifying PI as clocks caught.
- Actual old/new source-to-native-operand projections equal for12 PHY/PC combinations, all1,156 PI bits unique.
- Clocked face-register lockstep,12 combinations ×1,000 cycles: PASS. Live PI-bit mutant caught in all12 cases. E4 unit oth-ubuntu-1444726-1794137862, log intel2 ~/codex-kv-types-0222/phy_miter_new.otrun.log.
- Framework old-vs-old control was run separately, not presented as new-event proof.

Full private strict bind is running at /srv/opentallas-scratch3/claude/codex-kv-phy-deadclock-0222/bind; no full-bind PASS or physical result is claimed here. Only after strict report0, kit source checks and actual generated-layout image review may one PLACE pilot start. No batch or production adoption.
