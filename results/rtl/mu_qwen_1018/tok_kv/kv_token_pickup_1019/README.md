# Actual KV attention vehicle pickup

GEN7 die 4db097403-codexmub remains diagnostic; SU/MU token qualification is open. Existing G7 WSQK/P0/P1 builds and old QK u1/u4cal/u4pack remain preserved. No stimuli, gold, deadlines, RTL, or production schedules changed.

The earlier RT31-versus-relay15 report compared the programmable V-port hardware bound with a nominal relay age. Actual qkd_pv16_vport_b consumes boot cfg_age; RT31 bounds its storage. G7 boot_ages programs WS0 DQ10/RT16. The relay-table estimate omits later expanded pin registers and cannot establish the final response age.

A second fixture omission left external age_pv and eight selected V-port age words at zero. The new fixture reads exact case_kv/boot_ages.json words, validates their named-field packing, and drives the existing external configuration ports before reset release. Missing or inconsistent ages fail closed. Exact original P0 map comparison proves only nine configuration assignments changed. Verilator runtime proof remains pending on the new GEN8 vehicle; this is a fixture correction, not hardware qualification.

The pinned connectivity ledger for head_WS_0_0 records 54 actual instances: four front, sixteen input stages, sixteen lanes, sixteen output stages, tree, and score. They share n_clk_core_WS[0], but distinct regional and derived reset nets prevent a lockstep exemption without reset/phase/valid-age proof.

The obsolete ep5 06a659135 GEN8 waiter665769 was stopped exactly. Replacement waiter1883470 watches actual ep6 6bc53920d GEN8 MU/mub prep inputs and a completed staging marker; original u1/u4cal/u4pack case files are reused. No duplicate of a progressing vehicle was launched.
