import csv,re,json,sys
from collections import defaultdict
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
K="kits"; g="M9w672_p70_SU"; x0,y0=26352,9504; bg=0.5823
def rd(d):
  o=defaultdict(float)
  for n in ("VDD","VSS"):
    for r in csv.DictReader(open(d+"/ir_%s.csv"%n)):
      v=float(r["Voltage"]); o[r["Instance"]]+=(v if n=="VSS" else 0.7-v)*1e3
  return o
S,A,F=[rd(f"{K}/{c}/{g}/psm") for c in "SAF"]
import numpy as np
M=np.zeros((69,69))
for k in S:
  i,j=map(int,re.match(r"u_b(\d+)_(\d+)",k).groups()); M[j,i]=S[k]+bg*(A[k]+F[k])
fig,ax=plt.subplots(figsize=(8,7))
im=ax.imshow(M,origin="lower",extent=[0,2972.16,0,2972.16],cmap="inferno"); plt.colorbar(im,label="upper colo mV (S own + bg 0.5823)")
cores=json.load(open("cores.json"))["cores"]
col={"qfd_dv_s5_su8_rst3":"cyan","qfd_dv_s8x_prog":"lime","qfd_dv_s8x_vmr":"white","qfd_dv_s8x_crh":"yellow","qfd_dv_s8x_btab":"magenta"}
for c in cores:
  r=c["rect"]
  if r[2]<x0 or r[0]>x0+2972 or r[3]<y0 or r[1]>y0+2972: continue
  ax.add_patch(Rectangle((r[0]-x0,r[1]-y0),r[2]-r[0],r[3]-r[1],fill=False,ec=col.get(c["module"],"grey"),lw=1))
b=[(m[1],float(m[2]),float(m[3])) for m in re.finditer(r"^ot_pad (\S+) \d+ (\S+) (\S+)",open(f"{K}/S/{g}/psm/bumps.tcl").read(),re.M)]
for n,x,y in b: ax.plot(x,y,"+" if n=="VDD" else "x",color="deepskyblue" if n=="VDD" else "red",ms=4)
ax.add_patch(Rectangle((450,450),2072,2072,fill=False,ec="white",ls="--"))
ax.set_title("QC SU window (sl_E4 su_c) upper deck M9.672/150um: su8 cyan, prog lime, vmr white, crh yellow, btab magenta\n+ VDD bump, x VSS bump; dashed = canonical interior",fontsize=8)
plt.savefig("su_window_upper.png",dpi=110); 
ax.set_xlim(1300,2100); ax.set_ylim(950,1750); plt.savefig("su_window_upper_zoom.png",dpi=110)
