"""PIN-STACK: same-net routed metal (M4-M7) of each signal BTerm net within WIN nm of its pin, from the core's signed DEF.
-> json {pin_name: {"pin": [[L,x0,y0,x1,y1]...], "stack": [[L,x0,y0,x1,y1]...]}} (core coordinates, nm)"""
import json, re, sys
HW = {"M1": 9, "M2": 9, "M3": 9, "M4": 12, "M5": 12, "M6": 16, "M7": 16, "M8": 40, "M9": 40}
LAY = {"M4", "M5", "M6", "M7"}
WIN = int(sys.argv[3]) if len(sys.argv) > 3 else 300
text = open(sys.argv[1]).read()
pins = {}
ps = text[text.index("\nPINS "):text.index("\nEND PINS")]
for blk in ps.split("\n    - ")[1:]:
    m = re.match(r"(\S+) \+ NET (\S+)", blk)
    if not m or "+ USE POWER" in blk or "+ USE GROUND" in blk:
        continue
    name, net = m.group(1), m.group(2)
    lm = re.search(r"\+ LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", blk)
    pm = re.search(r"\+ PLACED \( (-?\d+) (-?\d+) \) (\S+)", blk) or re.search(r"\+ FIXED \( (-?\d+) (-?\d+) \) (\S+)", blk)
    if not lm or not pm:
        continue
    L, a, b, c, d = lm.group(1), *map(int, lm.groups()[1:])
    X, Y, o = int(pm.group(1)), int(pm.group(2)), pm.group(3)
    if o not in ("N", "FN", "S", "FS"):
        a, b, c, d = b, a, d, c   # E/W: swap axes (rare for block pins)
    if o in ("S", "FN"):
        a, c = -c, -a
    if o in ("S", "FS"):
        b, d = -d, -b
    pins.setdefault(net, []).append((name.replace("\\", ""), [L, X + a, Y + b, X + c, Y + d]))
ns = text[text.index("\nNETS "):text.index("\nEND NETS")]
out = {}
for blk in ns.split("\n    - ")[1:]:
    net = blk.split()[0]
    if net not in pins:
        continue
    rects = []
    for m in re.finditer(r"(?:ROUTED|NEW) (M\d) (?:\d+ )?(?:\+ \S+ )*\( (-?\d+) (-?\d+)(?: -?\d+)? \)((?: \( (?:-?\d+|\*) (?:-?\d+|\*)(?: -?\d+)? \))?)(?: RECT \( (-?\d+) (-?\d+) (-?\d+) (-?\d+) \))?", blk):
        L = m.group(1)
        if L not in LAY:
            continue
        x0, y0 = int(m.group(2)), int(m.group(3))
        if m.group(5) is not None:   # RECT patch
            rects.append([L, x0 + int(m.group(5)), y0 + int(m.group(6)), x0 + int(m.group(7)), y0 + int(m.group(8))])
            continue
        p2 = re.match(r" \( (-?\d+|\*) (-?\d+|\*)", m.group(4) or "")
        if not p2:
            continue
        x1 = x0 if p2.group(1) == "*" else int(p2.group(1))
        y1 = y0 if p2.group(2) == "*" else int(p2.group(2))
        h = HW[L]
        rects.append([L, min(x0, x1) - h, min(y0, y1) - h, max(x0, x1) + h, max(y0, y1) + h])
    for name, pb in pins[net]:
        w = (pb[1] - WIN, pb[2] - WIN, pb[3] + WIN, pb[4] + WIN)
        st = [r for r in rects if r[1] < w[2] and r[3] > w[0] and r[2] < w[3] and r[4] > w[1]]
        out[name] = dict(pin=[pb], stack=st)
json.dump(out, open(sys.argv[2], "w"))
print("OT_PINSTACK pins", len(out), "stack_rects", sum(len(v["stack"]) for v in out.values()))
