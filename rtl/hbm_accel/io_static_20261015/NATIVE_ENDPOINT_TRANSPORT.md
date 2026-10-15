# Actual sequence endpoint through valid-preserving transport

The component bench uses the registered native HBM sequence endpoint at both
ends, actual four-bank 64x512 replay SRAM and parallel CRC, two instances of
`ot_hbm_static_frame_transport`, and three explicit 487-bit word registers.
Endpoint valid is the in-band bit 612 of the 613-bit transport frame. Idle
reservations carry zero valid, while the gearbox continues producing one
487-bit word per active cycle. There is no frame-to-core-cycle substitution.

For transport frame slot j, the compiler calendar is:

- TX gearbox start: edge 16; frame acceptance A(j) = 17 + floor(613*j/487).
- Endpoint SRAM write: A(j)-8; read: A(j)-4; TX3 output: A(j)-1.
- Transport word k leaves the TX register at 17+k. Three word registers carry
  it, and the RX gearbox samples it at 21+k; RX start is edge 20.
- Frame j finishes at word k = ceil(613*(j+1)/487)-1. RX gearbox produces it at
  21+k; the wrapper registered face captures at 22+k; endpoint RX captures at
  23+k and publishes at 24+k. The added wrapper edge is explicitly priced.

Slots j with j%7==3 or j%11==8 are genuine idle. The 300-slot bench therefore
checks 234 actual 545-bit payloads and 66 idle reservations. Logical sequence
advances only on compiled valid frames, passing three physical SRAM slot wraps.
The exact output edge and independent payload are checked for every valid
frame; publication on any idle edge fails. Continued slots after workload end
are also idle, preserving the gearbox calendar.

Negative runs flip the transported endpoint valid, remove the first physical
word, corrupt a bit of the first physical word, or force PHY-down at the first
endpoint TX edge. They require the specific missing-frame, transport word,
CRC, or TX PHY abort reason respectively. Missing word preserves its data bits
but drops word-valid; the gearbox faults even when reconstructed payload bits
happen to remain correct. No downstream payload is accepted as a success claim
from such a faulted epoch.

The model entry is `hgi_collective_native_transport_model()` in
`tools/uarch_model.py`; sustained digital frame capacity is 487/613 per cycle,
about 54.12 payload bytes/cycle before idle reservations. Run
`tools/hbm_io/run_native_endpoint_transport_gate.sh OUTPUT`.

This is a digital integration proof. Real FEC and its raw-word clock crossing
are separate work; no PHY, CDC, physical closure, or G96 token-rate claim is
made. No transport or endpoint RTL is altered by this bench commit.
