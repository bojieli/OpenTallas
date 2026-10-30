# HBM D34e3 unsigned lane/collar pre-place

Independent Codex GEOM2026-10-30: viewed plan.png (committed parent source7fb644db9), **PASS-COND for PREPLACE diagnostic only; no CTS/route**. Independently confirmed actual candidate intel1 codex-hbm-1030/d34e3/die_plan.json SHA721ba17b8ebf has four lane_exp0_id entries(two logical plus physical variants)414.72x207.36 at unchanged origins and collar88.992square.

Lane2x3 six94.824x41.064 SRAMs at x64.8/172.8/280.8,y53.724/118.812 give13.176horizontal/24.024verticalstreets, greaterthan10.8. Largeouterbands and face-wide N/S/W/E pin sets avoid new walls/partialfaces. Corrected clock/reset cluster207.384,103.68 lies in clear central24.024um street; exact corrected sidecar/fourdie taps are parent source contract (earlier220.32D34e2 rejected). N275/S374 names retained, no invented/tied input. Collarsole logical c_done atW selected over staleN alias, Eclock slot is only89um across.

Old lane580um/370capture select fanout failure is still open: narroweroutline and centreclock alone cannot close it. Coreowner must apply proposed centreselect affinity then examine actual full r2r/clock/pins/PDN/LEC/GRT before CTS; preserve failed variants. This review establishes initial packing and source-pin topology, not placement/timing/sign-off.
