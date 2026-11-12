# make the LCREP-off reference copy: every module of the file renamed *_REF, LCREP / LCMUT defaults forced 0
import sys,re
s=open(sys.argv[1]).read()
mods=re.findall(r"^\s*(?:\(\*[^)]*\*\)\s*)?module\s+(\w+)",s,flags=re.M)
for m in sorted(set(mods),key=len,reverse=True):
    s=re.sub(r"\b%s\b"%m,m+"_REF",s)
a=" LCREP=`ifdef OT_KSH_LCREP 1 `else 0 `endif,\n LCMUT=`ifdef OT_KSH_MUT_LCREP 1 `else 0 `endif)"
assert s.count(a)==1
s=s.replace(a," LCREP=0,\n LCMUT=0)")
open(sys.argv[2],"w").write(s)
print(sorted(set(mods)))
