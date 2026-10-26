def channels(ty, slot, minband=12.0):
    w, h = ty["outline_um"]
    boxes = []
    for c in ty.get("hard_cores", []):
        x, y = c["origin_um"]; cw, ch = c["outline_um"]
        boxes.append((x - 1.1, y - 1.1, x + cw + 1.1, y + ch + 1.1))
    fin = slot["in_face"]
    a, b = sum(slot["in_window_um"]) / 2, sum(slot["out_window_um"]) / 2
    lo, hi = min(a, b), max(a, b)
    span = h if fin in "NS" else w
    free = []
    for v10 in range(60, int(span * 10) - 60, 5):
        v = v10 / 10
        ok = True
        for x0, y0, x1, y1 in boxes:
            if fin in "NS":
                if y0 < v < y1 and x0 < hi and x1 > lo: ok = False; break
            else:
                if x0 < v < x1 and y0 < hi and y1 > lo: ok = False; break
        free.append((v, ok))
    iv, cur = [], None
    for v, ok in free:
        if ok and cur is None: cur = [v, v]
        elif ok: cur[1] = v
        elif cur is not None: iv.append(cur); cur = None
    if cur: iv.append(cur)
    cands = []
    for s, e in iv:
        if e - s >= minband:
            cands += [round((s + e) / 2, 1)]
            if e - s >= 60: cands += [round(s + 20, 1), round(e - 20, 1)]
    return cands, iv

