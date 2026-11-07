#!/usr/bin/env python3
"""QC-NLNK-RF2 kit derivation (vR): mk_vr.py KIT nl|nk  (KIT = rsync of the vB2p / vB2hp kit without run/).
Applies: macro x shifts (multiples of 1.728 um = lcm of M3/M4/M5 pitches and 0.192), config (RSTP 3, copies <= 8, M6, max wire 100),
io-only hold not padded in-core (dont_touch port -> face flop nets, PRE_CTS)."""
import re, sys, json
from pathlib import Path
K = Path(sys.argv[1]); T = sys.argv[2]
RB0, RB1 = r"g_rb\[\d\]\.g_single\.g_col\[0\]\.u_leaf", r"g_rb\[\d\]\.g_single\.g_col\[1\]\.u_leaf"
if T == "nl":
    MOVES = {RB0: -8.64, RB1: -8.64, r"g_sl\\?\[3\]\.g_hd\.u_lh\.u_native_rawleaf": 25.92, r"g_sl\\?\[6\]\.g_hd\.u_lh\.u_native_rawleaf": 25.92,
             r"g_sl\\?\[7\]\.g_hd\.u_lh\.u_native_rawleaf": 25.92}
else:
    MOVES = {RB0: -6.912, RB1: -6.912}
    for s in (0, 2, 4, 7):
        MOVES[rf"g_sl\\?\[{s}\]\.g_hd\.u_lh\.u_native_rawleaf"] = -25.92
mp = K / "macro_place.tcl"; L = mp.read_text().split("\n"); moved = {}
pre = K / "macro_place.tcl.pre_vR"; pre.write_text(mp.read_text())
cur = None
for i, l in enumerate(L):
    m = re.search(r'error "hard child (\S+):', l)
    if m: cur = m.group(1)
    m = re.match(r'(\$i setLocation \[expr \{round\()([\d.]+)( \* \$dbu\).*)', l)
    if m and cur:
        for rx, dx in MOVES.items():
            if re.search(rx, cur.replace("\\", "")) or re.search(rx, cur):
                nx = round(float(m.group(2)) + dx, 3)
                L[i] = f"{m.group(1)}{nx}{m.group(3)}"; moved[cur] = (float(m.group(2)), nx)
    m = re.match(r'puts "hard child (\S+) -> (.*) (\S+) at ([\d.]+) ([\d.]+) (.*)', l)
    if m and m.group(1) in moved:
        L[i] = f'puts "hard child {m.group(1)} -> {m.group(2)} {m.group(3)} at {moved[m.group(1)][1]} {m.group(5)} {m.group(6)}'
need = 10 + (3 if T == "nl" else 4)
if len(moved) != need: sys.exit(f"moved {len(moved)} != {need}: {moved}")
mp.write_text("\n".join(L))
# freeze.json macro rows follow the plan
fj = K / "freeze.json"
txt = fj.read_text()
def walk(o):
    if isinstance(o, dict):
        if o.get("inst") in moved or (isinstance(o.get("inst"), str) and o["inst"].replace("\\", "") in moved):
            for k, v in list(o.items()):
                if isinstance(v, list) and len(v) >= 2 and isinstance(v[0], (int, float)):
                    if abs(v[0] - moved.get(o["inst"], moved.get(o["inst"].replace("\\", "")))[0]) < 1e-6:
                        v[0] = moved.get(o["inst"], moved.get(o["inst"].replace("\\", "")))[1]; walk.n += 1
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk.n = 0
d = json.loads(txt); walk(d); fj.with_suffix(".json.pre_vR").write_text(txt); fj.write_text(json.dumps(d, indent=1))
c = K / "config.mk"; s = c.read_text(); (K / "config.mk.pre_vR").write_text(s)
nick = f"kq_qfd_tile_{T}_a0c_vR"
s = re.sub(r"^export DESIGN_NICKNAME = .*$", f"export DESIGN_NICKNAME = {nick}", s, flags=re.M)
s, n = re.subn(r"^(export VERILOG_TOP_PARAMS = .*)$", r"\1 RSTP 3", s, flags=re.M); assert n == 1
for k, v in (("MAX_ROUTING_LAYER", "M6"), ("MAX_CLK_ROUTING_LAYER", "M6")):
    s, n = re.subn(rf"^export {k} = .*$", f"export {k} = {v}", s, flags=re.M); assert n <= 1, k
    if n == 0: s += f"export {k} = {v}\n"
s += ("\n# QC-NLNK-RF2 vR (OWNER 21:5x conservative form): pipelined reset tree RSTP 3 + copies <= 8 loads; signals and clock <= M6;\n"
      "# repeater pitch 100 um at the base build (place repair_design + GRT grt_maxwire.tcl); io-only hold not padded in-core (NEEDS_PARENT).\n"
      "export OT_RST_COPIES_MAX = 8\nexport MAX_WIRE_LENGTH = 100\nexport OT_MAXWIRE_UM = 100\n")
c.write_text(s)
b = K / "b3_pre_cts.tcl"; b.write_text(b.read_text() + "\n# QC-NLNK-RF2 vR: io-only hold is the parent's (NEEDS_PARENT), no in-core pads on port -> face flop nets\nsource /work/vr_io_nopad.tcl\n")
(K / "vr_io_nopad.tcl").write_text(r'''# QC-NLNK-RF2 vR: dont_touch on every net from a non-clock input port to its first flop, so hold repair adds no pad there.
# A hold miss on these paths alone is NEEDS_PARENT (COORD rule); the pads cost TT setup in vB2 (tap[392] -30.7 after ECO pads).
set blk [ord::get_db_block]; set n 0; set nf 0
foreach bt [$blk getBTerms] {
  if {[$bt getIoType] ne "INPUT" || [$bt getSigType] ne "SIGNAL"} continue
  if {[$bt getName] eq "ck"} continue
  set stack [list [$bt getNet]]
  while {[llength $stack]} {
    set net [lindex $stack 0]; set stack [lrange $stack 1 end]
    if {[$net isDoNotTouch]} continue
    $net setDoNotTouch 1; incr n
    foreach it [$net getITerms] {
      if {![$it isInputSignal]} continue
      set inst [$it getInst]
      if {[regexp {^(BUF|HB)} [[$inst getMaster] getName]]} {
        foreach o [$inst getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend stack [$o getNet] } }
      } else { incr nf }
    }
  }
}
puts "OT_VR_IO_NOPAD dont_touch nets $n, first loads $nf"
''')
print("VR", T, "moved", len(moved), "freeze rows", walk.n)
for k, v in sorted(moved.items()): print(" ", re.sub(r".*(g_rb|g_sl)", r"\1", k), v)
(K / "vB_FORM.txt").open("a").write(f"QC-NLNK-RF2 vR: mk_vr.py {T}: RSTP 3 + copies <=8, M6, max wire 100, io nopad, macro x shifts {sorted(set(MOVES.values()))}\n")
