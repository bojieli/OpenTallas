#!/usr/bin/env python3
"""QR-TAIL1 10-21: qfd_dv_s8_station_tail1 scale multiplier, one extra pipeline cut (SCALE_LAT 6 -> 7).

All four routed tail1 variants (t1a/t1b @5de01e82f, pfxa/pfxb @423018c29) failed TT setup only (-58..-85 ps) on the same
class: g_sc[*].u_mul.g_exact.u_d, the LAST stage of the LAT=6 bf16-scale mul (round-increment AND chain -> XNOR ->
encode OR-reduction -> y/err flop, ~27 cells, 1.06 ns at SS).  This tool appends module
qfd_dv_s8s_station_mul_data_g7 = the generated qfd_dv_s8s_station_mul_data_g with a register level cut through the
middle of the combinational cone of its output flops (the flops that drive y / err):

  level(net) = longest comb depth from any flop Q / ring q / module input (cells: one assign or one comb instance = 1)
  every comb edge u -> v in that cone with level(u) <= L < level(v), and every output-flop D/R pin fed at level <= L,
  reads a registered copy of u (qfd_s8s_bmath_dff_p, kept copies <= PER loads each, NATIVE32).

Levels rise strictly along every path, so every flop -> output-flop path crosses the cut exactly once: the netlist is
the same function with exactly one more edge of latency on y / err (valid ring D 6 -> 7 in mul_bounded LAT==7).
Asserts: no cone cell above the cut feeds anything outside the cone (no duplicated logic needed)."""
import re,math,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
F=R/'rtl/qwen_dv/s5/s8/qfd_dv_s8_station_math_g.sv'
SRC,DST='qfd_dv_s8s_station_mul_data_g','qfd_dv_s8s_station_mul_data_g7'
OUTPINS=('Q','Y','q','y')
NET=r'\bn_\d+(?:_[gs]\d+)*\b'
PER=10
FRAC=float(sys.argv[1]) if len(sys.argv)>1 else 0.5

def main():
    src=F.read_text()
    if f'module {DST}(' in src:
        a=src.index(f'// QR-TAIL1 CUT BEGIN');b=src.index('// QR-TAIL1 CUT END')+len('// QR-TAIL1 CUT END\n')
        src=src[:a]+src[b:]
    a=src.index(f'module {SRC}(');b=src.index('endmodule',a)+len('endmodule')
    lines=src[a:b].split('\n')
    inst_re=re.compile(r'^((?:\(\*.*?\*\) )?)(\w+) (#\(.*?\) )?(u_\w+)\((.*)\);$')
    # nodes: id -> (ins, outs, kind)
    nodes=[];drv={}
    out_nets=set()
    for i,l in enumerate(lines):
        if l.startswith('assign '):
            lhs,rhs=l[7:].rstrip(';').split('=',1)
            lhs=lhs.strip()
            if lhs in ('y','err'):
                out_nets|=set(re.findall(NET,rhs));continue
            ins=re.findall(NET,rhs);outs=re.findall(NET,lhs)
            if not ins:  # module inputs / clk
                for n in outs:drv[n]=('src',i)
                continue
            nodes.append((i,ins,outs,'comb'))
            continue
        im=inst_re.match(l)
        if not im:continue
        typ=im[2];pins=re.findall(r'\.(\w+)\(([^()]*)\)',im[5])
        ins=[n for p,v in pins if p not in OUTPINS and p not in ('C','clk','rst_n') for n in re.findall(NET,v)]
        outs=[n for p,v in pins if p in OUTPINS for n in re.findall(NET,v)]
        seq=('dff' in typ) or ('ring' in typ)
        nodes.append((i,ins,outs,'seq' if seq else 'comb'))
    for k,(i,ins,outs,kind) in enumerate(nodes):
        for n in outs:drv[n]=(kind,k)
    # levels
    lev={}
    sys.setrecursionlimit(100000)
    def L(n):
        if n in lev:return lev[n]
        d=drv.get(n)
        if d is None or d[0] in ('src','seq'):lev[n]=0;return 0
        k=d[1];v=1+max([L(x) for x in nodes[k][1]]+[0]);lev[n]=v;return v
    for n in list(drv):L(n)
    # output flops
    oflops=[k for k,(i,ins,outs,kind) in enumerate(nodes) if kind=='seq' and set(outs)&out_nets]
    assert oflops
    for k in oflops:assert 'dff' in lines[nodes[k][0]],lines[nodes[k][0]][:120]
    cone=set()
    st=[n for k in oflops for n in nodes[k][1]]
    while st:
        n=st.pop()
        d=drv.get(n)
        if d is None or d[0]!='comb' or d[1] in cone:continue
        cone.add(d[1]);st+=nodes[d[1]][1]
    dmax=max(lev[n] for k in oflops for n in nodes[k][1])
    cut=max(1,int(round(dmax*FRAC)))
    # cone cells above the cut must only feed cone cells / output flops
    users={}
    for k,(i,ins,outs,kind) in enumerate(nodes):
        for n in ins:users.setdefault(n,[]).append(k)
    oset=set(oflops)
    for k in cone:
        for n in nodes[k][2]:
            if lev[n]>cut:
                for u in users.get(n,[]):
                    dead=nodes[u][3]=='comb' and not any(users.get(o) or o in out_nets for o in nodes[u][2])
                    assert dead or u in cone or u in oset,('above-cut net leaves cone',n,lines[nodes[u][0]][:120])
                assert n not in out_nets
    # edges to register: (consumer node k, net u)
    reg={}  # net -> list of (node,count)
    for k in list(cone)+oflops:
        i,ins,outs,kind=nodes[k]
        clev=lev[outs[0]] if kind=='comb' else 10**9
        if clev<=cut:continue
        for n in ins:
            if lev[n]<=cut:reg.setdefault(n,[]).append(k)
    # kept copies: <= PER consumer references per copy
    newlines=list(lines);wires=[];regs=[];rid=2000000
    plan={}
    for n,ks in sorted(reg.items(),key=lambda x:x[0]):
        refs=len(ks);c=math.ceil(refs/PER);per=math.ceil(refs/c)
        names=[f'{n}_p{j}' for j in range(c)]
        wires+=names
        for nm in names:
            regs.append(f'(* keep_hierarchy="yes" *) qfd_s8s_bmath_dff_p #(.ID({rid})) u_p{rid}(.C(n_2),.D({n}),.Q({nm}));');rid+=1
        plan[n]=(names,per,[0])
    def subst(k,txt):
        def f(mo):
            n=mo.group(0)
            if n in plan and k in reg[n]:
                names,per,seen=plan[n];j=min(seen[0]//per,len(names)-1);seen[0]+=1;return names[j]
            return n
        return re.sub(NET,f,txt)
    for k in set(k for ks in reg.values() for k in ks):
        i=nodes[k][0];l=lines[i]
        if l.startswith('assign '):
            lhs,rhs=l.split('=',1);newlines[i]=lhs+'='+subst(k,rhs)
        else:
            newlines[i]=re.sub(r'\.(\w+)\(([^()]*)\)',lambda mo:mo[0] if mo[1] in OUTPINS or mo[1] in ('C','clk','rst_n') else '.'+mo[1]+'('+subst(k,mo[2])+')',l)
    for n,(names,per,seen) in plan.items():assert seen[0]==len(reg[n]),(n,seen[0],len(reg[n]))
    body='\n'.join(newlines).replace(f'module {SRC}(',f'module {DST}(',1)
    w0=body.index('\nwire ')
    body=body[:w0]+'\nwire '+', '.join(wires)+';'+body[w0:]
    e=body.rindex('endmodule')
    body=body[:e]+'\n'.join(regs)+'\n'+body[e:]
    hdr=(f'// QR-TAIL1 CUT BEGIN (tools/qwen_dv/gen_s8_mul_cut.py: {SRC} + one level cut at depth {cut}/{dmax} of the '
         f'output-flop cone; {len(reg)} nets, {len(regs)} cut registers, kept copies <= {PER} loads)\n')
    src=src.rstrip('\n')+'\n'+hdr+body+'\n// QR-TAIL1 CUT END\n'
    F.write_text(src)
    print(f'CUT depth {cut}/{dmax} cone_cells {len(cone)} out_flops {len(oflops)} cut_nets {len(reg)} cut_regs {len(regs)}')
if __name__=='__main__':main()

def apply_station():
    """mul_bounded: LAT==7 -> mul_data_g7 + valid ring D=7 (LAT==6 branch kept); tail1 SCALE_LAT default 6 -> 7."""
    S8=R/'rtl/qwen_dv/s5/s8'
    p=S8/'qfd_dv_s8_station_safe.sv';s=p.read_text()
    old=("generate if(LAT==6 && DRST==0) begin:g_exact\nqfd_dv_s8s_station_mul_data_g u_d(.clk(clk),.rst_n(rst_n),.a(a),.b(b),.y(y),.err(err));\n"
         "if(CV) begin:g_v qfd_dv_s8s_ring_delay #(.W(1),.D(6),.ID(ID)) u_v(.clk(clk),.rst_n(rst_n),.d(valid_in),.q(valid_out));end else begin:g_nv assign valid_out=0;end\n")
    new=old+("end else if(LAT==7 && DRST==0) begin:g_exact\n// QR-TAIL1: +1 edge, encode cut (gen_s8_mul_cut.py)\nqfd_dv_s8s_station_mul_data_g7 u_d(.clk(clk),.rst_n(rst_n),.a(a),.b(b),.y(y),.err(err));\n"
             "if(CV) begin:g_v qfd_dv_s8s_ring_delay #(.W(1),.D(7),.ID(ID)) u_v(.clk(clk),.rst_n(rst_n),.d(valid_in),.q(valid_out));end else begin:g_nv assign valid_out=0;end\n")
    if 'mul_data_g7' not in s:
        assert s.count(old)==1;p.write_text(s.replace(old,new))
    p=S8/'qfd_dv_s8_station_tail1.sv';s=p.read_text()
    old='    parameter integer SCALE_LAT = 6,'
    if old in s:p.write_text(s.replace(old,'    parameter integer SCALE_LAT = 7,       // QR-TAIL1 10-21: scale mul encode cut (+1 result edge)',1))
if __name__=='__main__' and len(sys.argv)>2 and sys.argv[2]=='station':apply_station()
