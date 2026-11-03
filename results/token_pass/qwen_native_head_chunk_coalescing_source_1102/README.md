This is a source/record proposal, with no implementation, adoption or new job.
It preserves the admitted B source and the compact24-word post PASS scope.

Actual capture6742ae10a has511exact833000fs deltas in each512-word chunk,
including63→64,127→128 and all other round boundaries. The source active loop
also retains active/wrom_re across t increments, and its valid pipeline has no
round gate. The selected collector only retimes whole words. Therefore a
per-round STN reconfiguration inside an eight-round raw burst overlaps the
actual cfg_schedule_fault exclusion: cfg_v/mid/final0 versus any near/far/nb
valid. This is broader than the final partial-tail issue.

The preferred candidate keeps four actual8/8/8/1 GME instructions plus END,
coalescing each full chunk into six sender/receiver STNpairs with NWORDS64/KC8.
The last chunk retains five pairs (four NWORDS8, one NWORDS3, q5absent).
That is23pairs/46STNs, saving252CALRentries while preserving four-entry packing.
Current S8 authority nent1021→769/local37first1020→768 if all other entries and
alignment remain unchanged. Legacy KC1 calendar_candidate is not this authority.

All1187used BTABwords match the genuine scale image. Each physical receiver has
sbase72+8*r, so full chunks read contiguous72..135,136..199,200..263. Last round
starts264; all used addresses fit nine bits. All18992 real scalar row addresses
are covered exactly once by the candidate records in source_assessment.json.

Current controller r_addr=dbase+16*r_idx is wrong from index8 for a coalesced
chunk. An explicit defaultOFF HEAD stride is required:

    dbase + 768*(r_idx>>3) + 16*(r_idx&7)

A small implementation can compute seven-bit threeq=3*r_idx[7:3] and form the
head offset by concatenation, then retain the existing24-bit dbase adder. Only
offset bits14:7 need an eight-bit mux against the legacy offset. All256 r_idx
values were checked algebraically. Source proposal: use currently unused STN
bit67, latched as one controller flag; KC occupies59..66, user51..52, and all298
current HEAD STNs have bit67zero. The defaultOFF parameter and BASE profile
check are essential. STNcfg29/header/r_idx8 need no widening.

This is an analytic cost of approximately one flag FF per controller, a seven-
bit constant adder and eight-bit mux. No new pipeline edge is proposed, but no
TT/FF/fanout closure is claimed. The actual HARD1 controller is generated
repair4, so a logical-reference edit alone would not execute this candidate;
a guarded regenerated source view and equivalence/physical review are required.

NWORDS64/KC8 already fits station counters. Its final-K beats repeat every64raw
words, producing64results across512raw words. The eight-entry h9 ring wraps
normally, but positive lead, prefetch and per-wave storage bounds remain lease
qualifications. Nextcfg must wait both old result/busy drain and all input/
neighbor/config-pipeline exclusion. No dates are assigned in this proposal.

The q4partial/q5absent tail contract still needs a separate reviewed publisher
or sink fix. A cheap five-FF publisher needs a NEW local-drain-qualified mode-
changing GO lease; the old ready/barrier proxy does not prove it. Its data/control
scope must remain distinct from full L6 execution.

The alternative25one-round+END programme fits PC28..53/meta_rows54 and is disjoint
from WTN400..444, but26calendarrecords do not fit current eight-row/four-bit CALB.
Changing DEPTH alone crosses existing XPF space and PW1023. Coalescing avoids that
new storage/loader format. meta_rows is the CALS reservation count, not a physical
metadata instruction row. Full constraints are retained in the source report.
