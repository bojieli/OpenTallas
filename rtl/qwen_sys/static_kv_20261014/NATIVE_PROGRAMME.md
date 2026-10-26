The native writer programme is an opt-in, all36-stage writer component
candidate. One exceptional boot loads 36 tables, each containing four cycle32
slots and one stop32 root. A global seal makes every table available for
successive stages and tokens without configuration or reset. Runtime slots
depend on a counter and the table selected once at accepted start. Payload,
word-valid, readiness, credit and completion cannot move them.

Boot addresses 5*(stage-1)+0..4 contain four cycle32 roots and stop32, each in
the low32 of data64 with upper32 zero. Address180 seals the complete table with
514b565052473336 (QKVPRG36). The loader accepts only ascending addresses and
validates each row's monotonic slots, first slot >=4, and at least three drain
cycles. Reset is required to replace the sealed image. A malformed boot,
partial table or invalid start faults and cannot open a transaction.

At start, the parent supplies independently compiled stage6 plus accepted
epoch16/token18/position13/generation2. The selected five timing roots and
TAG59 are captured once. Changes to inputs during execution cannot relabel a
transaction or select another table. TAG59 is
{epoch16,stage6,token18,position13,segment6=0}. This leaf does not allocate an
epoch or implement the parent's epoch-wrap/drain protocol.

The module's internal accepted start binds the actual segment0 core-start. Cycle0
is the interval immediately after that start edge, before the next receiver
sampling edge. Stored cycle roots and stop are relative to this start. The
compiler uses explicit producer/path ages relative to the same origin. It
does not add an absolute segment core_start_cycle to those ages. The parent
must present the external start/context one edge before that core-start; asserting it at outer
stage-start would be a different, unsupported binding. Clocks must agree across
all36 profiles and with their qualified segment profiles.

The compiled outputs connect to the actual native writer's
compiled_word_slot, compiled_word_index, compiled_identity and
compiled_generation. kvn_word_slot duplicates that slot at this receiver
boundary; it does not schedule an upstream formatter or D2D launch. Transport
calendars require their own implemented clock crossings and registered hops.
Independent expected_valid4/pc20/stack2/identity59/generation2/address29 appear
after the same two capture edges as the writer. The component bench compares
the actual physical writer's outputs, raw data and inverse physical addresses
without hierarchical signal access.

The compiler requires exactly 36 ordered stage profiles, the complete actual
programme/source identity and actual descriptors. Partial tables are refused.
Each stage binds sole native PC11 and source segment bases 0/14/22. Production
output additionally requires a source-bound measured writer receipt and the
existing full segment physical profile for every stage. Component-test mode
is noninstallable; its declared ages do not establish physical qualification.

Reproduce source and component evidence with:

    QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 QWEN_O4_AR_WORDS=256 python tools/qwen_tp8_fulltoken_plan.py --snapshot /path/to/b968826d9c46dd6066d109eabc6255188de91218 --out /fresh/source
    python tools/qwen_static_kv/run_native_programme_gate.py --source-dir /fresh/source --out /fresh/gate

Latest evidence is in results/rtl/qwen_native_kv_programme_1103/reset_v4; pin_v3 and all36_v2 are preceding structural/functional revisions. The regression
uses one reset, one 181-write boot and one seal, then executes all36 stages for
two tokens over 16 boundary positions per stage: 1152 cohorts, 4608 fixed word
slots and 9216 physical sectors. Stage-table selection and stage-identity
mutants fail, alongside slot/index/address/identity controls. The original
single-stage evidence is preserved as history and does not establish the
all36 table mechanism.

The regenerated source SHA remains
f7a290112c2858f5b8dd169ade5c7c9afbaa372cc7f0f8e29a387c064f54bd71; the historical
installed programme remains
cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796.
Only PC16 chase_n (64→509) and PC20 chase_n (24→192) differ under the current
decoder. Native PC11, K/V source PCs3/8/10 and descriptors are unchanged.
The historical plan has stale current ISA source pins and is refused. The
regenerated candidate is not an installed-programme replacement.

The unified model counts 6292 logical state bits per writer, including 5760
boot-table bits and 160 selected timing roots, plus 1448 bytes of exceptional
boot traffic. The 36-way root selection, replica count and boundary widths are
explicit. Area, slot fit, routing capacity and SS/FF timing remain unmeasured.
No added writer capture stage or token-rate credit is claimed. Controller
command/refresh/reservations, HBM blk_go, ring expected-return slots, full-root
integration and full-token execution remain separate required work.

Every functional input terminates first at an explicit pin FF: cfg_we1,
cfg_addr8 and cfg_data64 (73 bits), plus start1/stage6/epoch16/token18/position13/
generation2 (56 bits). A boot beat is processed one edge after external capture;
flush one edge after the final seal beat before checking configured. The external
start and its roots are captured at E0; internal accepted start/cycle0 occurs
at E1. The compiler reports external_start=internal_core_start-1 and requires
start_pin_capture_edges=1. It refuses an unimplemented start-root pipeline.

compiled_word_slot1, compiled_word_index2 and kvn_word_slot1 now originate at
four output FFs. Cycle+1 predecode feeds those FFs so each external slot interval
relative to internal cycle0 is identical to the preceding all36 revision.
compiled_identity59 and compiled_generation2 directly originate at captured
transaction-root FFs; no received writer identity is used. All expected
descriptor outputs and status/cycle outputs remain FF outputs. A Yosys
read/proc/memory_map/opt_clean audit checks all functional input consumers are
FF D pins and every output bit is a direct FF Q. It counts exactly 6292 FF
bits: 5887 synchronous data bits and 405 asynchronously reset bits. This is a
structural audit, not technology mapping or physical timing evidence.

The proposed physical envelope remains 86.4 by 194.4 micrometres with a single
833.334 ps clock root, subject to the KV die lead's final site and routed
qualification. Added input capture ownership is 129 FF bits, and registered
slot ownership is four FF bits. No slot interval or writer capture latency is
added; start capture adds one explicitly declared edge before the internal
origin and boot capture adds one exceptional flush edge.

External rst_n now terminates at exactly one kept one-bit reset pin FF.
It asserts asynchronously and releases synchronously after one clock edge;
its Q owns every internal asynchronous reset pin, including the input valid
capture flags. The structural audit explicitly requires the external reset to
have exactly one one-bit FF ARST sink. The reset pin adds one logical FF bit
to pin_v3, giving 6292 total bits. Normal start and slot intervals after reset
release are unchanged.

The compiler requires reset_pin_release_edges=1 and adds that edge to the
downstream reset-release/fill budget. Its reset_release path age describes the
downstream reset network from the reset pin Q; the source's one-edge pin release
is accounted separately. With the existing four-edge minimum downstream fill,
minimum_reset_fill_edges is now five. Missing/reset-bypass profiles are refused.
The external ABI, physical pin count, boot image layout, start capture latency
and slot predecode latency are unchanged.
