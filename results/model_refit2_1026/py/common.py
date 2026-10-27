"""MODEL-REFIT-2 shared parsing: mscts_h spec, geo, measured stage/sink dumps."""
import re, statistics as st
P2 = 833.0 / 2

def parse_spec(p):
    t = open(p).read()
    entry = re.search(r"set\s+ot_h_entry_n\s+(\d+)", t)
    if entry and int(entry.group(1)):
        raise ValueError("uf_phys cannot price ot_h_entry_n: encode the common entry trunk as explicit tree nodes")
    root = tuple(map(float, re.search(r"set ot_ms_root \{([\d.]+) ([\d.]+)\}", t).groups()))
    tree = {}
    blk = t.split("set ot_ms_tree {")[1].split("\n}")[0]
    for ln in blk.strip().splitlines():
        f = ln.strip().strip("{}").split()
        tree[f[0]] = dict(par=f[1], xy=(float(f[2]), float(f[3])), cell=f[4])
    leaves = {}
    blk = t.split("set ot_ms_leaves {")[1].split("\n}\nset ot_ms_macros")[0]
    for ln in blk.strip().splitlines():
        ln = ln.strip()
        m = re.match(r"\{(\S+) (\S+) \{([\d.]+) ([\d.]+)\} \{(.*)\} (\S+)\}$", ln)
        regs = re.findall(r"\{\{([^{}]*)\} \{(\w+)\}\}", m.group(5))
        leaves[m.group(1)] = dict(par=m.group(2), xy=(float(m.group(3)), float(m.group(4))), regs=regs, cell=m.group(6))
    macros = []
    blk = t.split("set ot_ms_macros {")[1].split("\n}")[0]
    for ln in blk.strip().splitlines():
        m = re.match(r"\s*\{\{(.*)\} (\S+) \{([\d.]+) ([\d.]+)\}\}", ln)
        macros.append(dict(inst=m.group(1), leaf=m.group(2), xy=(float(m.group(3)), float(m.group(4)))))
    return dict(root=root, tree=tree, leaves=leaves, macros=macros)

def parse_geo(p):
    sinks, macs = {}, {}
    for ln in open(p):
        f = ln.split()
        if f and f[0] == "SINK":
            sinks[(f[4], f[5])] = (float(f[1]), float(f[2]))
        if f and f[0] == "MACRO":
            macs[f[1]] = dict(rect=tuple(map(float, f[3:7])), pin=(float(f[8]), float(f[9])))
        if f and f[0] == "PIN" and f[1] == "ck":
            entry = (float(f[2]), float(f[3]))
    return sinks, macs, entry

def parse_stage(p):
    d = {}
    for ln in open(p):
        if not ln.startswith("PIN"):
            continue
        f = ln.rstrip("\n").split("\t")
        v = [float(x) for x in f[6:12]]
        d[(f[1], f[2])] = dict(net=f[4], cell=f[5], ar=v[0], af=v[1] - P2, sr=v[2], sf=v[3], amr=v[4], amf=v[5] - P2)
    return d

def _rng(ln):
    v = [float(x) for x in re.findall(r"[\d.]+", ln.split(":")[1])]
    return sum(v) / len(v)

def parse_nets(p):
    nets = {}
    cur = None
    for ln in open(p):
        if ln.startswith("NETRPT"):
            cur = ln.split()[1]; nets[cur] = {}
        elif cur and "Wire capacitance:" in ln:
            nets[cur]["cw"] = _rng(ln)
        elif cur and "Pin capacitance:" in ln:
            nets[cur]["cp"] = _rng(ln)
    return nets

def parse_sinks(p):
    taps = {}
    mac = {}
    for ln in open(p):
        if ln.startswith("#"):
            continue
        pin, net, rM, fM, rm, fm = ln.rstrip("\n").split("\t")
        v = dict(rise=float(rM), late=max(float(rM), float(fM) - P2), early=min(float(rm), float(fm) - P2))
        if net.startswith("ot_ms_m") and net[7].isdigit():
            mac[pin] = v; continue
        taps.setdefault(net[len("ot_ms_"):-len("_clk")], []).append(v)
    return {k: {b: st.mean(x[b] for x in v) for b in ("rise", "late", "early")} for k, v in taps.items()}, mac
