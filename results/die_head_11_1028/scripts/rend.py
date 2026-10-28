import re,sys,matplotlib
matplotlib.use("Agg");import matplotlib.pyplot as plt
t=open(sys.argv[1]).read()
c=[(float(a),float(b),n) for n,a,b in re.findall(r"place_inst -name (ck_\S+) -location \{([\d.]+) ([\d.]+)\}",t)]
p=[(float(a),float(b)) for a,b in re.findall(r"place_pin -pin_name t_\S+ -layer \w+ -location \{([\d.]+) ([\d.]+)\}",t)]
f,ax=plt.subplots(1,2,figsize=(16,8))
for a in ax:
    a.plot([0,17521.92,17521.92,0,0],[0,0,17556.48,17556.48,0],"k-",lw=.5)
    a.scatter([x for x,y,n in c if "_b" in n[:4]],[y for x,y,n in c if "_b" in n[:4]],s=4,c="b",label="node INV")
    a.scatter([x for x,y,n in c if "_r" in n[:4]],[y for x,y,n in c if "_r" in n[:4]],s=1,c="r",label="rep INV")
    a.scatter([x for x,y in p],[y for x,y in p],s=6,c="g",marker="^",label="taps")
ax[0].legend();ax[0].set_title(sys.argv[1]+f"  cells {len(c)} taps {len(p)}")
ax[1].set_xlim(2300,8000);ax[1].set_ylim(14500,16600);ax[1].set_title("zoom top rib")
plt.savefig(sys.argv[2],dpi=90)
