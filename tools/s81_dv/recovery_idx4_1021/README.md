Actual historical IDX4 binding recovery. Parent selected72 plan/source58dc5866d remain untouched.

Recovered read-only EPYC6 /srv/opentallas-scratch/claude/s81-die11/mu7i4d2/src/results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json; actual source 20071be974b0470b7306ddde1259c9085f132443. Overlay contains ONLY five missing masters, six associated module port-width maps, two status-fault master registrations and opt-in vertical-relay mirror setting. Apply to the CURRENT table (not historical table):

python3 tools/s81_dv/recovery_idx4_1021/apply_overlay.py results/arch/s81_dv_1016/bind/bind_table_p4l3_mu.json

Current main frame-clock/landing entries remain intact. dv_bind adds historical absent-master abut skip and c179023bd's opt-in opposite vertical relay selection. dv_rvcase merges actual relay_mirror.json into CURRENT orientation map, preserving frame orientations. No broad legacy dv_bind or DIESTA reset-calendar replacement.

Actual missing RTL copied byte-for-byte from source20071be97: dsdv_idx_bsplit.sv (also defines ot_s81sl_slice_iq), dsdv_bk_sel_vm.sv, dsdv_idx_rg3_nq.sv. Existing current dsfd_ctrl_rg3/dsdv_idx_rg3/dsdv_idx_tree definitions are retained. The slice wrapper has +1 edge on bo and iq; bank-selector wrapper has +2 on rung and exports ca/cb/vm_fault; reader head and chain-end semantics are exactly the historical recorded recipe. No new alias, tie or view was invented.

Historical recorded STRICT_BIND PASS on BOTH checkers: 46 masters/12,266 instances and all binding-error counters zero. Actual case generated M8,190 stand-ins. These facts concern old122-frame plan, NOT a claimed selected72 result. All five added master views remain NULL/unqualified. In particular the reader's later ad3f30738 synthesis resolved async-load inference but its native19/max128 failure remains unresolved; no CLOSED reader/view claim. Controller gates are separate ongoing closures. This packet enables real integration generation with truthful stand-ins while child closures proceed. No new checks/tests/audits run.
