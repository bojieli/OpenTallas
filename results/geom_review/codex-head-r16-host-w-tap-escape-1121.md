# HEAD r16 west host M7 tap-access draft · 2026-11-21 16:52 PST

Viewed `epyc9:/srv/opentallas-scratch3/claude/head-crossing-1119/host_w_escape_1650/candidate/west_m7_escape_draft.png`. The original M7 pins and OBS/PG shapes come from the retained failed GRT database for AP `83022e003308`. The draft overlays additional pin metal on the same tracks to reach the seven residual GRT bins’ local y spans.

Plan draft `78ee0571446f` sets six supported `tap_pin_heights_um` entries between 1.196 and 2.652 µm. All six BTerm centers, widths and layers remain fixed. The measured minimum gap to overlapping-y OBS, PG or other M7 pin shapes is 100nm for every draft shape. The actual generator changes exactly six pin-size lines and yields identical placement and reserved-site obstruction scripts.

This is a source geometry review. The west beat-bank 405 µm locality issue remains open, along with actual gcell access, GRT and timing. There was no physical continuation from this draft.
