"""Prebuild clock placement origins obey native CKINVDCx16 body and existing halos.
Reject DME elongation candidates that snap repeaters beyond existing450um rule.
No clock target, margins, pins, PG or functional cycles are changed.
"""
def install(D,width=1.62,height=.27,repeat_limit=450.):
 base=D.SiteMap
 class BodySiteMap(base):
  def __init__(self,P,halo=2.16,bucket=250.):
   super().__init__(P,halo=halo,bucket=bucket)
   self.parts=[(a,b,c-width,d-height) for a,b,c,d in self.parts]
   self.forb=[(r[0]-width,r[1]-height,*r[2:]) for r in self.forb]
   self.idx={}
   for k,r in enumerate(self.forb):
    for i in range(int(r[0]//bucket),int(r[2]//bucket)+1):
     for j in range(int(r[1]//bucket),int(r[3]//bucket)+1):self.idx.setdefault((i,j),[]).append(k)
 D.SiteMap=BodySiteMap
 original=D.chain_ps
 def safe_chain_ps(pts):
  if any(D._man(a,b)>repeat_limit+1e-6 for a,b in zip(pts,pts[1:])):return float('inf')
  return original(pts)
 D.chain_ps=safe_chain_ps
 return {'native_clock_body_um':[width,height],'repeater_limit_um':repeat_limit}
