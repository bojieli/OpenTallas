# S81 J8 station t14 attempt 1

Viewed 2026-11-23 08:59 PST. **FAIL**.

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t14/gen/slice_station__t14
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t14/geom/auto_geom.png
- The rendered east feedthrough bodies are densely packed at the bottom and middle right. Station strips fan diagonally into the lower half, leaving a large untapped upper-left region.
- OpenDB C111189 places reset relay u_bound.u_rrl_180/q at approximately (335.7, 1218.1) um. The nearest planned clock is 736.31 um away. Pin-reg p90 is 54.90 um. The longest register hop is 362.07 um.
- Add a legal local tap for the upper-left reset relay and bring the remote capture group into its own working range at equal depth. Review the new place image before route.
