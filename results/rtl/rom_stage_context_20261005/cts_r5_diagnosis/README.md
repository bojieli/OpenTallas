W5 R5 actual CTS diagnosis (placement-estimated parasitics, not signoff)

All 41,870 actual register clock terminals have a native clock in SS and FF.
The CTS-0179 warnings do not prove missing register clocks. The intermediate
spine clock has no direct register launch/capture paths; its descendants do.
There is no parent ETM insertion in this vehicle: full source registers,
four real ROMs and actual ICG/DLL clock arcs are present, but XS/cm_q and final
capture remain external IO with ideal external clock insertion. No qualification
or power/adoption credit follows from this diagnostic.

Separate actual worst classes (SS setup / FF hold, ps):

| Class | SS setup | FF hold |
| --- | ---: | ---: |
| Return metadata | -1803.911 | -67.590 |
| Return adder | -1399.628 | +10.132 |
| AO quarantine | -1294.552 | -55.609 |
| Return control | -1073.147 | +11.666 |
| Return tag queue | -1067.284 | +10.923 |
| Return payload | -1044.299 | +11.255 |
| Domain control/result | -860.062 | -267.954 |
| Loader | -786.097 | -202.671 |
| AO scheduler/controller | -725.659 | -33.192 |
| AO replay/control | -657.741 | -29.278 |
| Retained shadow | -631.748 | -6.313 |
| MAC/control | -501.661 | -79.579 |
| Checked source state | -110.407 | -313.594 |
| BST capture | +290.502 | -592.634 |
| Domain ingress/DIF | +169.259 | -364.794 |
| Enclosing IO | -1731.123 | +497.237 |

The return metadata path starts at bt[38][9], passes RD64 head selection and
parent/normalization logic, and ends at by_t[6]. Its arrival is 3455.712ps;
required is1651.801ps. The separate return-adder path starts at the queue read
pointer; metadata-only acceleration will not repair that path.

AO qualifier DLL clocks are on the large root-register tree while ICG clock
checks are on the shallow macro branch. SS launch fall insertion1028.406ps
versus ICG target rise insertion289.169ps produces795.162ps setup skew including
uncertainty/CRPR. DLL->AO freeze arrival2274.106ps exceeds required979.554ps.
Domain r_go->element ICG has the same independent topology defect: source
1046.875ps versus target190.187ps,909.108ps setup skew. Loader qualifier also
feeds AO shadow/replay/scheduler paths; AO qualifier feeds enqueue enables and
fault output. These failures must be repaired without latch/ICG waivers.

BST FF hold is a real input-to-register path: XS port external delay166.667ps,
data arrival204.194ps, propagated capture insertion758.229ps plus25ps policy
and13.6ps library hold, required796.829ps. The missing real parent XS launch
context must be supplied; inserting guessed input latency or excluding IO is
not a repair. Config cm_q similarly needs the current source-owned synchronous
configuration-ROM provider, including actual clock/load and original loader
capture, rather than ideal IO timing. POR/native reset/gating paths stay checked.

Original raw metadata is preserved even though its slack_ps column was in
native ns: set_units emitted STA-0345 and report_units said1ns. The corrected
summary converts using actual report units, excludes native graph clock nodes
and deduplicates endpoints. Remaining missing-path graph nodes are enumerated
by pin kind; SETN/RESETN/tie-output/unused macro bits must not be called functional
unconstrained data solely because get_fanin reports a startpoint.

R5 global-route repair continues unchanged. No routed SS/FF or power result yet.
