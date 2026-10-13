#!/usr/bin/env python3
"""ring_mut.py <tile.sv> <out.sv> <DROP|ADDR|CREDIT|FORK> <laneA reg> <laneB reg> <fork reg> <WB>: mutated COPY of a
generated relay tile (one statement 'reg [H:0] r_X_0; always @(posedge ck) r_X_0 <= SRC[H:0];' per lane).  Exits non-zero
when the mutant does not apply or leaves the text unchanged (a mutant that changes nothing would be a vacuous negative)."""
import re, sys
src, out, mut, la, lb, lf, wb = sys.argv[1:8]
txt = open(src).read()

def lane(name):
    m = re.search(r"reg \[(\d+):0\] r_%s_0; always @\(posedge ck\) r_%s_0 <= (\w+)\[(\d+):0\];" % (name, name), txt)
    if not name or not m or m.group(1) != m.group(3):
        sys.exit(f"ring_mut: lane {name!r} not found in {src}")
    return m, int(m.group(1)), m.group(2)

if mut == "DROP":      # dropped beat: the valid bit (0) is cleared when the per-station sequence byte [16:9] is 0x77
    m, h, s = lane(la)
    new = f"reg [{h}:0] r_{la}_0; always @(posedge ck) r_{la}_0 <= ({s}[0] && {s}[16:9] == 8'h77) ? {{{s}[{h}:1], 1'b0}} : {s}[{h}:0];"
elif mut == "ADDR":    # wrong station: address bits 0 and 1 (frame bits 1 and 2) swapped
    m, h, s = lane(la)
    new = f"reg [{h}:0] r_{la}_0; always @(posedge ck) r_{la}_0 <= {{{s}[{h}:3], {s}[1], {s}[2], {s}[0]}};"
elif mut == "CREDIT":  # stale credit: the top bit of lane B (lane A MAIN credit) is refreshed every other clock only
    if int(wb) == 0:
        sys.exit("ring_mut: CREDIT needs a two-way tile (the credit of a one-way tile does not cross it)")
    m, h, s = lane(lb)
    new = (f"reg [{h}:0] r_{lb}_0; reg mut_ph = 1'b0; always @(posedge ck) begin mut_ph <= ~mut_ph; "
           f"r_{lb}_0[{h-1}:0] <= {s}[{h-1}:0]; if (mut_ph) r_{lb}_0[{h}] <= {s}[{h}]; end")
elif mut == "FORK":    # station fork one bit off
    m, h, s = lane(lf)
    new = f"reg [{h}:0] r_{lf}_0; always @(posedge ck) r_{lf}_0 <= {s}[{h+1}:1];"
else:
    sys.exit(f"ring_mut: unknown mutant {mut}")
res = txt[:m.start()] + new + txt[m.end():]
if res == txt:
    sys.exit("ring_mut: mutant left the RTL unchanged")
open(out, "w").write(res)
print(f"ring_mut: {mut} applied to {src} -> {out}")
