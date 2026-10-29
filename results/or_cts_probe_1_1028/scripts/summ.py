import json, sys, re, os
B = sys.argv[1]
for case in ("s81", "qc"):
    meta = json.load(open(f"{B}/{case}/meta.json")); ins = meta.get("insertion_rel", {})
    for v in sorted(os.listdir(f"{B}/{case}")):
        d = f"{B}/{case}/{v}"
        if not os.path.isdir(d) or not os.path.exists(f"{d}/arr_FF.txt"): continue
        row = dict(case=case, v=v)
        for C in ("TT", "FF"):
            S = {}; nb = 0
            for l in open(f"{d}/arr_{C}.txt"):
                s = l.split()
                if s[0] == "S": S[s[1]] = (float(s[2]), float(s[4]))
                if s[0] == "B": nb += 1
            glue = {k: a for k, (a, _) in S.items() if k.endswith("/CLK")}
            core = {k: a + ins[C] for k, (a, _) in S.items() if "/clk" in k}
            allv = list(glue.values()) + list(core.values())
            row[C] = dict(glue_spread=round(max(glue.values()) - min(glue.values()), 1), spread=round(max(allv) - min(allv), 1),
                          lat=[round(min(glue.values()), 1), round(max(glue.values()), 1)], max_slew=round(max(x for _, x in S.values()), 1), nbuf=nb)
            if core: row[C]["core_raw"] = [round(a, 1) for k, (a, _) in S.items() if "/clk" in k]
        L = open(f"{d}/log_TT.txt").read()
        m = re.search(r"OT_CTS_MS (\d+)", L); row["cts_ms"] = int(m.group(1)) if m else None
        m = re.findall(r"Total wire length = ([\d.]+)|^Total\s+([\d.]+)um", L, re.M)
        m = re.search(r"\n(Clock|Sequential|Combinational)?.*?\nTotal\s+[\d.e+-]+\s+[\d.e+-]+\s+[\d.e+-]+\s+([\d.e+-]+)", L)
        pw = re.findall(r"^Clock\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)", L, re.M)
        row["clock_power_W"] = float(pw[-1][3]) if pw else None
        wl = re.findall(r"^(M[2-9])\s+([\d.]+)um", L, re.M); row["wl_um"] = round(sum(float(x) for _, x in wl), 1)
        row["dpl_disp"] = re.findall(r"(?:max|average) displacement.*", L)[:2]
        print(json.dumps(row))
