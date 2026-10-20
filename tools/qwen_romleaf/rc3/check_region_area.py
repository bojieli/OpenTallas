#!/usr/bin/env python3
"""QW-A0-RC3 cheap pre-gate check (no openroad): region box area vs cell area, and the free lane beside every fence.

Inputs: the kit spec (outline + hard children) and its <kit>_regions.tcl (EXCLUSIVE boxes).  Cell areas are the MEASURED
rc2 gate numbers (QRL_REGION register area per group; DPL movable area after repair/hold insertion), same RTL (REGROOT 7):
  NL rc2 ot-epyc8 ...nl_romleaf_rc2-20261019-172047 cts.log: DPL movable 8951 um2; NK rc2 ...nk_romleaf_rc2-20261019-172148:
  20194 um2 (incl. 5714 INHOLD cells/drivers + 2343 output-port flops at the pin faces).
Model: row capacity = box area outside hard children x 0.946 (rc2 tx0: 3826.7 measured / 4044.6 box).  Each corridor
(vertical std-cell lane between macro columns) gets its fences' registers plus a share of the non-member cells
(comb + repair buffers) proportional to its register area x 1.5 margin, plus NK bus buffers (1542 n_a/n_b/n_y nets x 2
x 0.35 um2) in the west channel and the central column, and the tap buffers (508 x 2 x 0.35) in the east channel/centre.
Checks (FAIL on any):
  fence registers / fence rows        <= 0.35  (the parent_regions.tcl limit); hub fence aspect <= 2.5:1 (ck H-tree)
  fence width                         >= 10 um
  free rows in the corridor / corridor >= 0.40  and  non-member cells / free rows <= 0.60
  (registers + non-member) / corridor rows <= 0.60   (brief: <= 60 % local utilisation)
Usage: check_region_area.py KIT [KIT...]   (kit names; specs in tools/ref_tile/specs_qw_cluster3_1019)
"""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]
ROWF = 0.946
SEQ = {  # measured rc2 register area per group (um2)
    "tx": 132.853, "rsw": 150.436, "rnw": 150.057, "rse": 150.436, "rne": 150.057, "dw": 307.930, "de": 307.930,
    "hub_nl": 898.770, "hub_nk": 749.383}
FREE_SEQ = 3159 * 0.292                      # land_tx/land_rq/land_fault (FREE: placed between driver and loads)
DPL_MOVABLE = {"nl": 8951.11, "nk": 20194.22}
PIN_CELLS = {"nl": 801 * 0.292 + 2116 * 0.22, "nk": 2343 * 0.292 + 5714 * 0.22}   # output flops + INHOLD at the faces
BUS = {"nk": 1542 * 2 * 0.35, "nl": 0.0}
TAP = 508 * 2 * 0.35
SIZES = {"ot_qwen_tile_romleaf": (172.8, 110.16), "ot_qwen_tile_lsl_fp1": (99.792, 140.4), "ot_qwen_tile_node": (47.52, 432.0)}


def overlap(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def rows(box, macros):
    return max(0.0, (box[2] - box[0]) * (box[3] - box[1]) - sum(overlap(box, m) for m in macros)) * ROWF


def check(kit):
    spec = json.load(open(ROOT / f"tools/ref_tile/specs_qw_cluster3_1019/{kit}.json"))
    W, H = spec["outline"]["w"], spec["outline"]["h"]
    macros = []
    for c in spec["children"]:
        w, h = SIZES[c["view"].rsplit("/", 1)[-1]]
        x, y = c["at"]
        macros.append((x, y, x + w, y + h))
    rtcl = spec["pin_hook_before_flops"][0]
    txt = (ROOT / rtcl).read_text()
    fences = {m.group(1): tuple(map(float, m.group(2).split()))
              for m in re.finditer(r"name (\w+) type EXCLUSIVE .*? boxes \{\{([0-9. ]+)\}\}", txt)}
    k = "nk" if "_nk_" in kit else "nl"
    seq = {n: SEQ["tx"] if n.startswith("tx") else SEQ.get(n, SEQ["hub_" + k]) for n in fences}
    # corridors: x-ranges between macro columns, full core height
    ivs = sorted((m[0], m[2]) for m in macros if m[3] - m[1] < 400.0)   # ROM / LSL stacks; the NK node sits IN a corridor
    merged = []
    for x0, x1 in ivs:
        if merged and x0 <= merged[-1][1] + 0.5:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    edges = [2.16] + [e for m in merged for e in m] + [W - 2.16]
    corridors = [(a, b) for a, b in zip(edges[::2], edges[1::2]) if b - a > 5.0]
    total_fence_seq = sum(seq.values())
    nonmember = DPL_MOVABLE[k] - total_fence_seq - FREE_SEQ - PIN_CELLS[k] - BUS[k] - TAP
    fails, out = [], []
    for n, bx in fences.items():
        cap = rows(bx, macros)
        f = seq[n] / cap if cap else 9
        wid = bx[2] - bx[0]
        out.append(f"  fence {n:4s} w={wid:5.1f} rows={cap:8.0f} regs={seq[n]:6.0f} fill={f:5.3f}")
        if f > 0.35: fails.append(f"{n} register fill {f:.2f} > 0.35")
        if wid < 10.0: fails.append(f"{n} width {wid:.1f} < 10 um")
        asp = max(wid, bx[3] - bx[1]) / max(1e-9, min(wid, bx[3] - bx[1]))
        if n == "hub" and asp > 2.5:   # rc3/rc3b gates: ck H-tree over a 1:19 / 1:9.5 hub -> spread 193 / 148 ps > 80
            fails.append(f"hub fence aspect {asp:.1f}:1 > 2.5 (one ck root over a tall strip: H-tree spread)")
    for a, b in corridors:
        cbox = (a, 2.16, b, H - 2.16)
        crow = rows(cbox, macros)
        fin = {n: bx for n, bx in fences.items() if a - 0.5 <= bx[0] and bx[2] <= b + 0.5}
        frow = sum(rows(bx, macros) for bx in fin.values())
        fseq = sum(seq[n] for n in fin)
        free = crow - frow
        share = nonmember * 1.5 * fseq / total_fence_seq if total_fence_seq else 0.0
        if fin and a < 260 < b + 1: share += BUS[k]                      # west channel: n_a/n_b/n_y path
        if fin and any(n == "hub" for n in fin): share += BUS[k] + TAP     # central column
        if fin and a > 570 and b < 610: share += TAP                     # east channel: tap path
        if a < 50: share += PIN_CELLS[k] * (0.78 if k == "nk" else 0.5)   # W face strip
        if b > W - 50: share += PIN_CELLS[k] * (0.22 if k == "nk" else 0.5)
        ffree = free / crow if crow else 0
        nm = share / free if free > 0 else 9
        util = (fseq + share) / crow if crow else 9
        out.append(f"  corridor {a:6.1f}-{b:6.1f} rows={crow:8.0f} fences={','.join(fin) or '-':24s} free={ffree:4.2f} "
                   f"nonmember={share:6.0f} nm/free={nm:4.2f} util={util:4.2f}")
        if fin and ffree < 0.40: fails.append(f"corridor {a:.1f}-{b:.1f} free rows {ffree:.2f} < 0.40")
        if nm > 0.60: fails.append(f"corridor {a:.1f}-{b:.1f} non-member/free {nm:.2f} > 0.60")
        if util > 0.60: fails.append(f"corridor {a:.1f}-{b:.1f} util {util:.2f} > 0.60")
    print(f"{kit}: {'PASS' if not fails else 'FAIL'} (non-member cells {nonmember:.0f} um2 model, {len(fences)} fences)")
    print("\n".join(out))
    for f in fails:
        print("  FAIL", f)
    return not fails


if __name__ == "__main__":
    ok = [check(k) for k in sys.argv[1:]]
    sys.exit(0 if all(ok) else 1)
