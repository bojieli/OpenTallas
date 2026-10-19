import json
from pathlib import Path
from openroad import Design,Tech
tech=Tech();design=Design(tech)
design.readDb('/src/results/asap7/opentallas_qfd_coll_face_s1_safe_asap7_ref_gate/base/1_synth.odb')
block=design.getBlock()
insts={i.getName():i for i in block.getInsts()}
def sequential(i):return i.getMaster().getName().startswith('DFF')
def area(i):return i.getMaster().getWidth()*i.getMaster().getHeight()/1e6
seeds={g:[] for g in ('TX','RX','CONTROL')}
for name,i in insts.items():
    if not sequential(i) or 'u_codec.u_ctl.' not in name:continue
    n=name.replace('\\','').split('u_codec.u_ctl.',1)[1]
    if n.startswith(('q_pin[','p_tx_flit[','p_tx_v$','s1[','s2[','s3[','s4[','v1$','v2$','v3$','v4$','g_phy_pin.')):g='TX'
    elif n.startswith(('rf[','rx_flit[','rx_v$','rv$','ev$','es[','re[')):g='RX'
    else:g='CONTROL'
    seeds[g].append(i)
result={}
for g,ff in seeds.items():
    comb={};boundary=set();stack=[]
    for i in ff:
        stack.extend(it.getNet() for it in i.getITerms() if it.getMTerm().getName()=='D' and it.getNet())
    seen=set()
    while stack:
        net=stack.pop()
        if net.getName() in seen:continue
        seen.add(net.getName())
        for it in net.getITerms():
            if it.getIoType()!='OUTPUT':continue
            driver=it.getInst();name=driver.getName()
            if sequential(driver) or driver.getMaster().isBlock():
                boundary.add(name);continue
            if name in comb:continue
            comb[name]=driver
            stack.extend(q.getNet() for q in driver.getITerms() if q.getIoType()=='INPUT' and q.getSigType() not in ('POWER','GROUND') and q.getNet())
    result[g]=dict(flops=len(ff),flop_area_um2=sum(area(i) for i in ff),
        combinational_cells=len(comb),combinational_area_um2=sum(area(i) for i in comb.values()),
        combinational_cell_areas_um2={n:area(i) for n,i in comb.items()},unique_comb_instances=sorted(comb),source_boundary_instances=sorted(boundary),flop_instances=[i.getName() for i in ff])
Path('/work/cones_synth.json').write_text(json.dumps(result,indent=1))
for g,r in result.items():print(g,r['flops'],r['flop_area_um2'],r['combinational_cells'],r['combinational_area_um2'])
