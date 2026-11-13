#!/usr/bin/env python3
"""QC-S28-B B2 repair of the STREET-RULE-1 legalize output (da9ad4d161): the band remap that makes every off-core
coordinate follow the moved cores also moves the type's BOUNDARY geometry (landing face pins, edge-clock entry taps,
collector root / up pins, local resets and collector sources at a face pin), e.g. sle_sc_v3 W-face pins x 2.144 ->
2.01 and N-face pins up to -21.6 um, although the bus windows (the die contract) did not change.  Boundary geometry
is the parent seam: it must not move in a positions-only type event.

  pin_boundary.py BASE.json CAND.json OUT.json REPORT.json [--types T1,T2]

For every type that differs: every point / rect that lies within EDGE_UM of the BASE outline and moved is restored
to its BASE value (when the outline is unchanged on that side); clock.tap_um / reset.tap_um (the die clock / reset
entry of the type) are restored unless the base site now lies under a moved hard core (then kept and reported)."""
import copy, json, sys
EDGE_UM = 4.5


def num(v, n):
    return isinstance(v, list) and len(v) == n and all(isinstance(x, (int, float)) for x in v)


def on_edge(v, W, H, m=EDGE_UM):
    if num(v, 2):
        x, y = v
        return x <= m or y <= m or x >= W - m or y >= H - m
    if num(v, 4):
        x0, y0, x1, y1 = v
        return x0 <= m or y0 <= m or x1 >= W - m or y1 >= H - m
    return False


def under_core(t, xy):
    for c in t.get("hard_cores") or []:
        x0, y0 = c["origin_um"]
        w, h = c["outline_um"]
        if c.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        if x0 < xy[0] < x0 + w and y0 < xy[1] < y0 + h:
            return c["inst"]
    return None


def restore(a, b, W, H, path, log):
    """walk a (base) / b (cand) in parallel; on-edge numeric leaves of a that differ in b are put back"""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) & set(b):
            if isinstance(a[k], list) and on_edge(a[k], W, H) and a[k] != b[k] and (num(a[k], 2) or num(a[k], 4)):
                log.append(("/".join(map(str, path + (k,))), a[k], b[k]))
                b[k] = copy.deepcopy(a[k])
            else:
                restore(a[k], b[k], W, H, path + (k,), log)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i in range(len(a)):
            if num(a[i], 2) or num(a[i], 4):
                if on_edge(a[i], W, H) and a[i] != b[i]:
                    log.append(("/".join(map(str, path + (i,))), a[i], b[i]))
                    b[i] = copy.deepcopy(a[i])
            else:
                restore(a[i], b[i], W, H, path + (i,), log)


def main():
    base, cand, out, rep = sys.argv[1:5]
    only = None
    if "--types" in sys.argv:
        only = set(sys.argv[sys.argv.index("--types") + 1].split(","))
    A, B = json.load(open(base)), json.load(open(cand))
    R = {}
    for tn, t1 in B["partition_types"].items():
        t0 = A["partition_types"][tn]
        if t0 == t1 or (only and tn not in only):
            continue
        W, H = t0["outline_um"]
        W1, H1 = t1["outline_um"]
        log = []
        # a grown side moves its own boundary: restore only against the unchanged sides
        if (W, H) == (W1, H1):
            restore(t0, t1, W, H, (), log)
        else:
            restore_partial(t0, t1, W, H, W1, H1, log)
        lc0 = (t0.get("clock") or {}).get("landing_contract") or {}
        lc1 = (t1.get("clock") or {}).get("landing_contract") or {}
        ct0, ct1 = lc0.get("collector_tree") or {}, lc1.get("collector_tree") or {}
        if "root" in ct0 and ct0.get("root") != ct1.get("root"):
            # the collector root is the type's status up-link at the parent seam (collector_reattach refuses a move)
            log.append(("clock/landing_contract/collector_tree/root", ct0["root"], ct1.get("root")))
            ct1["root"] = copy.deepcopy(ct0["root"])
        kept = []
        for sec in ("clock", "reset"):
            a0, a1 = (t0.get(sec) or {}).get("tap_um"), (t1.get(sec) or {}).get("tap_um")
            if a0 is not None and a0 != a1:
                c = under_core(t1, a0)
                if c:
                    kept.append(dict(path=f"{sec}/tap_um", base=a0, cand=a1, under=c))
                else:
                    t1[sec]["tap_um"] = copy.deepcopy(a0)
                    log.append((f"{sec}/tap_um", a0, a1))
        R[tn] = dict(restored=len(log), kept=kept, classes=sorted({p.split("/")[0] + "/" + "/".join(
            x for x in p.split("/")[1:3] if not x.isdigit()) for p, _, _ in log}),
            max_shift_um=round(max([max(abs(u - v) for u, v in zip(x, y)) for _, x, y in log] or [0]), 3))
        print(tn, R[tn]["restored"], "restored, max shift", R[tn]["max_shift_um"], "kept", kept)
    open(out, "w").write(json.dumps(B, indent=1) + "\n")
    json.dump(R, open(rep, "w"), indent=1)


def restore_partial(t0, t1, W, H, W1, H1, log):
    """outline grew: the W / S faces stay; the E / N faces move by the growth.  Restore W/S-edge items to base,
    E/N-edge items to base + growth (the die-side window moves with the grown face)."""
    dW, dH = W1 - W, H1 - H

    def fix(a, b, path):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in set(a) & set(b):
                if (num(a[k], 2) or num(a[k], 4)) and on_edge(a[k], W, H):
                    nv = shifted(a[k])
                    if nv != b[k]:
                        log.append(("/".join(map(str, path + (k,))), nv, b[k]))
                        b[k] = nv
                else:
                    fix(a[k], b[k], path + (k,))
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for i in range(len(a)):
                if (num(a[i], 2) or num(a[i], 4)) and on_edge(a[i], W, H):
                    nv = shifted(a[i])
                    if nv != b[i]:
                        log.append(("/".join(map(str, path + (i,))), nv, b[i]))
                        b[i] = nv
                else:
                    fix(a[i], b[i], path + (i,))

    def shifted(v):
        v = list(v)
        xs, ys = (0, 2) if len(v) == 4 else (0,), (1, 3) if len(v) == 4 else (1,)
        if dW and max(v[i] for i in xs) >= W - EDGE_UM:
            for i in xs:
                v[i] = round(v[i] + dW, 4)
        if dH and max(v[i] for i in ys) >= H - EDGE_UM:
            for i in ys:
                v[i] = round(v[i] + dH, 4)
        return v
    fix(t0, t1, ())


if __name__ == "__main__":
    main()
