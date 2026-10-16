#!/usr/bin/env python3
"""Index the closed archive: per element, latest closed view -> outline, pins per face, std-cell / macro area,
hard children (from 6_final.def COMPONENTS) and the minimum macro channel.  Output: JSON (one row per element)."""
import glob, json, os, re, subprocess, sys
from concurrent.futures import ProcessPoolExecutor

ARCH = "/home/ubuntu/closed_archive"
STD = re.compile(r"_ASAP7_75t_[RLS]$|^(TAPCELL|FILLER|DECAP)")


def parse_lef(path):
    """Return {macro: {w,h,cls,pins:{face:{layer:n}}}} for every MACRO in the file."""
    out = {}
    cur = None; w = h = None; cls = None; pins = {}
    pin = None; layer = None; pin_faces = None; in_obs = False
    lines = read_text(path).splitlines() if path.endswith(".zst") else open(path, errors="replace")
    if True:
        for line in lines:
            s = line.strip()
            if not s:
                continue
            t = s.split()
            k = t[0]
            if k == "MACRO" and len(t) > 1:
                cur = t[1]; w = h = None; cls = None; pins = {}; pin = None; in_obs = False
            elif cur is None:
                continue
            elif k == "CLASS" and pin is None and not in_obs and cls is None:
                cls = " ".join(t[1:]).rstrip(" ;")
            elif k == "SIZE" and len(t) >= 4:
                w = float(t[1]); h = float(t[3])
            elif k == "PIN" and len(t) > 1:
                pin = t[1]; pin_faces = {}
            elif k == "OBS":
                in_obs = True
            elif k == "LAYER" and pin is not None and not in_obs:
                layer = t[1]
            elif k == "RECT" and pin is not None and not in_obs and w:
                try:
                    vals = [float(x) for x in t[1:5] if x not in (";",)]
                    if t[1] == "MASK":
                        vals = [float(x) for x in t[3:7]]
                    x1, y1, x2, y2 = vals
                except Exception:
                    continue
                eps = 0.3
                face = None
                if x1 <= eps: face = "W"
                elif x2 >= w - eps: face = "E"
                elif y1 <= eps: face = "S"
                elif y2 >= h - eps: face = "N"
                if face and (face, layer) not in pin_faces:
                    pin_faces[(face, layer)] = ((x1 + x2) / 2, (y1 + y2) / 2)
            elif k == "END" and len(t) > 1 and pin is not None and t[1] == pin:
                if pin_faces:
                    face, layer = sorted(pin_faces)[0]
                    pins.setdefault(face, {}).setdefault(layer, 0)
                    pins[face][layer] += 1
                elif pin not in ("VDD", "VSS"):
                    pins.setdefault("INT", {}).setdefault("-", 0)
                    pins["INT"]["-"] += 1
                pin = None
            elif k == "END" and len(t) > 1 and t[1] == "OBS":
                in_obs = False
            elif k == "END" and len(t) > 1 and t[1] == cur:
                out[cur] = {"w": w, "h": h, "cls": cls, "pins": pins}
                cur = None
    return out


def read_text(path):
    if path.endswith(".zst"):
        return subprocess.run(["zstdcat", path], capture_output=True, text=True, errors="replace").stdout
    return open(path, errors="replace").read()


def def_macros(path):
    """Non-std components of a DEF: list of (master, x, y, orient) in um."""
    cmd = f"zstdcat -f '{path}' | awk '/^COMPONENTS/{{p=1;next}} /^END COMPONENTS/{{exit}} p' | grep -v -E '_ASAP7_75t_[RLS] |TAPCELL|FILLER'"
    txt = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, errors="replace").stdout
    units = 1000.0
    res = []
    for line in txt.splitlines():
        m = re.match(r"\s*-\s+(\S+)\s+(\S+).*?(PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)", line)
        if m:
            res.append((m.group(2), int(m.group(4)) / units, int(m.group(5)) / units, m.group(6), m.group(1)))
    return res


_STDSZ = None
def stdsz():
    global _STDSZ
    if _STDSZ is None:
        _STDSZ = {}
        for p in glob.glob("/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lef/asap7sc7p5t*.lef"):
            for k, v in parse_lef(p).items():
                if v["w"]:
                    _STDSZ[k] = v["w"] * v["h"]
    return _STDSZ


def def_fallback(path):
    cmd = f"zstdcat -f '{path}' | awk '/^DIEAREA/{{print}} /^COMPONENTS/{{p=1;next}} /^END COMPONENTS/{{exit}} p && /^ *- /{{print $3}}'"
    txt = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, errors="replace").stdout
    sz = stdsz(); std = 0.0; nm = 0; w = h = None
    for line in txt.splitlines():
        if line.startswith("DIEAREA"):
            n = [int(x) for x in re.findall(r"-?\d+", line)]
            w = (n[2] - n[0]) / 1000.0; h = (n[3] - n[1]) / 1000.0
            continue
        m = line.strip()
        if re.match(r"(FILLER|DECAP|FILL)", m) or m.startswith("DECAP"):
            continue
        if m in sz:
            if not m.startswith(("DECAP", "FILL")):
                std += sz[m]
        else:
            nm += 1
    out = {"std_area": round(std, 2), "n_macros": nm}
    if w:
        out.update({"w": w, "h": h, "die_area": w * h})
    return out


def latest_entry(el):
    best = None
    for j in glob.glob(f"{ARCH}/{el}/*/"):
        man = os.path.join(j, "manifest.json")
        try:
            mj = json.load(open(man))
        except Exception:
            mj = {}
        key = mj.get("closed_at") or mj.get("archived_at") or ""
        if best is None or key > best[0]:
            best = (key, j, mj)
    return best


def scan(el):
    b = latest_entry(el)
    if not b:
        return None
    key, j, mj = b
    block = mj.get("block") or el
    row = {"element": el, "block": block, "job": mj.get("job") or os.path.basename(j.rstrip("/")), "closed_at": key,
           "metrics": mj.get("metrics", {}).get("reason")}
    lefs = (sorted(glob.glob(f"{j}final/{block}.lef*")) or sorted(glob.glob(f"{j}**/{block}.lef*", recursive=True))
            or sorted(glob.glob(f"{j}**/*.lef*", recursive=True)))
    if lefs:
        allm = parse_lef(lefs[0])
        lm = allm.get(block) or (list(allm.values())[0] if len(allm) == 1 else None)
        if lm:
            row.update({"w": lm["w"], "h": lm["h"], "pins": lm["pins"], "lef": lefs[0]})
    metas = glob.glob(f"{j}run/routes/*/physical_artifacts/metadata.json") or glob.glob(f"{j}**/metadata.json", recursive=True)
    if metas:
        md = json.load(open(metas[0]))
        g = lambda k: md.get("finish__design__" + k)
        row.update({"die_area": g("die__area"), "core_area": g("core__area"), "std_area": g("instance__area__stdcell"),
                    "macro_area": g("instance__area__macros"), "n_macros": g("instance__count__macros"),
                    "std_count": g("instance__count__stdcell"),
                    "seq_area": md.get("finish__design__instance__area__class__sequential_cell"),
                    "buf_area": (md.get("finish__design__instance__area__class__timing_repair_buffer") or 0)
                    + (md.get("finish__design__instance__area__class__buffer") or 0)})
    if row.get("std_area") is None or not row.get("w"):
        defs = sorted(glob.glob(f"{j}final/6_final.def*")) or sorted(glob.glob(f"{j}**/6_final.def*", recursive=True))
        if defs:
            fb = def_fallback(defs[0])
            row["from_def"] = True
            for k, v in fb.items():
                if row.get(k) is None:
                    row[k] = v
    if (row.get("n_macros") or 0) > 0:
        defs = sorted(glob.glob(f"{j}final/6_final.def*")) or sorted(glob.glob(f"{j}**/6_final.def*", recursive=True))
        if defs:
            row["children"] = def_macros(defs[0])
            row["def"] = defs[0]
    return row


def main():
    els = sorted(os.listdir(ARCH))
    with ProcessPoolExecutor(24) as ex:
        rows = [r for r in ex.map(scan, els, chunksize=4) if r]
    # macro LEF index: archive views + repo LEFs
    lefidx = {}
    for r in rows:
        if r.get("w"):
            lefidx[r["block"]] = {"w": r["w"], "h": r["h"], "src": "archive"}
    for p in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "physical", "**", "*.lef"), recursive=True):
        try:
            for mname, mm in parse_lef(p).items():
                if mm["w"] and mname not in lefidx:
                    lefidx[mname] = {"w": mm["w"], "h": mm["h"], "src": p, "cls": mm["cls"]}
        except Exception:
            pass
    json.dump({"rows": rows, "lefidx": lefidx}, open(sys.argv[1], "w"))
    print(len(rows), "rows", len(lefidx), "lefs")


if __name__ == "__main__":
    main()
