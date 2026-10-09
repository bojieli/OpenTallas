"""Source-pinned native R25I placement and full-shape endpoint pin plans.

The endpoint contract is a reservation until service/controller wrapper bindings
and measured timing are supplied. Historical R25 remains replayable.
"""
import json
from pathlib import Path


def install(m, fp):
    from hbm_indexer_r25i_model import hbm_indexer_r25i_physical_model
    root = fp.ROOT / 'physical/hbm_accel_die_views/index/native'
    master = 'hfd_idx_score_native_c2' if m['variant'].get('indexer_large_slot') else 'hfd_idx_score_native'
    scores = {}
    fixed = m.setdefault('fixed_ports', {})
    def add(name, mn, x, y, orient, kind):
        rec = json.loads((root / mn / 'ports.json').read_text())
        it = fp.Inst(name, mn, x, y, rec['w_um'], rec['h_um'], orient,
                     kind=kind, region='hub', domain='stream_1p2')
        m['insts'].append(it)
        def pins(mst, k=1, rec=rec):
            spec, order = {}, []
            for pn, port in rec['ports'].items():
                ps = port['pins']; first, last = ps[0], ps[-1]
                x0,y0=(first[2]+first[4])/2,(first[3]+first[5])/2
                if pn in ('ck','rst'):
                    spec[pn]=('area', 'M7', x0,y0,0.064,0.288)
                else:
                    face=port['face']; along0=y0 if face in 'WE' else x0
                    along1=(last[3]+last[5])/2 if face in 'WE' else (last[2]+last[4])/2
                    pitch=round((along1-along0)/(len(ps)-1)/0.048) if len(ps)>1 else 2
                    spec[pn]=('face',len(ps),face,port['layer'],
                              along0+len(ps)*pitch*0.048/2,pitch)
                order.append(pn)
            if k>1:
                fp._bundle_pack(mst,spec,order,k)
            mst.ports,mst.order=spec,order
        fixed[mn]=pins
        m.setdefault('master_notes',{})[mn]='Full-shape native indexer; exact and physical verdicts tracked separately'
        return it
    h=json.loads((root/master/'ports.json').read_text())['h_um']
    g=m['geo']
    # Reserve inner side bands outside all eight stack SM footprints. Origins
    # align to the M7 mirrored pin lattice and the 2.16um placement row lattice.
    for st,group in m['groups'].items():
        side,half=st
        x=10732.608 if half=='W' else 16994.88
        y=1596.24 if side=='S' else round(g['H']-1596.24-h,6)
        orient={'SW':'R0','SE':'MY','NW':'MX','NE':'R180'}[st]
        scores[st]=add('idx_score_'+st,master,x,y,orient,'hub')
    sel=add('idx_selector','hfd_idx_sel',14164.416,17169.84,'R0','spine')
    m['indexer_native']=dict(scores=scores, selector=sel,
        model=hbm_indexer_r25i_physical_model(),
        qualification='OPT_IN_NATIVE_RESERVATION; service joins and whole-die routing not yet qualified')
    m['notes'].append('R25I reserves four full16-lane scorers and captured-SRAM T1/LA7 selector; historical placeholder key/top-k nets require replacement before adoption.')
