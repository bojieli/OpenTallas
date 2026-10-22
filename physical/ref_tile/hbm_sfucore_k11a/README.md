# SFU k11 registered diagnostic gather

SAFE design review before gates:
1. Pins: existing same-region ABI unchanged; long boundary links remain registered/landed.
2. Reach: per-lane partial -> pair -> side -> two inward relays replaces the flat 1.9 mm fault gather. Exact physical reach remains to be measured.
3. Fanout: every tree node has <=2 consumers; existing native32 source retained; full parent census must pass before floorplan.
4. Depth: per-lane address/source/scalar compare then registered OR tree replaces the 16-lane gather.
5. Storage: existing SRAM inventory unchanged; only control fault flops added.
6. Floorplan: same 1.9 mm parent with hard lanes; no shrink. Actual generated macro/child counts checked in native-first gate.
7. Clock: existing lane/store roots unchanged; tree uses existing engine clock. Physical gate must report per-region spreads and crossing timing. No clock waiver.
8. Schedule: five extra diagnostic edges in the fault paths; payload/valid/result edges unchanged. Existing positive and DROP13 fault-class bench plus normal split lockstep apply. Parent fault sticky is later; no early cancellation is claimed.

No physical PASS yet. Source4733c83d8 copied the paused incomplete k11 source bytes into this isolated branch. Current MAIN helpers are used locally without publishing helper changes.
