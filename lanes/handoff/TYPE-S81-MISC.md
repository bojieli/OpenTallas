# TYPE-S81-MISC (successor, 2026-11-14 19:35 PST)
Scope: s81 slice_station t29 (resume a16), gunit t1, leaf t72 (plus earlier private t17/t42/t44/dsiq forms).
- t29: private resume launched 19:3x: epyc7 /srv/opentallas-scratch2/claude/type-s81-t29/r16/gen (kit slice_station__t29__cl2e5c855a, copy of wave attempt_16 incl 4_cts.odb 370 MB, copy complete 3.7 GB on intel1/epyc7/epyc8), resume.json start=grt, config.mk + OT_PREGRT_FF_HOLD=1 (orig config.mk.orig-r16), ot-run --mem 64 --hosts epyc7 queued for memory; client log intel2 ~/type-s81-t29-r16.log. Wave a16 (autopilot a4, intel2 container dpkit-slice_station__t29__cl2e5c855a-2127884, 48 GB, no pre-GRT hold, GRT extra iter 10/30 at 19:30) left running as the A/B arm. Forms fa/fb are dead (exit 143), do not restart.
- gunit t1: wave a33 INFRA-VIEW-MISSING (child dsdv_gunit_l1f_ba0/bf not signed on any host); owner TYPE-GUNIT-L1F; dict/str TypeError already fixed + keyed by KIT-OPS-5 19:05. Nothing to relaunch until a child view exists.
- leaf t72: owned by TL-LEAFT72 (private kit epyc2 alive, GRT iter 13/30). No second build.
On t29 pass: AUTO-RESIGN row + export to AGIdock and rtx-pro, RESULT line.
