# Private RXB input face retiming candidate

vB RAW face guard stops before floorplan: 864 input bits each fan into four ring bank write muxes; 592 output bits pass. Attributes cannot change this topology.

Candidate adds one dedicated capture per input bit, keeps all D=4 runtime slots and selectors, and uses existing local reader EPOCH_BIAS=1 with K=2. The reader selects one newer slot while retaining original K=2 warmup. Each slot contains one older captured input, so external data age and all cycles are unchanged. Only first five boundary landings change; all internal landings remain original. Source and destination clocks are the same ck, with equal-depth regional resets. No claim for independent-clock use.

Adds864 FF/~260um2; new pin cycles0. Internal ring setup span becomes1 cycle rather than2; native receiver clock extraction/STA must use that tighter relation. Requires random streaming and warm-reset lockstep, faulty-bias and warmup mutants, full-column proof, RAW ownership pass before placement. No generic LANDING contract or POR change.
