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

The module's accepted start binds the actual segment0 core-start. Cycle0
is the interval immediately after that start edge, before the next receiver
sampling edge. Stored cycle roots and stop are relative to this start. The
compiler uses explicit producer/path ages relative to the same origin. It
does not add an absolute segment core_start_cycle to those ages. The parent
must assert start on the source-profiled core-start edge; asserting it at outer
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

Evidence is in results/rtl/qwen_native_kv_programme_1103/all36_v2. The regression
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

The unified model counts 6158 logical state bits per writer, including 5760
boot-table bits and 160 selected timing roots, plus 1448 bytes of exceptional
boot traffic. The 36-way root selection, replica count and boundary widths are
explicit. Area, slot fit, routing capacity and SS/FF timing remain unmeasured.
No added writer capture stage or token-rate credit is claimed. Controller
command/refresh/reservations, HBM blk_go, ring expected-return slots, full-root
integration and full-token execution remain separate required work.
