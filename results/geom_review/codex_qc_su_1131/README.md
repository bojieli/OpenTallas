# Actual QC SU l3/l4/l7 independent locality review

LOOKED all3actual placed images and parsed JSON. Source intel2:/srv/opentallas-scratch2/claude/autopilot/auto_geom/<id>/auto_geom.{png,json,tsv}: l3=423127193bd8,l4=85a68fc62757,l7=c8bf2e9c4709. Original AUTOFAILs preserved. No new physical job launched.

l3/l7: PASS-COND for consumer/pin locality ONLY, using fixed parent interfaces.981S-face pins occupy the planned36%-face band; measured peak7.0/um M5 remains WARN. Pinregp909.09/max45.57/57.94, flop-r2r366.77/336.20 with0over405, fill.2694/.2693, channelmax.513/.410,col_v.308/.329,0unregistered pins/blockedchannels/relaycollapse. Two central macros have clear surrounding streets/halos; logic distributes around them, no macro wall. Existing reportedGRT0 is retained, not replaced by a speculative port spread.

l4 stays HELD on isolated rst_n→firstreg175.72um, nextworst data pin9.8um. Data pin locality/r2r299.11 and channels.315/.327 are clean; the owner cseq_cb retains reset-source/timing/geometry diagnosis. No blanket waiver or route/GRT release for this reset failure.

Zero-clock-cell preCTS reach449.38/411.07/449.43um is information at this stage. Actual clock, TT/FF, source/reset correctness and native timing gates remain unchanged. This is a scoped consumer-locality judgment, not a complete source/route/sign-off qualification.
