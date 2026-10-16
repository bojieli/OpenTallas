#!/usr/bin/env python3
"""Derive split station masters (bit slices) from a wide GEN18r station macro: glue module (posedge form) + LEF macro
whose data pins are the parent's pins of the slice's first W bits at the generator pitch, shifted to the slice origin.
usage: mk_split.py LEF.gz PARENT WIDTH OUT_GLUE OUT_LEF"""
import gzip, re, sys
lef, parent, W, og, ol = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
txt = gzip.open(lef, 'rt').read()
m = re.search(r'^MACRO %s\n(.*?)^END %s\n' % (re.escape(parent), re.escape(parent)), txt, re.S | re.M)
body = m.group(1)
w, h = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', body).groups())
pins = {}
for pm in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n', body, re.S):
    r = re.search(r'LAYER (\S+) ;\s+RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', pm.group(2))
    pins[pm.group(1)] = (r.group(1), *map(float, r.groups()[1:]))
horiz = parent.startswith('dsfd_hstnh_')
name = re.sub(r'_\d+$', f'_{W}s', parent)          # dsfd_hstnv_129s: a slice master of a split wide station
d0 = pins['di[0]']
a0 = d0[1] if not horiz else d0[2]                 # along-face origin of bit 0
pitch = ((pins['di[1]'][1] - d0[1]) if not horiz else (pins['di[1]'][2] - d0[2]))
span = a0 + (W - 1) * pitch + (a0 + 0.024)        # same end margin as the start
out = [f'MACRO {name}', '  CLASS BLOCK ;', f'  FOREIGN {name} 0 0 ;',
       f'  SIZE {span if not horiz else w:.3f} BY {h if not horiz else span:.3f} ;', '  SYMMETRY X Y ;']
def pin(n, L, x1, y1, x2, y2):
    out.extend([f'  PIN {n}', '    DIRECTION INOUT ;', '    USE SIGNAL ;', '    PORT', f'      LAYER {L} ;',
                f'        RECT {x1:.3f} {y1:.3f} {x2:.3f} {y2:.3f} ;', '    END', f'  END {n}'])
for b in range(W):
    for p in ('di', 'dq'):
        L, x1, y1, x2, y2 = pins[f'{p}[{b}]']
        if not horiz:
            dx = x1 - pins[f'{p}[0]'][1]; pin(f'{p}[{b}]', L, pins[f'{p}[0]'][1] + dx, y1, pins[f'{p}[0]'][3] + dx, y2)
        else:
            dy = y1 - pins[f'{p}[0]'][2]; pin(f'{p}[{b}]', L, x1, pins[f'{p}[0]'][2] + dy, x2, pins[f'{p}[0]'][4] + dy)
L, x1, y1, x2, y2 = pins['ck[0]']
if not horiz:   # ck on the W face, mid height
    pin('ck[0]', L, x1, y1, x2, y2)
else:           # ck on the S face, mid width
    pin('ck[0]', L, x1, y1 if y1 < span / 2 else 0.048, x2, (y2 if y2 < span / 2 else 0.240))
out.append(f'END {name}')
open(ol, 'w').write('\n'.join(out) + '\n')
open(og, 'w').write(f'''module {name} (
    input wire [0:0] ck,
    input wire [{W - 1}:0] di,
    output wire [{W - 1}:0] dq
);
    reg [{W - 1}:0] q;   // common-clock station: every di bit captured at the rising edge of ck
    always @(posedge ck[0]) q <= di;
    assign dq = q;
endmodule
''')
print(name, 'span', round(span, 3), 'pitch', pitch, 'horiz', horiz)
