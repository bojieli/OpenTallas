# HBM static collective successor

Owner HANDOFF0an requires compiler-fixed cycles for all on-chip HBM paths. The historical credit-based P2P design and its physical views remain evidence of the earlier design, not the production successor.

The successor contains actual fixed-cycle quadrant capture/switch RTL, a four-stop 2x2 ring with native FP32 serial/tree arithmetic, a full-width RGX/TKW sector writer, and an HBM545 specialization of the existing native SRAM/CRC static link. Positive and mutation benches exercise these DUTs at their real widths. `evidence.json` identifies the exact scope and receipts. The compiler transport backend emits calendar words consumed by actual quadrant RTL; it is not the full production instruction source or an end-to-end collective implementation.

The switch now includes a real input face register before its output stage. A source captured at C reaches its output pin C+2, and the compiler sink instruction is presented at C+1. Ring state read selectors are separately reserved one edge before their consumers. The native adder remains LAT8; the explicit state-read boundary moves the eight-tag serial wave's last result to65 and tree to49. Physical relay edges must be added to both calendars.

The static VM writer is a local/mirror sector transport. It does not implement HBM-space writes or replicate a mirror across slices. The compiler must schedule four actual slice writes for replicated results. `launch_done` means launch of the high sector, not SRAM commit. Actual bank composition and HBM-stack block staging remain required.

The static link has actual native storage and CRC hardware, with normal TX3/RX1 timing. `retry_requested` denotes an exceptional abort request. Recovery drain, replay and restart are still unimplemented. The ordinary schedule has no credits or backpressure. The normal codec uses64 frame slots per explicit epoch; the production compiler must account for epoch drains and forbid stale identities.

`physical_contract.json` lists real leaf modules, clock roots, width/face proposals and unresolved requirements. No assigned final outline, CTS insertion, routed TT/FF sign-off, full operation price or die qualification is claimed. Earlier CLOSED credit FIFO and ring views cannot be substituted for these new modules. Final production qualification requires a complete actual producer/issuer/data-path join and immutable-price measurement at the correct shape.

The collected historical G8 diagnostic passed image equality, but used n5120 and G8. The priced DeepSeek operation uses n1024 FP32 input, G96 with subgroup8 and n12288 BF16 output, at1325.9 cycles. Averaging5199/4 from the different diagnostic is not a valid rate acceptance.
