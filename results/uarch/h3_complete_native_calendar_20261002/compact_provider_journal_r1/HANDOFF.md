Lossless streamed actual-provider journals — ready after 626d61a88

The additive CompactJournalBudget / CompactDiskEvents API dictionaries source/version/owner and phase metadata once; each event stores canonical unsigned64 integer fields, optional signed receipt metadata, dictionary IDs and a raw32-byte payload digest. Event streams and sparse128-event indexes remain on disk. Dictionary lookup cache is256 entries. No event list, phase sampling, dropped event, dictionary-per-phase fullJSON repetition or silent width truncation.

Every original canonicalJSON event can be reconstructed byte-exactly and reproduces the original length-framed SHA256. Online verification retains complete identity/tag/generation through request, reservation, issue, service, write visibility/read capture, consumer, reverse acceptance and reverse grant. Actual provider construction binds tag and write-residence capacities. Bad phase order/stale generation/tag reuse/capacity/changed write-payload digest faults retain the stored fault event and live debt. File close requires drain. Actual32-byte write payload hashes are captured at admission and backing visibility; read hashes use the actual captured return bytes. Existing raw journals lacking per-sector hashes are losslessly preserved as they are; no invented historical payload checksum.

Original r30/r21 provider arithmetic, addresses, finite queues, costs, storage and completion paths stay byte-identical. compact_sector_provider_class guards those exact source hashes and changes only the journal plus payload-checksum capture. CompactEventSpan is re-iterable with start/end/len and is compatible with r36 SizedEvents/SizedSlice; real original RF publish/readback is tested. open_compact_journal_reader gives an archived source-span reader for calendar/operand proof consumers. Software tick costs are unchanged; storage encoding supplies no hardware/clock/rate credit.

Runtime opt-in BEFORE provider construction, in a fresh process:

    import sys
    from tools.h3_complete_native_calendar import install_compact_provider_journals
    # Import the actual provider factory and Sagan driver/source-view modules first.
    modules = [m for name,m in list(sys.modules.items())
               if getattr(m,'__file__',None) and
               (name == 'hbm_bound_event_journal_r30' or
                name.startswith(('h3_ds_', 'h4_c0_ds_')))]
    receipt = install_compact_provider_journals(modules)
    # Archive receipt, construct the same actual factory/driver, execute unchanged.

The installer records each explicit alias and immutable module hash. It does not edit source files, existing instances or old evidence. Include the factory module itself if loaded under a different name. The original prefix/full-driver source/input GO checks still apply. Budget capacities are computed disk reservations, not injected RLIMIT/time/memory/file caps. Archivers MUST retain dictionary.sqlite and EVERY *.events/*.index file; budget.path alone is only the dictionary and is NOT a complete event archive. Preserve the caller's original output/input reference hashes and hardware qualification flags.

Existing joined source replay: all285184 events /37888 transactions across98 source journals replayed byte-exactly; this includes initialization and all219136 reviewed producer/shared/writer events, plus512 source receipts. No new synthetic arithmetic run. Current full calendar suite:80 PASS including real RF publisher, re-iterable slices, source96rank/home sizing, signed/null metadata, checksum mutation, stale reverse, premature tag reuse, truncation and width controls. Original compact replay and source model are byte-identical on regeneration.

Actual production PC0 journal is in sibling compact_actual_PC0_journal_r2. Parent reviewed original SQLite SHA6b4f32a19ab71908e90d51d9e6d292d73932c8d8d28d974fefc92f5b859940de; all5664480 actual events /738816 transactions /97 journals /96 ranks encoded and EVERY journal decoded and compared byte-exactly against its original framed digest. Compact files118545700 bytes, archive~23MiB, accounting119694206 bytes. Conversion395.32 seconds, peak206092KiB. Actual source producer file unchanged. The immutable codec snapshot used for that experiment is retained; current additive null/signed/span fixes are compatible with its binary format and are separately tested. No full-program or primitive-scratch transport credit: this source is actual PC0 native publication/golden comparison, source acquisition separately reviewed.

source_layout_bound.py sizes ALL actual PC0 record layouts, not a sample or compression ratio. Each integer/dictionary ID pays its64-bit maximum representation. It includes sparse indexes, file allocation padding, conservative static dictionary storage and prospective actual payload-checksum variants. Bound734381088 bytes for the same completed PC0 record shapes. Newly encountered future-PC/source receipt shapes require source sizing; this is NOT an all2213PC journal admission bound.

Historical staged-scratch PC0 model is explicitly separate: PC0_full96_source_phase_bound.json binds native c65 and real PC0 output homes for all96 ranks; 140850600720-byte compact phase reservation includes the old staged primitive-scratch upper plus source-derived real RF publication. Current r38 actual CPU-private/native path did NOT execute that scratch transport. It must not be used as a measured primitive movement count or to block an already admitted current prefix.

Kepler's r39 prefix0..9 PID1791203 was observed already running in its pinned tree with original encoding and source-sized362869817344-byte journal budget. It was left untouched; this codec is not a new gate, restart or alternate/fewer-rank substitute. Parent's later TASKS checkpoint reports that prefix stopped FAIL_CLOSED_PRESERVED on a persistent-output home binding; Kepler repairs that identity/home directory independently. Sagan/Kepler may opt into the compact API for subsequent source-admitted runs. This worker launched only lossless replay of the immutable completed PC0 evidence; no checkpoint/numerical rerun or W15/D1 restart.

Reproducible commands:

    python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
    python3 results/uarch/h3_complete_native_calendar_20261002/compact_provider_journal_r1/convert_retained.py --verify
    python3 results/uarch/h3_complete_native_calendar_20261002/compact_provider_journal_r1/source_size.py --verify
    python3 results/uarch/h3_complete_native_calendar_20261002/compact_actual_PC0_journal_r2/source_layout_bound.py --verify
    python3 results/uarch/h3_complete_native_calendar_20261002/compact_actual_PC0_journal_r2/convert_actual.py --verify

The last command reads the exact retained original1.39GB SQLite at /tmp/kepler-ds-r38-PC0-96rank-execution-20261002/actual-prefix-journal/events.sqlite and takes~6m36s; no production rerun. The committed23MiB compact archive plus source framed digests permits independent restoration without this source file. Native c65/source-home projection input prerequisites remain as documented in626d; no duplicate native or checkpoint archive is introduced.

Production primitive/shared movements remain193316 UNKNOWN. Finite physical RF/shared/L2 endpoint/calendar cost join and full released-checkpoint token remain incomplete. All previous failed/unqualified models remain unchanged. DS MTP third-party agentic per-request median provenance remains pending; pooled/chat assumptions receive no headline qualification.

Current production-owner join after Popper54bf8bc8 / parent19 tests:512 PC10 source spans point to state-fragment backing rather than their current production RF homes;64 output tiles use synthetic slot32 rather than their required production output slots. This codec preserves those source receipts and cannot relabel them as production. Source leaf pipeline costs alone exclude backend/arbitration/drain/consumer/reverse waits. No provisional1/1/1 costs are admitted. Required next input is source-resolved production rank/die/home translation, actual combined H1 ACK plus both copy write acceptance observations, and source-bound per-endpoint finite contender/hold/consumer/reverse guarantees. Whole-token physical movement remains UNKNOWN. See retained parent_production_owner_review.json and main tools/h4_hbm_production_owner.py final_r5.
