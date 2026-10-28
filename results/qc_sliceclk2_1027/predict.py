"""QC-SLICECLK-2 analytic prediction: per-slice balanced tree, OCV on unshared branches with the shared model
(main clk_aocv.branch_pessimism + APPROVED g021 table), for intra-slice related pairs and slice landing crossings."""
import json,sys,math
sys.path.insert(0,sys.argv[1]); import clk_aocv as CA
T=json.load(open(sys.argv[1]+"/clk_aocv_table_g021.json"))["clock_aocv"]
PS_MM={"TT":199.4}            # measured: stock QC die_trial tree, 405-um BUFx24 stages, fit over 7,121 taps (OWN)
PS_MM["FF"]=PS_MM["TT"]*T["classes"]["A"]["FF"]["mu_stage_ps"]/T["classes"]["A"]["TT"]["mu_stage_ps"]
REP=0.405
def br(L,corner):
    u=L*PS_MM[corner]; fc=T["classes"]["A"][corner]["cell_share"]
    return dict(cell_ps=fc*u,net_ps=(1-fc)*u,stages={"A":max(1,round(L/REP))}),u
def pess(La,Lb,d_mm,corner,check,same):
    a,_=br(La,corner); b,_=br(Lb,corner)
    return CA.branch_pessimism(T,corner,a,b,d_mm*1000,same,check)
W=2.471; H=26.266
rows=[]
def tree_path(h,w): return h/2+w/2     # ideal equal-length bisection path (root -> leaf), mm
print("form | domain h mm | root->leaf mm | ins TT ns | worst intra pair (root split): unshared/side mm, setup pess TT ps (droop 0 / +5.1%), hold pess FF ps (0/+5.1%)")
for k in (1,2,3):
    h=H/k; L=tree_path(h,W); d=math.hypot(h/2,W)
    s0=pess(L,L,d,"TT","setup",True); s1=pess(L,L,d,"TT","setup",False)
    h0=pess(L,L,d,"FF","hold",True); h1=pess(L,L,d,"FF","hold",False)
    print(f"K={k} | {h:.2f} | {L:.2f} | {L*PS_MM['TT']/1000:.2f} | {L:.2f}, {s0:.0f}/{s1:.0f}, {h0:.0f}/{h1:.0f}")
print()
print("landing crossing (neighbour slices, sl_fe->sl_fw near slice centre): unshared = internal path both sides + top feed segment")
for k in (1,2,3):
    h=H/k; L=tree_path(h,W)
    for feed,fl in (("H-tree top (neighbours split at die root, ~15.6 mm)",15.6),("forwarded chain/spine (split at neighbour tap, 2.47 mm)",W)):
        La=L+fl; Lb=L; d=math.hypot(W*2,h/2)
        p_tt=max(pess(La,Lb,d,"TT","setup",False),pess(Lb,La,d,"TT","setup",False))
        p_ff=max(pess(La,Lb,d,"FF","setup",False),pess(Lb,La,d,"FF","setup",False))
        uns=(La+Lb)*PS_MM["TT"]/1000
        print(f"K={k} {feed}: unshared {La:.1f}+{Lb:.1f} mm = {uns:.2f} ns TT; phase damage TT {p_tt:.0f} / FF {p_ff:.0f} ps vs window 416.5 (margin {416.5-p_tt:.0f}, nominal |d| excluded)")
print()
print("top feed = shared horizontal spine (common point) at the sl band; nominal arrivals balanced -> unshared = slice insertions only")
for k,L1,L2,lab in ((1,14.37,14.37,"K=1 slice<->slice"),(3,3.92,3.92,"v3 sl-band<->sl-band (sl domain 5.36 mm)")):
    d=math.hypot(2*W,1.0)
    for c in ("TT","FF"):
        p=max(pess(L1,L2,d,c,"setup",False),pess(L2,L1,d,c,"setup",False))
        print(f"{lab} {c}: unshared {(L1+L2)*PS_MM['TT']/1000:.2f} ns TT, damage {p:.0f} ps; margin vs 416.5 after 80 ps nominal target = {416.5-80-p:.0f}")
