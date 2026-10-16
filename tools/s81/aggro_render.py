#!/usr/bin/env python3
"""S81-AGGRO die images: field root frames (real canonical packer, hub_shape_sweep.place) + hub for the more-dies knee
points, and the rm5 die with the C5 strip vs the VM-centred column hub.  Planning images, not GEN layouts."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import hub_shape_sweep as H  # noqa: E402
import hub_vm_centred as V  # noqa: E402

COL = dict(su="#8fb8de", vm="#f4a261", mix4="#e9c46a", capture="#e76f51", gather="#d62828", pq="#90be6d",
           wfc="#43aa8b", sseq="#577590", collective="#9d4edd", host="#c77dff", hc_s="#2a9d8f", hc_t="#264653")


def die(ax, shape, P, title, hub_rects=None, flows=None):
    pl = H.place(shape, P, False)
    for p in pl["placements"]:
        ax.add_patch(plt.Rectangle((p["x"] / 1e3, p["y"] / 1e3), p["w"] / 1e3, p["h"] / 1e3, fc="#d9d9d9", ec="#7f7f7f", lw=0.3))
    for (n, x, y, w, h) in shape["field_fixed"]:
        ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fc="#eee8d5", ec="#a0a0a0", lw=0.3))
    for r in shape["hub_rects"]:
        ax.add_patch(plt.Rectangle((r[0] / 1e3, r[1] / 1e3), r[2] / 1e3, r[3] / 1e3, fill=False, ec="#c00000", lw=1.0, ls="--"))
    if hub_rects:
        for k, (x, y, w, h) in hub_rects.items():
            ax.add_patch(plt.Rectangle((x / 1e3, y / 1e3), w / 1e3, h / 1e3, fc=COL.get(k, "#bbbbbb"), ec="k", lw=0.5))
            ax.text((x + w / 2) / 1e3, (y + h / 2) / 1e3, k, ha="center", va="center", fontsize=5.5,
                    rotation=90 if h > 2.5 * w else 0)
    if flows:
        for f in flows:
            ra, rb = hub_rects[f["a"]], hub_rects[f["b"]]
            ca = ((ra[0] + ra[2] / 2) / 1e3, (ra[1] + ra[3] / 2) / 1e3)
            cb = ((rb[0] + rb[2] / 2) / 1e3, (rb[1] + rb[3] / 2) / 1e3)
            bad = f.get("face_b") == "TURN"
            ax.annotate("", xy=cb, xytext=ca, arrowprops=dict(arrowstyle="-", lw=0.4 + f["bits"] / 6000,
                                                               color="#c00000" if bad else "#1d3557", alpha=0.7))
    ax.set_xlim(0, 33)
    ax.set_ylim(0, 26)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=7)
    ax.tick_params(labelsize=5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    S = json.loads(a.summary.read_text())
    rows = {(r["name"], r["refill"]): r for r in S["rows"]}
    fig, axs = plt.subplots(2, 3, figsize=(13, 7.6))
    for ax, k in zip(axs.flat, (2, 3, 4, 5, 6, 8)):
        r = rows[(f"strip-{k}", False)]
        st = r.get("stages")
        die(ax, H.strip(k, False), r["pairs"],
            f"-{k} cols: {r['pairs']} pairs, {st or '>119'} stages, {r.get('dies', '?')} dies, hub {r['hub_width_um'] / 1e3:.1f} mm"
            + (f"\nMTP {r['MTP_tok_s']:.0f} / AR {r['AR_tok_s']:.0f} tok/s, silicon {100 * r['silicon_vs_today']:+.1f}%" if st else ""))
    fig.suptitle("S81 more-dies knee: real canonical packer + real allocator stage counts (field frames grey, hub dashed red)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(a.out_dir / "knee_dies.png", dpi=130)
    plt.close(fig)
    ev = {L["key"]: (L, V.evaluate(L)) for L in V.layouts()}
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.9))
    for ax, key in zip(axs, ("c5", "vmc2", "vmc3")):
        L, e = ev[key]
        die(ax, H.strip(5, False), 1973, f"rm5_p1973 + {L['name']}\nhub relays {e['relays_all']}, structural turns "
            f"{len(e['structural_turns'])}, roads {e['roads_um']['W']:.0f}/{e['roads_um']['E']:.0f} um",
            hub_rects=L["rects"], flows=e["flows"])
    fig.tight_layout()
    fig.savefig(a.out_dir / "rm5_hub_c5_vs_vmc.png", dpi=140)
    plt.close(fig)
    for key in ("c5", "vmc", "vmc2", "vmc3"):
        L, e = ev[key]
        fig, ax = plt.subplots(figsize=(5.2, 9.5))
        die(ax, H.strip(5, False), 1973, L["name"], hub_rects=L["rects"], flows=e["flows"])
        ax.set_xlim(V.HUB[0] / 1e3 - 0.4, V.HUB[1] / 1e3 + 0.4)
        for f in e["flows"]:
            if f["bits"] < 4000:
                continue
            ra, rb = L["rects"][f["a"]], L["rects"][f["b"]]
            m = (((ra[0] + ra[2] / 2) + (rb[0] + rb[2] / 2)) / 2e3, ((ra[1] + ra[3] / 2) + (rb[1] + rb[3] / 2)) / 2e3)
            lab = f"{f['name']} {f['bits']}b " + ("TURN" if f.get("face_b") == "TURN" else f"cut {f['cut']} r{f['relays']}")
            ax.text(*m, lab, fontsize=5, color="#c00000" if f.get("face_b") == "TURN" else "#1d3557",
                    bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.5))
        fig.tight_layout()
        fig.savefig(a.out_dir / f"hub_{key}.png", dpi=150)
        plt.close(fig)


if __name__ == "__main__":
    main()
