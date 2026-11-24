# QC-HC3-LEC handoff (child of QC-ALLFIX; job: hc3 pvcca/clccfc R8 LEC NOT EQ 51 differs)
Updated 2026-11-24 13:58 PST.
## Root cause (posted 13:51)
- R8 netlist 00112d4e4e98 (kit QC-RELAUNCH-R1, copy epyc10 RELEC-R2/k/hc3p), fixed lec hash_seed 0, no hints: 51 differs = q[48..63]+q_bad in u_xl3_2/5/7.u_leaf.
- Leaf ot_qfd_xs_leaf_fo32 g_t: unkept hen[3] has same D/enable as kept hl[3]/hh[3]; l_en[gt]=hen[3] drives exactly q[48..63], q_bad (bad3).
- Gate has 0 hen flops (yosys merged into hl[3] or hh[3] per tile); lec pairs gold-only hen with the wrong survivor. Class (a) legal merge + (c) LEC correspondence gap. (b) ruled out: kit leaf sha 7b15b78e == main == cJ tree.
- EQ 22ee41 (pvcca, intel1 3818294) is the same class: unhinted it failed 85; EQ only with 32 proved hints hen==hh, hl==hh (LEC-AUTOFILL/r/hc3_pvcca_827_exact/enable_hints.json, epyc11).
## Fix
- RTL: delete hen, l_en[gt]=hh[3]. Clone epyc10 /srv/opentallas-scratch2/claude/QC-HC3-LEC/clone (uncommitted until NG4 bench). Bench (ot-run E10 oth-ubuntu-3715096-1795556968): NG3 PASS, MUT2 FAIL as required, NG4 pending.
## Rebuild
- Tree fork intel1 QC-ALLFIX/cJ/tree -> epyc10 QC-HC3-LEC/trees/c1j_hc3/tree (unit oth-ubuntu-3861061-1795557355). Bind refsha epyc10 QC-HC3-LEC/tmp/cJ_bind_refsha.json. Next: bind fork --bind-tree, overlay RTL, private-spec slw_hc3__clccfc3e6b__pvcca9ff41 goal route on E10, rt c66a01ee7285 (C1j spec rt).
