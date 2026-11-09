import sys,re
def pp(lines, defs):
    out=[]; st=[]  # (active, taken)
    for l in lines:
        s=l.strip()
        m=re.match(r'`(ifdef|ifndef|elsif)\s+(\w+)',s)
        if s.startswith('`ifdef') or s.startswith('`ifndef'):
            par=all(a for a,_ in st); c=(m.group(2) in defs)^(m.group(1)=='ifndef'); st.append((par and c, c)); continue
        if s.startswith('`elsif'):
            a,t=st.pop(); par=all(x for x,_ in st); c=(m.group(2) in defs) and not t; st.append((par and c, t or c)); continue
        if s.startswith('`else'):
            a,t=st.pop(); par=all(x for x,_ in st); st.append((par and not t, True)); continue
        if s.startswith('`endif'): st.pop(); continue
        if all(a for a,_ in st): out.append(l)
    return out
f,defs=sys.argv[1],set(sys.argv[2:])
sys.stdout.writelines(pp(open(f).readlines(),defs))
