# QC N_PAD HC0 retained-placement review
- Looked at `epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/qwen_compute/kit-wave/qwen_compute/s29q103S4Q9N46R6V1/items/sle_hc0__cl929603c0__cl4baa7c9c__pvcaa93304/geom/auto_geom.png` for attempt 1, with the route attempt on epyc10.
- North and East face pin banks have nearby relay banks. The soft data cell mass concentrates in the southwest and center, while all four sides leave visible access. The dense South clock cluster and 752 µm own-driver outlier merit CTS measurement. The retained placement scan reports zero predicted global overflow.
- Verdict: apply the corrected pre-CTS guard and run CTS only on a private copy. Review the clock and placement findings before any route continuation.

