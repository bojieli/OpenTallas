# KV ESTRIP v6n placed and four repair plan reviews

I viewed the layout and density for exact Intel1 G3 kit kv3_pv_v6n_1125211711. Placement passed with 158,157 cells. The center macros are staggered. The top and east edges show pin clusters. Channel use peaks at 0.167, pin-track use at 0.588, and density at 1.046. The bound ctl_cmd bit 9 spans 1,514.9 µm across three sinks. There are 57 opposite-face advisories. Keep the VPORT parity route hold.

I also viewed the exact preplacement plan renders under epyc12 /srv/opentallas-scratch2/claude/kv-pv-estrip/placed_repair_render_1126 after strict bind and PRE.

- v4. The writer START site moves into the core with the existing stage. Its repair is confined to the south edge. The preview shows remaining long nominal paths and a concentration of center-east taps.
- v5ne. The south-center landing ring gives the aisle beside the PV pair 4.32 µm more width. Keep placement to measure the actual aisle and START distribution.
- v3e. The shifted north ring opens the aisle above u_pvg3_p1. The upper transit bundles remain visibly dense. Nominal chain centers and exact per-bit stage sites are different in that area.
- hgi_v5. The signed NS west landing footprint clears the neighboring macro envelope. The preview still shows long diagonal nominal links into the north and south seams. Use the exact D and Q bank paths and the new placed map before any route.

Verdict. Place-only for the scoped repairs. No route release follows from a plan preview.
