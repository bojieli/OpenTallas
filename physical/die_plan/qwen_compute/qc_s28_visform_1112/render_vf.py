"""QC-S28-VISFORM type-frame renders (plan view, before | after)."""
import json, sys, colorsys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
X = json.load(open(sys.argv[1])); OUT = sys.argv[2]
FACE_C = {"in": "#1f77b4", "out": "#d62728"}
def col(i, n): return colorsys.hsv_to_rgb((i * 0.618) % 1, 0.65, 0.8)
def draw(ax, f, title, hl=None, zoom=None, flops=None):
    W, H = f["outline"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    for n, x, y, w, h in f["cores"]:
        ax.add_patch(Rectangle((x, y), w, h, fc="#bbbbbb", ec="#555555", lw=1, alpha=0.8))
        if len(f["cores"]) == 1:
            ax.annotate("", xy=(W, y + h / 2), xytext=(x + w, y + h / 2), arrowprops=dict(arrowstyle="<->", color="m", lw=1.5))
            ax.text(x + w + 2, y + h / 2 + 12, f"E gap {W - x - w:.1f} um", color="m", fontsize=8, rotation=90, va="bottom")
            ax.text(x + 5, y + h - 25, n, fontsize=7)
    for i, s in enumerate(f["slots"]):
        c = col(i, len(f["slots"]))
        for j, bs in enumerate(s["bits"]):
            if not bs: continue
            moved = hl and (s["name"], j + 1) in hl
            ax.scatter([b[0] for b in bs], [b[1] for b in bs], s=0.3 if not zoom else 2, color="r" if moved else c, alpha=0.7, lw=0)
        rg = s["regs"]
        ax.scatter([r[0] for r in rg], [r[1] for r in rg], s=10, marker="x", color=c, lw=0.8)
    for n, face, (a, z), w, d in f["buses"]:
        k = FACE_C[d]
        if face in ("E", "W"):
            x = W if face == "E" else 0
            ax.plot([x, x], [a, z], color=k, lw=4, solid_capstyle="butt")
        else:
            y = H if face == "N" else 0
            ax.plot([a, z], [y, y], color=k, lw=4, solid_capstyle="butt")
    for n, (x, y), k in f["taps"]:
        ax.scatter([x], [y], marker="*", s=60 if k == "core" else 25, color="orange" if k == "core" else "g", zorder=5)
    for n, (x, y) in (f.get("collectors") or {}).items():
        ax.scatter([x], [y], marker="o", s=6, color="purple", zorder=4)
    for n, r in (f.get("groups") or {}).items():
        ax.add_patch(Rectangle((r[0] - 6, r[1] - 6), r[2] - r[0] + 12, r[3] - r[1] + 12, fill=False, ec="red", lw=2))
        ax.text(r[0] + 8, r[1], n.replace("u_cland_collect_", "ovr "), color="red", fontsize=7)
    if flops:
        for c, x, y in flops:
            ax.add_patch(Rectangle((W - x - 1.08, y), 1.08, 0.27, fc="#d62728" if x < 2.16 else "#2ca02c", ec="none"))
    if zoom:
        ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
    else:
        ax.set_xlim(-10, W + 10); ax.set_ylim(-10, H + 10)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9)
def pair(tn, fname, hl=None, note=""):
    f = X[tn]
    fig, axs = plt.subplots(1, 2, figsize=(10, 14 * f["before"]["outline"][1] / 1831.68 + 1.2))
    draw(axs[0], f["before"], f"{tn} BEFORE (HF-1c 55d318eece08)")
    draw(axs[1], f["after"], f"{tn} AFTER (visform){note}", hl=hl)
    fig.suptitle("x = ft station regs, dots = ft bit sites (red = re-sited), blue/red bars = in/out bus windows, "
                 "orange star = core clock tap, purple = active collector nodes, red box = landing group override", fontsize=7)
    fig.tight_layout(); fig.savefig(f"{OUT}/{fname}", dpi=110); plt.close(fig)
moved = {"sle_sc_v2": {("x_fw_fe_p1", 2), ("x_fw_fe_p2", 3), ("x_stm_fe", 3), ("x_fe_stm_p1", 2), ("x_ctl_su_c_p1", 1), ("x_ctl_su_c_p1", 2), ("x_ctl_su_c_p2", 2)}}
pair("sle_sc_v2", "sc_echan_sle_sc_v2.png", hl=moved["sle_sc_v2"])
pair("slw_sc_v1__cl64543eaf__cl5e017c6f", "sc_echan_slw_sc_v1_cl5e017c6f.png")
pair("sle_ctl__cl372cea1c", "land_ovr_sle_ctl_cl372cea1c.png")
pair("sle_stm_v1__cl27746664", "stm_v1_cl27746664_frame.png", note=" (no plan change)")
# FW-EFACE: E-face pin-register band, default vs form (model of face_flops.tcl), zoom on the x_fe_i / x_fe_p1 windows
sys.path.insert(0, sys.argv[3]); import eface_model as M
for tn, z in (("sle_fw_v1__clf58b4dfb", (560, 624, 540, 700)), ("slw_st_a_v2__cl9f076a5c", (560, 624, 270, 430))):
    f = X[tn]["after"]
    pins = []
    for io in ("in", "out"):
        for n, face, (a, b), w, d in f["buses"]:
            if face == "E" and d == io: pins += [a + (i + 0.5) * (b - a) / w for i in range(w)]
    fig, axs = plt.subplots(1, 2, figsize=(10, 12))
    for ax, (ps, st, lab) in zip(axs, ((40, 1, "DEFAULT 40-site pitch, +-2 rows"), (80, 3, "FORM cpitch 80, row_stride 3"))):
        fl = M.place(pins, ps, st)
        draw(ax, f, f"{tn} E face: {lab}\nred = column 0 (face gcell), green = deeper", zoom=z, flops=fl)
    fig.tight_layout(); fig.savefig(f"{OUT}/fw_eface_{tn}.png", dpi=110); plt.close(fig)
print("rendered")
