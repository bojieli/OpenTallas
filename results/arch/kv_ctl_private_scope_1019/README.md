# CTL bounded private-source decision packet

Recommendation: authorize only the private functional writer/programme pair below.
Do not authorize the whole 602-copy forest, physical storage adoption or a new gate.
No RTL was emitted, no simulation launched, and no live job changed in this packet.

## Exact source and adoption gap

The prior efca20ca6 / 133c52b22 native graph is the c5fbbded9 mu5 candidate,
ODB SHA fcbc77429404faa5ab91981c1901b93dfb43f5b254bc0992e0d9cdd38460af0a.
It is not the selected 5f2ce19bc graph. source_identity.json records exact hashes.
Writer SHA is 5107a0163d44 at c5 versus dcf2a7b68d22 at 5f2.
The former adds RCOPIES=1 and SRAM=0 parameters, optional reset-family exports,
and a one-edge SRAM read replacing the indexed flop table when SRAM=1.
The 5f2 module has only MUT=0 and VMAP=0; it cannot accept those extra bindings.
The entire qkd_static_kv_layer_programme_mus module is absent at 5f2;
selected historical layer_programme and layer_programme_mu are distinct modules.
Adopting mu5 therefore requires an explicit parent programme/boot/ownership ABI
and parameter binding decision, not a cherry-pick of 602 native names.
No selected-source broad census was repeated and no selected root was rebound.

## Exact native partition, with startup STOP

partitions.json.gz supplies deterministic partitions of all 191 copied native roots:
expanded endpoints include each destination's own copy multiplicity; each partition
has at most 32 endpoint pins, with BUF/INV/HB already collapsed. It retains
114 FF roots /278 extra FF, 76 combinational roots /323 extra gates, and one
extra tie. Four-round fixed point remains 584 ->601 ->602 ->602.
Existing-master area +121.1598 um2 and 278 clock contacts are demand-model values,
not synthesis area or retained-source proof. Native QN polarity must be respected.
No combinational copies may be counted if synthesis merges them.

startup.json enumerates all 114 FF roots and actual native D/CLK/reset inputs.
There are 90 unreset native roots requiring 159 extra FF and 24 async-reset roots
requiring 119. The former includes unreset input captures AND reset carriers.
The reset-only subset across master kinds remains 60 roots /149 extra FF.
A clone can have arbitrary old Q before its first capture. In particular a
sampled reset carrier can independently assert/deassert downstream asynchronous
reset before the first ck edge. Equal D and equal CLK do not prove equal old Q.
Consequently arbitrary-start all-output equivalence and whole-forest source grant
are HOLD. No proof assumes initial equality, a quiet boot, or ignored outputs.

For unconditional landing data/epoch, equality follows after one shared capture,
provided all consumers use the matching later valid and no raw observable output
uses it earlier. For async-reset state, prove actual assertion reaches every copy,
identical reset polarity/value, D/enable equality and consumer ordering. For
reset carriers and boot relay/index roots, derive actual parent reset ancestry
and first affected consumer before emitting clones. The raw pre-frontier behavior
must be checked and recorded; monitor suppression is not a source equivalence proof.
The supplied partition is implementable connectivity, not that missing proof.

## Proposed minimum functional source grant

Private directory rtl/qwen_sys/ctl_private_20261019; five new files only:
qkd_kv_native_programme_ctlp.sv, qkd_static_kv_layer_programme_ctlp.sv,
ctlp_contract.json, tb_ctlp.sv, run_ctlp.sh. Add no shared helper, default binding,
macro view, root parameter, reset forest or public-source edit.
Private modules clone the exact c5 writer and mus programme, with ENABLE=0 by
default. ENABLE=0 must preserve their original behavior/parameters and compare
all public outputs. ENABLE=1 initially changes only the writer's SRAM read CE
from raw start_p to the exact accepted-start predicate already setting ld.
Keep original 128x256 storage and every existing capture/age/mask/valid/reset.
This is a functional minimum; it does not make existing dense macros physical SAFE.
Under reset_pin_n high, the accepted-start predicate is !fault && start_p && configured && !active &&
!cfg_we_p && stage_p>=1 && stage_p<=36 (retain exact original priority).
Read address remains selected_stage-1; ld consumes its registered result on the
following edge. No extra source cut: target edge delta 0, SU/MU delta NULL until
actual parent binding/calendar and whole-source lockstep. Do not rewrite boot,
row field layouts, arithmetic, fault precedence or programme identity.

The existing real writer collision witness proves raw reads can overlap writes.
Previously established consumer invariants are conditional: configured implies
!wq_v; ld follows an accepted configured start only; only ld consumes rt0..rts;
reset clears enables and requires 180 ordered words plus seal before next use.
A legal-read CE should remove rejected raw reads without changing consumed Q.
The mus programme reads only on e_begin; ordered boot/seal and disabled contexts
separate accepted runtime reads from pending writes under the shared ck/rn model.
Use these exact sources, not a fresh permissive surrogate model.

Minimum causal bench: all-output ENABLE=0 miter; legal full boot/seal/runtime,
back-to-back stages and tokens; rejected start during final pending boot write;
reset during write/read/ld and full reboot with arbitrary old macro contents;
bad address/order/epoch/digest and simultaneous start/config priority. Compare
every public output every edge, not only valid results. A mutant enabling reads
one edge late must fail on first accepted row; wrong-row and mask/word mutants
must fail; invalid-start acceptance must fault causally. Preserve original
collision witness, including its rejected-start fault. Use a 4-state control for
arbitrary pre-reset Q and first-use checks; any clone old-Q leakage stops the
forest step. Fleet Verilator5.050/Icarus only; no whole-die build needed.
This proposed grant is not yet authorization to emit these files.

## Storage and common-family dependency

Keep useful row widths 256/168/160: four + three + three 128x64 banks, masks
and padding preserved, 20888 useful macro bits plus 136 g0 register bits
(20736 boot bits plus288 derived flags). The functional source above uses the
original three128x256 macros until an independently reviewed physical successor.
Actual CTL wrapper uses one ck; a dual-clock family must bind both clocks to ck
without inventing an operating asynchronous mode. Its primitive must nevertheless
have genuine independent-clock characterization, not single-clock substitution.
No memory payload reset or assumed zero initialization. Registered read latency
and exact write mask/CE/hold behavior stay unchanged. If OLD same-address access
is claimed it needs a true primitive contract; arbitrary read Q is sufficient
only where source noninterference is proved. Physical write integrity during
simultaneous read/write cannot be inferred from behavioral array code.

Existing n64 bc42f77a8 is unsafe: contacts cluster at0.096um (105 contacts per
face); whole-face averages cannot qualify <=6 contacts/um local access.
There is no active qualified128x64 successor owner, generator, Liberty or view.
LEAD-QW owns common method c634d1540 at
/home/ubuntu/artifacts/sram-new-master-model-1019; its scope is Qwen32x64
dual-clock and S81512x128 single-clock, and StageA2c2d union failed.
The active A2 owner is /root/takeover2_qwen/qwen_sram_coupon_a2,
native-visible coupon only (no AP/PDN/views). The32x64 dual-clock contract
forbids simultaneous same-address access; only512x128 single-clock has OLD.
Neither supplies CTL collision/write-integrity evidence.
HBM c1f1c2c0c at /home/ubuntu/artifacts/hbm-bw-fit-clock-model-1019 is a
contact/fit model only. Both leads confirmed this dependency; no helper duplicated.
Required new CTL topology: real >=0.192um port leads/local <=6-window access,
internal-array RC, native vias/OBS/PG, both clocks and collision/write-integrity
contracts, earliest/latest read/capture timing, and actual parent routing grid.
Do not stretch terminal coordinates or inherit S81 single-clock OLD evidence.
The proposed345.6x475.2 outline still does not fit1123x172.8 parent; parent regrant,
405um reach, full clock/reset/load/PG and SU/MU throughput/calendar remain OPEN.
