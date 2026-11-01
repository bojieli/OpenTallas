# DIE-HEAD-50: wire new type tap inputs clk_tA..clk_tB to the instance region clock in s81_head_top.sv (as DH48 l47v did for hd_st_turn)
import re,sys
f=sys.argv[1]; mods={m.split(":")[0]:(int(m.split(":")[1]),int(m.split(":")[2])) for m in sys.argv[2:]}
s=open(f).read(); out=[]; n=0
pat=re.compile(r"^(\s*)(\w+)\s+(?:#\([^;]*?\)\s*)?(\w+)\s*\(", re.M)
lines=s.split("\n"); i=0; cur=None
while i<len(lines):
    L=lines[i]; m=re.match(r"^\s*(ot_s81hd_\w+)\b",L)
    if m: cur=m.group(1) if m.group(1) in mods else None
    out.append(L)
    if cur:
        mm=re.match(r"^(\s*)\.clk_t(\d+)\((clk_region_\w+)\),\s*$",L)
        nxt=lines[i+1] if i+1<len(lines) else ""
        if mm and not re.match(r"^\s*\.clk_t\d+\(",nxt):
            a,b=mods[cur]; assert int(mm.group(2))==a-1,(cur,L)
            for k in range(a,b+1): out.append(f"{mm.group(1)}.clk_t{k}({mm.group(3)}),"); n+=1
            cur=None
    i+=1
open(f,"w").write("\n".join(out)); print("added",n)
