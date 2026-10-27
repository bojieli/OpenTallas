import re, sys, os
src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
def parse(p):
    L = open(p).read().split('\n')
    s = next(i for i,l in enumerate(L) if l.startswith('module lec_top'))
    e = next(i for i in range(s, len(L)) if L[i].startswith('endmodule'))
    inst = [l for l in L[s:e] if re.match(r'\s+ot_s81hd_tile_p_(old|new)\b', l)]
    return '\n'.join(L[:s]), inst
gpre, gi = parse(f'{src}/gold.sv'); tpre, ti = parse(f'{src}/gate.sv')
assert len(gi) == len(ti) == 264
nm = lambda l: re.search(r'\)\s+(\w+)\s*\(|_new\s+(\w+)\s*\(', l)
for a, b in zip(gi, ti):
    na = re.search(r'\s(t\w+)\s\(', a).group(1); nb = re.search(r'\s(t\w+)\s\(', b).group(1); assert na == nb, (na, nb)
def top(insts, base):
    k = len(insts)
    hdr = f"""module lec_top (
    input wire clk, input wire clk_t1, input wire clk_t2, input wire clk_t3, input wire clk_t4, input wire clk_t5,
    input wire arst_n,
    output wire [{k}-1:0][0:0] rst_o_0, output wire [{k}-1:0][0:0] rst_o_1,
    output wire [{k}-1:0][0:0] rst_o_2, output wire [{k}-1:0][0:0] rst_o_3,
    input wire [565:0] i,
    output wire [{k}-1:0][565:0] o
);"""
    body = []
    for j, l in enumerate(insts):
        idx = base + j
        l2 = l
        for p in ['rst_o_0','rst_o_1','rst_o_2','rst_o_3','o']:
            l2, c = re.subn(rf'\.{p}\({p}\[{idx}\]\)', f'.{p}({p}[{j}])', l2); assert c == 1, (p, idx, l)
        body.append(l2)
    return hdr + '\n' + '\n'.join(body) + '\nendmodule\n'
ys = open(f'{src}/lec.ys').read()
for c in range(0, 264, n):
    d = f'{out}/c{c:03d}'; os.makedirs(d, exist_ok=True)
    open(f'{d}/gold.sv','w').write(gpre + '\n' + top(gi[c:c+n], c))
    open(f'{d}/gate.sv','w').write(tpre + '\n' + top(ti[c:c+n], c))
    open(f'{d}/lec.ys','w').write(ys.replace(f'{src}/', f'{d}/').replace('/srv/opentallas-scratch2/claude/hb4_lec/all/', f'{d}/'))
# mutant: chunk 0 copy with first strap_row0 value +1
d = f'{out}/mut_strap'; os.makedirs(d, exist_ok=True)
g = gpre + '\n' + top(gi[0:n], 0); t = tpre + '\n' + top(ti[0:n], 0)
t2, k = re.subn(r"strap_row0\(17'd(\d+)\)", lambda m: f"strap_row0(17'd{int(m.group(1))+1})", t, count=1); assert k == 1
open(f'{d}/gold.sv','w').write(g); open(f'{d}/gate.sv','w').write(t2)
open(f'{d}/lec.ys','w').write(ys.replace('/srv/opentallas-scratch2/claude/hb4_lec/all/', f'{d}/'))
print('chunks', len(range(0,264,n)))
