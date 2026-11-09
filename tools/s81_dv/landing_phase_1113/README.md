Current final landing conditional phase law
==========================================

Actual frozen bind.f on E4 selects
`/srv/opentallas-scratch3/claude/codex-wave-bind-1106/src_28fc7/rtl/common/`
`ot_dp_clk_landing.sv` SHA2f223b19bc4d65333738a9bf6f7df2829618b60c110003b763eb01f7b99b5d2c
and `ot_meso_fifo.sv` SHA72750a546e10260ec6fa1e8ec69f34ae29302c5362eb3baa4df72bf28bd29396.
Current main and kw35 captured bytes match. Existing RCK W515 equivalence
receipt does not measure absolute phase age, so this smallest177-bit vehicle
tests the additional missing mechanism only.

The source register samples a full177-bit word on forwarded rising edge N.
Actual WNEG1 writes the ring at its falling edge; the real final consumer
register samples landing q on a core rising edge. W177 pads internally to192,
DEPTH4/OFFSET2/RDREG1/SETTLE16/FREG0 are unchanged. No RTL form is modified.
The full word contains varied payload and a separate epoch bit176; all bits
are compared. Both initial release at core edge47 and a warm reset600..607
are test inputs, not an emulation of actual distributed reset trees.

With T=833000fs and phi=(core rising epoch−source rising epoch)modT:
for tested strictly positive phases the final output observes the source
sample after3T+phi. At exact coincident phase0 this simulation instead observes
4T, consistent with the ring's adjacent placement choices at coincidence.
It is unsafe to silently price3T at that boundary. Tested phi values are
0/1000/83000/208000/416500/625000/750000/832000fs; these are test inputs,
not a physical phase envelope certification. No metastability or timing
margin is established by this digital bench.

One build includes an actual WNEG0 wrong-edge control. It differs on all1105
observations at1000/83000/208000/416500fs; high-phase cases legitimately
coincide in age and are not sensitivity evidence. A one-fs wrong-phase
booking disagrees at every point. Good has1105checks/0errors/fault0 per phase.

`bind_phase.consumer_observation` requires explicit actual source/core epochs,
source/consumer register identities, source hashes, observed receiver ready
edge and positive phase guard. Missing phase, wrong source reference and
phase inside the supplied uncertainty/coincidence guard are rejected. It
returns only the final source-register→landing→consumer-register law; no89,
53,77,41 bound lane count is used as a source-sampling date. The caller must
still qualify its physical guard and book all upstream transports. Source
seqhost raw reset36 and published tap44 are distinct source-relative facts;
their difference is not a new data latency or an absolute START time.
