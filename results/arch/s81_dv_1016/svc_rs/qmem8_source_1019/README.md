# SVC qmem8 DEFAULT-OFF source prototype

`dsdv_svc_att.QMEM_SRAM=0` retains the existing FF read/write semantics.
Selecting1 instantiates eight immutable single-clock32x64 macros; their
registered rd_out replaces eq_w directly. Added data edges0, eight clocks,
4419.25632um2 raw/16384 physical bits for8192 useful bits. Native family
b65718325, qualified-view reference7549fae73; exact behavior is copied under
native/ and its hash must match storage_model_1019/model.json. No regeneration,
dual-clock read/write model, extra output FF or controller wait is introduced.

Before code, MODEL.md binds real write/address/read/valid/reset lifetimes.
make_vehicle.py checks every unaffected parent token against53ccd5927 after
reversing only the default-off packaging. Original qmem declaration/write/read
statements are preserved literally (eq_w capture's private variable renamed).
The legacy miter uses the actual new legacy branch; reference uses original
source statements. This is a bounded component miter plus source projection,
not synthesis graph/formal equivalence of the entire parent.

## Fleet evidence

Unpinned ot-run, Verilator5.050,12GB/4threads, ep8:
- unit1650229-1792440108: eight seeds each381edges,349 checked store words,
  288 qualified reads, all16 distinct nonzero heads,50 OLD same-address
  collisions,12 address wraps,three jobs and occupied reset. Five actual RTL
  mutants reject: wrong read head+1, previous/early head-1, added capture edge,
  NEW bypass on collision, wrong write head+1. Committed mutant1..5.log are
  original causal failures; no schedule/expected-word alteration.
- unit1657648-1792440200: eight seeds each55 real pre-edge engine captures,
  three completed16-head jobs and one active job reset after seven captures.
  q_have/GO/run/rc/eq_v expressions are source-checked from the original parent;
  row nbeat=0 intentionally isolates the unchanged sixteen-head q schedule.
  Occupied reset clears valid/lifetime before another complete job. Early GO
  after15 heads triggers actual unchanged fc[9] check (early_go.log).

OT_MEM_NO_INIT disables the native behavior's simulation zero initializer;
--x-initial unique and +verilator+rand+reset+2 randomize physical arrays and
outputs independently across seeds1,17,29,113,787,1009,32003,65521. No pre-write
payload is accepted; first use must follow a complete unique-head load.
The existing parent q_have count alone does not detect duplicated head writes;
this prototype does not claim a new identity guard or repair that old contract.

The first attempted stdin transport failed before simulation (transport_attempt1.log);
inputs were then staged on ep4 and ep8 and placement remained unpinned. Both
actual simulations completed exit0, with each intended negative exiting1.
No worker or original SVC gate was killed or restarted.

## Reproduce and scope

From repository: python3 results/arch/s81_dv_1016/svc_rs/qmem8_source_1019/make_vehicle.py.
Run bash run.sh on fleet in that generated directory, Verilator5.050 required.
For an explicit production-shaped candidate source list, supply actual
rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv, dsdv_svc_qmem8.sv and this exact
native behavior (or its source-pinned synthesis BB/views), set QMEM_SRAM=1.
No existing caller/default is changed to1. Macro model defines same-edge OLD
in one process, clock-enable hold and actual64-bit mask; masks are all ones.

No physical gate, whole SVC simulation or arithmetic rebuild was performed.
This internal component relies on the parent's existing write and engine
boundaries; it is not a newly hardened standalone tile with qualified pin
register/clock/reset/PG/escape/placement contracts. Whole-block uncapped fanout,
macro clock CQ/timing context, other wq/sw/pvq stores,32 dense legacy macros,
G9/G9b/G10 destinations, true SRAM-backed release, throughput, and SU/MU token
qualification remain OPEN. No SAFE, area-fit or timing adoption is claimed.
