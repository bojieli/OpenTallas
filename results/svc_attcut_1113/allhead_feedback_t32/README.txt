All16 logical heads, two H8 passes, real feedback/native T32 partition PASS

One actual D32 native provider's source fixture is replayed at16 declared
SX role offsets; this is an explicit staged dimension-provider replication,
not16native arithmetic instances. A protected SX master is reused16times;
a protected actual fold2 SM master is reused16times, eight active per HB.
Each active head uses production SE assembly, real160x256 Pbuffer/helper,
realH8 Psource, actual SX return and production-copied P packet glue.
Finite gain2^-8 and sink−32 make each uniform per-row head its own max;
independent oracle is e=exp0=1 (rawFP32 3f800000/BF16 3f80) on all32rows.
All256Pcoeff slots/pass and packed8words/pass are exact ones.
HB0 stage SMwrites386..398 byrole; HB1 writes391..403. Both root257..264,
Proot852..866, header853/body854..868, virtualGO128; late testPIO800.
Stageunit E7 oth-ubuntu-3043502-1794617737 PASS bothHBs, no errors/SX/SMfault.

Actual cached outer/native replay uses one WIN/landing, MORE1 firstpass,
Qreload with HB1, MORE0 secondpass; the second Q vector is quarter-scale so
stale Q reuse is detectable. Every fresh SCORE FP32 field,row/mask/flag/date
exactly equals the corresponding staged input. HB1's initially derived exact
quarter-scale candidate is now independently verified by fresh actualnative
output; native/fresh_source_hb*.hex equals staged/score_hb*.hex byte for byte.
Both GOcycles402/1702 have pre-edgephase1. Eachpass Q8,KV8(+2..9),SCORE8
(+77..84),returnedP8input(+726..740),Pconsume4,rawPV8(+892..899),drain40
slots(+1026..1065). Every rawPV FP32 field on all8activeheads is32 (42000000),
flags0; total512PVfields checked. Firstpass retainsjobOpen1/done0/active0
and all32landing rows. Finalpw/pr16,done1/jobOpen0,fc0,actualaf0,errors0.
Nativeunit E7 oth-ubuntu-3184400-1794618565 PASS, exactly1testbenchdriver
interposition; original/private archive checksums unchanged, no UUT edits or
state/memory backdoors. Native archive/limited-observability basis is1d60ef.
Cached tag/HB publication and drained payload outputs remain unobservable;
only live drain slots/counts are claimed. Parent's separate live drain proof
is complementary. No SO normalization, epoch identity, full-die G5, global
minimumPIO/PVO or H8 calibration claim. This is staged arithmetic/transport.

T128 runtime support IS IMPLEMENTED but NOT RUN. Both new binaries accept
rows32/128; host constructor has wcount0/nsel128 with8SELwords/128ROWS,
expectsKV32 and128-valued PV. Candidate T128SCORE dates77..108 require fresh
actual comparison, not adoption. T640 is deferred: it needs realwcount128/
nsel512 WIN/rank construction, not illegalnsel640. No T128/T640 qualification.

Capsules on epyc7 /srv/opentallas-scratch2/claude/hard-s81-svc-1/:
 allhead_feedback/t32 (SMprotectedcache sm_pl/, cone obj/, staged logs/hex)
 allhead_native_replay/t32 (native log, finalreceipt,closedmanifest,freshhex)
 allhead_native_replay/package.py (receipt collector, read-only)
Original qualified native cache remains native_programme/out/obj; private
link archive remains returned_p_replay/out_live/model_private.a. No own job
is running. These completedPASS files were checkpointed only for Claude reset
handoff; no new launch, test, adoption, merge, tag or POR change was made.
