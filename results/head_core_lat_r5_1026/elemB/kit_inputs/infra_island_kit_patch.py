import re,sys
D,old,new,short=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),sys.argv[4]
g=new-old
io=open(D+'/io.tcl').read().splitlines()
pins=open(D+f'/island_{short}_pins.tcl').read().splitlines()
out=['# HEAD-CORE-LAT 10-26: outline %.3f -> %.3f (lattice), E/N face pins +%.3f, clk/rst_n on the infra-island hole edge'%(old,new,g)]
n=0
for ln in io:
    m=re.match(r'place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{(\S+) (\S+)\}(.*)',ln)
    if not m: out.append(ln); continue
    name,lay,x,y,rest=m.group(1),m.group(2),float(m.group(3)),float(m.group(4)),m.group(5)
    if name in ('clk','rst_n'): continue
    if x>old-1.0: x+=g
    if y>old-1.0: y+=g
    out.append('place_pin -pin_name {%s} -layer %s -location {%.4f %.4f}%s'%(name,lay,x,y,rest)); n+=1
out+=pins
open(D+'/io.tcl','w').write('\n'.join(out)+'\n')
print('pins',n,'+2 island')
c=open(D+'/config.mk').read()
c=re.sub(r'export DIE_AREA = .*','export DIE_AREA = 0 0 %.3f %.3f'%(new,new),c)
c=re.sub(r'export CORE_AREA = .*','export CORE_AREA = 4.32 4.32 %.3f %.3f'%(new-4.32,new-4.32),c)
open(D+'/config.mk','w').write(c)
mp=open(D+'/macro_place.tcl').read()
if 'INFRA_ISLAND' not in mp:
    open(D+'/macro_place.tcl','w').write(mp+'\n'+open(D+f'/island_{short}.tcl').read())
