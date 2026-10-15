# Native fixed-slot KV writer source proof

`qkd_kv_static_writer` attaches the actual formatter word's retained TAG59 and
HOST generation2 to the real KV sector/address producer. It replaces the old
credit-driven write queue for this selected FP8 TP8 path. The old mapping in
`ot_qkvd_kv_wq::sec_of` and the actual controller `wj` packing are preserved.

The producer accepts Klo/Khi/Vlo/Vhi in compiler slots 0/1/2/3. A low word is
captured in a dedicated seat; the high-word slot produces four complete 256-bit
sectors. Missing, early, late, order, stale identity and generation faults do not
move a slot. Independent expected-valid, identity, address and physical target
signals come from the compiler inputs; actual write fields come from the word
and retained low seat. A high-word slot expects four writes even when a payload
is missing. Each functional input is captured; descriptors appear one edge after
the input capture edge. No producer ACK, credit or readiness changes timing.

TAG59 is `{epoch16,stage6,token18,pos13,segment6}`; native stages are 1..36,
segment0, and one local FP8 head. Row is 64+stage-1. Bank/column preserve canonical
KV mapping: bank `{kind,head0,pos6,pos4:3}`, column `{pos12:9,pos5}`. Four quarters
map to logical PCs `8*q+pos[2:0]`, physical straps
`4*index({4,5,0,1,2,3,6,7},pos[2:0])+q`, stack `pos[8:7]`.
`es288={w_v,s_we,bank5,col5,row19,data256,s_v}`. Native writes always carry the
actual full 256-bit mask. Partial KV writes are forbidden at controller intake.

## Exact dependencies

- Actual compute service, command context, formatter, per-seat identity transport
  and record endpoint: `970b75b99`.
- Actual SRAM completion fence: `fe242d5ba`.
- Native attention record codec: `34cfa0d07`.
- Persistent actual controller, same-entry descriptor CDC/SROW context, physical
  PO register and native write observer: `6f673e98d`.
- Producer: `7fb00c594`; physical joint bench and script accompany this receipt.

Both gate scripts export these immutable sources using `git show`. Source SHA256
receipts cover all compiled dependencies. External sources are not copied into
this branch's RTL or modified. `run_writer_gate.sh OUTPUT` and
`run_physical_writer_gate.sh OUTPUT` are intended for `ot-run`.

## Evidence

`unit/`: all 36 stages x all 8192 positions = 294,912 identities and 2,359,296
sectors pass an independent inverse physical-address and byte-data oracle.
All physical stacks, lanes, bank/column combinations, generations and row layers
are exercised. Actual compute-service/formatter/retained-context transport also
passes its composed writer test (4 words, 8 sectors, captured context remains
correct after the source presents a future layer). Data/address/mask/TAG,
missing write and descriptor +1-edge mutations fail. Missing input and stale
input context raise producer faults without rescheduling.

`physical/`: the actual compute service and formatter feed this writer, four
actual persistent physical PCs (28..31), the SAME actual context/descriptor FIFO,
SROW entries, ECC/pcport and raw physical PO. Only PROFILE0 executes. Fixed
reservations at HBM edges250 and300 yield actual physical commands254 and304;
no ready-dependent reservation or issue is used. A raw external HBM boundary
model captures actual 288-bit writes and checks them against independently
encoded expected FP8 bytes and inverse addresses. Eight sectors pass.

The observed boundaries are physical CMD+5 data/native observation, CMD+17
actual HBM retirement FIFO enqueue, and CMD+22 core completion visibility in
this common-clock test. Input-to-es capture adds one producer edge. The
physical command delay from reservation is four HBM edges. Six actual producer
mutants fail at this physical composition: wrong data is caught at the raw
memory boundary; address/mask/TAG/missing/late mutations raise intake faults at
edge270, before the first expected HBM retirement271.

`native_commit_valid` reports actual physical observation and must be consumed
with all fault inputs. In particular, the current controller's core intake fault
is `er[260]`; mask/TAG/address/latency corruption may leave `fo` and
`completion_fault` clear. Checking only those two would incorrectly accept a
faulted native operation. Raw expected data comes from the independent model,
not from a second copy of the producer descriptor.

## Qualification boundary

This is source and actual physical-interface component proof. The four-PC
composition uses a common clock. It does not establish full128PC routing,
producer/die relay latency, native clock insertion/phase, SRAM placement, a full
36-layer token calendar, token rate or routed closure. CORE833.334ps and
HBM1024ps are the actual source clock periods; the die owner has not yet assigned
this fresh producer's physical home or a shared native phase. No prior hardened
view is bound to this new source. Physical face can omit duplicate helper buses
and constant full-mask pins only with the same actual full-sector intent and
independent expected descriptor checks preserved.
