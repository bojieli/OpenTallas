#!/usr/bin/env python3
"""KIT-OPS-6 11-14 (COORD r33 (2)): sync the reaper protect lists from the hub to every host.  qct13/views vanished because only the hub
listed the die-config view dirs.  Writes protect.d/hub-kit-wave-live.txt (every die's src/plan dir, item_inputs paths and every prov_view_sources
dir, from the hub's kit_wave.json) + copies the hub's protect.d/kit_wave.txt and kit_wave.txt.prov-views (as *.txt: wt-reaper reads protect.d/*.txt) to
each host by copy+mv.  Hub timer: every 15 min."""
import json, os, re, subprocess, sys
HOME = os.path.expanduser("~")
HOSTS = ["intel1", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10"]
cfg = json.load(open(HOME + "/coord/autopilot/kit_wave.json"))["dies"]
paths = set()
def add(p):
    if isinstance(p, str) and p.startswith("/srv/"):
        paths.add(p.rstrip("/"))
for die, d in cfg.items():
    add(d.get("src")); add(os.path.dirname(str(d.get("plan") or "")))
    for it in (d.get("item_inputs") or {}).values():
        if isinstance(it, dict):
            add(it.get("src")); add(os.path.dirname(str(it.get("plan") or "")))
    for lst in (d.get("prov_view_sources") or {}).values():
        for c in lst if isinstance(lst, list) else [lst]:
            if isinstance(c, dict):
                add(c.get("dir"))
                if c.get("base"): add(c["base"])
paths.add("/srv/opentallas-scratch2/claude/kit-ops-6")
# KIT-OPS-6 11-15 (COORD loop-gap): cleanup pruned the bind worktrees live kit_rtl records point at (FAIL FLOW "pruned bind worktree").  Protect, for every die
# AND every item_inputs override (= pending plan binds): kit_rtl bind_out / asbuilt / script (+ dirs) and the source tree of every HDL file the bind names.
sys.path.insert(0, HOME + "/OpenTallas/tools/autopilot")
def lane_root(f):
    m = re.match(r"^(/srv/opentallas-scratch[0-9]*/claude/.*?)/(?:rtl|physical|tools|src)(?:/|$)", f)
    if m: return m.group(1)
    m = re.match(r"^(/srv/opentallas-scratch[0-9]*/claude/[^/]+(?:/[^/]+){0,2})", f)
    return m.group(1) if m else None
def kr_paths(kr):
    for k in ("bind_out", "asbuilt", "script"):
        v = (kr or {}).get(k)
        if isinstance(v, str) and v.startswith("/srv/"):
            add(v); add(os.path.dirname(v))
    return (kr or {}).get("bind_out")
bind_outs = []
for die, d in cfg.items():
    for kr in [d.get("kit_rtl")] + [(i or {}).get("kit_rtl") for i in (d.get("item_inputs") or {}).values() if isinstance(i, dict)]:
        if isinstance(kr, dict):
            bo = kr_paths(kr)
            if isinstance(bo, str) and bo.startswith("/srv/"): bind_outs.append((die, bo, d.get("gen_hosts") or []))
try:
    import kit_wave as KW
    for die, bo, hosts in bind_outs:
        try:
            for f in KW.bind_named_sources(bo, hosts):
                r = lane_root(f)
                if r: paths.add(r)
        except Exception as e:
            print(f"PROTECT-SYNC bind sources {die}: {type(e).__name__}", flush=True)
except Exception as e:
    print("PROTECT-SYNC kit_wave import failed:", e, flush=True)

body = "".join(p + "\n" for p in sorted(paths))
pd = HOME + "/.local/state/wt-reaper/protect.d"
files = {"hub-kit-wave-live.txt": body}
for src, dst in (("kit_wave.txt", "hub-kit_wave.txt"), ("kit_wave.txt.prov-views", "hub-kit_wave-prov-views.txt")):
    try: files[dst] = open(f"{pd}/{src}").read()
    except OSError: pass
for h in HOSTS:
    ok = []
    for name, txt in files.items():
        r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", h,
                            f"mkdir -p ~/.local/state/wt-reaper/protect.d && cat > ~/.local/state/wt-reaper/protect.d/{name}.new && mv -f ~/.local/state/wt-reaper/protect.d/{name}.new ~/.local/state/wt-reaper/protect.d/{name}"],
                           input=txt, capture_output=True, text=True, timeout=120)
        ok.append(r.returncode == 0)
    print(f"PROTECT-SYNC {h}: {sum(ok)}/{len(ok)} files, {len(paths)} live paths", flush=True)
# the hub itself: its own protect.d gets the live list too (the hub runs wt-reaper and ot-autoclean)
for name, txt in files.items():
    if name.startswith("hub-kit_wave"):
        continue
    os.makedirs(pd, exist_ok=True)
    open(f"{pd}/{name}.new", "w").write(txt); os.replace(f"{pd}/{name}.new", f"{pd}/{name}")
print("PROTECT-SYNC intel2 (hub): local", flush=True)
