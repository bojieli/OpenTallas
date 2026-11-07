#!/usr/bin/env python3
"""DIE-QC-87 vR3 (OWNER 11-07 03:29 conservative form) from a vR kit dir: mk_vr3.py SRC_KIT DST_KIT nl|nk
 density 0.40; reset tree 8/64/512 copies so OT_RST_COPIES_MAX 8 holds (vR 4/32/256 gave 12/10); macro channels with rows.
 NL: open the 4.32-um gap g_sl[4]|g_sl[1] (the 2-pin N-S 150-um slew nets had no row): right column g_sl[0,1,2] +8.64, g_sl[4,5] -8.64 -> 21.6 um (rows 12.96).
 NK: stacks abut 0.024 um at y~859: rows y 718.584 and y 859.008 move apart in 0.192 steps clear of the M6 PG bands; Y row halo 2.16.
 Physical kit has lec.py set aside; a sibling <DST>_lec kit (goal synth) carries the proof."""
import json,re,shutil,sys,os,subprocess
src,dst,t=sys.argv[1:4]
assert t in('nl','nk') and not os.path.exists(dst)
subprocess.check_call(['rsync','-a','--exclude=run','--exclude=lec','--exclude=lec_first','--exclude=signoff','--exclude=FAIL_PREFLOOR','--exclude=run_*.log','--exclude=.kwrs_done*',src+'/',dst+'/'])
def sub(path,pat,new,n=1):
    s=open(path).read(); s2,c=re.subn(pat,new,s,flags=re.M)
    if c!=n: sys.exit(f'{path}: {pat!r} matched {c}, expected {n}')
    open(path,'w').write(s2)
cfg=dst+'/config.mk'
sub(cfg,r'^export DESIGN_NICKNAME = .*$',f'export DESIGN_NICKNAME = kq_qfd_tile_{t}_a0c_vR3')
sub(cfg,r'^export PLACE_DENSITY = .*$','export PLACE_DENSITY = 0.40')
body=f'{dst}/rtl/qfd_tile_{t}_rp2_45.sv'
for a,b in (('reg [3:0] s1__ot_rl1v','reg [7:0] s1__ot_rl1v'),('reg [31:0] s2__ot_rl2v','reg [63:0] s2__ot_rl2v'),('reg [255:0] s3__ot_rl3v','reg [511:0] s3__ot_rl3v'),('{4{q}}','{8{q}}'),('{32{s1__ot_rl1v[0]}}','{64{s1__ot_rl1v[0]}}'),('{256{(RMUT','{512{(RMUT')):
    s=open(body).read(); assert s.count(a)==1,a; open(body,'w').write(s.replace(a,b))
MOVES={'nl':{'g_sl[0]':(8.64,0),'g_sl[1]':(8.64,0),'g_sl[2]':(8.64,0),'g_sl[4]':(-8.64,0),'g_sl[5]':(-8.64,0)},
       'nk':{k:(0,float(v)) for k,v in (a.split('=') for a in os.environ.get('NK_DY','').split(',') if a)}}[t]
if t=='nk':
    assert MOVES
    sub(cfg,r'^export MACRO_ROWS_HALO_Y = .*$','export MACRO_ROWS_HALO_Y = 2.16')
mp=dst+'/macro_place.tcl'; L=open(mp).read().split('\n'); done=set()
for i,l in enumerate(L):
    m=re.match(r'puts "hard child (\S+) -> \[\$i getName\] (\S+) at (\S+) (\S+) (.*)$',l)
    if not m or 'u_native_rawleaf' not in m.group(1): continue
    k=re.search(r'g_sl\[\d\]',m.group(1)).group(0)
    if k not in MOVES: continue
    j=i-1
    while 'setLocation' not in L[j] or 'round(' not in L[j]: j-=1
    ml=re.search(r'round\((\S+) \* \$dbu\).*round\((\S+) \* \$dbu\)',L[j])   # the setLocation is the real site (pinband moved y, the puts text is stale)
    x,y=float(ml.group(1)),float(ml.group(2)); nx,ny=round(x+MOVES[k][0],3),round(y+MOVES[k][1],3)
    L[j]=L[j].replace(f'round({ml.group(1)} * $dbu)',f'round({nx} * $dbu)').replace(f'round({ml.group(2)} * $dbu)',f'round({ny} * $dbu)')
    L[i]=l.replace(f' at {m.group(3)} {m.group(4)} ',f' at {nx} {ny} ')
    done.add(m.group(1))
assert len(done)==len(MOVES),done
open(mp,'w').write('\n'.join(L))
fz=json.load(open(dst+'/freeze.json')); n=0
for c in fz['hard_children']:
    if c['inst'] in done:
        k=re.search(r'g_sl\[\d\]',c['inst']).group(0); c['at']=[round(c['at'][0]+MOVES[k][0],3),round(c['at'][1]+MOVES[k][1],3)]; n+=1
assert n==len(done); json.dump(fz,open(dst+'/freeze.json','w'),indent=1)
open(dst+'/vB_FORM.txt','a').write(f'DIE-QC-87 vR3: density .40, reset copies 8/64/512, channels {MOVES}\n')
# proof sibling keeps lec.py; physical kit skips the inline LEC (2-3 h) and starts at once
lk=dst+'_lec'; subprocess.check_call(['rsync','-a',dst+'/',lk+'/'])
os.rename(dst+'/lec.py',dst+'/lec.py.in_sibling_lec_kit')
print('OK',t,MOVES)
