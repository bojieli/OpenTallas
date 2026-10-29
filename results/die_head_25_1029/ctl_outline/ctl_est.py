import json,math
d=json.load(open('hk4.json')); t=d['partition_types']['hd_ctl']
face={}
for b in t['buses']: face[b['face']]=face.get(b['face'],0)+b['width']
for s in t['ft_slots']:
    face[s["in_face"]]=face.get(s["in_face"],0)+s["width"]; face[s["out_face"]]=face.get(s["out_face"],0)+s["width"]
nwin={}
for b in t['buses']: nwin[b['face']]=nwin.get(b['face'],0)+1
for s in t['ft_slots']: nwin[s["in_face"]]=nwin.get(s["in_face"],0)+1; nwin[s["out_face"]]=nwin.get(s["out_face"],0)+1
STD=70508.119-4*171.288*77.784; MAC=4*171.288*77.784
g=8.64; up=lambda x: math.ceil(x/g-1e-9)*g
print('face bits',face,'windows',nwin,'std %.0f macro %.0f'%(STD,MAC))
def row(name,Wd,Ht,note):
    A=Wd*Ht; print('%-34s %7.2f x %7.2f  area %8.0f  fill_total %.3f  std_free_fill %.3f  macro%% %.1f  %s'%(name,Wd,Ht,A,(STD+MAC)/A,STD/(A-MAC),100*MAC/A,note))
row('slot (current)',1442.88,1226.88,'')
row('CTLX 216x233.28 (HBM number)',216,233.28,'INFEASIBLE: area < 4 SRAM' if 216*233.28<MAC else '')
for dens,lay in ((6,2),(6,4)):
    per=dens*lay/2   # budget face_pins_per_um is per layer pair? report both readings
    W_full=up((face['W'])/ (dens*lay/2) +10*nwin['W']); S=up(face['S']/(dens*lay/2)+10*nwin['S']); N=face['N']/(dens*lay/2)
    W_noft=up((face['W']-1026)/(dens*lay/2)+10*(nwin['W']-2))
    print(f'-- {dens} pins/um x {lay} layers: W needs {W_full:.1f} (no w3 ft {W_noft:.1f}), S {S:.1f}, N {N:.1f}')
    w=max(S,up(2*171.288+2*8.64))
    row(f'B1 keep ft, {lay}L',w,max(W_full,up(2*77.784+20)),'')
    row(f'B2 ft+n_tx moved off ctl, {lay}L',w,max(W_noft,up(2*77.784+20)),'')
