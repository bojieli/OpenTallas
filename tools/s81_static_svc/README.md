S81 fixed-slot SVC storage successor
===================================

`ot_s81_svc_static_store` is a real RTL payload storage mechanism for a new
static SVC controller. It does not replace the closed ATTQ/home/comb masters,
qualify native attention arithmetic, or establish an internal production
microcalendar. Instantiation is opt-in by explicit successor binding; there is
no modification or alias of an existing physical view.

The compiler reserves each put and get cycle, address, and 32-bit identity.
The identity must bind source port, row, mask, tag, and generation to the
compiler's operation table; no hash/truncation of those fields is implied.
Each get yields the existing addressed payload and supplied expected identity
on the immediately following registered edge, even after a fault. A consumer
must treat any fault as invalid execution. Same-address simultaneous get/put
reads the preceding word and then replaces it. Capacity may be reused on that
edge. Missing or wrong-identity producers leave an occupied invalid word;
there is no replay, ready-driven stall, or returned credit. All missing, late,
stale, identity, capacity, and unavailable-consumer observations are sticky
faults. Reset clears control validity; SRAM payload reset is unnecessary.

The model at this mechanism boundary is one put and one get per stream edge,
WIDTH bits/cycle each, one registered get edge. Existing nominal storage sizes
are SC: 8 x 2132 = 17056 payload bits plus 256 identity and 16 validity bits;
PV: 4 x 8456 = 33824 payload bits plus 128 identity and 8 validity bits.
These remain actual finite storage, not credit windows. There are seven fault
bits and WIDTH+33 output register bits per instance. No area, slot fit, native
clock-root, SRAM macro mapping, pin, or physical timing qualification is claimed.
Any production successor needs distinct physical views and qual_clock evidence.

Run `python tools/s81_static_svc/test_static_store.py` for full SC shape
(640 rows / 4 lanes = 160 records, 2132 bits) and all 8 PV records (8456 bits).
These exact-width boundary tests inject component stimuli and check real RTL
payloads, identities, same-slot storage replacement, fixed output count/cycles,
and six observed failing cases. Their fixed storage test itinerary is explicitly
not an inferred arithmetic microcalendar. Neither Python nor a golden reference
produces internal DUT arithmetic in this test, because arithmetic is outside its
declared boundary. Full native arithmetic remains pending with its owner.

Compiler integration must use `tools/s81_compile_schedule/compile_calendar.py`
`compile_program(program,binding,contract,root)` and its source evidence,
relative issue/ingress/enqueue/service/response/commit/deadline edges. No fixture
SC/PV ages may be adopted. The existing native issuer additionally requires
`integration_ready`, `sequencer_cmd_pin_to_done_pin`, stream clock-domain and
actual command ABI evidence before execution is admissible.

Still missing for an actual internal SVC production binding:

* Native engine Q/KV/probability acceptance and SC/PV production fixed ages,
  including engine launch, SRAM stages and every physical clock phase.
* Static replacement for engine SC_CRED/PV_CRED demand issue and q/kv/p_ready.
* Static merger/assembler admission, actual ownership table and selected rows.
* Fixed home/comb window/read/write/return/reduction/drain itineraries and
  all inter-master link landing/relay storage and phases.
* Compiler-sealed producer identities, capacities, completion deadlines and
  real endpoint command wiring for the actual production shape.

Historical ATTQ queues (qmem, probability FIFO, SC/PV queues), row assembler,
CKV merger, engine internal buffers and home/comb relay queues must all be
accounted for in that static allocation. The two primitive instances alone do
not cover them and cannot establish full-token completeness or token rate.
