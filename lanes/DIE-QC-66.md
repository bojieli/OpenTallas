# DIE-QC-66 (QC die owner, succeeds DIE-QC-65 (died ~05:50); started 2026-11-03 06:11 PST)
Collected (no relaunch) [CHECKED ps/docker intel1/intel2/epyc2 06:1x]: SUL eco_loop l1 l4 l5 l6 (epyc2) + l2 l3 l7 (intel1); A0 NL eco (nl_eco.sh) + NL lec2 + NK ICG_IREG resume (intel1); CLK v3 chain (epyc2 oth-ubuntu-2627141); EV glue_pipe docker qc65ev-glue-sc + compose_selftest (epyc2).
TWO-STRIKES (OWNER 06:07): in-flight admitted runs finish their current step; no next iteration on any >=2-strike core/type -> RE-FORM rows in CLOSURE-LIST.
Work dir: /home/ubuntu/OpenTallas/tmp/dieqc66 (local, light only).
## log
- 06:17 CLOSURE posted (QC-023..029), TWO-STRIKES cancels done
- 06:20 helpers launched: /CLK (hold-safe estimate 08:00, collects v3), /CORES (NK > su l0-l3 > l4-l7 > NL re-form), /PLAN (RF-QC-1 plan event: shape/split/infra/channels/latency table/templates + plan-time GEOM + prototype). Brief tmp/dieqc66/helper_brief.md (localhost OpenTallas).

## CLK
- 06:46 DIE-QC-66/CLK: collected v3 (no relaunch, still KIT 229/230 DME 06:45). ESTIMATE posted: 10251 parent entries (+181 on 50 partitions), 3180 core entries, all die-clock crossings face reg + DLL lockup (worst TT +136.8 / FF +237.0 core<->parent RE-FORM), landed = count-aligned fixed latency. claude/die-qc-66-clk-1103@2ade841c39c results/qc_die66_clk_1103/.
- 06:52 OWNER 07:0x: RE-FORM withdrawn; ECO units re-submitted; helpers rescoped (CORES->ECO watch, PLAN->tool-failure class fix, CLK target)
- 07:04 v3 collected (DONE 07:02), estimate refreshed @4318ffbe729; reframed as die STA target (OWNER 07:0x), feeds QC-006/007/028.
- 08:19 CA landed check v3: 30 low-side fails (su_l0 x_ctl/x_sc + st_a x_fe__4), +1 cycle -> 0 fail; @8e705df31c1 ca_v3/.

## CORES
- 2026-11-03 08:33 PST DIE-QC-66/CORES: NL IDLE_UCK READY claude/die-qc-66-cores-1103@3613d647aa5 (routed LEC b3h EQ 40386/40386; bench MUT0 PASS, MUT1 caught). PRD class fixes READY claude/die-qc-66-prdid-1103@9870c455d77 (4_1_cts identity from 5_1_grt; MM post_grt_drv body). NL eco_loop with the fixed tools is running: intel1 die-qc-66-cores/nl_eco66.log. NK estimate claude/die-qc-66-nkpipe-1103@ff83c1664b9 (nk_pipe/ESTIMATE.txt; place WNS pending). Watcher stopped.
