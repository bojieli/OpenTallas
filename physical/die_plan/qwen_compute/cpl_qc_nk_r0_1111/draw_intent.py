"""CPL-QC-NK-R0: hand-drawn intent arrangement (SVG) of cbn_q11 before (s21) / after (s22): NK tiles, data-pin edge
(red), tap/ck edge (blue), bc column (middle channel), the RTL NK chain as arrows labelled with depth and macro
crossings.  usage: draw_intent.py OUT.svg"""
import sys
S = 0.28                      # px per um
W, H = 1235.52, 2540.16
TILES = {"u_t22": (86.4, 69.12), "u_t32": (691.2, 69.12), "u_t23": (86.4, 1304.64), "u_t33": (691.2, 1304.64)}
TW, TH = 457.92, 1157.76
Y = {"n_a": 750, "n_b": 851, "n_y": 1052, "t_out": 951}
LINKS = [("u_t22", "t_out", "u_t32", "n_a", "D3"), ("u_t32", "n_y", "u_t23", "n_a", "D10"),
         ("u_t23", "t_out", "u_t33", "n_a", "D3"), ("u_t33", "n_y", "u_t23", "n_b", "D3"),
         ("u_t32", "t_out", "u_t32", "n_b", "D3+r8"), ("u_t33", "t_out", "u_t33", "n_b", "D3+r8")]
def panel(ox, orients, title, out):
    def X(x): return ox + 40 + x * S
    def Yp(y): return 60 + (H - y) * S
    out.append(f'<text x="{ox+40}" y="30" font-size="15" font-weight="bold">{title}</text>')
    out.append(f'<rect x="{X(0)}" y="{Yp(H)}" width="{W*S}" height="{H*S}" fill="#f7f7f2" stroke="#333"/>')
    out.append(f'<rect x="{X(617.76)}" y="{Yp(H)}" width="{(706.94-617.76)*S}" height="{H*S}" fill="#dfe9f7" opacity="0.6"/>')
    out.append(f'<text x="{X(560)}" y="{Yp(1265)}" font-size="9">bc column (bc_i32 S / bc_o33 N), stations u_xstn32/33</text>')
    def pin(i, port):
        ox_, oy_ = TILES[i]; r0 = orients[i] == "R0"
        x = ox_ + (0.096 if r0 else 457.824) if port != "tap" else ox_ + (457.824 if r0 else 0.096)
        return x, oy_ + (Y.get(port, 610))
    for i, (x0, y0) in TILES.items():
        out.append(f'<rect x="{X(x0)}" y="{Yp(y0+TH)}" width="{TW*S}" height="{TH*S}" fill="#e8d9c4" stroke="#7a5a30"/>')
        r0 = orients[i] == "R0"
        dx = x0 if r0 else x0 + TW
        tx = x0 + TW if r0 else x0
        out.append(f'<line x1="{X(dx)}" y1="{Yp(y0+700)}" x2="{X(dx)}" y2="{Yp(y0+1103)}" stroke="#c0392b" stroke-width="5"/>')
        out.append(f'<line x1="{X(tx)}" y1="{Yp(y0+561)}" x2="{X(tx)}" y2="{Yp(y0+675)}" stroke="#2c6fbb" stroke-width="5"/>')
        out.append(f'<text x="{X(x0+150)}" y="{Yp(y0+400)}" font-size="13">{i} {orients[i]}</text>')
    for a, pa, b, pb, d in LINKS:
        (x1, y1), (x2, y2) = pin(a, pa), pin(b, pb)
        ch = lambda i: (0 if orients[i] == "R0" else 1) if TILES[i][0] < 400 else (1 if orients[i] == "R0" else 2)
        c = abs(ch(a) - ch(b))
        col = {0: "#1e8449", 1: "#d68910", 2: "#c0392b"}[c]
        if a == b:
            x1 -= 0 if orients[a] == "R0" else 0
        out.append(f'<line x1="{X(x1)}" y1="{Yp(y1)}" x2="{X(x2)}" y2="{Yp(y2)}" stroke="{col}" stroke-width="2.5" marker-end="url(#ah)"/>')
        out.append(f'<text x="{(X(x1)+X(x2))/2+4}" y="{(Yp(y1)+Yp(y2))/2-4}" font-size="10" fill="{col}">{a[2:]}.{pa}&#8594;{b[2:]}.{pb} {d} x{c}</text>')
    for i in ("u_t32", "u_t33"):   # station tap feed
        x, y = pin(i, "tap"); c = 0 if orients[i] == "MY" else 1
        out.append(f'<line x1="{X(662)}" y1="{Yp(y)}" x2="{X(x)}" y2="{Yp(y)}" stroke="#2c6fbb" stroke-width="1.5" stroke-dasharray="5,3" marker-end="url(#ah)"/>')
        out.append(f'<text x="{X(700)}" y="{Yp(y)+12}" font-size="9" fill="#2c6fbb">xstn tap_d 508b x{c}</text>')
out = ['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="820" font-family="sans-serif">',
       '<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#333"/></marker></defs>',
       '<rect width="900" height="820" fill="white"/>']
panel(0, dict(u_t22="R0", u_t32="MY", u_t23="MY", u_t33="MY"), "BEFORE s21: cbn_q11 (t32/t33 MY)", out)
panel(440, dict(u_t22="R0", u_t32="R0", u_t23="MY", u_t33="R0"), "AFTER s22: t32/t33 R0", out)
out.append('<text x="40" y="800" font-size="11">red edge = NK data pins (n_a/n_b/t_out/n_y), blue edge = tap/ck/rst_n/tile_id. '
           'Arrow colour/xN = NK macro widths crossed (green 0, orange 1, red 2). Dashed = station tap feed.</text>')
out.append('</svg>')
open(sys.argv[1], "w").write("\n".join(out))
