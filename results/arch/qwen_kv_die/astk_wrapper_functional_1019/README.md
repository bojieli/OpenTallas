# ASTK wrapper functional proof (ROOT bounded grant)

**PASS: Boolean functional equivalence of the exact routed netlist to actual RTL default and explicit MUT=0.** All 296 outputs and all three reset states are retained. Actual MUT=1 produces the required causal counterexample. Physical/native qualification remains HOLD.

The frozen native netlist is `6_final.v` from `qkd_astk_rly_296-fl1-bd369b99e` on ep4 scratch2. The four original source files match their authentic gate snapshot hashes; the wrapper SHA is `f6e02fd59762f27329eeb539efbfdfd427043faa11721a741d818ecf102a142c`. The selected view identity and raw-to-selected LEF transformation are unchanged. No live GEN8 source/run, receipt, binding, default, or physical file was changed.

`prove.py` performs a complete structural transition-graph proof, rather than a bounded trace comparison. It independently elaborates actual RTL default, MUT0 and MUT1 using Yosys. For the native netlist it reads the exact five Liberty paths named by the frozen `export_tt.tcl`, checks every instantiated cell's Boolean function, and resolves every driver. Unrecognized cells, undriven signals, graph cycles, unmatched states, mismatched data/reset/clock functions, or unaccounted instances fail the proof.

The native 299 DFFASRHQN flops use Liberty `QN=IQN`, `next_state=!D`, `preset=!RESETN`, `clear=!SETN`, with positive `CLK`. The state bijection is native IQN = complement of the corresponding logical RTL state. Every SETN resolves to constant 1 through a real native tie cell; all clocks resolve through native buffers/inverters to positive ck. All CTS load cells, including their intentionally disconnected outputs, are accounted. There are zero blackboxes and no state/output waivers.

Both RTL variants and the native graph reduce to the same complete relations:

- 296 data states: on positive ck capture their corresponding arbitrary input bit, asynchronously clear when the logical relay reset state is 0; each output is its own logical state.
- sync0, sync1, relay: positive ck respectively captures 1, old sync0, old sync1; all asynchronously clear when rst_n=0.

This bijection maps **all arbitrary initial states**, without choosing zero or assuming a reset preamble. Identical outputs, asynchronous reset actions and next-state relations establish equivalence inductively for arbitrary Boolean data and every ideal logical clock/reset history. No async2sync, startup substitution, quiet-window assumption or ignored reset state is used. The scope is Boolean functional semantics; it does not establish analog/metastability, timed/delta-ordering, power-loss, or Z-valued-input equivalence.

The actual MUT1 source has only 296 states and bypasses the relay reset. The structural checker rejects it. The committed Icarus witness instantiates actual native netlist + Liberty-derived primitive functions, default, explicit MUT0 and actual MUT1. On the **first** release edge, input all ones yields native/default/MUT0 all zero and MUT1 all ones. Baseline checks include startup and repeated midcycle reset assertion/release; 47,952 bit comparisons pass. This finite simulation supplies the causal witness; it is not the universal proof.

The native functions are pinned to current ep4 image `openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29` and per-file SHA256s. The historical export command recorded only `openroad/orfs:latest`, not its digest. Consequently this packet does **not** claim independent historical image-digest identity. Original native macro Liberty/view hashes remain pinned separately. PG pins are not modeled as a power-integrity proof; functionality assumes powered cells.

The immutable input archive contains exact netlist, source, and the five full native libraries. `proof.json` includes the complete 299-state bijection and cell inventory; `provenance.json` records identities and infrastructure refusals. Earlier failures are preserved. The first run's stdout was not persisted by its client call; its systemd unit is recorded honestly. Subsequent refusal logs show the disconnected CTS outputs and Yosys scopeinfo metadata before those cases were explicitly accounted. An earlier broad extraction included three unused FAKE-named library files; no such cell occurs in the netlist. The final proof uses only the five original export paths, and the earlier hash list is preserved.

Run only on the fleet with measured admission, unpinned `ot-run`, in an isolated scratch directory:

```
bash reproduce.sh
```

No synth/route, native receipt, native_qualified flag, or physical qualification is granted. Legacy reset fanout296, actual local contact density, PG connectivity, native capture/hold and current safety remain **HOLD**. ROOT is the sole merger and decides any further integration.
