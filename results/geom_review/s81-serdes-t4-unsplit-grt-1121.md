# Private unsplit t4 GRT checkpoint

The older unsplit t4 run `serdes__t4_1121074458` produced `5_1_grt.odb` on epyc10. I viewed [the actual GRT congestion](s81-serdes-t4-unsplit-grt-congestion.png) and density views. FastRoute reports zero overflow. The renderer marks 38 grid cells outside macros at 100% and 9,170 above 90% out of 8.89 million. Congestion concentrates around the central SRAMs and on the narrow west delivery strip. The local density peak rose from 94.6% at placement to 97.6% at GRT.

The same runtime log shows per-chunk single-mode hold repair temporarily meeting its scoped test. The broader post-GRT repair reports -150.02 ps hold after it stalled, and the hook reports that the final TT/FF two-mode repair did not run. The non-tap census is 444,448 versus a 400,000 target. This proof reached GRT. It does not qualify the structural row for release or carry-forward. The split and front3 paths have separate reviews and are held.

Exact runner artifacts remain in `epyc10:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/dc92652f0d5/private/FAM-S81-SERDES-R4/serdes__t4_1121074458/gen/serdes__t4`.
