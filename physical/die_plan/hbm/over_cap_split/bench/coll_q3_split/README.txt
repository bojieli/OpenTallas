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
