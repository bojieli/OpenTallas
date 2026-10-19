# Native TP8 recorded stage cuts

Nine positive stage cases pass on the immutable Verilator 5.050 N12/MUT0/MU_NU1 executable from source `9f185989e`: L0/L1 residual-1, SiLU, QKV and GU, plus L0 residual-2. These consume recorded P8191 TP8 golden operands and native L0/L1 image hashes, with exact ISA words checked. L1 residual-2 is intentionally absent because the next-layer norm snapshot is unavailable.

QKV passes 769/769 checks and 768 ISA words per layer; GU 3073/3073 and 3072 ISA words; SiLU 2/2 and 1536 ISA words; each residual 28/28 and 4097 ISA words. Residual span is 1109, SiLU 814, and matrix VM delivery 407 edges. These component windows are not additive full-token latency.

The applicable residual `arwin` mutant fails 4/28 (wrong all-reduce window), and SiLU `nor` fails 1/2. Residual `nor` passes unchanged because that lowering does not use the flag; it is retained as an ineffective control, not counted as a negative witness. The original main job was terminal exit0, and the separately admitted AR-window job returned simulator rc1 as expected. The updated replay driver explicitly checks the expected return codes and includes the applicable AR-window mutant; the committed client logs/source receipts describe the actual prior run.

`receipt.json` records all twelve terminal outcomes. `source_receipt.json` pins the reused executable, fixture generator and original run driver. The two fixture manifests pin actual golden snapshots, native images and frozen VM-map source. Lowering manifests preserve generated compiler programmes and timing. Local `client.log` and `arwin_client.log` retain fleet units and terminal status.

Scope: recorded native TP8 component cuts on the old frozen arithmetic RTL. This does not qualify current SAFE slice RTL, embedding/head/context joins, an entire layer, a full token, multi-user programme residency, or physical timing. Source fixture generation is commit `6afb5ad53`; original replay driver is `b4cf49112`. The preceding ODscale evidence is in `../odscale` and keeps its own source/expected failures.
