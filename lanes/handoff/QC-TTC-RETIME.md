# QC-TTC-RETIME handoff (lane memory)
Row: tt_ctlm logic depth, Native32 F5 cpub39 flat bmath core (B1 source 1166f7d9630f, epyc8 QC-V4/f16_physical_1536/combined_abi_1554/source). Owner QC-TTC-RETIME (COORD 19:20), predecessor CODEX-TOKEN.
Work dir: intel1 /srv/opentallas-scratch2/claude/QC-TTC-RETIME/{wt (lane clone), in (B1 source copy), tool, a1, rs1}.
Findings 19:20:
- graph: 103397 cells, 25172 flops (18979 ck_core, 6193 ck_hr), 8 macros, 200 reset nets (reset tree = 226 cells, fixed).
- Howard max cycle ratio per gate SCC: 4 loops above 14 bmath levels/register: 39.5 (79 lv / 2 regs, SCC 21151 gates, regs u_12820,u_12854), 21.0 (u_10084), 17.0 (u_13192), 15.0 (u_9839). No pure retiming can beat 39.5/stage.
- host->host (I/O + macros) paths need no extra latency at cap 14 (only loops bind).
- kit maps each bmath gate alone (keep_hierarchy): worst CTS path = ~22 bmath cells + ~14 buffers.
Plan: (A) depth resynth of comb logic (yosys+ABC SOP balance, flops/macros kept) -> census; (B) Leiserson-Saxe retime with fixed I/O (tool rgraph.py feas) ; (C) loops still > cap -> loop register + protocol.
