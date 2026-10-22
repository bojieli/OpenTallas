# s81sl_lepab_r1a

Regional structural successor after t5c/t5d one-root/1.6mm setup -0.9ns. Two native32 pair-A cores, C dispatch/registered onehot merge; all C<->A/B buses real D4K2 rings, three independent related CTS roots. Every path receives ordinary same-frequency STA (no data multicycle or async cuts). Two-edge matched outer lane payload/valid and reverse return relays; endpoint DR/CRED12 and peer CORE_CRED12. New ML E-face matched bus bands, old N-face fit invalid. Parent R0 land and existing ML E2 landing chunk placement pending, with +1 eachway owed if those stages cannot cover<=405um segments. Cycle model: +4 centre-to-pair, +5 pair-to-centre, +2 lane data/valid and +2 reverse returns, RTT+4. New strict view/ports required, no alias of old AB or CRED8.

SAFE checklist before first gate:
1 PASS source pin/region registers; local control/valid resets tree3 and equal7-stage ring forests; no payload reset.
2 FIXED planned regional topology: C first dispatch aroundy800; C->A writer691/readA648; C->B writer800/readB1070; native IN_PIPE/roq/write stages carry into compact pair cores. Lane two-edge relays, W pinbands, midpoint register stations. Crossings realD4K2 rings with conservative ordinary STA; actual reach must pass gate. MLface movedE; parent existing E2 chunks need coordinateproof before parentgate.
3 PASS mapped native4 max32 /0violations /0roleerrors over230399roots, full DR/CRED12. Native report hash/source manifest results/rtl/s81_lepab_regional_1021/native_r4_summary.json.
4 FIXED <=16-bit registered onehot merge slices; local replay decoders; no single-cycle A/B 1104-bit mux acrossmm.
5 PASS 20TX512x128 +20RX32x128 SRAM; RX logical12, no runtime flop FIFO; D4 landing rings are approved crossing infrastructure; outer relays2 only.
6 PASS macro origins from qualified pair-A lattice translated by43.2 multiples, >=20um channels andfull macro-free centre band. Epaired bus density5.11/um, W<4/um. Pin/lane-pitch-bound lowfill/aspect guidance; no die-fit claim.
7 FIXED three explicit related clock roots/IOdomains. No cross-root cuts or data multicycle. Real D4K2 ring semantics (5.050 phase80/160psPASS); gate TT/FF perroot spread<=80, io_hold .03.
8 FIXED composed hop model: +4forward/+5return, +2 each lane data/valid and reverse return (RTT+4), matched finite offdie12slots. Static regional schedule, no new runtime scheduling credits. Parent ML extraedges stillconditional until existing E2 chunkplacement covers everysegment.

Exact NB80 bench PASS400delivered/160landed, bothpairs/replay/finite return counts240perlane. Four causal fail witnesses committed; route runs current source benches again. Parent/die adopt only after actual72frame33x26reticle+corridorfit.
