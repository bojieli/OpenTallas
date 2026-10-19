TXRP takeover structural revision

Shared core TXRP=1 registers the SRAM read before the output pin flop. TX lane launch gains one edge; MU exact benches with TXRP enabled pass, including cut-through, landed and replayed traffic, and HOST/KS per-cycle comparison. The die schedule must price the extra off-die edge.

Safe-design review before gate:
1. Source pin flops and reset landing2 preserved.
2. SRAM-to-pin reach split by TXRP register; final placed reach pending gate.
3. Existing RX per-group pointers and reset-region copies preserved; synthesized fanout pending gate.
4. TX SRAM read and transport separated; RX structural head/AO222 retained; final timing pending gate.
5. TX payload SRAM preserved, no new runtime flop table.
6. Existing pin-limited outlines/inter-row channels preserved. Macro lattice/pin faces/area and density must be reviewed with PNGs after gate; no submit on failure.
7. io_hold_margin0.03 and route hold_margin0.045, reset_landing2; CTS pin spread pending gate.
8. Static scheduling preserved; +1 TX launch edge handed to S81 coordinator.

Gate logs: /home/ubuntu/scratch/codex-mu-endpoints-txrp-1019/.
