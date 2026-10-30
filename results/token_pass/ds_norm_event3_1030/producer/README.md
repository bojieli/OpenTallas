Actual current NORMR producer and schedule contradiction

Intel1 ot-run1878015-1793371931 PASS: one current selected VPb19ded3/VN05da5709
pair consumes all3920 genuine new-event3 input row writes through its real SRAM,
HLOAD/GAIN/NORMR. All80 independent BF16 hc_pre/chunk8 FP32 square-sum partials
match exactly at833ps. Payload control fails2 checks; +1age control fails80.
VP public c_v/c_d drive immediately after edge t -> n_go t+5 -> VN_b partial
output t+116. The first VP command capture t+1 is included116. Down facts end
at native leafdn_i*_q before that VP capture; up begins at VN_b output register
already included116. No boundary is counted twice. Earlier historical115 is
not reused. Actual80 native wrappers match VNa/b LM5LA6,bHW_STAGE0,zero extra
chain and n_go routing stages. The initial build lacking the explicit real VP
SRAMmodel is retained as build_missing_vp_macro.log and corrected in source.f.

Current path+116+PDSK has equal leaf2/3 totals139 at SID0 and141 at SID5.
Strict selected XRT59a53960 line884 faults on any non11111 partial set; line819
launches prun on first|pv. pq byte storage captures values but does not wait for
an asynchronous set. PDSK is a fixed per-leaf shift,not an elastic collector.
Distinct NORMR a1=5sid+leaf values force different CTL commands,so equal path
totals require the same engine slot and cannot be repaired by staggering alone.
composition.json preserves this current-source BLOCKED result.

repair_schedule.py searches all existing3bit PDSK options, minimizing changed
fields/depth delta/flops/selector bits. Minimum two fields: leaf3 depth1->0 only
at SID0/u_s_0S and SID5/u_s_2N,15'o01234->15'o00234. Removes64data+2valid FF,
keeps local max path151. It packs actual80 unchanged NORMR payloads into unique
per-engine slots (N20..81,S20..94),6live perengine,321decoded unsealedHOSTwords.
This is an unapplied source/physical freeze exception candidate,not adopted RTL,
a measured changed-selector collector or a complete safe programme. No GO,
KIT/END,sealing,global XFIN/RSTD/VQ K-profile or physical START claim. Initial
composition.json candidate+66FF is superseded by repair_candidate.json−66FF;
its current-source contradiction remains valid. Owner question recorded plainly.
