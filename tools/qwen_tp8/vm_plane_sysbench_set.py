#!/usr/bin/env python3
"""Bit-plane VM SYSTEM bench set (tb_qfd_vm_bv_ports, XPR): the whole record with one command.

  tools/qwen_tp8/vm_plane_sysbench_set.py [--src ROOT] [--host HOST] [--rdir DIR] [--only name,name] [--collect]

Syncs the needed sources of ROOT (default: this checkout) to <host>:~/<rdir>/wt (host default: the one `ot-run
--pick` names, i.e. the most memory free), launches every run
of RUNS in parallel there (each under `ot-heavy --mem`; nothing is built on localhost), fetches the run logs and
writes results/rtl/qwen_tp8_vm_plane_20261013/system/{record.json,<name>.log} into THIS checkout.
--collect skips the launch and rebuilds the record from the logs already on the host.
Exit status 0 only when record "ok" is true:
  every PASS-expected run prints PASS with exactly the stated counts, every FAIL-expected mutant prints FAIL
  (a real bench FAIL line with rc 0: a build failure or a crash is not a killed mutant), and the known system-bench
  gap (MUT=5) is killed by the committed leaf miter.
The -G sets are the predecessor's scratch command lines verbatim (recovered from each scratch build's
Vtb_qfd_vm_bv_ports__verFiles.dat); shape rule (parent comments): VMT x latency XVM = 12 + RV + RO + 7, SU answer
VL = 7 + RV + RO + 5, bit plane XVM += XPR + 1 - RO.  Bench defaults: RV 1, RO 2, SEED 5, NRB 16, ELEMS 16384.
"""
import argparse, hashlib, json, os, re, shlex, subprocess, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REC = "results/rtl/qwen_tp8_vm_plane_20261013/system"
LEAF_REC = "results/rtl/qwen_tp8_vm_plane_20261013/leaf_miter/record.json"
COMMON = "-GCYCLES=40000 -GTSR=1 -GXQT=1 -GMEE=1 -GVMT=1"
BASE_FILES = [
    "rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv",
    "rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv",
    "rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xplane.sv",
    "rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_xtree.sv",
    "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv",
    "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv",
    "rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv",
    "rtl/hdc/ot_hdc_delay.sv",
]
RQ_FILES = [
    "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_region_quarter.sv",
    "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_xfifo8_t.sv",
    "rtl/qwen_sys/vm_die_split_20261012/ot_qfd_vm_answer_tiles.sv",
]
RQ = "+define+OT_QFD_VM_TILE_MOD=ot_qfd_vm_region_quarter " + " ".join(RQ_FILES)
RL_FILES = RQ_FILES + ["rtl/qwen_sys/vm_plane_20261013/ot_qfd_vm_region_leaf.sv"]
RL = "+define+OT_QFD_VM_TILE_MOD=ot_qfd_vm_region_leaf " + " ".join(RL_FILES)
# trees + owners (qwen-tp8-vm-rtl): control trees 3 levels (+0 edges), me tree 2 levels (me 3 edges early), line / x_q
# leaf owners with 2 x_q relay stages (+ XQR + 2 = 4 edges: XVM 32 -> 36 on r21, 31 -> 35 on the RO 2 / r11 shapes).
T = "-GXTK=3 -GXMK=2 -GXLO=1 -GXQR=2"
TR = dict(XTK=3, XMK=2, XLO=1, XQR=2)
TP = "-GXTK=7 -GXMK=2 -GXLO=1 -GXQR=2"
TRP = dict(XTK=7, XMK=2, XLO=1, XQR=2)
S3 = "-GSEED=3 -GVL=15 -GXPR=10"
S9 = "-GSEED=9 -GVL=15 -GXPR=10"
R11 = "-GSEED=5 -GRV=1 -GRO=1 -GVL=14 -GXPR=10"
R21 = "-GSEED=7 -GRV=2 -GRO=1 -GVL=15"
N64 = "-GSEED=5 -GRV=1 -GRO=1 -GVL=14 -GNRB=64"
C_R21 = dict(NRB=16, SW=8, VL=15, su_reads=60170, row_reads=9427, tuples=2683, bursts=1612, land_steps=1603)
PM = 48   # GB for a production-shape run with trees: the verilation alone peaks above 12 GB (12 GB runs were OOM-killed)
# NRB 64 counts re-based 2026-10-13 with the work-conserving skid queue, as SEED 3 below (was 60313 / 9296 / 2992 / 1635 /
# 1625); the four tile variants (grp, region_quarter, region_leaf, with and without the bit plane) still agree exactly.
C_N64 = dict(NRB=64, SW=8, VL=14, su_reads=60379, row_reads=9334, tuples=2909, bursts=1615, land_steps=1606)


def run(name, args, expect, what, counts=None, extra="", mem=4, scratch=None, same_as=None, tree=None, wq=None,
        prod=None):
    """same_as: a run whose PASS counts this run must reproduce exactly.  tree: the TREE line the log must carry
    (parameters equal, every requested structure seen moving): the coverage refusal of a tree / owner build.
    wq: requirements on the bench's WQ line (the skid capacity rule's model against the memory): a dict of
    key -> exact value, or key -> ">=N".  prod: 0 / 1 = the PRODUCTION shape through vm_plane_sysbench_prod.sh
    (0 the tree-less reference at me_want lookahead 3, 1 trees + owners); args are then the extra -G only."""
    return dict(name=name, args=args, extra=extra, expect=expect, what=what, counts=counts, mem=mem, scratch=scratch,
                same_as=same_as, tree=tree, wq=wq, prod=prod,
                tile="ot_qfd_vm_region_leaf" if ("region_leaf" in extra or prod is not None)
                else "ot_qfd_vm_region_quarter" if extra else "ot_qfd_vm_grp")


# expect: PASS | FAIL | GAP (a mutant the system bench is known not to kill: recorded, never counted as a mutant pass)
#         | INFO (recorded, not gated).  counts: required on the PASS line.  scratch: the scratch log's line (reference).
RUNS = [
    run("base_r21", R21 + " -GXVM=22", "PASS", "XPR=0 regression, vmt_r21 shape (RV 2 RO 1), tile ot_qfd_vm_grp", C_R21),
    run("bp_r21", R21 + " -GXVM=32 -GXPR=10", "PASS", "XPR=10, r21 (RV 2 RO 1)", C_R21),
    # SEED 3 counts re-based 2026-10-13 with the work-conserving skid queue (was 59514 / 8973 / 3016 / 1560 / 1550): a
    # sequencer row behind a denied one is now written at once, the merge's row of that edge waits, and the engine
    # stall (me_ok) moves by an edge, which shifts this bench's engine-synchronous random draws.  Every other fixed
    # count of this set except the NRB 64 shape (C_N64) is unchanged by the fix.
    run("bp_s3", "-GSEED=3 -GXVM=31 -GVL=15 -GXPR=10", "PASS", "XPR=10, bench default RV 1 RO 2, stimulus SEED 3",
        dict(NRB=16, SW=8, VL=15, su_reads=59467, row_reads=8937, tuples=3002, bursts=1546, land_steps=1536)),
    run("bp_s9", "-GSEED=9 -GXVM=31 -GVL=15 -GXPR=10", "PASS", "XPR=10, bench default RV 1 RO 2, stimulus SEED 9",
        dict(NRB=16, SW=8, VL=15, su_reads=61202, row_reads=9670, tuples=2711, bursts=1583, land_steps=1574)),
    run("bp_r11", "-GSEED=5 -GRV=1 -GRO=1 -GXVM=31 -GVL=14 -GXPR=10", "PASS", "XPR=10, r11 (RV 1 RO 1), SEED 5",
        dict(NRB=16, SW=8, VL=14, su_reads=60240, row_reads=9406, tuples=2630, bursts=1606, land_steps=1597)),
    run("bp_nomee", "-GSEED=3 -GXVM=31 -GVL=15 -GXPR=10 -GMEE=0", "PASS", "XPR=10, MEE=0 (no early enable), RV 1 RO 2, SEED 3",
        dict(NRB=16, SW=8, VL=15, su_reads=59130, row_reads=8975, tuples=2835, bursts=1561, land_steps=1551)),
    run("bp_r21_x11", R21 + " -GXVM=33 -GXPR=11", "PASS", "XPR=11 (one more relay), r21", C_R21),
    run("bp_r21_m3", R21 + " -GXVM=32 -GXPR=10 -GMUT=3", "FAIL", "mutant: plane 5 fine rotation wrong", scratch="x=37438"),
    run("bp_r21_m4", R21 + " -GXVM=32 -GXPR=10 -GMUT=4", "FAIL", "mutant: plane 5 element shift wrong", scratch="x=38308"),
    run("bp_r21_m5", R21 + " -GXVM=32 -GXPR=10 -GMUT=5", "GAP",
        "mutant: plane 5 range count ignored. KNOWN SYSTEM-BENCH GAP: the bench never issues an x beat past ELEMS, "
        "so this mutant is invisible here; it is killed only by the leaf miter (lf_p3 in " + LEAF_REC + ")", C_R21),
    run("bp_r21_m6", R21 + " -GXVM=32 -GXPR=10 -GMUT=6", "FAIL", "mutant: one relay free-runs", scratch="x=1158"),
    run("bp_r21_m7", R21 + " -GXVM=32 -GXPR=10 -GMUT=7", "FAIL", "mutant: planes 0 and 1 swapped", scratch="x=38028"),
    run("bp_r21_lat9", R21 + " -GXVM=31 -GXPR=10", "INFO",
        "XVM one edge SHORT of the rule (31 instead of 32): the scratch run PASSED (row_reads 9422). XVM goes to both "
        "the DUT and the reference, so the bench does not pin the latency rule by itself; recorded, not gated",
        scratch="PASS row_reads=9422"),
    run("n64_base", N64 + " -GXVM=21", "PASS", "NRB=64 XPR=0, default tile ot_qfd_vm_grp (the scratch n64_base shape)",
        C_N64, mem=8),
    run("n64_base_rq", N64 + " -GXVM=21", "PASS", "NRB=64 XPR=0, region tile ot_qfd_vm_region_quarter", C_N64, RQ, 8),
    run("n64_bp_rq", N64 + " -GXVM=31 -GXPR=10", "PASS", "NRB=64 XPR=10, region tile", C_N64, RQ, 8),
    run("n64_bp_rq_m3", N64 + " -GXVM=31 -GXPR=10 -GMUT=3", "FAIL", "NRB=64 region tile, mutant: plane 5 fine rotation",
        None, RQ, 8, "x=38574"),
    run("n64_bp_rq_m6", N64 + " -GXVM=31 -GXPR=10 -GMUT=6", "FAIL", "NRB=64 region tile, mutant: one relay free-runs",
        None, RQ, 8, "x=249"),
    # ---- the region built from leaves only (ot_qfd_vm_region_leaf: gctl_t, rowrd_t, delay leaves) ----
    run("n64_base_rl", N64 + " -GXVM=21", "PASS", "NRB=64 XPR=0, region tile ot_qfd_vm_region_leaf", C_N64, RL, 8),
    run("n64_bp_rl", N64 + " -GXVM=31 -GXPR=10", "PASS", "NRB=64 XPR=10, region_leaf tile", C_N64, RL, 8),
    # ---- trees and owners in the parent.  Control trees alone and owners alone keep the stimulus (same counts as the
    #      committed runs); the me tree needs me_want 3 negedges ahead (MWD 3), which shifts the bench's random stream:
    #      its reference is the tree-less run at the same MWD. ----
    run("tr_k3_r21", R21 + " -GXVM=32 -GXPR=10 -GXTK=3", "PASS", "control trees only (3 levels): x latency + 0, XVM 32",
        C_R21, tree=dict(XTK=3, XMK=0, XLO=0, XQR=0)),
    run("tr_lo0_r21", R21 + " -GXVM=34 -GXPR=10 -GXLO=1", "PASS", "line / x_q owners only, XQR 0: x latency + 2, XVM 34",
        C_R21, tree=dict(XTK=0, XMK=0, XLO=1, XQR=0)),
    run("mw3_bp_r21", R21 + " -GXVM=32 -GXPR=10 -GMWD=3", "PASS", "REFERENCE: no trees, me_want lookahead 3 (r21)"),
    run("mw3_bp_s3", S3 + " -GXVM=31 -GMWD=3", "PASS", "REFERENCE: no trees, me_want lookahead 3 (s3)"),
    run("mw3_bp_s4", "-GSEED=4 -GVL=15 -GXPR=10 -GXVM=31 -GMWD=3", "PASS", "REFERENCE: no trees, me_want lookahead 3 (SEED 4)"),
    # SEED 9 at lookahead 3 (the 09:05 open finding, CLOSED): at cycle 30,465 the 2-deep head-of-line sequencer skid
    # queue lost row 381: three row writes on consecutive edges (352, 367, 381), the first denied twice by SU lane
    # rows on bank 0.  Legal traffic (no spacing rule on the row port): an RTL capacity defect of the base memory.
    # Fixed by the work-conserving SQD 4 queue + the stated capacity rule; these runs are GATED now, and the queue
    # must really have held 3 sequencer rows (the old design's overflow point).
    run("mw3_bp_s9", S9 + " -GXVM=31 -GMWD=3", "PASS", "REFERENCE: no trees, lookahead 3, SEED 9 (3 sequencer rows waiting)",
        wq=dict(seq=3, model_overflow=0, dut_overflow=0)),
    run("mw3_base_s9", "-GSEED=9 -GVL=15 -GXVM=22 -GMWD=3", "PASS", "XPR 0 (no bit plane), lookahead 3, SEED 9",
        dict(NRB=16, SW=8, VL=15, su_reads=61149, row_reads=9469, tuples=2767, bursts=1588, land_steps=1578),
        wq=dict(seq=3, model_overflow=0, dut_overflow=0)),
    run("wq_s9_m14", "-GSEED=9 -GVL=15 -GXVM=22 -GMWD=3 -GMUT=14", "FAIL",
        "mutant: skid queues hold 2 rows (the pre-fix capacity) on SEED 9 lookahead 3: the row is lost again",
        wq=dict(model_overflow=0, dut_overflow=">=1"), scratch="image=1"),
    # ---- skid capacity rule, directed (WDIR): SQD sequencer rows on consecutive edges onto one bank that SU lane
    #      rows hold, two of them the same row, then a reducer element on that bank ----
    run("wq_d1_base", R21 + " -GXVM=22 -GWDIR=1", "PASS", "directed burst AT the bound, XPR 0: sequencer queue at SQD = 4",
        wq=dict(seq=4, model_overflow=0, dut_overflow=0)),
    run("wq_d1_tr", R21 + " -GXVM=36 -GXPR=10 -GWDIR=1 " + T, "PASS", "directed burst AT the bound, ALL trees + owners",
        wq=dict(seq=4, model_overflow=0, dut_overflow=0), tree=TR),
    run("wq_d1_m14", R21 + " -GXVM=22 -GWDIR=1 -GMUT=14", "FAIL", "mutant: 2-row skid queues under the directed burst",
        wq=dict(model_overflow=0, dut_overflow=">=1")),
    run("wq_d2_failstop", R21 + " -GXVM=22 -GWDIR=2", "FAIL",
        "one row BEYOND the bound: the rule's model overflows and the memory must raise w_fault (fail-stop, not a mutant "
        "of the memory: a negative control of the rule)", wq=dict(model_overflow=1, dut_overflow=1), scratch="w1"),
    run("mw3_bp_r11", R11 + " -GXVM=31 -GMWD=3", "PASS", "REFERENCE: no trees, me_want lookahead 3 (r11)"),
    run("tr_m2_r21", R21 + " -GXVM=32 -GXPR=10 -GXMK=2", "PASS", "me tree only (2 levels, me 3 edges early): + 0, XVM 32",
        same_as="mw3_bp_r21", tree=dict(XTK=0, XMK=2, XLO=0, XQR=0)),
    run("tr_all_r21", R21 + " -GXVM=36 -GXPR=10 " + T, "PASS", "ALL trees + owners, r21: XVM 36", same_as="mw3_bp_r21", tree=TR),
    run("tr_all_s3", S3 + " -GXVM=35 " + T, "PASS", "ALL trees + owners, RV 1 RO 2 SEED 3: XVM 35", same_as="mw3_bp_s3", tree=TR),
    run("tr_all_s4", "-GSEED=4 -GVL=15 -GXPR=10 -GXVM=35 " + T, "PASS", "ALL trees + owners, RV 1 RO 2 SEED 4: XVM 35",
        same_as="mw3_bp_s4", tree=TR),
    run("tr_all_s9", S9 + " -GXVM=35 " + T, "PASS", "ALL trees + owners, RV 1 RO 2 SEED 9: XVM 35", same_as="mw3_bp_s9",
        tree=TR, wq=dict(seq=3, model_overflow=0, dut_overflow=0)),
    run("tr_all_r11", R11 + " -GXVM=35 " + T, "PASS", "ALL trees + owners, r11: XVM 35", same_as="mw3_bp_r11", tree=TR),
    run("tr_nomee", "-GSEED=3 -GXVM=35 -GVL=15 -GXPR=10 -GMEE=0 -GXTK=3 -GXLO=1 -GXQR=2", "PASS",
        "MEE=0 (no early enable, so no me tree): control trees + owners, XVM 35", same_as="bp_nomee",
        tree=dict(XTK=3, XMK=0, XLO=1, XQR=2)),
    run("mw4_rsd5_bp_r21", R21 + " -GXVM=32 -GXPR=10 -GMWD=4 -GRSD=5", "PASS",
        "REFERENCE: no trees, me_want lookahead 4, stall loop RSD 5"),
    run("tr_all_m3_r21", R21 + " -GXVM=36 -GXPR=10 -GXTK=3 -GXMK=3 -GXLO=1 -GXQR=2 -GRSD=5", "PASS",
        "ALL trees + owners with a 3-level me tree (me 4 edges early: needs the stall loop RSD >= 5)",
        same_as="mw4_rsd5_bp_r21", tree=dict(XTK=3, XMK=3, XLO=1, XQR=2)),
    run("tr_all_r21_lat", R21 + " -GXVM=35 -GXPR=10 " + T, "INFO",
        "XVM one edge SHORT of the rule with trees + owners (35 instead of 36): recorded, not gated"),
    run("tr_all_r21_m3", R21 + " -GXVM=36 -GXPR=10 -GMUT=3 " + T, "FAIL", "trees + owners, mutant: plane 5 fine rotation"),
    run("tr_all_r21_m6", R21 + " -GXVM=36 -GXPR=10 -GMUT=6 " + T, "FAIL", "trees + owners, mutant: one relay free-runs"),
    run("tr_all_r21_m8", R21 + " -GXVM=36 -GXPR=10 -GMUT=8 " + T, "FAIL", "mutant: a plane-control tree node is transparent"),
    run("tr_all_r21_m9", R21 + " -GXVM=36 -GXPR=10 -GMUT=9 " + T, "FAIL", "mutant: a me-tree node is transparent"),
    run("tr_all_r21_m10", R21 + " -GXVM=36 -GXPR=10 -GMUT=10 " + T, "FAIL", "mutant: line leaf 3 picks a wrong source"),
    run("tr_all_r21_m11", R21 + " -GXVM=36 -GXPR=10 -GMUT=11 " + T, "FAIL", "mutant: x_q face 0 free-runs"),
    run("tr_all_r21_m12", R21 + " -GXVM=36 -GXPR=10 -GMUT=12 " + T, "FAIL", "mutant: a line-control tree node is transparent"),
    run("tr_all_r21_m13", R21 + " -GXVM=36 -GXPR=10 -GMUT=13 " + T, "FAIL", "mutant: one x_q relay free-runs"),
    run("mw3_n64_bp_rq", N64 + " -GXVM=31 -GXPR=10 -GMWD=3", "PASS", "REFERENCE: NRB=64 region_quarter, no trees, lookahead 3",
        None, RQ, 8),
    run("n64_tr_rl", N64 + " -GXVM=35 -GXPR=10 " + T, "PASS", "NRB=64, region_leaf tile, ALL trees + owners: XVM 35",
        None, RL, 8, same_as="mw3_n64_bp_rq", tree=TR),
    run("n64_tr_rl_m9", N64 + " -GXVM=35 -GXPR=10 -GMUT=9 " + T, "FAIL", "NRB=64 region_leaf + trees, mutant: me-tree node",
        None, RL, 8),
    run("n64_tr_rl_m10", N64 + " -GXVM=35 -GXPR=10 -GMUT=10 " + T, "FAIL", "NRB=64 region_leaf + trees, mutant: line leaf 3",
        None, RL, 8),
    # ---- PRODUCTION SHAPE (vm_plane_sysbench_prod.sh): SW 64, ELEMS 177,808, NRB 64, SMIN 7, SMAX 11, BMAX 8, the
    #      die's 14 strides, CRB 16, region built from leaves, RV 1 RO 1; bit plane XPR 10, trees XTK 3 / XMK 2,
    #      owners with XQR 2.  x latency: XVM 24 (tiles) -> 34 (bit plane) -> 38 (owners); SU answer VL 14. ----
    run("prod_ref", "", "PASS", "PRODUCTION shape, bit plane, NO trees (reference at me_want lookahead 3): XVM 34",
        mem=12, prod=0, wq=dict(model_overflow=0, dut_overflow=0)),
    run("prod_tr", "", "PASS", "PRODUCTION shape, bit plane + ALL trees + owners (XPR 10, XQR 2): XVM 38",
        mem=PM, prod=1, same_as="prod_ref", tree=TR, wq=dict(model_overflow=0, dut_overflow=0)),
    run("prod_tr_s9", "-GSEED=9", "PASS", "PRODUCTION shape, trees + owners, SEED 9", mem=PM, prod=1, tree=TR,
        wq=dict(model_overflow=0, dut_overflow=0)),
    run("prod_tr_d1", "-GWDIR=1", "PASS", "PRODUCTION shape, trees + owners, directed skid burst at the bound",
        mem=PM, prod=1, tree=TR, wq=dict(seq=4, model_overflow=0, dut_overflow=0)),
    run("prod_tr_m1", "-GMUT=1", "FAIL", "PRODUCTION shape mutant: SU read lane select one lane off", mem=PM, prod=1),
    run("prod_tr_m3", "-GMUT=3", "FAIL", "PRODUCTION shape mutant: plane 5 fine rotation wrong", mem=PM, prod=1),
    run("prod_tr_m6", "-GMUT=6", "FAIL", "PRODUCTION shape mutant: one x relay free-runs", mem=PM, prod=1),
    run("prod_tr_m9", "-GMUT=9", "FAIL", "PRODUCTION shape mutant: a me-tree node is transparent", mem=PM, prod=1),
    run("prod_tr_m10", "-GMUT=10", "FAIL", "PRODUCTION shape mutant: line leaf 3 picks a wrong source", mem=PM, prod=1),
    run("prod_tr_m13", "-GMUT=13", "FAIL", "PRODUCTION shape mutant: one x_q relay free-runs", mem=PM, prod=1),
    run("prod_tr_m14", "-GWDIR=1 -GMUT=14", "FAIL", "PRODUCTION shape mutant: 2-row skid queues under the directed burst",
        mem=PM, prod=1, wq=dict(model_overflow=0, dut_overflow=">=1")),
    # ---- PLAN parameters (claude/qwen-tp8-vm PLAN 2026-10-13, results/arch/qwen_tp8_1012/vm_plane_lanes_claude.json): the
    #      placed x lanes need XPR 12 relay stages (every lane padded to 12), the control trees over the 5-mm column row
    #      need XTK 7 registered levels (13 stations at the strip tops, <= 449 um apart, root at the row centre; tapped 7
    #      entries early: + 0), me tree 2 levels, XQR 2.  x latency = XPR + 1 - RO
    #      + XQR + 2: r21 / r11 (RO 1) 22 -> 38 / 21 -> 37, RO 2 shape 22 -> 37, production (RO 1) 24 -> 40 = + 16. ----
    run("plan_r21", R21 + " -GXVM=38 -GXPR=12 " + TP, "PASS", "PLAN XPR 12 / XTK 7 / XMK 2 / XQR 2, r21: XVM 38",
        same_as="mw3_bp_r21", tree=TRP),
    run("plan_s3", "-GSEED=3 -GVL=15 -GXPR=12 -GXVM=37 " + TP, "PASS", "PLAN parameters, RV 1 RO 2 SEED 3: XVM 37",
        same_as="mw3_bp_s3", tree=TRP),
    run("plan_r21_m6", R21 + " -GXVM=38 -GXPR=12 -GMUT=6 " + TP, "FAIL", "PLAN parameters, mutant: one relay free-runs"),
    run("plan_r21_m8", R21 + " -GXVM=38 -GXPR=12 -GMUT=8 " + TP, "FAIL",
        "PLAN parameters, mutant: a plane-control tree node (last level) is transparent"),
    run("plan_r21_m12", R21 + " -GXVM=38 -GXPR=12 -GMUT=12 " + TP, "FAIL",
        "PLAN parameters, mutant: a line-control tree node (last level) is transparent"),
    run("plan_n64_rl", N64 + " -GXVM=37 -GXPR=12 " + TP, "PASS", "PLAN parameters, NRB=64, region_leaf tile: XVM 37",
        None, RL, 8, same_as="mw3_n64_bp_rq", tree=TRP),
    run("plan_prod", "-GXPR=12 -GXVM=40 -GXTK=7", "PASS", "PRODUCTION shape at the PLAN parameters (XPR 12, XTK 7): XVM 40",
        mem=PM, prod=1, same_as="prod_ref", tree=TRP, wq=dict(model_overflow=0, dut_overflow=0)),
    run("plan_prod_m6", "-GXPR=12 -GXVM=40 -GXTK=7 -GMUT=6", "FAIL", "PRODUCTION shape, PLAN parameters, mutant: one x relay free-runs",
        mem=PM, prod=1),
    run("plan_prod_m8", "-GXPR=12 -GXVM=40 -GXTK=7 -GMUT=8", "FAIL",
        "PRODUCTION shape, PLAN parameters, mutant: a plane-control tree node is transparent", mem=PM, prod=1),
]


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=ROOT)
    ap.add_argument("--host", default="")
    ap.add_argument("--rdir", default="claude-vm-verif-1013/A")
    ap.add_argument("--only", default="")
    ap.add_argument("--collect", action="store_true")
    a = ap.parse_args()
    RDIR = a.rdir
    if not a.host:
        pk = sh("ot-run --mem 64 --pick -- true")
        m = re.search(r"-> (\S+)", pk.stdout + pk.stderr)
        if not m:
            sys.exit("no host from ot-run --pick: " + (pk.stdout + pk.stderr)[-300:])
        a.host = m.group(1)
        print("host", a.host, file=sys.stderr)
    src = os.path.abspath(a.src)
    runs = [r for r in RUNS if not a.only or r["name"] in a.only.split(",")]
    files = BASE_FILES + RL_FILES
    out = os.path.join(ROOT, REC)
    os.makedirs(out, exist_ok=True)
    runner = os.path.join(HERE, "vm_plane_sysbench.sh")
    prunner = os.path.join(HERE, "vm_plane_sysbench_prod.sh")
    if not a.collect:
        sh(f"ssh {a.host} mkdir -p {RDIR}/wt {RDIR}/b", check=True)
        subprocess.run(["rsync", "-a", "--relative"] + files + [f"{a.host}:{RDIR}/wt/"], cwd=src, check=True)
        subprocess.run(["rsync", "-a", runner, prunner, f"{a.host}:{RDIR}/"], check=True)
        lines = [f"cd ~/{RDIR} && export VM_SYSB_WT=$HOME/{RDIR}/wt VM_SYSB_B=$HOME/{RDIR}/b && "
                 + " ".join(f"rm -f b/{r['name']}.line;" for r in runs)]
        for r in runs:
            cmd = f"./vm_plane_sysbench.sh {r['name']} {shlex.quote(r['args'])} {r['extra']}"
            if r["prod"] is not None:
                cmd = f"./vm_plane_sysbench_prod.sh {r['name']} {r['prod']} {shlex.quote(r['args'])}"
            lines.append(f"( ot-heavy --mem {r['mem']} -- {cmd} > b/{r['name']}.line 2>b/{r['name']}.err ) &")
        lines.append("wait")
        p = subprocess.run(["ssh", a.host, "bash", "-s"], input="\n".join(lines) + "\n", text=True)
        if p.returncode:
            print("remote launch rc", p.returncode, file=sys.stderr)
    # the remote tree must be byte-identical to the hashed sources
    hashes = {f: sha(os.path.join(src, f)) for f in files}
    rh = sh(f"ssh {a.host} 'cd {RDIR}/wt && sha256sum {' '.join(files)}; sha256sum ../vm_plane_sysbench.sh; "
            f"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --version; hostname'").stdout.split("\n")
    remote = {l.split()[1]: l.split()[0] for l in rh if re.match(r"^[0-9a-f]{64} ", l)}
    tree_ok = all(remote.get(f) == h for f, h in hashes.items()) and remote.get("../vm_plane_sysbench.sh") == sha(runner)
    prh = sh(f"ssh {a.host} sha256sum {RDIR}/vm_plane_sysbench_prod.sh").stdout.split()
    tree_ok = tree_ok and bool(prh) and prh[0] == sha(prunner)
    ver = next((l for l in rh if l.startswith("Verilator")), "?")
    host = [l for l in rh if l.strip()][-1] if rh else "?"
    commit = sh(f"git -C {shlex.quote(src)} rev-parse HEAD").stdout.strip()
    dirty = sh(f"git -C {shlex.quote(src)} status --porcelain -- {' '.join(files)}").stdout.strip()
    names = " ".join(r["name"] for r in runs)
    subprocess.run(f"cd {shlex.quote(out)} && for n in {names}; do scp -q {a.host}:{RDIR}/b/$n.log . 2>/dev/null; done",
                   shell=True)
    rl = sh(f"ssh {a.host} 'cd {RDIR}/b && for n in {names}; do echo \"@@ $n\"; cat $n.line 2>/dev/null; done'").stdout
    got = {}
    for blk in rl.split("@@ ")[1:]:
        n, _, rest = blk.partition("\n")
        got[n.strip()] = rest.strip()
    leaf = {}
    try:
        leaf = json.load(open(os.path.join(src, LEAF_REC)))["runs"]["lf_p3"]
    except Exception as e:  # noqa
        leaf = {"error": str(e)}
    leaf_kills = leaf.get("expect") == "FAIL" and leaf.get("got") == "FAIL"
    recs, bad = [], []

    def wq_check(r, o):
        """The WQ line of the run's log against r['wq'] (the skid capacity rule: model vs memory)."""
        wl = ""
        try:
            wl = next((l for l in open(os.path.join(out, r["name"] + ".log")) if l.startswith("WQ ")), "")
        except OSError:
            pass
        wv = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", wl)}
        ok = bool(wl)
        for k, v in r["wq"].items():
            ok = ok and k in wv and (wv[k] >= int(v[2:]) if isinstance(v, str) else wv[k] == v)
        o.update(wq_expected=r["wq"], wq_line=wl.strip(), wq_ok=ok)
        return ok
    for r in runs:
        line = got.get(r["name"], "")
        m = re.search(r"rc=(\S+) ((?:PASS|FAIL) .*?) maxrss_kb=(\d+) wall=([\d.]+) build_s=(\d+)", line)
        o = dict(name=r["name"], what=r["what"], args=f"{COMMON} {r['args']}", extra_verilator_args=r["extra"],
                 production_shape=r["prod"] is not None,
                 runner="vm_plane_sysbench_prod.sh %d" % r["prod"] if r["prod"] is not None else "vm_plane_sysbench.sh",
                 tile_module=r["tile"], expected=r["expect"], ot_heavy_mem_gb=r["mem"], scratch_reference=r["scratch"],
                 log=f"{r['name']}.log")
        if not m:
            o.update(observed="NO-RESULT", observed_line=line[:300], ok=False)
        else:
            res = m.group(2)
            cnt = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", res)} if res.startswith("PASS") else None
            o.update(observed=res.split()[0], observed_line=res, rc=int(m.group(1)), counts=cnt,
                     fail_counts=dict(re.findall(r"(\w+)=(\S+)", res)) if res.startswith("FAIL") else None,
                     maxrss_kb=int(m.group(3)), wall_s=float(m.group(4)), build_s=int(m.group(5)))
            exp_cnt = r["counts"]
            cnt_ok = exp_cnt is None or (cnt is not None and all(cnt.get(k) == v for k, v in exp_cnt.items()))
            o["expected_counts"] = exp_cnt
            if r["expect"] == "PASS":
                o["ok"] = o["observed"] == "PASS" and o["rc"] == 0 and cnt_ok
                if r["tree"]:
                    # coverage refusal: the log must carry the bench's TREE line with the requested parameters and
                    # every requested structure moving (the bench itself does not compile if the structure is absent)
                    tl = ""
                    try:
                        tl = next((l for l in open(os.path.join(out, r["name"] + ".log")) if l.startswith("TREE ")), "")
                    except OSError:
                        pass
                    tv = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", tl)}
                    need = dict(r["tree"])
                    act = {"XMK": ["me_toggles", "me_t_checks"], "XTK": ["pctl_changes"], "XLO": ["xline_changes"]}
                    tree_ok = bool(tl) and all(tv.get(k) == v for k, v in need.items()) and all(
                        tv.get(a, 0) >= 100 for k, al in act.items() if need.get(k) for a in al)
                    o.update(tree_expected=need, tree_line=tl.strip(), tree_ok=tree_ok)
                    o["ok"] = o["ok"] and tree_ok
                if r["wq"]:
                    o["ok"] = wq_check(r, o) and o["ok"]
            elif r["expect"] == "FAIL":
                o["ok"] = o["observed"] == "FAIL" and o["rc"] == 0
                o["scratch_match"] = r["scratch"] in res if r["scratch"] else None
                if r["wq"]:
                    o["ok"] = wq_check(r, o) and o["ok"]
            elif r["expect"] == "GAP":
                # not a mutant-gate pass: the record stays ok only while the leaf miter kills this mutant
                o["mutant_killed_by_system_bench"] = o["observed"] == "FAIL"
                o["killed_by_leaf_miter"] = leaf_kills
                o["leaf_miter_run"] = leaf
                o["ok"] = leaf_kills
            else:
                o["ok"] = None
        if o["ok"] is False:
            bad.append(r["name"])
        recs.append(o)
    by = {o["name"]: o for o in recs}

    def same(x, y):
        return x in by and y in by and by[x].get("counts") is not None and by[x].get("counts") == by[y].get("counts")
    for r in runs:
        if r["same_as"]:
            o = by[r["name"]]
            o["same_counts_as"] = r["same_as"]
            o["same_counts_ok"] = same(r["name"], r["same_as"])
            if not o["same_counts_ok"]:
                o["ok"] = False
                bad.append(r["name"] + "-counts-differ-from-" + r["same_as"])
    cross = {}
    if not a.only:
        cross = {"xpr0_eq_xpr10_r21": same("base_r21", "bp_r21"), "n64_base_rq_eq_bp_rq": same("n64_base_rq", "n64_bp_rq"),
                 "n64_grp_eq_region_tile": same("n64_base", "n64_base_rq"),
                 "n64_region_leaf_eq_quarter": same("n64_base_rl", "n64_base_rq") and same("n64_bp_rl", "n64_bp_rq")}
        bad += [k for k, v in cross.items() if not v]
    if not tree_ok:
        bad.append("remote-tree-differs-from-hashed-sources")
    if dirty:
        bad.append("sources-dirty-vs-commit")
    gate = lambda e: [o["name"] for o in recs if o["expected"] == e]  # noqa
    rec = {
        "record": "qwen_tp8_vm_plane_system_bench",
        "date": datetime.date.today().isoformat(),
        "ok": not bad and not a.only,
        "not_ok_because": bad + (["partial set (--only)"] if a.only else []),
        "bench": "rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv (top tb_qfd_vm_bv_ports): bench shape ELEMS 16384 / SW 8, and the "
                 "PRODUCTION shape (runs with production_shape true: ELEMS 177808, SW 64, NRB 64, SMAX 11, 14 strides)",
        "host": host, "launcher": "ot-heavy --mem <ot_heavy_mem_gb> per run, all runs in parallel",
        "verilator": ver, "runner": "tools/qwen_tp8/vm_plane_sysbench.sh", "driver": "tools/qwen_tp8/vm_plane_sysbench_set.py",
        "source_commit": commit, "sources_clean_at_commit": not dirty, "remote_tree_matches_sha256": tree_ok,
        "sources_sha256": hashes, "runner_sha256": sha(runner),
        "summary": {"pass_expected": gate("PASS"), "fail_expected_mutants": gate("FAIL"),
                    "known_system_bench_gaps": gate("GAP"), "info_not_gated": gate("INFO"),
                    "pass_ok": sum(1 for o in recs if o["expected"] == "PASS" and o["ok"]),
                    "mutants_killed": sum(1 for o in recs if o["expected"] == "FAIL" and o["ok"]),
                    "cross_checks": cross},
        "known_gaps": ["MUT=5 (plane 5 ignores the in-range count) PASSES the system bench: no x beat past ELEMS is ever "
                       "issued. It is NOT counted as a mutant-gate pass; the kill is the leaf miter's lf_p3 (" + LEAF_REC + ")."],
        "runs": recs,
    }
    json.dump(rec, open(os.path.join(out, "record.json"), "w"), indent=1)
    for o in recs:
        print(f"{o['name']:14s} exp {o['expected']:4s} got {o['observed']:9s} ok={o['ok']} {o.get('observed_line', '')[:150]}"
              f" rss={o.get('maxrss_kb')} wall={o.get('wall_s')}")
    print("cross", cross, "OK" if rec["ok"] else f"NOT OK: {rec['not_ok_because']}")
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
