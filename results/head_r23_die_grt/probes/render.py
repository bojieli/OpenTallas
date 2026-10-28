"""HEAD-R23 render: M8 PG stripes vs clock jogs + drawn VSS shields around sample endpoints."""
import json, sys
sys.path.insert(0, sys.argv[1])
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema as S, die_clock_128 as C, die_infra as DI, die_clock_mesh as D
O, plan, png = sys.argv[2], sys.argv[3], sys.argv[4]
M = json.load(open(O + "/mesh.json"))
P = S.Plan(S.load(plan)); pgr = DI.pg_rects(P, C.pg_grid(P, None))
nd = D.NDR[M["meta"]["ndr"]]
shapes = C.clock_shapes(D.mesh_segments(M) + C.tree_segs(M["fixed_wires"]), nd, "VSS")
taps = M["taps"]
nat = next(t for t in taps if t["mesh_boundary"]["endpoint_kind"] == "native_core_clock" and t["mesh_boundary"]["jog_um"] > 3)
grd = next(t for t in taps if t["mesh_boundary"]["endpoint_kind"] == "published_grid_clock" and t["mesh_boundary"]["jog_um"] > 3
           and abs(t["mesh_boundary"]["xy"][1] % 2.16) < 0.01)
fig, axs = plt.subplots(2, 1, figsize=(14, 9))
for ax, t, title in ((axs[0], nat, "native core clock"), (axs[1], grd, "published grid clock (pin on a PG stripe centre)")):
    mb = t["mesh_boundary"]; px, py = mb["xy"]; ax_ = mb["anchor"]
    x0, x1 = min(px, ax_[1]) - 6, max(px, ax_[1]) + 6; y0, y1 = py - 4, py + 4
    for net, L, a, b, c, d in pgr:
        if L == "M8" and c > x0 and a < x1 and d > y0 and b < y1:
            ax.add_patch(Rectangle((max(a, x0), b), min(c, x1) - max(a, x0), d - b, color="red" if net == "VDD" else "blue", alpha=0.35))
    for L, net, kind, plo, phi, alo, ahi in shapes:
        if L != "M8" or ahi < x0 or alo > x1 or phi < y0 or plo > y1: continue
        ax.add_patch(Rectangle((max(alo, x0), plo), min(ahi, x1) - max(alo, x0), phi - plo,
                               color="green" if kind == "tree" else "grey", alpha=0.8))
    for net, L, a, b, c, d in pgr:
        if L == "M9" and c > x0 and a < x1:
            ax.axvspan(max(a, x0), min(c, x1), color="orange", alpha=0.08)
    ax.plot([px], [py], "kx", ms=10); ax.plot([mb["port_node"][1]], [mb["port_node"][2]], "m+", ms=14)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_title(f"{title} {t['port']} {mb['part']}:{mb['endpoint_port']} pin y={py:.3f} track y={mb['port_node'][2]:.3f} jog {mb['jog_um']:.1f} um stub {mb.get('stub_um',0):.2f}; red VDD / blue VSS M8 PG, green clock M8, grey VSS shields, orange M9 PG (other layer)", fontsize=8)
plt.tight_layout(); plt.savefig(png, dpi=110)
print(png)
