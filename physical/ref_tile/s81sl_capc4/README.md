# S81 CAPC4 zero-cycle physical reach correction

Successor of CLOSED capc2 1f4c80cf6. Same top, seven RTL sources byte-identical, all children/outline/clock/cycles unchanged. source_equivalence.json pins all seven SHA256s. Native prior mapped/routed source census: 298796 cells including fill, data/reset max16 effective loads, OVER32=0, no unknown std masters; PG597592 terminals/unbound0. Exact committed evidence results/rtl/codex_s81_capc_audit_1020.

Changes: rt_e full E-face pin range starts at43.2um instead of2.16um, moving low eq bank up41um. This removes the measured405..424um eq0..13->TE reaches without an added data stage. Existing rst_l1 second landing is placed FIRM in legal middle-band row(171.99,190.08), no clone or new reset edge. Native hook test on exact prior6_final passes child-overlap check. rst_l0 stays at S face; source reset pin/stage0->stage1 planned reach<200um, stage1->TE reset<300um. Hard rt top159.84, LD/ED bottom216 leave a full-width middle band. Full new native measurement is mandatory before adoption; no endpoint waiver.

Safe design checklist:
1 PASS source: every data pin remains registered; same2stage reset landing. Placement secondstage moved only.
2 FIXED design: low eq pins shifted north; reset secondstage centre-fed. Gate and native census MUST show all effective endpoint paths<=405um; old21 failures remain immutable evidence.
3 PASS mapped identical source: max16 effective loads incl reset, OVER32=0 in actual oldnative6_final; no RTL/netlist mechanism change. Repeat census after new placement.
4 PASS source: no logic change; prior CLOSED TT+259.08/FF+25.46, SS sensitivity+30.71. No new timing claim.
5 PASS source: existing hardened SRAM children; no new flops or storage.
6 PASS design: unchanged43.2lattice children and full-width bands; E280pins/366um<1pin/um. Low fill pin/child bound remains recorded.
7 PENDING measured: unchanged clock spine, secondstage clock sink relocated; require native TT+FF spread<=80 and linked-pair check. io_hold0.03.
8 PASS static schedule:0 added data/control/reset edges.

NO REVIEW or submit until actual gate PNG inspection and fresh native reach/fanout/PG/clock qualification.
