"""FTLOCK-S81 latch-form estimate from routed STA paths (GRT-free, analytic; [inferred]).
usage: latch_est.py pairs FFLOG OUT_PAIRS           -> worst hop pairs (launch_inst \t capture_inst) from FF_MIN
       latch_est.py est FFLOG TTLOG OUT_JSON         -> per pair: measured FF hold / TT setup + latch-form estimate
Latch u_fl at the hop midpoint on the LAUNCH station's clock (clock_taps hop-latch pass), wire delay split in half;
DLLx1_ASAP7_75t_R arcs (fall-edge CLK->Q, setup/hold to the rising closing edge) from the RVT SEQ TT/FF liberty at
20 ps slew / 1.44 fF."""
import json, re, sys
T = 833.0
DLL = {"FF": dict(ckq_min=27.48, ckq_max=36.30, hold=-1.45, setup=10.79),
       "TT": dict(ckq_min=37.17, ckq_max=50.42, hold=-0.35, setup=15.41)}
HOLD_UNC = 25.0


def paths(txt, tag):
    out = []
    for blk in re.split(r"(?=^Startpoint: )", txt, flags=re.M):
        if not blk.startswith("Startpoint:"):
            continue
        s = re.match(r"Startpoint: (\S+)", blk).group(1); e = re.search(r"Endpoint: (\S+)", blk).group(1)
        sl = re.search(r"^\s*(-?[\d.]+)\s+slack \((?:VIOLATED|MET)\)", blk, re.M)
        lines = [l for l in blk.splitlines() if re.match(r"\s*-?[\d.]+\s+-?[\d.]+\s", l)]
        def t_of(pat, nth=0):
            hits = [l for l in blk.splitlines() if pat in l]
            if len(hits) <= nth: return None
            nums = re.findall(r"-?\d+\.\d+", hits[nth])
            return float(nums[1]) if len(nums) >= 2 else None
        ck = [l for l in blk.splitlines() if "/CLK (" in l]
        tnum = lambda l: float(re.findall(r"-?\d+\.\d+", l)[1])
        arr = re.search(r"^\s*(-?[\d.]+)\s+data arrival time", blk, re.M)
        req = re.search(r"^\s*(-?[\d.]+)\s+data required time", blk, re.M)
        qn = [l for l in blk.splitlines() if re.search(r"/QN? \(", l)]
        if not (sl and arr and req and len(ck) >= 2 and qn):
            continue
        out.append(dict(tag=tag, start=s, end=e, slack=float(sl.group(1)), launch_clk=tnum(ck[0]), q=tnum(qn[0]),
                        arrival=float(arr.group(1)), capture_clk=tnum(ck[1]), required=float(req.group(1))))
    return out


def hop(s, e):
    a = re.match(r"u_bound\.u_ft_(\w+?)_(\d+)/", s); b = re.match(r"u_bound\.u_ft_(\w+?)_(\d+)/", e)
    return bool(a and b and a.group(1) == b.group(1) and int(b.group(2)) == int(a.group(2)) + 1)


if sys.argv[1] == "pairs":
    txt = open(sys.argv[2]).read().split("PROBE_BEGIN FF_MIN", 1)[1]
    ps = [p for p in paths(txt, "FF") if hop(p["start"], p["end"])]
    open(sys.argv[3], "w").write("".join(f"{p['start']}\t{p['end']}\n" for p in ps))
    print(len(ps), "hop pairs; worst", ps[0]["slack"] if ps else None, "of", len(paths(txt, "FF")), "paths")
else:
    ff_txt, tt_txt = open(sys.argv[2]).read(), open(sys.argv[3]).read()
    ff = {(p["start"], p["end"]): p for p in paths(ff_txt.split("PROBE_BEGIN FF_MIN", 1)[1].split("PROBE_END", 1)[0], "FF")}
    rows = []
    for chunk in tt_txt.split("PROBE_BEGIN TT_MAX ")[1:]:
        tt_part, _, ffs_part = chunk.partition("PROBE_BEGIN FF_MIN_SAME")
        tp = paths(tt_part, "TT")
        if not tp or (tp[0]["start"], tp[0]["end"]) not in ff:
            continue
        t, f = tp[0], ff[(tp[0]["start"], tp[0]["end"])]          # FF numbers from the FF session (FF libs)
        tm = paths(ffs_part.split("PROBE_END")[0], "TT")          # the TT session's min path = TT hold (info)
        wf = f["arrival"] - f["q"]; wt = t["arrival"] - t["q"]
        clkq_f = f["q"] - f["launch_clk"]; clkq_t = t["q"] - t["launch_clk"]
        hold_lc = f["slack"] + T / 2 + DLL["FF"]["ckq_min"] - clkq_f - wf / 2
        hold_ll = clkq_f + wf / 2 - HOLD_UNC - DLL["FF"]["hold"]
        setup_lc = t["required"] - (t["launch_clk"] + T / 2 + DLL["TT"]["ckq_max"] + wt / 2)
        setup_ll = (T + t["launch_clk"] - DLL["TT"]["setup"]) - (t["launch_clk"] + clkq_t + wt / 2)
        rows.append(dict(start=f["start"], end=f["end"], ff_hold_now=f["slack"], tt_setup_now=t["slack"],
                         tt_hold_now=tm[0]["slack"] if tm else None,
                         ff_launch_clk=f["launch_clk"], ff_capture_clk=f["capture_clk"], ff_clkq=round(clkq_f, 2), ff_wire=round(wf, 2),
                         tt_launch_clk=t["launch_clk"], tt_capture_clk=t["capture_clk"], tt_clkq=round(clkq_t, 2), tt_wire=round(wt, 2),
                         est_ff_hold_latch_to_capture=round(hold_lc, 2), est_ff_hold_launch_to_latch=round(hold_ll, 2),
                         est_tt_setup_latch_to_capture=round(setup_lc, 2), est_tt_setup_launch_to_latch=round(setup_ll, 2)))
    summ = {k: (min(r[k] for r in rows) if rows else None) for k in
            ("ff_hold_now", "tt_setup_now", "est_ff_hold_latch_to_capture", "est_ff_hold_launch_to_latch",
             "est_tt_setup_latch_to_capture", "est_tt_setup_launch_to_latch")}
    json.dump(dict(pairs=len(rows), worst=summ, T_ps=T, dll=DLL, hold_unc=HOLD_UNC, rows=rows,
                   tag="[inferred] analytic: routed arcs of the current DB + DLLx1 liberty arcs; latch mid-hop on the launch tap"),
              open(sys.argv[4], "w"), indent=1)
    print(json.dumps(dict(pairs=len(rows), worst=summ)))
