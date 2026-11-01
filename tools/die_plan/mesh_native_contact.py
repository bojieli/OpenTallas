"""Actual native M5 clock input contacts for a regular FIXED mesh.

Descriptors come from a transformed OpenDB ITerm plus actual TT/FF Liberty
clock roles and an explicit source contract. They never create boundary aliases.
"""
import math
from pathlib import Path
import sys
import clock_routed as C


def descriptor(iterm, libraries, source_contract, dbu=1000):
    from face_guard import clock_pins_from_liberties
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'clk'))
    from native_clock_source import physical_rect
    if dbu != C.DBU:
        raise ValueError('native contact requires actual ASAP7 1000 DBU/um')
    if set(libraries) != {'TT', 'FF'}:
        raise ValueError('native mesh contact needs actual TT and FF libraries')
    inst=iterm.getInst();master=inst.getMaster().getName();pin=iterm.getMTerm().getName()
    if (not isinstance(source_contract,dict) or not source_contract.get('source_identity') or not source_contract.get('scope')
            or source_contract.get('master')!=master or pin not in source_contract.get('clock_pins',[])):
        raise ValueError('native mesh contact lacks matching current source contract')
    for corner,path in libraries.items():
        if (master,pin) not in clock_pins_from_liberties([path]):
            raise ValueError(f'{corner}: native input is not actual Liberty clock:true: {master}/{pin}')
    if str(iterm.getMTerm().getIoType())!='INPUT':
        raise ValueError('native mesh contact must be an actual input ITerm')
    shapes=[s for p in iterm.getMTerm().getMPins() for s in p.getGeometry()
            if s.getTechLayer() and s.getTechLayer().getRoutingLevel()>0]
    if len(shapes)!=1 or shapes[0].getTechLayer().getName()!='M5':
        raise ValueError('native mesh contact supports one actual M5 rectangle')
    expected=source_contract.get('outline_um')
    actual=[inst.getMaster().getWidth()/dbu,inst.getMaster().getHeight()/dbu]
    if not expected or len(expected)!=2 or any(abs(a-b)>1e-6 for a,b in zip(expected,actual)):
        raise ValueError('native actual master outline differs from current source/plan contract')
    if not iterm.getNet():raise ValueError('native actual clock input is not connected to a net')
    shape=shapes[0];rect=[v/dbu for v in physical_rect(inst,shape)]
    if rect[2]-rect[0]<.032 or rect[3]-rect[1]<.224:
        raise ValueError('native M5 pin does not enclose the measured access stack')
    return dict(inst=inst.getName(),pin=pin,master=master,layer='M5',net=iterm.getNet().getName(),
                xy=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2],rect=rect,
                master_rect_dbu=[shape.xMin(),shape.yMin(),shape.xMax(),shape.yMax()],
                origin_dbu=list(inst.getOrigin()),orient=str(inst.getOrient()),
                source_contract=dict(source_contract),libraries={c:str(p)for c,p in libraries.items()})


def validate_descriptor(contact):
    from face_guard import clock_pins_from_liberties
    libs=contact.get('libraries',{});contract=contact.get('source_contract',{})
    if (set(libs)!={'TT','FF'} or not contract.get('source_identity') or not contract.get('scope')
            or contract.get('master')!=contact.get('master') or contact.get('pin')not in contract.get('clock_pins',[])):
        raise ValueError('native descriptor lacks actual typed clock libraries/current source contract')
    for corner,path in libs.items():
        if (contact['master'],contact['pin'])not in clock_pins_from_liberties([path]):
            raise ValueError(f'{corner}: native descriptor is not actual Liberty clock:true')
    # The emitter must not accept an invented global point beside a real ITerm.
    from types import SimpleNamespace as NS
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'clk'))
    from native_clock_source import physical_rect
    a,b,c,d=contact['master_rect_dbu']
    inst=NS(getOrigin=lambda:contact['origin_dbu'],getOrient=lambda:contact['orient'])
    shape=NS(xMin=lambda:a,yMin=lambda:b,xMax=lambda:c,yMax=lambda:d)
    rect=[v/C.DBU for v in physical_rect(inst,shape)]
    xy=[(rect[0]+rect[2])/2,(rect[1]+rect[3])/2]
    if any(abs(a-b)>1e-6 for a,b in zip(rect,contact['rect']))or any(abs(a-b)>1e-6 for a,b in zip(xy,contact['xy'])):
        raise ValueError('native descriptor point differs from actual transformed pin metal')
    if not contract.get('outline_um')or len(contract['outline_um'])!=2:
        raise ValueError('native descriptor lacks current source/plan outline')
    if any(any(c in name for c in '{}\n\r\t')for name in[contact['inst'],contact['pin'],contact['master']]):
        raise ValueError('native clock name cannot be represented exactly in Tcl')


def access_path(contact):
    """M8/M9 PG-gap approach, M7/M6 escape, M5 landing inside the native bar."""
    validate_descriptor(contact)
    if contact['layer']!='M5':raise ValueError('unsupported native clock input layer')
    layer,ax,ay=contact['anchor'];px,py=contact['xy'];pg=contact['pg'];pitch=float(pg['pitch_um']);ox,oy=pg['origin_um']
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'clk'))
    from mesh_form import snap_gap
    gapx=lambda v:snap_gap(v-ox,pitch)+ox
    gapy=lambda v:snap_gap(v-oy,pitch)+oy
    sx=gapx(px)+float(contact.get('gap_offset',0))*pitch;row=gapy(py)
    pts=[(layer,ax,ay)]
    if layer=='M8':
        if ay!=row:pts += [('M8',sx,ay),('M9',sx,ay),('M9',sx,row),('M8',sx,row)]
        else:pts.append(('M8',sx,row))
    elif layer=='M9':pts += [('M9',ax,row),('M8',ax,row)]
    else:raise ValueError('native mesh anchor must be actual M8/M9 conductor')
    # Step away from the native X so the M6 run always exceeds minimum area.
    ex=sx-math.copysign(C.STEP['M8'],px-sx)
    dy=row-py;sign=1 if dy>=0 else -1
    ey=py+sign*C.STEP['M5'] if abs(dy)>=C.STEP['M7']+C.STEP['M5'] else py-sign*C.STEP['M5']
    pts += [('M8',ex,row),('M7',ex,row),('M7',ex,ey),('M6',ex,ey),('M6',px,ey),('M5',px,ey),('M5',px,py)]
    pts=[(l,round(x,4),round(y,4))for l,x,y in pts]
    pts=[p for i,p in enumerate(pts)if not i or p!=pts[i-1]]
    rect=contact['rect']
    if not(rect[0]+.016<=px<=rect[2]-.016 and rect[1]+.016<=ey<=rect[3]-.016):
        raise ValueError('native access landing leaves actual M5 pin metal')
    for a,b in zip(pts,pts[1:]):
        if a[0]==b[0] and a[0]in('M8','M9'):
            normal=(a[2]-oy)if a[0]=='M8'else(a[1]-ox)
            clearance=pg['width_um'][a[0]]/2+pg['wire_width_um']/2+pg['spacing_um']
            if min(normal%pitch,pitch-normal%pitch)<clearance-1e-8:
                raise ValueError('native upper contact clips actual PG spacing')
    return pts


def validate_tcl(contact,net):
    """Reject a stale descriptor against actual loaded placement/master/metal."""
    validate_descriptor(contact)
    i,p,m=contact['inst'],contact['pin'],contact['master'];x,y=contact['origin_dbu'];o=contact['orient']
    width,height=[C.q(v)for v in contact['source_contract']['outline_um']]
    a,b,c,d=contact['master_rect_dbu']
    placement='[[$nic getMaster] getName] ne {%s} || [[$nic getMaster] getWidth]!=%d || [[$nic getMaster] getHeight]!=%d || [$nic getOrient] ne {%s} || [$nic getOrigin] ne {%d %d}'%(m,width,height,o,x,y)
    geometry='[$sh getTechLayer] ne "NULL" && [[$sh getTechLayer] getName] eq "M5" && [$sh xMin]==%d && [$sh yMin]==%d && [$sh xMax]==%d && [$sh yMax]==%d'%(a,b,c,d)
    return ['set ni [IT {%s} {%s}]'%(i,p), 'set nic [$ni getInst]',
            'if {'+placement+'} {error {stale native clock placement/master}}',
            'if {[$ni getNet] ne [$blk findNet {%s}]} {error {native clock input is not on actual mesh net}}'%net,
            'set native_shape_found 0',
            'foreach mp [[$ni getMTerm] getMPins] {foreach sh [$mp getGeometry] {',
            'if {'+geometry+'} {set native_shape_found 1}',
            '}}', 'if {!$native_shape_found} {error {actual native clock pin geometry changed}}']
