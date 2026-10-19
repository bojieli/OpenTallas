
CODEX regions successor (10-19 09:08): source b2ce4668a supersedes the
pointer-correct987 gate. The987 and0aef gates are immutable diagnostic evidence.
The current design captures the exact next-edge winning event select per12 output
bits, so output payload ORs and collision faults retain their original edges.
Parallel endpoint collision registers remove the former global collision stage.
Reset-distinct event time/config/wrap/address and RX compare copies preserve
physical fanout. A balanced reset tree releases after exactly3 edges, replacing
SYNC2+TREE1 without a latency change;261 checks across483 regions match the legacy
relay. The new colliding-event test checks400 outputs and firstfault edge1023.

Pre-gate safe-design review:
1 FIXED: every pin remains registered; flow reset landing2 remains enabled.
2 REVIEW: outline475.2x432.0 and original macro grid retained; final placed wire
  reach must be measured<=405um before submission. No reach waiver is claimed.
3 FIXED/PENDING SYNTH AUDIT: event-local physical copies remove the former
  armed196/address83/time77/RX48 cones.0aef strict audit leaves only boot37,
  slice-select33 (approximately32), and flat reset roots. Balanced reset replacement
  limits root/group reset distribution to<=32 loads, with identical release edges.
  Latest synthesized copy survival and mapped loads must be checked.
4 FIXED: registered one-hot output selects per12 bits, parallel collision checks;
 0aef depth561.8ps/15levels. Latest physical stage timing remains required.
5 PASS:84 true SRAM macros hold all runtime payload tables; parallel RX identity
 1457bits and fired flags752bits remain below2kb individually.
6 SIZING PASS: unchanged43.2um macro lattice, minimum channels22.41/24.84um;
  measured0aef std6987um2 fits the full-width bandy2.16..34.56 at~45.8%.
  ROOT08:20 approval covers the geometry/schema only; latest sizing/PNG required.
7 PENDING CTS: native TT/FF pin-flop spread<=80ps and parent boundary matching
  remain required;io_hold_margin0.03. No insertion waiver replaces native audit.
8 PASS: all data and reset release edges preserved; original D/gap minima retained;
  static schedule, no credits/backpressure and no additional data latency.
