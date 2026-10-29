"""DIE-S81-25: plan pictures of the two BF variants (outline, ROM sites, ROM pin bands, clock entry, E pin band)."""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
W, H, RW, RH = 450.168, 198.72, 125.304, 62.952
V = {"t16a: TAG_GROUPS 16, ROM W stack (V1 sites), channel 10.872 um": [(42.12, 30.960, "R180"), (42.12, 104.784, "MY")],
     "t16b: TAG_GROUPS 16, ROMs on S/N faces, centre band 60.7 um": [(42.12, 6.048, "R180"), (42.12, 129.744, "MY")]}
fig, axs = plt.subplots(2, 1, figsize=(11, 10))
for ax, (t, sites) in zip(axs, V.items()):
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
    ax.add_patch(Rectangle((4.32, 4.32), W - 8.64, H - 8.64, fill=False, lw=.6, ls="--"))
    for x, y, o in sites:
        ax.add_patch(Rectangle((x, y), RW, RH, color="gray", alpha=.5))
        py = y + RH - 0.78 if o == "R180" else y + 0.78      # R0 pin band W edge y 0.78 -> E edge after R180 / MY
        ax.plot([x + RW], [py], "r>", ms=9)
        ax.text(x + 4, y + RH / 2, f"ROM {o} y={y}", fontsize=8)
    ys = sorted(s[1] for s in sites)
    ax.annotate(f"gap {ys[1] - ys[0] - RH:.3f} um", (x + RW + 3, ys[0] + RH + 1), fontsize=8, color="b")
    ax.plot(273.24, 95.58, "*", color="gold", ms=14, mec="k")
    ax.plot([W, W], [62, 137], color="g", lw=4)
    ax.set_title(t, fontsize=10); ax.set_aspect("equal"); ax.set_xlim(-8, 460); ax.set_ylim(-8, 207); ax.grid(alpha=.2)
fig.suptitle("BF col plan variants (450.168x198.72 = plan_s13r2 slot). red > ROM clk/addr pin band, star clock entry, green E pins")
fig.tight_layout(); fig.savefig("bf_variants_plan.png", dpi=110)
