# Clock-first route comparison on HEAD hd_spn

I inspected the placed layout and final GRT congestion images for the exact attempt-5 hd_spn retained kit. The long spine has open standard-cell channels, no hard macro wall, aligned boundary windows, and 42 distributed clock taps. A west-edge endpoint cluster is local. The retained congestion view has no sustained blocked channel across the spine and the PDN stripes are continuous across the width. This is a suitable geometry for checking whether the clock-first flow changes congestion or clock spread.

Images: epyc7, /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81_head/kit-wave/s81_head/head_rp21z20NF15f_r16/items/hd_spn/attempt_5/gen/hd_spn/run/layout_review/place/layout.png and run/layout_review/grt/congestion.png in the same kit.

Verdict: PASS for the read-only saved-CTS route comparison. The harness compares baseline and clock-first resistance-aware from the same 4_cts.odb. The retained child plan, placement, PG, and production route are untouched.
