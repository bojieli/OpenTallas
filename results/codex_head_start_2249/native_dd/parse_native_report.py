import json,re
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-head-start-2249');rows=[]
for corner in ('TT','FF'):
    text=(r/(corner+'3')/'run.log').read_text();assert 'NATIVE_REPORT_DONE' in text
    mode=edge=None;blocks=[];current=None
    for line in text.splitlines():
        if line.startswith('NATIVE_CASE '):
            if current:blocks.append(current);current=None
            _,mode,edge=line.split()
        elif line.startswith('Startpoint: '):
            if current:blocks.append(current)
            current=dict(mode=mode,edge=edge,lines=[line])
        elif current:current['lines'].append(line)
    if current:blocks.append(current)
    assert len(blocks)==8,(corner,len(blocks))
    for b in blocks:
        lines=b['lines'];ep=next(x.split(': ',1)[1].split()[0] for x in lines if x.startswith('Endpoint:'))
        pts=[]
        for line in lines:
            m=re.match(r'\s*([-\d.]+)\s+([-\d.]+)\s+([\^v]?)\s*(.*)',line)
            if m:pts.append((float(m[2]),m[4]))
        origin=next(a for a,n in pts if n.startswith('cland_tstart_in (in)'))
        target=next(a for a,n in pts if n.startswith(ep+'/D ('))
        cclock=next(a for a,n in pts if n.startswith(ep+'/CLK ('))
        roots=[(a,n) for a,n in pts if re.fullmatch(r'clock clk \((rise|fall) edge\)',n)]
        assert len(roots)==1,(corner,ep,roots)
        rows.append(dict(corner=corner,mode=b['mode'],signal_edge=b['edge'],endpoint=ep+'/D',
                         port_to_D_ps=round(target-origin,6),
                         capture_clock_insertion_ps=round(cclock-roots[0][0],6)))
summary={}
for corner in ('TT','FF'):
    for ep in sorted({q['endpoint'] for q in rows}):
        a=[q['port_to_D_ps'] for q in rows if q['corner']==corner and q['endpoint']==ep]
        summary[corner+':'+ep]=dict(min_ps=min(a),max_ps=max(a))
out=dict(schema='head_native_start_pin_delay/1',type='hd_mesh_e',source='die-head-34 mesh_e r3 actual6_final.odb+SPEF',
         source_signed=False,scope='actual native first-sync port-to-D component; no die phase or sign-off claim',
         constraints='existing signoff_r3fwd clock/IO; reported edges separately',rows=rows,summary=summary)
(r/'native_delay.json').write_text(json.dumps(out,indent=1));print(json.dumps(summary,indent=1))
