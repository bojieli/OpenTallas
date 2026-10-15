# Actual frame/PMA composition API

`ot_hbm_core_fec_frame_link` is a wires-only functional composition. The caller
keeps its native TX6/RX2 endpoints. `endpoint_tx_frame[611:0]` and its real
`endpoint_tx_v` enter the stepped 613-bit transport; the recovered registered
`endpoint_rx_frame/endpoint_rx_v` feed the caller's RX pins. External link pins
are actual `pma_tx/pma_rx[511:0]`. There is no ideal 612-bit cross-clock rail.

It composes two actual stepped frame wrappers, two 16-entry external word CDCs,
and the frozen 151-FEC-edge `hfd_serdes487_phy512_static_window`. Both directions
have externally supplied starts/takes/last flags. The core stays at 1.2 GHz;
all FEC roots belong to the 16/17 frequency family. `expected_tx_slot` is a
calendar observation for checking, never readiness or an issue selector.

The exact reservation equations and finite stop contract are in
`CORE_FEC_BOUNDARY.md`. The module adds no state beyond its real component
instances. Its RX frame appears at core C(699,lastword), the caller endpoint
captures at C(700,lastword), and RX2 publishes at C(702,lastword).

Clock ports preserve actual arithmetic/storage root groups:

| Port | Actual root |
|---|---|
| `core_clk` | Core-domain transport and external CDC logic |
| `fec_clks[0]` | FEC control and external crossing FEC sides |
| `[1]`, `[2]`, `[3]` | FEC collect, encode, codeword |
| `[4]`, `[5]` | FEC RX capture, syndrome |
| `[6]..[9]` | BM0..BM3 |
| `[10]`, `[11]` | Chien, emit |
| `[12]..[15]` | Four serializer storage bank roots, banks 0..3 |
| `phy_clks[0]`, `[1]` | PHY TX, RX |
| `[2]..[5]` | Four deserializer storage bank roots, banks 0..3 |

Numerical benches explicitly tie same-family roots to their declared phase.
That tie does not bind physical arrival phases. Physical hard-leaf partition,
clock delivery at each actual root, and all routed CDC paths remain open.

Faults stay separate by domain:

- `fault_core[0:3]`: TX gearbox, RX gearbox, TX CDC write, RX CDC read.
- `crossing_fault_fec[0:1]`: TX CDC read, RX CDC write, both FEC control.
- `pma_fault[0:3]`: serializer write (FEC control), serializer read (PHY TX),
  deserializer write (PHY RX), deserializer read (FEC capture).
- `status` and `padding_fault` are the existing FEC control-domain observations.

No asynchronous aggregate chooses data transfer or issue. The caller must use
its exceptional fault-handling contract rather than treating fault wires as
normal readiness.

`run_core_fec_frame_link_gate.sh OUT 0` verifies this exact composition API with
actual native endpoints and FEC/PMA. It checks 234 exact payloads, 66 idle frame
slots, 2,048 decoded words, 2,048 internal CDC words, and exact core publication
edges. Four fault scenarios cover valid flip, missing receiver word-valid,
CRC-protected frame-bit corruption before FEC, and endpoint PHY-down. Missing
word-valid is an explicit bench force on the receiver wire; the production
module has no fault-injection mux. `... OUT 2` compiles the actual Forney mutant
and requires exact-decoder failure. The direct-component assembly gate and all
historical clock profiles are preserved separately.
