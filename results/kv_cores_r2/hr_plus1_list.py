#!/usr/bin/env python3
"""KV-CORES-R2 for TOK-QK: COMPLETE per-bus list of hr face buses that take +1 cycle under the KV slice ruling
(COORD 10-27 00:37 ASK-1; class rules = tools/die_plan/kv_core_hr_price.py).  Runs face_guard (uncapped copy) on each
kit's synth netlist, checks the counts equal the kit's own face_guard.json, and writes per bus:
bus, width, direction, class, source port/cell, sink port/cell (as face_guard names them).
    hr_plus1_list.py FACE_GUARD.py OUT.json KIT [KIT ...]"""
import collections, glob, importlib.util, json, os, re, sys
fgsrc, outp, kits = sys.argv[1], sys.argv[2], sys.argv[3:]
src = open(fgsrc).read().replace('res["fails"] = {k: v[:50] for k, v in res["fails"].items()}', 'pass  # uncapped (KV-CORES-R2)')
src = src.replace("for b in sorted(want - have)[:50]:", "for b in sorted(want - have):")
mpath = "/tmp/kvr2_face_guard_uncapped.py"; open(mpath, "w").write(src)
sys.path.insert(0, os.path.dirname(fgsrc))
spec = importlib.util.spec_from_file_location("fgu", mpath); FG = importlib.util.module_from_spec(spec); spec.loader.exec_module(FG)
CYC = {"in_fanout", "unregistered", "feedthrough"}
out = dict(schema="opentallas.kv_hr_plus1_buses.v1", rule="kv_core_hr_price.py classes: input fanout (non-reset) -> landing reg +1; "
           "unregistered output -> output reg +1; feedthrough -> in-core ft reg +1; shared output -> private Q copy 0; reset fanout 0; dropped 0 (pin drop)",
           cores={})
for k in kits:
    k = k.rstrip("/"); core = os.path.basename(k).split("__")[0]
    net = glob.glob(k + "/run/results/asap7/*/base/1_2_yosys.v")
    if not net: out["cores"][core] = dict(status="NO synth netlist", kit=k); continue
    pins = json.load(open(k + "/pins.json"))
    rows_p = pins if isinstance(pins, list) else pins.get("pins", pins)
    pdir = {}
    kw = {}
    if os.path.exists(k + "/ft_stations.txt"): kw["ft"] = k + "/ft_stations.txt"
    argv = [net[0], "--top", core, "--pins", k + "/pins.json", "--out", "/tmp/kvr2_fg_" + core + ".json"] + (["--ft", kw["ft"]] if kw else [])
    if os.path.exists(k + "/straps.json"): argv += ["--straps", k + "/straps.json"]
    try:
        rc = FG.main(argv)
    except SystemExit as e:
        rc = e.code
    fg = json.load(open("/tmp/kvr2_fg_" + core + ".json"))
    kitfg = json.load(open(k + "/face_guard.json")) if os.path.exists(k + "/face_guard.json") else {}
    buses = collections.defaultdict(lambda: dict(bits=[], cls=collections.Counter(), why=[]))
    fz = json.load(open(k + "/freeze.json")) if os.path.exists(k + "/freeze.json") else {}
    skip = set(fz.get("clocks", [])) | set(fz.get("resets", [])) | {"ck", "ck_phy", "clk", "rst_n", "arst_n"}
    skip_re = "(?:" + FG.SKIP_RE + ")|^(?:" + "|".join(re.escape(x) for x in sorted(skip)) + ")$"
    kept = collections.Counter()
    for cls, rows in fg["fails"].items():
        for r in rows:
            pin, why = r.split(": ", 1)
            if cls == "missing_port" or re.match(skip_re, re.sub(r"\[\d+\]$", "", pin.strip())):
                continue
            kept[cls] += 1
            pin = pin.strip(); bus = re.sub(r"\[\d+\]$", "", pin)
            if cls == "shared":
                c = "in_fanout" if re.match(r"^\d+ loads on", why) else "out_shared"
                if c == "in_fanout" and re.search(r"rst", bus): c = "reset_ctl"
            else:
                c = cls
            m = re.search(r"\[(\d+)\]$", pin)
            buses[bus]["bits"].append(int(m.group(1)) if m else 0)
            buses[bus]["cls"][c] += 1
            buses[bus]["why"].append(f"{pin}: {why}")
    plus1 = []
    for b, v in sorted(buses.items()):
        if not any(v["cls"][c] for c in CYC): continue
        cl = sorted(c for c in v["cls"] if c in CYC)
        srcs, sinks = [], []
        for w in v["why"]:
            pin, why = w.split(": ", 1)
            if "buffered from port" in why or "wired to port" in why:
                srcs.append(re.sub(r".*port\(?s?\)? ?", "", why)); sinks.append(pin)
            elif "loads on" in why or "loads besides" in why:
                srcs.append(pin); sinks.append(why)
            else:
                srcs.append(why); sinks.append(pin)
        plus1.append(dict(bus=b, width=len(set(v["bits"])), bits_failing=len(v["bits"]), bit_range=[min(v["bits"]), max(v["bits"])],
                          classes=dict(v["cls"]), plus1_class=cl, source=sorted(set(srcs))[:64], sink=sorted(set(sinks))[:64],
                          source_n=len(set(srcs)), sink_n=len(set(sinks)), detail=v["why"]))
    out["cores"][core] = dict(kit=k, netlist=net[0], face_guard_rc=rc, fail_counts=dict(kept), raw_fail_counts=fg["fail_counts"], clock_reset_skipped=sorted(skip),
                              kit_fail_counts=kitfg.get("fail_counts"), counts_match_kit=dict(kept) == kitfg.get("fail_counts"),
                              listed_complete=sum(len(v) for v in fg["fails"].values()) == sum(fg["fail_counts"].values()),
                              plus1_buses=len(plus1), plus1_bits=sum(p["bits_failing"] for p in plus1), zero_cycle=not plus1, buses=plus1)
    print(core, dict(kept), "match_kit", out["cores"][core]["counts_match_kit"], "complete", out["cores"][core]["listed_complete"], "plus1", len(plus1), [p["bus"] for p in plus1][:10], flush=True)
json.dump(out, open(outp, "w"), indent=1)
