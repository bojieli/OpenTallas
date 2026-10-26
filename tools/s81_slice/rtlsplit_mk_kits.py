"""S81/RTLSPLIT: synth + face_guard kits for the four split cores from the closed ve / vn kit templates (tmpl/).
Only DESIGN_NAME / NICKNAME / DIE_AREA / CORE_AREA, the RTL (current worktree files) and pins.json (the plan pin table
inputs/core_pins/<mod>.json) change; every flow hook is the template's.   python3 mk_kits.py WORKTREE"""
import json, os, re, shutil, subprocess, sys
W = sys.argv[1]; L = os.path.dirname(os.path.abspath(__file__))
SIZE = {"ot_s81sl_ve_m": (172.8, 345.6), "ot_s81sl_ve_s": (164.16, 345.6),
        "ot_s81sl_vn_a": (356.4, 164.16), "ot_s81sl_vn_b": (356.4, 172.8)}
TM = {"ot_s81sl_ve_m": "ot_s81sl_ve_c", "ot_s81sl_ve_s": "ot_s81sl_ve_c", "ot_s81sl_vn_a": "vn2", "ot_s81sl_vn_b": "vn2"}
files = subprocess.run(["git", "-C", W, "ls-files", "rtl"], capture_output=True, text=True).stdout.split()
for mod, (w, h) in [(m_, s_) for m_, s_ in SIZE.items() if len(sys.argv) < 3 or m_ in sys.argv[2:]]:
    k = os.path.join(L, "kits", mod)
    shutil.rmtree(k, ignore_errors=True)
    shutil.copytree(os.path.join(L, "tmpl", TM[mod]), k)
    for b in os.listdir(os.path.join(k, "rtl")):
        if b.endswith("_bb.v"):
            continue
        c = [f for f in files if f.endswith("/" + b) and "/test/" not in f]
        pref = [f for f in c if "s81_dv" in f or f.startswith(("rtl/hdc/", "rtl/lib/", "rtl/proto/", "rtl/dsrom_sys/engram/"))]
        src = (pref or c)[0]
        shutil.copy(os.path.join(W, src), os.path.join(k, "rtl", b))
    cfg = open(os.path.join(k, "config.mk")).read()
    old = re.search(r"^export DESIGN_NAME = (\S+)", cfg, re.M).group(1)
    cfg = re.sub(r"^# GENERATED.*$", "# S81/RTLSPLIT synth + face_guard kit (mk_kits.py, template %s): %s %gx%g, plan pins inputs/core_pins/%s.json"
                 % (TM[mod], mod, w, h, mod), cfg, count=1, flags=re.M)
    cfg = re.sub(r"^export DESIGN_NICKNAME = .*$", "export DESIGN_NICKNAME = ks_" + mod, cfg, flags=re.M)
    cfg = re.sub(r"^export DESIGN_NAME = .*$", "export DESIGN_NAME = " + mod, cfg, flags=re.M)
    cfg = re.sub(r"^export DIE_AREA = .*$", "export DIE_AREA = 0 0 %g %g" % (w, h), cfg, flags=re.M)
    cfg = re.sub(r"^export CORE_AREA = .*$", "export CORE_AREA = 4.32 4.32 %g %g" % (round(w - 4.32, 4), round(h - 4.32, 4)), cfg, flags=re.M)
    open(os.path.join(k, "config.mk"), "w").write(cfg)
    P = json.load(open(os.path.join(W, "physical/die_plan/s81/inputs/core_pins/%s.json" % mod)))["pins"]
    out = []
    for p in P:
        m = re.match(r"(.+)\[(\d+)\]$", p["name"])
        bus, bit = (m.group(1), int(m.group(2))) if m else (p["name"], None)
        x, y = p["x"], p["y"]
        face = "W" if x < 1 else "E" if x > w - 1 else "S" if y < 1 else "N"
        out.append(dict(bus=bus, bit=bit, layer=p["layer"], x=x, y=y, face=face))
    json.dump(out, open(os.path.join(k, "pins.json"), "w"))
    for f in ("face_guard.json", "face_guard_odb.json", "image.txt", "run_synth.log", "synth_odb_v.log", "sdc_lint.log", "pins_snapped.json"):
        if os.path.exists(os.path.join(k, f)):
            os.remove(os.path.join(k, f))
    sl = json.load(open(os.path.join(k, "sdc_lint.json")))
    dirs = {}
    for o in out:
        if o["bus"] in ("clk",):
            continue
        dirs[o["bus"]] = None
    lefd = dict(re.findall(r"PIN (\S+)\s+DIRECTION (\w+)", open(os.path.join(W, "physical/die_plan/s81/cores/leaf/lef/%s.lef" % mod)).read()))
    bus_dir = {}
    for n, d in lefd.items():
        bus_dir[n.split("[")[0]] = d
    sl["inputs"] = sorted(b for b, d in bus_dir.items() if d == "INPUT" and b != "clk")
    sl["outputs"] = sorted(b for b, d in bus_dir.items() if d == "OUTPUT")
    json.dump(sl, open(os.path.join(k, "sdc_lint.json"), "w"), indent=1)
    print(mod, old, "->", mod, "pins", len(out), {f: sum(1 for o in out if o["face"] == f) for f in "NSEW"})
