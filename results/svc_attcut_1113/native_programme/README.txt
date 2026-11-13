Native H8 static producer + real banded engine programme: PASS

Actual dsdv_svc_att decoder, Q/landing memories (macro SYNC1), native H8 RT2
head cores, band CAPD2/MREG1/SRX1/PAIR5. Fixed decoded CFG/WIN/SEL/ROWS/Q/P/GO
programme, T32, PO64/PVO200 declared test dates, both reset/GO phases. No source
or memory backdoors, no protocol engine stub, no runtime-ready-driven issue.
No production RTL/compiler edits in this commit; producer fix is84b3a53d7e.

Final E7 ot-run unit oth-ubuntu-1901239-1794612638 exit0.
Both GO phases: Q8, KV8 at II1, Ppush4/Paccept4 at II2, score8, rawPV8,
drained40words, done1, productionfc0, actualaf0 (all four expanders), phase
errors0. All score/PV beats explicitly nonzero. Exact phase-to-phase payloads,
flags and metadata match.
Relative to actual outer static-program GO edge (phase before that edge):
 phase1: Q3,5,...17; Ppush64,66,68,70; Paccept65,67,69,71;
         score77..84; rawPV156..163; drain202..241.
 phase0: Q2,4,...16; Ppush65,67,69,71; Paccept66,68,70,72;
         score76..83; rawPV157..164; drain202..241.
 KV accepts2..9 in both cases. These dates match prospective phase records.

Independent exact oracle: selected-row E2M1 code2 × E4M3 scale38 =1 in all32
dimensions, K=V=1. Q BF16(h,d)=3e80+32h+d; P BF16(r,h)=3e00+8r+h. All are
positive integer multiples of2^-10. Oracle sums32Q/head for scores and32P/head
for P.V using integers, then directly encodes exact FP32 bits; sums fit24bits
and do not depend on reduction order or DUT FP helpers. All1,024 FP32 fields
(32fields ×16beats ×2phases), tags, and zero arithmetic flags pass.

Original out/ zero-fixture receipt remains PASS for control/timing only; its
outputs were allzero because ROWS scale3c00 put scale0 in the low16 dimensions
where all nonzero FP4 codes were placed. It is retained/labeled, not promoted
as arithmetic evidence. New fixture uses all32 code2 fields and scales3838.
Original source copy/receipt/log and limitation text are included under zero/.

Scope: named fixedT32 source/control/timing and arithmetic witness. P words are
preloaded; this does NOT calibrate softmax-feedback PIO, general PVO, global
SX/P_ARR, compiler H8 readiness, or whole-die G5. H8_CALIBRATED staysFalse.
Native raw build/run capsules: epyc7 hard-s81-svc-1/native_programme/{out,
out_nonzero}; cache reused out/obj. Original unit1602885 exit0, finalunit1901239.
