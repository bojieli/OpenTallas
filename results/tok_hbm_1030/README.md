HBM native VM continuation (2026-10-30)

Qualified bounded chain now covers actual source records1458–1558 (101 source
records) as684 native commands in fourteen phases. No RTL/arithmetic change.
The original unreplayed1537–1558 preparation is not adopted: wrapping exposed
phase0/1542 consuming a sector written by phase3/1540. A second source-order
hazard appears inside1545: earlier-row outputs overwrite later-row C scalars.
The original blanket two-phase reorder therefore fails, despite fitting VM.

The explicit cuts1537–1541,1542–1544,1545,1546–1558 restore original value order.
The HC_POST1545 first three rows remain scalar commands because native ROWX
independence fails; its next three rows retain a native array. Shared-weight SM
arrays remain grouped. Phase-private early publication exports nine HC sectors.

vm_pipeline.py walks actual boundary liveness backwards from the final cut.
Each source region retains downstream loads and untouched boundary sectors,
including partial-sector neighbours. This fixes the missing147504 publication
reported when linking directly against the older chain_attention artifact.
All fourteen phases fit the old262144-word VM; largest stays238592.

Reproduction (set compiler tools/image to the source snapshot in the prior handoff):
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_pipeline.py \
 --image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --scratch-base 0x1F00000000 \
 --cuts 1458:1473,1474:1527,1528:1536,1537:1541,1542:1544,1545:1545,1546:1558 \
 --out-dir results/tok_hbm_1030/pipeline
python3 results/tok_hbm_2249/check_chain.py \
 --shadow results/tok_hbm_1030/pipeline/link6 \
 --values results/tok_hbm_1030/pipeline/values0

Canonical source/value replay PASS2534778 read words,143856 final boundary
words,29 early sectors; wrong interstage epochs, missing drains and illegal
stripe controls caught. Real native HGI DMA executes added transfers; arithmetic
outputs remain tagged source versions, not numerical RTL execution.

Native boundary traffic6136704bytes, plus conservative unit drains, remains
UNPRICED. Each phase uses separate candidate linear HBM scratch; reservation is
explicitly false. Original source1458–1558 entry epoch publication, dynamic
expert boundary1559 onward, all other programme regions, actual numerical RTL,
mutable HBM execution and full physical calendar are OPEN. No whole-programme
fit, G5 or token-rate claim.
