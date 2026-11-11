"""summ.py LOG [LOG...]: DS85-HEHOT summary -> GRT-0096 total + M6 congestion, 2D H overflow over each he/hw instance
and over the e11 hotspot (macro boxes taken from each log's WI_MACRO lines)."""
import re, sys, collections
HCA = '/srv/opentallas-scratch3/claude/die-s81-85/hcabs/grt/h9/o/hca.log'
for lg in sys.argv[1:]:
    t = open(lg).read(); i = t.rfind("GRT-0096")
    if i < 0: print(lg, "not done"); continue
    tab = {l.split()[0]: l.split()[-1] for l in t[i:i+1500].split("\n") if re.match(r"^(M\d|Total)\s", l)}
    mac = [l.split() for l in t.split("\n") if l.startswith("WI_MACRO")] or [l.split() for l in open(HCA) if l.startswith("WI_MACRO")]
    box = {inst.split(".")[-1]: (int(a)/1000, int(b)/1000, int(c)/1000, int(d)/1000) for _, inst, m, a, b, c, d in mac
           if m.startswith("ot_v41_rom_elem")}
    ov = collections.Counter(); typ = "H"
    rpt = lg[:-4] + ".congestion.rpt"
    for ln in open(rpt):
        if ln.startswith("violation type"): typ = "H" if "Horiz" in ln else "V"
        m = re.search(r"capacity:(\d+) usage:(\d+)", ln)
        if m: o = int(m.group(2)) - int(m.group(1))
        m = re.search(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)", ln)
        if m:
            x = (float(m.group(1)) + float(m.group(3))) / 2; y = (float(m.group(2)) + float(m.group(4))) / 2
            ov["2D_" + typ] += o
            for k, B in box.items():
                if B[0] <= x <= B[2] and B[1] <= y <= B[3]: ov[k + "_" + typ] += o
    he = sum(v for k, v in ov.items() if k.endswith("_e_H"))
    print(f"{lg.split('/')[-1]:14s} total {tab.get('Total')} M6 {tab.get('M6')} M4 {tab.get('M4')} | 2D H {ov['2D_H']} he_H {he} e11e_H {ov['u_u_e11_u_e_H']} e10e_H {ov['u_u_e10_u_e_H']} hw_H {sum(v for k,v in ov.items() if k.endswith('_w_H'))}")
