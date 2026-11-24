# QC-TTC-RETIME handoff (lane memory)
Row: tt_ctlm logic depth, Native32 F5 cpub39 flat bmath core (B1 source 1166f7d9630f, epyc8 QC-V4/f16_physical_1536/combined_abi_1554/source). Owner QC-TTC-RETIME (COORD 19:20), predecessor CODEX-TOKEN.
Work dir: intel1 /srv/opentallas-scratch2/claude/QC-TTC-RETIME/{wt (lane clone), in (B1 source copy), tool, a1, rs1}.
Findings 19:20:
- graph: 103397 cells, 25172 flops (18979 ck_core, 6193 ck_hr), 8 macros, 200 reset nets (reset tree = 226 cells, fixed).
- Howard max cycle ratio per gate SCC: 4 loops above 14 bmath levels/register: 39.5 (79 lv / 2 regs, SCC 21151 gates, regs u_12820,u_12854), 21.0 (u_10084), 17.0 (u_13192), 15.0 (u_9839). No pure retiming can beat 39.5/stage.
- host->host (I/O + macros) paths need no extra latency at cap 14 (only loops bind).
- kit maps each bmath gate alone (keep_hierarchy): worst CTS path = ~22 bmath cells + ~14 buffers.
Plan: (A) depth resynth of comb logic (yosys+ABC SOP balance, flops/macros kept) -> census; (B) Leiserson-Saxe retime with fixed I/O (tool rgraph.py feas) ; (C) loops still > cap -> loop register + protocol.
Update 20:15:
- rs1 (ABC sopb resynth, comb only): depth 71->22; loops 21 (u_3615 self-loop, and/or chain, SCC 33k), 17,17,16.5,15.5,14.5. ABC variants sopb3/dsd/deep plateau 20-21.
- Shannon (loop_shannon.py, ls2) does not converge: cancelled. Retime (rt_apply.py) feasible only at cap>=17 (rt17 built, prehistory 3) -> no gain over rs1.
- LEC: tool/lec.sh (lec_model.py: macros exposed, async reset -> init, x mux input = don't care) gold=in F5 vs rs1/out.sv, intel1 lec_rs.
- Probe: epyc11 /srv/opentallas-scratch/claude/QC-TTC-RETIME/{probe.sh, tmplf5 (COLL kit, F5 calrom path), cores/, r_f5_orig, r_f5_rs1_unkeep (rs1 + comb un-keep)}. Verdict 4_cts_post_hook.rpt.
- cpub39 (COLL kit core) resynth needs contracts for qfd_tt_ctlm_dv_wtn + qfd_hp13_corepub39 (cp1 failed on that).
- Next if loop misses -42: accounted loop register (protocol change).
