PATH-HBM/Q3 2026-10-25: split of ot_hfd_coll_q3_hard_v8x_s #(NLINK 3, TP 192, AR_ITER 1, ROWS 256, VM_RT 81) -DOT_COLL_ISSUER256_NATIVE32
ORFS ASAP7 synth (yosys stat, SYNTH_HIERARCHICAL 1, members kept): orfs_config.mk -> synth_stat_q3s.txt (ring_ag not kept: paramod),
orfs_config_q3s2.mk -> synth_stat_q3s2.txt (ring_ag + vm + probes kept). Total 661,550 cells.
Pieces (ASAP7 cells, q3s2): body_core 229,064 (= total - ring 147,960 - reduce 129,647 - 3x link_e 24,368 - argmax 8,934 - vmasm 36,096 - writer 36,745)
  edge_core 82,038 (3x ot_hgi_coll_link_e + ot_hgi_coll_argmax_m_tp192), vm_core 72,841 (u_vmasm + u_writer),
  ring_ag = coll_q2 ot_hfd_coll_q2_ring_ag_core (build_split_tops on the q3 netlist: byte-identical wrapper),
  reduce = coll_q2 ot_hfd_coll_q2_reduce_core (identical except the q3 netlist carries pub_meta[32:24] as one TIEHI net; RTL ties 9'h1ff = q2 core).
Pin counts (bits in/out): body_core 6196/9836, edge 4109/4030, vm 4934/4297, ring_ag 899/1345, reduce 629/547.
Registration (port_regclass, regclass_*.txt): body_core and vm_core: every cut and master port bit registered (clock/reset excepted).
  edge_core: 44 cut input bits captured through logic: arg_mode 1, arg_in_slot 4, arg_in_v 4, link{0,1,2}_epoch_begin 3 (reg+logic),
  link0_epoch_new 8 (shared by the 3 links), link{0,1,2}_held_epoch 24 (link*_ck = clocks, fine). Body launches them from flops.
Lock-step: build.sh / tb from physical/die_plan/hbm/cores/harden/{split_asm.py,gen_split_tb.py}; results lockstep_*.log.
EDGE _pr (10-25): edge members -> pin-registered twins rtl/.../p2p/ot_hgi_coll_edge_pr.sv (same ports; build_split_tops coll_q3_edge
  rtl map + gen_coll_q3_s.py q3 body copy ot_hfd_coll_q3_body_s use them):
  ot_hgi_coll_link_e_pr: epoch_begin/epoch_new/held_epoch pin flops, epoch select AFTER them (was before the epoch pin flop): 0 edges.
  ot_hgi_coll_argmax_m_tp192_pr: only the pin-captured fold (old u_chk) with out_v/out_flit/fault; mode gate after the pin flops;
    u_data (live-input duplicate) removed. ARG publish +1 edge (fault unchanged) -> COLL compiler: ARG-source capture slot +1 edge.
  port_regclass edge_core (regclass_edge_core.txt): every cut data/control input bit lands on a flop; left = link*_ck[4:1] store clocks.
  edge_pr_eq/: unit equivalence vs the pinned members (Verilator 5.050, 9 runs x 30k cycles, random stimulus + async resets):
    link_e_pr == link_e every output every edge; argmax_pr out_v/out_flit == argmax +1 edge, fault same edge (flit while out_v=0,
    or a faulted publish within 64 edges of an async reset, counted as unqualified: non-reset fold data around the reset);
    controls mut=1 (no +1) and mut=2 (held_epoch corrupted) FAIL as required.
Lock-step build (10-25): build.sh verilates only; comp_ind.sh compiles one .cpp per cc1plus (<1 GB each) and links (the vm_classes
  amalgamations needed >13 GB per unit).
