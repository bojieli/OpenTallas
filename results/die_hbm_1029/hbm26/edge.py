import json,sys
plan=json.load(open(sys.argv[1])); T=plan['partition_types']; P={p['name']:p for p in plan['partitions']}
def rect(n):
    p=P[n]; w,h=T[p['type']]['outline_um']
    if p.get('orient','R0') in ('R90','R270','MXR90','MYR90'): w,h=h,w
    x,y=p['origin_um']; return (x,y,x+w,y+h)
ports=plan['ports']
def edge(a,b):
    A,B=rect(a),rect(b)
    if abs(A[2]-B[0])<.5 or abs(B[2]-A[0])<.5: return max(0,min(A[3],B[3])-max(A[1],B[1]))
    if abs(A[3]-B[1])<.5 or abs(B[3]-A[1])<.5: return max(0,min(A[2],B[2])-max(A[0],B[0]))
    return 0
for a,b in [("NE_hub","NE_su01"),("NE_hub","NE_su00"),("NE_hub","NE_su21"),("NE_hub","NE_su20"),("NE_b010","NE_su00"),("NE_hub","NE_b000"),("NE_su30","NE_b100"),("NE_su30","NE_su31"),("NE_hub","NW_hub"),("NW_hub","root"),("NE_hub","root")]:
    L=edge(a,b); used=sum(p['width'] for p in ports if {p['src']['part'],p['dst']['part']}=={a,b})
    print(f"{a}|{b}: edge {L:.1f} um, cap {L*6:.0f} pins (6/um), used {used} b")
