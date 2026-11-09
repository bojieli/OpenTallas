import re,sys
# usage: vm_shell.py IN OUT [mutant]  -- drop every ot_hbm_face_nreg output stage; the posedge u_bout face register drives the port
t=open(sys.argv[1]).read()
pat=re.compile(r'^\s*\(\* keep \*\) ot_hbm_face_nreg #\(\.W\((\d+)\)\) (u_bout_\w+?)__nl \(\.clk\(clk\), \.d\((\w+)__fl\), \.q\((\w+)\)\);\s*$',re.M)
m=pat.findall(t); assert len(m)==10, len(m)
def rep(x):
    return "    assign %s = %s__fl; // HBM-OPEN-B vE: half-cycle lockup stage removed (latency +0)"%(x.group(4),x.group(3))
t=pat.sub(rep,t)
if len(sys.argv)>3:  # mutant: bypass one posedge output face register
    pm=re.compile(r'\(\* keep \*\) ot_hbm_face_reg #\(\.W\(281\)\) u_bout_writer_kq3 \(\.clk\(clk\), \.d\((\w+)\), \.q\((\w+)\)\);')
    assert len(pm.findall(t))==1
    t=pm.sub(lambda x:'assign %s = %s;'%(x.group(2),x.group(1)),t)
open(sys.argv[2],'w').write(t)
print(len(m),[a[3] for a in m][:10])
