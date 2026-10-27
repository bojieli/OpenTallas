#!/usr/bin/env python3
"""HBM-CORE-LAT-R5 collar_idx256r: right-sized outline + rebalanced pins (COORD 02:20 spot-check: no more trunk;
shrink the 108^2 outline, rebalance pins).  Reads the R4 kit, writes a new kit dir.
  usage: gen_r5_collar.py R4KIT NEWKIT SIDE_UM
Outline SIDE (4.32 lattice), core margin 4.32, centre clock-entry island 8.64^2 on the lattice, clk pin at its centre.
Pins: 1560 bits rebalanced to 390/face by destination (planS2 internal_stations, CHECKED there):
  W: rec (221, -> u_hb_argmax, which sits W), c_busy/c_fault/go (-> argmax), tgt, clk_in, rst_n, c_done__W, pw_data[0..k)
  N: cfg_* (L74m_i lands N), control outs active/fault/ready/c_done/pw_we/start_v/pw_addr, prm[hi] remainder
  E: prm (face buses L124/L64/L80 land E at x 1105)
  S: prm rest + pw_data rest (pw_data station sits S at y 764)
Each face: bits in bus order, uniform spacing over [2.184, SIDE-2.184], snapped to the 0.048 track grid (+0.024)."""
import json, sys, shutil, re
from pathlib import Path
r4, new, side = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])
pins = json.load(open(r4 / "pins.json"))
bits = {}
for p in pins:
    bits.setdefault(p["bus"], []).append(p["bit"])
for b in bits: bits[b].sort(key=lambda x: -1 if x is None else x)
def take(bus, lo=0, hi=None):
    v = bits[bus][lo:hi]; return [(bus, x) for x in v]
nprm = len(bits["prm"]); npw = len(bits["pw_data"])
W_ = take("rec") + take("c_busy") + take("c_fault") + take("go") + take("tgt") + take("clk_in") + take("rst_n") + take("c_done__W")
N_ = []
for b in ("cfg_v", "desc_v", "launch_v", "cfg_target", "cfg_addr", "cfg_data", "active", "fault", "ready", "c_done", "pw_we", "start_v", "pw_addr"):
    N_ += take(b)
tgt = len(pins) - 1 - 0  # clk is not a face pin
per = (len(pins) - 1) // 4
kw = per - len(W_)                       # pw_data bits that go W
W_ += take("pw_data", 0, kw)
E_ = take("prm", 0, per)
kn = per - len(N_)
S_ = take("prm", per, nprm - kn) + take("pw_data", kw, npw)
N_ += take("prm", nprm - kn, nprm)
faces = dict(N=N_, E=E_, S=S_, W=W_)
allb = sorted(sum(faces.values(), []), key=str)
want = sorted(((p["bus"], p["bit"]) for p in pins if p["bus"] != "clk"), key=str)
assert allb == want, "pin set changed"
lo, hi = 2.184, side - 2.184
out, io = [], []
for f, lst in faces.items():
    n = len(lst); pitch = (hi - lo) / (n - 1)
    assert pitch >= 0.144, (f, pitch)
    last = -1
    for i, (bus, bit) in enumerate(lst):
        t = lo + i * pitch
        t = round(0.024 + round((t - 0.024) / 0.048) * 0.048, 3)
        assert t > last + 0.047; last = t
        nm = bus if bit is None else f"{bus}[{bit}]"
        if f in "NS":
            y = side if f == "N" else 0.0
            out.append(dict(bus=bus, bit=bit, layer="M5", x=t, y=y, face=f))
            io.append(f"place_pin -pin_name {{{nm}}} -layer M5 -location {{{t:.4f} {side-0.096 if f=='N' else 0.096:.4f}}} -pin_size {{0.0240 0.1920}}")
        else:
            x = side if f == "E" else 0.0
            out.append(dict(bus=bus, bit=bit, layer="M4", x=x, y=t, face=f))
            io.append(f"place_pin -pin_name {{{nm}}} -layer M4 -location {{{side-0.096 if f=='E' else 0.096:.4f} {t:.4f}}} -pin_size {{0.1920 0.0240}}")
c = side / 2; i0, i1 = c - 4.32, c + 4.32
cx = round(0.024 + round((c - 0.024) / 0.048 + 1e-9) * 0.048, 3)  # M5 track (COORD: no half-track clk pin); 43.2 -> 43.224
out.append(dict(bus="clk", bit=None, layer="M5", x=cx, y=c, face="C"))
io.append(f"place_pin -pin_name {{clk}} -layer M5 -location {{{cx:.4f} {c:.4f}}} -pin_size {{0.032 0.192}}   ;# master-plan slice centre entry (R5 trial outline)")
if new.exists(): raise SystemExit(f"{new} exists")
shutil.copytree(r4, new, ignore=shutil.ignore_patterns("run", "lec", "FAIL_*", "*.log", "placed.csv", "postcts_gate_*", "ot_face_flops.txt", "hold_census.txt", "__pycache__", "face_shell_work"))
(new / "pins.json").write_text(json.dumps(out) + "\n")
(new / "io.tcl").write_text(f"# HBM-CORE-LAT-R5 gen_r5_collar.py: trial outline {side}x{side}, rebalanced pins ({len(io)} pins, core frame um). Proposal to HBM-MU-QUAD-3 (planU2 delta).\n" + "\n".join(io) + "\n")
cm = (new / "config.mk").read_text()
cm = re.sub(r"export DIE_AREA = .*", f"export DIE_AREA = 0 0 {side:g} {side:g}", cm)
cm = re.sub(r"export CORE_AREA = .*", f"export CORE_AREA = 4.32 4.32 {side-4.32:.2f} {side-4.32:.2f}", cm)
cm = re.sub(r"export PLACE_DENSITY = .*", "export PLACE_DENSITY = 0.65", cm)
cm = re.sub(r"export OT_TRUNK_ISLAND = .*", f"export OT_TRUNK_ISLAND = {i0:.2f} {i0:.2f} {i1:.2f} {i1:.2f}", cm)
cm += f"# HBM-CORE-LAT-R5 2026-10-27: trial outline {side:g}^2 (was 108^2, ~35% empty) + rebalanced pins (gen_r5_collar.py); same 12.8c trunk 7x BUFx10 (plan pick unchanged, see README); PLACE_DENSITY 0.65 >= util\n"
(new / "config.mk").write_text(cm)
ms = json.load(open(new / "master_slice.json"))
ms["outline_um"] = [side, side]
ms["islands"][0]["rect_um"] = [i0, i0, i1, i1]; ms["islands"][0]["centre_um"] = [c, c]
ms["islands"][0]["clock_pin"]["xy_um"] = [cx, c]
ms["note"] += f" | HBM-CORE-LAT-R5: TRIAL outline {side}^2 + rebalanced pins, pending HBM-MU-QUAD-3 planU2 delta"
(new / "master_slice.json").write_text(json.dumps(ms, indent=1) + "\n")
t = (new / "master_slice.tcl").read_text()
d = lambda v: str(int(round(v * 1000)))
t = t.replace("47520 47520 56160 56160", f"{d(i0)} {d(i0)} {d(i1)} {d(i1)}")
(new / "master_slice.tcl").write_text(t)
mio = json.load(open(new / "master_slice_io.json")); mio["slice_pins"]["clk"]["xy_um"] = [c, c]
(new / "master_slice_io.json").write_text(json.dumps(mio, indent=1) + "\n")
fz = json.load(open(new / "freeze.json")); fz["outline_um"] = [side, side]; fz["r5_note"] = "HBM-CORE-LAT-R5 trial outline + rebalanced pins (gen_r5_collar.py); plan delta pending QUAD-3"
(new / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
print(json.dumps({f: len(v) for f, v in faces.items()}), "island", i0, i1)
