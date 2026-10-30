"""mixed-column mode: narrow macros are bundled side by side (10.8 gaps) into rows padded to the widest master
width (171.288), so every column is one uniform width and small macros stack under/over the 64x512 banks inside the
same column; expanded back to real per-macro sites before the packer's own check() (same kit_contract rules)."""
import place_sites as PS

CH = PS.CH


def install():
    orig = PS.place

    def place(tn, t, groups):
        wmax = max(it[2][0] for _, items, _ in groups for it in items)
        ng, bundles = [], {}
        for g, items, pref in groups:
            by = {}
            for it in items:
                by.setdefault(it[1], []).append(it)
            out = []
            for m, its in by.items():
                w, h = its[0][2]
                k = max(1, int((wmax + CH + 1e-6) // (w + CH)))
                for i in range(0, len(its), k):
                    mem = its[i:i + k]
                    key = f"BUNDLE{len(bundles)}"
                    bundles[key] = (mem, w)
                    out.append((key, m, (wmax, h)))
            ng.append((g, out, pref))
        sites, rects, pts, left = orig(tn, t, ng)
        real, rl = [], []
        for s in sites:
            mem, w = bundles[s["inst"]]
            for j, it in enumerate(mem):
                real.append(dict(inst=it[0], module=it[1], xy=(round(s["xy"][0] + j * (w + CH), 4), s["xy"][1]),
                                 wh=it[2], group=s["group"]))
        for it in left:
            rl += bundles[it[0]][0]
        return real, rects, pts, rl
    PS.place = place
