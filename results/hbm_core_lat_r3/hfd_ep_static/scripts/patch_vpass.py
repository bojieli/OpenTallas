from pathlib import Path
import sys
p = Path(sys.argv[1]); s = p.read_text()
old_init = """        self.B = [[any(r[0] - halo < core[0] + i * G < r[2] + halo and r[1] - halo < core[1] + j * G < r[3] + halo for _, r, _ in macros)
                   for j in range(self.NY + 1)] for i in range(self.NX + 1)]
"""
new_init = """        M = [[any(r[0] - halo < core[0] + i * G < r[2] + halo and r[1] - halo < core[1] + j * G < r[3] + halo for _, r, _ in macros)
              for j in range(self.NY + 1)] for i in range(self.NX + 1)]
        # MACRO_VPASS (HBM-CORE-LAT-R3, --macro-vertical-pass): a macro whose OBS stops below the vertical clock layer
        # (e.g. ot_sram_1r1w_64x512_m1_r2c2: OBS M1-M4, PG on M4) is a NODE keep-out that clock wires cross VERTICALLY
        # only (M5, between the core M5 PG straps); horizontal moves over it stay illegal (M4 blocked).  Default off =
        # macros are full wire walls (unchanged).
        self.V = M if MACRO_VPASS else [[False] * (self.NY + 1) for _ in range(self.NX + 1)]
        self.B = [[False] * (self.NY + 1) for _ in range(self.NX + 1)] if MACRO_VPASS else M
"""
assert old_init in s; s = s.replace(old_init, new_init)
a = "    def site_ok(self, i, j): return not self.B[i][j] and not self.K[i][j]\n"
assert a in s
s = s.replace(a, "    def site_ok(self, i, j): return not self.B[i][j] and not self.K[i][j] and not self.V[i][j]\n\n"
              "    def step_ok(self, a, b, na, nb):\n"
              "        return not self.B[na][nb] and (na == a or not (self.V[a][b] or self.V[na][nb]))\n")
a = "        ok = self.site_ok if node else (lambda a, b: not self.B[a][b])\n"
assert a in s
s = s.replace(a, "        ok = self.site_ok if node else (lambda a, b: not self.B[a][b] and not self.V[a][b])\n")
a = "                if 0 <= na <= NX and 0 <= nb <= NY and not B[na][nb] and D[na][nb] < 0:\n"
assert a in s
s = s.replace(a, "                if 0 <= na <= NX and 0 <= nb <= NY and D[na][nb] < 0 and self.step_ok(a, b, na, nb):\n")
a = "                if 0 <= n[0] <= self.NX and 0 <= n[1] <= self.NY and D[n[0]][n[1]] == D[a0][b0] - 1:\n"
assert a in s
s = s.replace(a, "                if 0 <= n[0] <= self.NX and 0 <= n[1] <= self.NY and D[n[0]][n[1]] == D[a0][b0] - 1 and self.step_ok(a0, b0, n[0], n[1]):\n")
s = s.replace("class Maze:\n", "MACRO_VPASS = False\n\n\nclass Maze:\n", 1)
a = "    ap.add_argument('--r6', action='store_true'); ap.add_argument('--no-side-hub', action='store_true')\n    a = ap.parse_args()\n"
assert a in s
s = s.replace(a, "    ap.add_argument('--r6', action='store_true'); ap.add_argument('--no-side-hub', action='store_true')\n"
              "    ap.add_argument('--macro-vertical-pass', action='store_true', help='macros = node keep-outs that clock wires cross '\n"
              "                    'vertically only (macro OBS below the vertical clock layer; default: macros are wire walls)')\n"
              "    a = ap.parse_args()\n    global MACRO_VPASS\n    MACRO_VPASS = a.macro_vertical_pass\n")
p.write_text(s); print("patched")
