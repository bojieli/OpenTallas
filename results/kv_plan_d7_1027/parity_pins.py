"""KV-PLAN-DELTA-7 diagnostic: FT station abstract pins on ONE layer by bit parity (even M4, odd M6), matching the face-pin
alternation, instead of the stacked M4+M5 squares; models a planned 50/50 M4/M6 layer split of every FT bundle."""
import re,sys
src,dst=sys.argv[1:3]
L=open(src).read(); n=[0,0]
def fix(m):
    name,bit,body=m.group(1),int(m.group(2)),m.group(3)
    r=re.search(r"LAYER M4 ;\s+RECT (\S+) (\S+) (\S+) (\S+) ;",body)
    x0,y0,x1,y1=map(float,r.groups()); cx,cy=(x0+x1)/2,(y0+y1)/2
    if bit%2==0: lay,hw,hh="M4",0.012,0.012; n[0]+=1
    else: lay,hw,hh="M6",0.016,0.016; n[1]+=1
    port=f"    PORT\n      LAYER {lay} ;\n        RECT {cx-hw:.4f} {cy-hh:.4f} {cx+hw:.4f} {cy+hh:.4f} ;\n    END\n"
    body2=re.sub(r"    PORT\n.*?    END\n",port,body,count=1,flags=re.S)
    return f"  PIN {name}[{bit}]\n{body2}  END {name}[{bit}]"
L2=re.sub(r"  PIN (ot_s_ft\d+_\d+_[dq])\[(\d+)\]\n(.*?)  END \1\[\2\]",fix,L,flags=re.S)
open(dst,"w").write(L2); print("M4",n[0],"M6",n[1])
