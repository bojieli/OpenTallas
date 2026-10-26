# Registered SRAM endpoint successor

`ot_hgi_coll_static_link_pinreg` is a distinct wires-only composition. The
controller leaf owns all sequence counters and epoch/identity checks. Its
`bank_we`, `bank_wa`, `bank_ra` and `bank_data` outputs are register Q. Each of
four `ot_hgi_coll_static_pinreg_store` leaves captures every input at a flop,
including the read address. The unchanged native W141 replay SRAM leaf is
flattened inside that leaf. Its actual 64x512 macro read address therefore
comes from the local captured-address flop; no raw parent address reaches it.
The native two-age write bypass and actual macro are preserved.

The added controller launch and store capture change read-to-TX from three to
**five edges**: reservation/launch n; store capture n+1; native macro read n+2;
store dout n+3; controller q_pin n+4; registered TX n+5. Native ownership
commands are delayed two edges to match actual store operations. RX remains
one edge. Write commits at n+3 with native bypass available. All counters are
inside the control leaf, not in the wires-only parent. There are no credits,
acknowledgments, readiness gates or dynamic issue. The frozen TX3 endpoint
remains separate and unchanged.

The 613/487 integration calendar explicitly uses read A-6 and write A-10 for
acceptance A(j)=17+floor(613*j/487). The RX wrapper and endpoint calendar stay
capture23+k/publication24+k, where k=ceil(613*(j+1)/487)-1. Idle and valid are
transported in-band. `hgi_collective_pinregistered_endpoint_model()` prices
the extra two edges before RTL build.

The native bench checks 1,024 frames per direction at full payload width,
16 physical slot laps, one epoch and 96 fixed flight edges. Its scoreboard
requires TX5/RX1. Eleven mutants cover CRC, sequence identity, actual native
store corruption, missing/late ingress, missing publication, ownership
collision, observed-write absence, stale same-low-slot RX/TX sequence and
unpublished read. The separate 613/487 vehicle checks 234 exact payloads and
66 idle slots, plus valid flip, missing word, corruption and PHY-abort faults.

`run_pinreg_face_audit.sh` synthesizes actual controller/CRC/store RTL with
four opaque real macro cells, then checks all external outputs, controller
launch Q, state input capture D, state dout Q, controller read capture D and
all macro input Q. The macro read address must specifically equal ra_pin Q.
A raw-address mutant must fail. Mapped generic registers measure control
3,201 and four state roots 597/597/597/567 (unused padding removed), all below
15,000. This is structural evidence, not placed TT/FF timing. The route owner
must flatten the native store inside each hard leaf and the codec inside the
controller leaf. Physical fit, clock delivery, channel capacity, FEC, recovery
and G96 token throughput remain unqualified.
