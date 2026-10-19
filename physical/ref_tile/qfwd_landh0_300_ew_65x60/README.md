# SAFE-QW-LAND300 candidate physical checklist

This opt-in implementation uses OT_QFD_LAND_SAFE_REG; existing source contracts stay on legacy RTL until qualified.
D4 storage is1200data bits plus epoch/valid metadata. Each kept select region spans at most24data bits.
Source epoch is registered before hop0 ICG; write-select slot0 is stored inverted, using async-clear cells only.

1. PASS data/flop interface: inputs write directly into constant-address ring slots; outputs register the masked4-slot mux. k drives only3face flops. Reset two-stage landing WAIVED provisionally under inherited regional-reset contract: rs and ea are already registered, async-assert/sync-release regional levels; extra face stages would change committed R0/G and K. Parent must prove this inherited contract or reject binding. Receiver clocks must run for>=2cycles with rs low to seed registeredk/read selection.
2. PASS reach:64.776x60.456um tile; diagonal<90um, below405um.
3. FIXED select fanout: kept hierarchical24bit regions, rotating onehot writes and registered onehot reads. Post-synthesis measurement is mandatory, especially warm and metadata fanout; no qualification until checked.
4. FIXED depth: constant four-slot OR of registered onehot-qualified banks; no runtime-indexed data mux and no combinational pin->pin data path. Measure TT depth/delay in gate.
5. PASS storage:4x300=1200bits, below2kb limit. Fixed4-slot ring, no long delay line. Production600bits must use2x300tiles.
6. PASS structure / measurement pending: no macros; one full standard-cell area64.776x60.456,aspect1.07; data face density<=301/60.456=4.98pins/um. Verify synthesized area gives40–60%util before accepting gate; change outline structurally if needed.
7. FIXED timing coverage: safe_land_clocks.tcl has no falsepath or multicycle. All inter-root bank/metadata/select paths receive conservative quarterT setup envelope using60ps+0.75T uncertainty. Hold25ps remains; actual CTSskew charged. io_hold_margin0.03. Measure TT/FFpin-flop spread<=80ps and neighbour-matched parent boundary.
8. PASS static schedule: no credit/ready/backpressure, no steady-state added capture edge. sample_window.json exhaustsK0..7 and supported read age[0.25T,3.25T], with next-slot overwrite>=0.75T later. Compiler must prove actual TT/FFcompensated-root ages are inside this envelope and inherit K+1hop0 reset epoch; otherwise reject binding. A mathematical envelope certificate alone never qualifies an arbitrary die link.

Native e1 receipts are historical interface metrics only; they do not repair the old broad clock falsepaths.
