# qwen-band-integrate spine campaign Thu Oct  8 04:38:42 PDT 2026 on ot-epyc1tb, commit 267b4cd3b
- sb_mut_frame (-GPBANDF=0 -GCYCLES=8000): FAIL qfd_spine_band oob=0 mism=947 first=233/16 burst_bad=134 prog_ahead=0 ovbad=0 idle_bad=41 img_bad=62 faults ser000000 w0 wh0 bursts=576 rows=5488 idle_checks=1 rc=1
- sb_mut_clnk (-GLNK=1 -GCLNK=2 -GDMUT=1 -GCYCLES=8000): FAIL qfd_spine_band oob=0 mism=182 first=81/32 burst_bad=6 prog_ahead=0 ovbad=0 idle_bad=1 img_bad=2 faults ser000000 w0 wh0 bursts=744 rows=5328 idle_checks=2 rc=1
- sb_mut_upper (-GUMUT=2 -GCYCLES=8000): FAIL qfd_spine_band oob=0 mism=784 first=216/8 burst_bad=299 prog_ahead=0 ovbad=0 idle_bad=143 img_bad=82 faults ser000000 w0 wh0 bursts=968 rows=6112 idle_checks=2 rc=1
- sb_mut_band (-GBMUT=1 -GCYCLES=8000): FAIL qfd_spine_band oob=0 mism=1411 first=216/8 burst_bad=564 prog_ahead=0 ovbad=0 idle_bad=393 img_bad=305 faults ser000000 w0 wh0 bursts=968 rows=6112 idle_checks=2 rc=1
- sb_link (-GLNK=1 -GCLNK=2 -GCYCLES=40000 -GSEED=2): FAIL qfd_spine_band oob=0 mism=0 first=0/0 burst_bad=0 prog_ahead=0 ovbad=0 idle_bad=1 img_bad=0 faults ser000000 w0 wh0 bursts=2712 rows=29584 idle_checks=7 rc=1
- sb_exact (-GCYCLES=40000 -GSEED=1): PASS qfd_spine_band GT=384 TCUT=3 splits=3..9 LNK=0 CLNK=0 RD=5 engine_edges=11368 ops=217 bursts=3448 rows=31896 landed=3448 idle_checks=6 rc=0
- sb_qwen (-GTCUT=7 -GSMAX=11 -GMAXT=2 -GMAXK=2 -GQB=9 -GCYCLES=20000 -GSEED=3): FAIL qfd_spine_band oob=0 mism=0 first=0/0 burst_bad=0 prog_ahead=0 ovbad=0 idle_bad=0 img_bad=0 faults ser000000 w0 wh0 bursts=1128 rows=16416 idle_checks=0 rc=1
DONE Thu Oct  8 05:14:47 PDT 2026
