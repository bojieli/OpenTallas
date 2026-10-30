Clock-family scope replay on the existing reviewed hd_mesh_e global-route ODB. No placement, routing, RTL or clock-budget change. Original kit mounted read-only. Source 146d4a4b7.

Actual STA ownership gives 248 local clk-family boundary registers (prior mixed-clock census 542). TT mean 452.60 ps vs450: insertion PASS. FF342.67 ps vs380: FAIL retained, true FF contract mismatch remains. The previous ad-hoc209 subset omitted39 actual clk-owned registers. Source-forwarded ring writers retain their own clock/landing-window timing obligations.

Artifacts: intel2:/srv/opentallas-scratch2/claude/codex-flow-scope-1850/mesh_e, pg_tt/ff.json and pinregs_TT/FF.tsv. Job ot-run --hosts localhost on intel2 hub unit oth-ubuntu-2742717-1793325138. Initial --hosts intel2 NOT RUN because hub SSH lacks self alias; corrected localhost admitted actual run.

15 focused tests PASS, main unfiltered-census negative control CAUGHT. No SIGNED/freeze claim. Source correction merits integration independently of retained genuine FF failure.
