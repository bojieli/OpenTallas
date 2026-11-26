"""QC-INT-R2-SUC phase 2: carry the re-sited representative legs into the per-bit sites (relay_sites u_ist_<lane>_<k>.q[b],
internal_stations bit_sites_um, ft_slots bit_sites_um). Reads OLD plan (per-bit truth) and NEW plan (re-sited regs_um).
Per bit: site(k) = R_k + lam_k * (S_b - R_0), S_b = the bit's own old stage-0 site (its source side), lam linear 1 -> 0 over the stages.
FT slots (compact banks): rigid shift of each stage bank onto its new station."""
import sys, json, re, math, collections
import numpy as np
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_fp_floorplan as fp
CW, CH = 1.404, 0.27
HALO = 4.32

def snap(x, y):
    return round(x / 0.054) * 0.054, round(y / CH) * CH

class Occ:
    def __init__(self, t, skip_prefix):
        self.bx = [fp._box(c) for c in t["hard_cores"]]
        self.occ = set()
        for k, v in t["relay_sites"].items():
            if not k.startswith(skip_prefix): self.occ.add(self.key(v))
        self.moved = 0
    def key(self, p): return (int(p[0] // CW), int(round(p[1] / CH)))
    def incore(self, p):
        return any(b[0]-HALO < p[0] < b[2]+HALO and b[1]-HALO < p[1] < b[3]+HALO for b in self.bx)
    def place(self, p, outline):
        x, y = snap(*p)
        W, H = outline
        x = min(max(x, 2.0), W - 4.0); y = min(max(y, 2.0), H - 2.0)
        for r in range(0, 400):
            for dx, dy in self._ring(r):
                q = (x + dx * CW, y + dy * CH)
                if self.incore(q) or q[0] < 1 or q[1] < 1 or q[0] > W-3 or q[1] > H-1: continue
                k = self.key(q)
                if k in self.occ: continue
                self.occ.add(k); self.moved += (r > 0)
                return list(snap(*q))
        raise RuntimeError("no free site near %s" % (p,))
    def _ring(self, r):
        if r == 0: yield (0, 0); return
        for dx in range(-r, r+1):
            for dy in (-r, r): yield dx, dy
        for dy in range(-r+1, r):
            for dx in (-r, r): yield dx, dy

def pack(i, n, cx, cy, cols=12, ft=False):
    """compact bank: bit i of n in row-major order around (cx, cy)"""
    r, c = divmod(i, cols)
    nr = (n + cols - 1) // cols
    return [cx + (c - cols / 2.0) * CW, cy + (r - nr / 2.0) * CH]

def lam(k, m): return 1.0 if m <= 1 else max(0.0, 1.0 - k / (m - 1))

def process(old, new, log):
    to, tn = old, new
    outline = tn["outline_um"]
    rs_old = to["relay_sites"]; rs_new = tn["relay_sites"]
    lanes = {}
    for s in tn["internal_stations"]:
        so = next(x for x in to["internal_stations"] if x["conn"] == s["conn"])
        if so["regs_um"] != s["regs_um"]: lanes[s["conn"].replace("bus:", "")] = (so, s)
    pref = tuple("u_ist_%s_" % l for l in lanes)
    occ = Occ(tn, pref)
    # relay_sites + bit_sites_um of the internal stations
    for lane, (so, s) in sorted(lanes.items()):
        R = s["regs_um"]; m = len(R)
        bits = collections.defaultdict(dict)
        for k, v in rs_old.items():
            mm = re.match(r"u_ist_%s_(\d+)\.q\[(\d+)\]$" % re.escape(lane), k)
            if mm: bits[int(mm.group(2))][int(mm.group(1))] = v
        nb = 0
        if bits:
            for b in sorted(bits):
                st = bits[b]; S = st[0]
                for k in range(m):
                    if k not in st: continue
                    p = pack(b, len(bits), R[k][0], R[k][1])
                    rs_new["u_ist_%s_%d.q[%d]" % (lane, k, b)] = occ.place(p, outline); nb += 1
        bs = s.get("bit_sites_um")
        if bs:
            S0 = [list(p) for p in bs[0]]; newbs = []
            for k, bank in enumerate(bs):
                l = lam(k, m)
                newbs.append([occ.place(pack(i, len(bank), R[k][0], R[k][1]), outline) for i in range(len(bank))])
            s["bit_sites_um"] = newbs; nb += sum(len(b) for b in newbs)
        reach = 0.0
        for b in bits:
            S = bits[b][0]; q = rs_new["u_ist_%s_0.q[%d]" % (lane, b)]
            reach = max(reach, abs(S[0]-q[0]) + abs(S[1]-q[1]))
        log.append(dict(lane=lane, sites=nb, old_stage0_to_new_stage0_um=round(reach, 1)))
    # FT slots: compact banks, rigid shift per stage
    for sn in tn["ft_slots"]:
        so = next(x for x in to["ft_slots"] if x["name"] == sn["name"])
        if so["regs_um"] == sn["regs_um"] or not sn.get("bit_sites_um"): continue
        off = 1 if len(so["bit_sites_um"]) == len(so["regs_um"]) - 1 else 0
        nb_banks = len(sn["regs_um"]) - off if sn["stations"] == len(sn["regs_um"]) else len(sn["regs_um"]) - 1
        nb_banks = len(sn["regs_um"]) - 1 if off else len(sn["regs_um"])
        width = len(so["bit_sites_um"][0])
        newbs = []
        for j in range(nb_banks):
            tx, ty = sn["regs_um"][j + off]
            newbs.append([occ.place(pack(i, width, tx, ty, cols=6), outline) for i in range(width)])
        sn["bit_sites_um"] = newbs
        log.append(dict(ft=sn["name"], sites=sum(len(b) for b in newbs)))
    log.append(dict(moved_for_collision=occ.moved))

if __name__ == "__main__":
    old = json.load(open(sys.argv[1])); new = json.load(open(sys.argv[2])); out = {}
    for n in sys.argv[4].split(","):
        log = []; process(old["partition_types"][n], new["partition_types"][n], log); out[n] = log; print(n, log, flush=True)
    json.dump(new, open(sys.argv[3], "w"), indent=1)
