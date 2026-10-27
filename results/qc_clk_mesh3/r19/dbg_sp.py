import sys, json
sys.argv=["x","solve","--r2","inputs/d43/r2_plan_d43.json","--stage","inputs/stage_table.json","--lanes","vss","--islands","type","--feed","periodic","--island-edge-sym","--row-at","10471.68=10445.76,5227.2=5218.56","--lift-lane","deepest","--row-slots","holder","--centre-channel","43.2","--centre-split","30.24","--top-w","16w","--top-m","2","--top-reach","450","--thev","inputs/thev_r2.json","--slew-sens","inputs/slew_sens.json","--r9-dir","r10_inputs","--corner","TT","--sample","0","--out","/tmp/x.json"]
import qc_clk_mesh3 as M
import argparse
ap=argparse.ArgumentParser(); 
# reuse main parser
p=None
orig=M.cmd_solve
def grab(a):
    st=M.Stage(a.stage); B=M.build(a,st)
    print("keys",sorted(B.keys()))
    print("gaps",len(B["gaps"]),B["gaps"][:10],B["gaps"][-3:])
    print("scols",len(B["scols"]),B["scols"][:10])
    print("cols",len(B["cols"]),B["cols"][:5],B["cols"][-2:])
    sd=[tuple(n["xy"]) for n in B["spine_drv"]]; print("spine_drv",len(sd),sd[:5])
    st_=[tuple(ct["tap"]) for ct in B["ctrees"]]; print("ctaps",len(st_),st_[:5])
    G=set(B["gaps"]); S=set(B["scols"])
    off=[q for q in sd+st_ if q[1] not in G and q[0] not in S]
    print("off",len(off),off[:10])
    ys=sorted({q[1] for q in st_}); print("ctap ys",len(ys),ys[:12])
    xs=sorted({q[0] for q in st_}); print("ctap xs",len(xs),xs[:12])
    return 0
M.cmd_solve=grab
M.main(sys.argv[1:])
