# Actual endpoint, valid gearbox, FEC and finite window

The gate instantiates two actual SRAM-backed `ot_hgi_coll_static_link_capture`
endpoints (TX6/RX2), two 613/487 frame wrappers, the unchanged root-proven
`hfd_serdes487_static_window`, actual rooted KP4 encoder/decoder arithmetic,
and the real finite raw-word CDC. The root's allowed PMA analog model remains
inside the FEC wrapper. A bit is flipped every third PMA cycle, within KP4's
correction capability. There is no ideal frame bypass or metadata-only delay.

Every control is compiled before execution. Reset releases at edge 8, endpoint
epoch starts at 450, and the TX gearbox starts at 497. Frame j is accepted at
A=498+floor(613*j/487); SRAM write/read are A-11/A-7 and endpoint TX is A-1.
The first actual FEC input is sampled at 499. Fixed capture start 600 reserves
601..2648; fixed CDC read start 608 reserves 609..2656, exactly 2,048 words.
The unchanged root-proven FEC capture age is 102 edges. The fixture checks each
decoded word against the actual sampled encoder input at that exact age and
each CDC word against its statically scheduled window index.

RX gearbox starts at 609 and samples the finite read stream at 610..2657.
For last-word index k=ceil(613*(j+1)/487)-1, its frame is recovered at 610+k,
wrapper output is registered at 611+k, endpoint capture is 612+k, and RX2
publication is 614+k. No observed arrival, lock or queue state chooses issue.
Lock/status are checked as outcomes. The 300 meaningful frame reservations
contain 234 exact payloads and 66 genuine idle frames; all remaining captured
transport slots carry idle while the finite window drains.

The independent endpoint scoreboard checks payload and exact valid edges. An
additional word scoreboard records actual FEC input words and checks all
2,048 decoded plus all 2,048 CDC read words. Valid-bit flip, missing receiver
word-valid, a deliberately corrupt word before encoding, and endpoint PHY-down
controls require their expected missing-frame/gearbox/CRC/TX-abort cause. The
separate actual decoder Forney MUT2 must fail the exact decoded-word check.
The positive workload is finite; no post-window operating contract or unbounded
continuous-window throughput is inferred.

This is an ideal same-phase 833.334 ps clock-family numerical integration gate.
Measured physical clock phases, frequency drift, physical FEC/endpoint routing,
link recovery, G96 integration and token throughput remain open. Application
bandwidth before idle is 64*487/613 = 50.845024 bytes/cycle; 545/8 bytes/cycle
is only the logical flit face's peak, including metadata.

Run `tools/hbm_io/run_fec_endpoint_gate.sh OUT 0` under admitted 8 GB/4 threads.
It builds once and runs four independent negative scenarios in parallel after
the positive. `... OUT 2` builds the actual Forney mutant and requires failure.
DUT files are byte-identical to root 262d5e14a. Initial fixture failures (1 ps
precision rounding the post-edge 1 fs observation to zero, then observing a
cycle-dependent corruption reference before delta settling) are retained in
the evidence. The fixed fixture samples the encoder input just before the
edge and observes registered outputs one femtosecond after it.
