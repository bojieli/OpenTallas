# qwen-band-integrate spine campaign Thu Oct  8 03:59:52 PDT 2026 on ot-epyc1tb, commit 7817f9e7b
- sb_mut_frame (-GPBANDF=0 -GCYCLES=8000): FAIL qfd_spine_band mism=971 first=233/16 burst_bad=158 prog_ahead=0 ovbad=0 idle_bad=391 img_bad=331 faults ser000000 w0 wh0 bursts=576 rows=5488 idle_checks=1 rc=1
- sb_mut_band (-GBMUT=1 -GCYCLES=8000): FAIL qfd_spine_band mism=1448 first=216/8 burst_bad=608 prog_ahead=0 ovbad=0 idle_bad=1425 img_bad=806 faults ser000000 w0 wh0 bursts=968 rows=6112 idle_checks=2 rc=1
- sb_mut_upper (-GUMUT=2 -GCYCLES=8000): FAIL qfd_spine_band mism=784 first=216/8 burst_bad=304 prog_ahead=0 ovbad=0 idle_bad=170 img_bad=97 faults ser000000 w0 wh0 bursts=968 rows=6112 idle_checks=2 rc=1
- sb_mut_clnk (-GLNK=1 -GCLNK=2 -GDMUT=1 -GCYCLES=8000): FAIL qfd_spine_band mism=172 first=81/32 burst_bad=6 prog_ahead=0 ovbad=0 idle_bad=14 img_bad=30 faults ser000000 w0 wh0 bursts=744 rows=5328 idle_checks=2 rc=1
- sb_link (-GLNK=1 -GCLNK=2 -GCYCLES=40000 -GSEED=2): FAIL qfd_spine_band mism=310 first=448/4 burst_bad=0 prog_ahead=0 ovbad=0 idle_bad=1 img_bad=0 faults ser000000 w0 wh0 bursts=2728 rows=28320 idle_checks=6 rc=1
- sb_exact (-GCYCLES=40000 -GSEED=1): FAIL qfd_spine_band mism=0 first=0/0 burst_bad=0 prog_ahead=0 ovbad=0 idle_bad=4 img_bad=1 faults ser000000 w0 wh0 bursts=3376 rows=29040 idle_checks=7 rc=1
- sb_qwen (-GTCUT=7 -GSMAX=11 -GMAXT=2 -GMAXK=2 -GCYCLES=12000 -GSEED=3): FAIL qfd_spine_band mism=0 first=0/0 burst_bad=0 prog_ahead=0 ovbad=0 idle_bad=0 img_bad=0 faults ser000000 w0 wh0 bursts=672 rows=9552 idle_checks=0 rc=1
DONE Thu Oct  8 04:38:06 PDT 2026
