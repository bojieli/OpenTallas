Actual shared-VM phase join, 2026-11-16

The selected source is genuine recovered rank0 layer1, slice0, user0, pidx9
(GU*r): nin256, nout1, destination1088, dsi1, no reduction. The source hash
and complete457-bit instruction are in every result. The native controller
uses live=((v<<3)+gl<nin_r); hence all eight heads are active on32 groups.
The native VMR requires lane0 active and equal address[23:3] among enabled
lanes. Actual private head graphs have equal intrinsic timing (QC ABI
normalized graph e20a48fb5894); no head-index compensation exists.

E_raw_actual.json preserves FAIL_SHARED_BANK_PHASE for every one of32
actual groups: command+write external phases43 on heads0..3,47 on4..7.
W_actual.json passes the static join at phase71 for all heads.
E_tuple4_candidate.json passes only the proposed coherent early-E tuple+4
phase map. It does not assert an emitted pad, native bank exactness or
physical qualification. QC owns that minimum bank/normalization proof.
Waiting between instructions cannot repair a split arrival within a group.

Reproducer: tools/qwen_layerbench/qc_vm_write_phase.py takes the protected
runtime mu_table_input.json and actual eight arrival phases. It decodes the
real stored instruction, checks active-lane bank/row and arrival alignment,
and exits2 on a mismatch while preserving a result. It refuses reduction
and non-window00 writers rather than applying this direct-bank law to
RED/CTL publication. No legacy compiler default or schedule is changed.

Timing endpoints remain separate: measured native SU output includes LRLY3;
normal MIF1 macro commit is five further native edges. Existing compiler
MARGIN8 already covers those five edges. Actual external write transport,
read-request overlap and SU busy-return control must compose before any
compiler gap or final period is selected. This packet does not invent one.

Runtime source: ep8 /srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/
tables_candidate1116/rank0/mu_table_input.json, permanently protected.
Native source: qfd_dv_s5_su8_rst3.sv live law247; qfd_dv_s5_vm8x.sv
qfd_dv_s8x_vmr normal-window decoder and w_bad_r. QC source census:
ep2 /srv/opentallas-scratch2/claude/qc-pinaccess-o/
QC-PINACCESS-O-SU-write-return-census.json. The static phase input is from
that exact source census; final normalized transport remains a separate input.
