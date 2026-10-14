# Isolated capture SS structural prototype

This branch is a prototype. It has no physical or native qualification and does not alter the immutable v3 route source9c12f4d15. The current capture stream continues on s81-spwfc-1013. Actual SS cones from frozen v2 identify three distinct issues: core write-enable logic(-133.35ps), serial read-pointer fanout through nine sequential BUFx3 buffers(-148.27ps), and core-to-serial state sampling through three hold buffers plus inversion(-72.32ps). The serial-to-core state crossing is+11.75ps. The epoch contract remains one PLL divided by3/4, one VCO tick of minimum cross setup, coincident-edge hold and60/25ps uncertainty. SS/FF is required for final native release; TT/FF element closure is only pathfinding.

The optional LOCAL_CTRL mode is enabled only in the x8 wrapper. Its structural changes add no data or valid cycle:

* Replace pointer subtraction/full comparison with equal low bits and opposite wrap bits. The identity holds for every binary pointer value at a power-of-two depth.
* Replace the hold-count subtract/compare with the exact Boolean identity !hc[2] || (wr && !hc[1]), including all8 count values.
* Capture complemented peer state and expose its complement at the same sampling epoch, allowing the native QN output polarity to remove an inverter from the crossing.
* Register a one-hot bank selector from the same next read pointer that updates rp. Each16-bit read slice retains its local selector bank. Selection equals current rp at every clock edge, rather than adding a pointer/data pipeline cycle. No additional CDC arc, timing exception, new clock root or transaction stage is introduced.

Default mode and positional LAG argument compatibility are retained. The focused equivalence test compares both default and local modes against the immutable9c12f4d15 FIFO, across four relative divider phases, random backpressure and independently repeated synchronous resets. The full capture exact/mutant bench remains required. Synthesis must confirm selector banks are retained, placement must verify the actual local cones, and actual routed SS/FF must pass before any qualification claim.
