The six modules in `qkd_context_records.sv` implement typed opaque548 records
12, 13 and 14. They consume actual source observations and compiler-assigned
send/receive slots. Each encoder and decoder adds exactly one register edge.
A missing source or arrival faults; it never moves the assigned slot. The
separate real static SRAM/CRC transport adds TX3 and RX1. Physical package and
directional relay phases remain unassigned here; the test's PHY5 is a component
fixture, not a native physical price.

All records use reserved[547:543]=0, kind[542:539], layer[538:533],
epoch[532:517], beat[516:512]=0 and DATA[511:0]. These three kinds use the
token/image-wide layer sentinel63. They cannot enter the attention1..4 decoder.

| Kind | DATA fields | Actual producer |
| --- | --- | --- |
|12 HOST context|TAG59[58:0], generation2[60:59], installed cap61, image epoch[77:62], image digest[141:78], remaining zero|HOST native endpoint request, real HC22 allocator epoch pulse, matching genuine returned image witness|
|13 image BEGIN|subtype1[1:0], expected PW11[12:2]=1024, DW4[16:13]=8, remaining zero|actual class8 decoder BEGIN/counts|
|13 image AUTH|subtype2[1:0], authorized digest[65:2], remaining zero|actual external authorization accepted by HOST loader|
|14 image witness|digest[63:0], installed cap64, actual ready65, actual fault66, remaining zero|actual joined TT/SU macro/DW ledgers and all control-store seals|

Runtime token epoch and program-image epoch are distinct. Actual HOST TAG59 is
`{epoch16,stage0,token18,position13,segment0}`; generation is the actual two-bit
HOST generation, not a local counter. The context encoder retains the real HC22
epoch pulse before the later registered native request. The receiver retains
validated context until an image BEGIN, image revocation, reset or violation.
Accepted CALS stages1..36 supply native per-layer stages in the separate native
helper; kind12 never invents a HOST layer counter. Native request presence is
prefetch context, not singleton cohort acceptance or an execution anchor.

BEGIN must arrive at least one receiving edge before AUTH, and AUTH at least one
edge before the first actual macro-consumed PW observation. These are compiled
constraints, without ACK gating. Kind13 decodes registered ledger inputs; its
additional register edge must be included in the calendar.

A ready1 kind14 must come from a genuine retained commit and match the actual
HOST authorized epoch/digest and authorized PW1023 footer. A ready0 kind14 is
an explicit installed-valid revocation, not a commit: it clears
`program_installed_valid` and capability and emits no commit pulse. A fault bit
also latches a fault. A local image BEGIN immediately revokes the HOST receiver
validity. Current native control seals reset on their actual rst_n, so their
ledger must share that reset and propagate ready0; retaining capability across
that reset would be false. POR-only retention is valid only if every actual
program macro and control-seal store also retains. HOST `image_ready` must use
this installed-valid level and matching commit identity, not loader replay-done.

`check_context_records.py` composes the source-pinned sole allocator, actual HC22
producer and actual native endpoint, the real SRAM/CRC slot link and retained
kind12 receiver. It tests image-digest, cap and runtime-epoch mutations. A second
component composes kind13, the strict1032 ledger, kind14 and ready0 revocation;
auth-digest, cap and missing-real-commit mutants fail. The ledger write-event
face in this context test is a fixture; separate real-macro proofs exist. The
full actual head/SU image-ledger join, cohort dispatch anchor and physical phase
composition remain required and are not claimed by this component receipt.
