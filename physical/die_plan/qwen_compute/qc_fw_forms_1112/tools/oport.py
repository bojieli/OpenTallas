"""output-port hold census from an OpenSTA full_clock min report: per port bus, n, worst slack, launch CLK arrival, data delay"""
import re, sys, collections, statistics as st
txt = open(sys.argv[1]).read()
rows = collections.defaultdict(list)
for blk in txt.split("Startpoint: ")[1:]:
    ep = re.search(r"Endpoint: (\S+) \(output port", blk)
    if not ep: continue
    sl = re.search(r"(-?[\d.]+)\s+slack", blk)
    clk = re.findall(r"^\s*([\d.-]+)\s+([\d.-]+) \^ (\S+)/CLK ", blk, re.M)
    arr = re.search(r"([\d.-]+)\s+data arrival time", blk)
    req = re.search(r"([\d.-]+)\s+data required time", blk)
    ck = float(clk[0][1]) if clk else None
    bus = re.sub(r"\[\d+\]$", "", ep.group(1))
    rows[bus].append((float(sl.group(1)), ck, float(arr.group(1)) - (ck or 0), float(req.group(1))))
tot = sum(len(v) for v in rows.values())
print("output-port min violators", tot, "buses", len(rows))
for b, v in sorted(rows.items(), key=lambda kv: min(x[0] for x in kv[1]))[:12]:
    print(f"{b:24s} n={len(v):4d} worst={min(x[0] for x in v):7.2f} clk_at_launch_med={st.median([x[1] for x in v if x[1] is not None]):6.1f} data_after_clk_med={st.median([x[2] for x in v]):6.1f} required={v[0][3]:6.1f}")
