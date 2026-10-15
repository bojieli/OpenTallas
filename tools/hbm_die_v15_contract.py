#!/usr/bin/env python3
"""Generate actual v15 VM/staging contracts and common-clock station RTL.

Unknown producer/consumer ports remain explicit failures. This cannot emit a
native-complete die from legacy direction guesses or pin-only masters.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import hbm_die_views as views
import hbm_die_station_gen as stations

ROOT = Path(__file__).resolve().parents[1]
VM_SOURCE = 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv'
DELIVERY = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_vm_delivery.sv'
LG_SOURCE = 'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_split.sv'
# Real static VM clients (fixed compiler cycles, no credit/ready). Each binds only
# where its source documents the exact VM face it was built and benched against.
SFU_SOURCE = 'rtl/hbm_accel/generic/peers/ot_hgi_sfu_scheduled_engine.sv'      # LG mid tap 14/11
DBK_SOURCE = 'rtl/hbm_accel/generic/peers/static/ot_hgi_dma_back_static.sv'    # direct RG, bank n+1/n+7
IDX_SOURCE = 'rtl/hbm_accel/index/ot_hbm_idx_scheduled_static.sv'              # direct RG, bank n+1/n+7
ATT_PV_SOURCE = 'rtl/hdc/v41x/static/ot_hbm_attn_pv_native_output_quad_local.sv'  # D local PV (owner-approved 10-15)
SU_SOURCE = 'rtl/hbm_accel/generic/adapters/static_su/ot_hbm_su_static_vm_ports.sv'  # LG near tap 10/7, 4 bank-pair groups
SID = ('SW','SE','NW','NE')


def generate(out):
    abi_path=ROOT/'results/arch/hbm_vm_static_1014/quadrant_abi.json'
    abi=json.loads(abi_path.read_text())
    modules={}; sources={}
    def module(name,path,top,params=None):
        p=ROOT/path
        parsed=views.L.parse_module(path,top,params or {})['ports']
        modules[name]=dict(master=top,source=path,params=params or {},ports={k:dict(direction=d,bits=w) for k,(d,w) in parsed.items()})
        sources[path]=hashlib.sha256(p.read_bytes()).hexdigest()
    for q, rec in abi['quadrants'].items():
        module('hb_vms_'+q,VM_SOURCE,rec['master'])
        actual=modules['hb_vms_'+q]['ports']
        expected={p['name']:dict(direction=p['direction'],bits=p['bits']) for p in rec['ports']}
        assert actual==expected,(q,'source/ABI drift')
        module('delivery_'+q,DELIVERY,'ot_hbm_svc_static_vm_delivery')
    module('hb_ckgen','rtl/hbm_accel/control/hfd_ckgen.sv','hfd_ckgen')
    service_contract=ROOT/'physical/hbm_accel_die_views/svc/v15/contract.json'
    service=None
    if service_contract.exists():
        service=json.loads(service_contract.read_text())
        for rec in service['instances']:
            top=rec['actual_module']
            module(rec['instance'],'physical/hbm_accel_die_views/svc/v15/rtl/'+top+'.sv',top)
            assert modules[rec['instance']]['ports']==service['actual_module_port_tables'][top]['ports']
        for q in abi['quadrants']:
            module('phy_'+q,'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5_bb.v',
                   'ot_hbm3e_phy_v41x_aw30_e8p5')
    calendar_source='rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv'
    if (ROOT/calendar_source).exists():
        for q in abi['quadrants']:
            module('calendar_'+q,calendar_source,'hfd_hgi_vm_calendar_'+q)
            for stage in range(3):
                # Adopted physical successor (23d5fd409/7da6141d7): eight independently
                # clocked bank leaves, same edge/phase and latency as the logical tap.
                module(f'lg_{q}_{stage}',LG_SOURCE,'ot_hbm_vm_lg_static_split',
                       dict(READ_RETURN=10+4*stage,WRITE_RETURN=7+4*stage))
    status_source='rtl/hbm_accel/generic/vm/static/ot_vms_status4_static.sv'
    if (ROOT/status_source).exists():module('vm_status4',status_source,'ot_vms_status4_static')
    coll_source='rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_static.sv'
    if (ROOT/coll_source).exists():
        for q in abi['quadrants']:module('hb_coll_'+q,coll_source,'ot_hfd_coll_q3_static' if q=='SW' else 'ot_hfd_coll_q2_static')
    for q in abi['quadrants']:
        module('hb_sfu_'+q,SFU_SOURCE,'ot_hgi_sfu_scheduled_engine',dict(PAGE_AW=1,AW=11,LWB=15))
        module('hb_dbk_'+q,DBK_SOURCE,'ot_hgi_dma_back_static',dict(STK=SID.index(q)))
        # SW/SE NPG 5: die-lead BANK_GROUP map, PROVISIONAL bank7 alone (0x43221100, = H-ELEM-B vehicle map)
        # until GEO-H confirms against the RG5 bank pin readback.
        swse=q in ('SW','SE')
        module('hb_su_'+q,SU_SOURCE,'ot_hbm_su_static_vm_ports',dict(QID=SID.index(q),READ_RETURN=10,WRITE_RETURN=7,
               NPG=5 if swse else 4,BANK_GROUP=0x43221100 if swse else 0x33221100))
    module('hb_idx',IDX_SOURCE,'ot_hbm_idx_scheduled_static')
    module('hb_attn_pv',ATT_PV_SOURCE,'ot_hbm_attn_pv_native_output_quad_local',dict(ACTIVE_HEADS=16))
    edges=[]; connected=set(); parts={}; logical_constants=[]
    def edge(name,src,dst):
        sm,sp=src; dm,dp=dst
        a=modules[sm]['ports'][sp];b=modules[dm]['ports'][dp]
        assert a['direction']=='output' and b['direction']=='input' and a['bits']==b['bits'],(name,a,b)
        edges.append(dict(name=name,bits=a['bits'],source=list(src),sink=list(dst),
                          clock='stream',ready_or_credit=False))
        connected.update((tuple(src),tuple(dst)))
    def slice_edge(name,src,dst,width):
        sm,sp,lo=src;dm,dp,dlo=dst
        a=modules[sm]['ports'][sp];b=modules[dm]['ports'][dp]
        assert a['direction']=='output' and b['direction']=='input'
        assert lo>=0 and lo+width<=a['bits'] and dlo>=0 and dlo+width<=b['bits'],(name,a,b,width)
        used=parts.setdefault((dm,dp),set())
        assert not used.intersection(range(dlo,dlo+width)),(name,'multiple drivers')
        edges.append(dict(name=name,bits=width,source=[sm,sp,lo,lo+width],sink=[dm,dp,dlo,dlo+width],
                          clock='stream',ready_or_credit=False))
        for end,low,rec in ((src,lo,a),(dst,dlo,b)):
            key=tuple(end[:2]);parts.setdefault(key,set()).update(range(low,low+width))
            if len(parts[key])==rec['bits']:connected.add(key)
    for q in abi['quadrants']:
        vm='hb_vms_'+q;cal='calendar_'+q;coll='hb_coll_'+q
        if cal in modules:
            for port,rec in modules[cal]['ports'].items():
                if rec['direction']=='output' and port in modules[vm]['ports']:
                    edge('calendar_'+q+'_'+port,(cal,port),(vm,port))
            for stage in range(3):
                tap=f'lg_{q}_{stage}'
                for port in ('read','write'):
                    slice_edge(f'{tap}_{port}_select',(cal,'lg_local_'+port,stage*8),(tap,'local_'+port,0),8)
                if stage==0:
                    slice_edge(tap+'_rq',(tap,'near_rq',0),(vm,'rq',0),136)
                    slice_edge(tap+'_wq',(tap,'near_wq',0),(vm,'wq',0),2248)
                    slice_edge(tap+'_rr',(vm,'rr',0),(tap,'near_rr',0),2056)
                    slice_edge(tap+'_w_done',(vm,'wq_done',0),(tap,'near_w_done',0),8)
                else:
                    near=f'lg_{q}_{stage-1}'
                    for suffix in ('rq','wq'):edge(tap+'_'+suffix,(tap,'near_'+suffix),(near,'far_'+suffix))
                    edge(tap+'_rr',(near,'far_rr'),(tap,'near_rr'))
                    edge(tap+'_wdone',(near,'far_w_done'),(tap,'near_w_done'))
                if stage==2:
                    for port in ('far_rq','far_wq'):
                        logical_constants.append(dict(sink=[tap,port],bits=modules[tap]['ports'][port]['bits'],
                            value=0,reason='actual three-tap topology termination; no fourth producer',
                            physical_tie_cells_qualified=False))
                        connected.add((tap,port))
        if 'vm_status4' in modules:
            # Source ABI sid order SW,SE,NW,NE; do not confuse with ring order.
            index=('SW','SE','NW','NE').index(q)
            slice_edge('status_'+q,(vm,'vmstat',0),('vm_status4','quadrant_status',19*index),19)
        if coll in modules:
            group=3 if q.startswith('S') else 5
            assert abi['quadrants'][q]['params']['RG']>group,(q,'COLL native read-group expansion missing')
            slice_edge('coll_vm_rq_'+q,(coll,'vm_rq',0),(vm,'rq',136*group),136)
            slice_edge('coll_vm_rr_'+q,(vm,'rr',2056*group),(coll,'vm_rr',0),2056)
            edge('coll_vm_kq_'+q,(coll,'vm_kq'),(vm,'kq'))
    slice_bind={}
    for q in abi['quadrants']:
        vm='hb_vms_'+q;reads=abi['clients'][q]['read']
        # SFU: middle LG tap. Its bridge latency is the tap's measured 14/11 (source asserts).
        sfu='hb_sfu_'+q;tap=f'lg_{q}_1'
        assert modules[tap]['params']==dict(READ_RETURN=14,WRITE_RETURN=11)
        edge(sfu+'_rq',(sfu,'local_rq'),(tap,'local_rq'))
        edge(sfu+'_wq',(sfu,'local_wq'),(tap,'local_wq'))
        edge(sfu+'_rr',(tap,'local_rr'),(sfu,'local_rr'))
        edge(sfu+'_w_done',(tap,'local_w_done'),(sfu,'local_w_done'))
        # SU (H-ELEM-B db4f2facb): near tap, bank-pair port groups, returns 10/7 asserted.
        # Tap selects are owned only by the VM calendar (SU no longer drives them).
        su='hb_su_'+q;tap0=f'lg_{q}_0'
        assert modules[tap0]['params']==dict(READ_RETURN=10,WRITE_RETURN=7)
        assert modules[su]['params']['READ_RETURN']==10 and modules[su]['params']['WRITE_RETURN']==7
        edge(su+'_rq',(su,'lg_rq'),(tap0,'local_rq'))
        edge(su+'_wq',(su,'lg_wq'),(tap0,'local_wq'))
        edge(su+'_rr',(tap0,'local_rr'),(su,'lg_rr'))
        edge(su+'_w_done',(tap0,'local_w_done'),(su,'lg_w_done'))
        # DMA back: direct read group 'DMA back' at bank n+1/n+7 (source ABI).
        g=reads.index('DMA back');dbk='hb_dbk_'+q
        slice_edge(dbk+'_rq',(dbk,'rq',0),(vm,'rq',136*g),136)
        slice_edge(dbk+'_rr',(vm,'rr',2056*g),(dbk,'rr',0),2056)
        rec=slice_bind.setdefault(q,dict(read_groups={},write_groups={},records={}))
        rec['read_groups'].update({'0':'lg_%s_0..2 (SU hb_su_%s near / SFU hb_sfu_%s mid / HC far)'%(q,q,q),str(g):dbk})
        coll_g=reads.index('COLL');rec['read_groups'][str(coll_g)]='hb_coll_'+q
        rec['write_groups']['0']='lg_%s_0..2 (SU hb_su_%s/SFU hb_sfu_%s/HC)'%(q,q,q)
    # One INDEX parent (four internal scorers); its VM operand face reads SW (sid 0).
    g=abi['clients']['SW']['read'].index('IDX')
    slice_edge('idx_vm_rq',('hb_idx','vm_rq',0),('hb_vms_SW','rq',136*g),136)
    slice_edge('idx_vm_rr',('hb_vms_SW','rr',2056*g),('hb_idx','vm_rr',0),2056)
    slice_bind['SW']['read_groups'][str(g)]='hb_idx'
    logical_constants.append(dict(sink=['hb_idx','sid'],bits=2,value=0,
        reason='INDEX operand face reads the SW slice (sid order SW,SE,NW,NE)',physical_tie_cells_qualified=False))
    connected.add(('hb_idx','sid'))
    # D local PV (owner-approved floorplan direction 2026-10-15): PV staging is quadrant-local
    # (128 stores / 2048 32x128 macros, head order per quadrant), but the source has ONE
    # serializer output wq that commits to the NE slice's canonical 'attention' write group.
    g=abi['clients']['NE']['write'].index('attention')
    slice_edge('attn_pv_wq',('hb_attn_pv','wq',0),('hb_vms_NE','wq',2248*g),2248)
    slice_bind['NE']['write_groups'][str(g)]='hb_attn_pv'
    long_returns=[dict(name='attn_pv_wq (PV drain -> NE VM WG%d)'%g,bits_per_edge=2248,
        source='hb_attn_pv serializer (gathers SW/SE/NW/NE quad-local PV stores)',sink='hb_vms_NE wq group %d'%g,
        reason='VM ABI gives attention a write group on NE only (canonical WG1); D source has one serializer output',
        cost='OPEN: bit-um / relay stages / compiler edges for the non-NE quadrants pending GEO-H D2 corridor measurement',
        alternative='per-quadrant attention write group (WG+1 on SW/SE/NW, 4 serializer outputs): bank port/area cost vs removed long drain -> GEO-H + H-ATTQ to price',
        status='OPEN_LONG_RETURN')]
    for q in abi['quadrants']:
        reads=abi['clients'][q]['read'];rec=slice_bind[q]
        for i,name in enumerate(reads):
            rec['read_groups'].setdefault(str(i),'UNBOUND: no static producer for "%s"'%name)
        writes=abi['clients'][q]['write']
        for i,name in enumerate(writes):
            rec['write_groups'].setdefault(str(i),'UNBOUND: no static producer for "%s"'%name)
        for i,name in enumerate(abi['clients'][q]['records']):
            rec['records'][str(i)]='UNBOUND: record client "%s" has no static cq338/cr274 source'%name
    # Coordinator structural rule 2026-10-15 (GEO-H bank<->LG geometry): every SU/SFU/HC
    # engine exposes >=4 LG port groups per quadrant (one per bank pair; 5 on SW/SE) so
    # each LG link stays <500 um at the fixed tap return latencies. A single connection
    # point means 1.5-7.7 mm wires. Logical bus may stay one port; the PIN/leaf plan must
    # split it per bank pair (bits b*17/b*281/b*257 of banks 2k,2k+1 form group k).
    engine_rule=dict(rule='>=4 LG port groups per quadrant per engine (one per bank pair), 5 on SW/SE; every LG link <500 um',
        source='coordinator decision 2026-10-15 on GEO-H 7025b4f52 (el1011-hbmdie.log)',
        bank_pair_bits=dict(rq='[(2k)*17,(2k+2)*17)',wq='[(2k)*281,(2k+2)*281)',rr='[(2k)*257,(2k+2)*257)',w_done='[2k,2k+2)'),
        engines={})
    for q in abi['quadrants']:
        need=5 if q in ('SW','SE') else 4
        for stage,eng,owner in ((0,'SU','H-ELEM-B (static SU)'),(1,'SFU','SFU owner'),(2,'HC','HC/hbm_hard_physical owner')):
            inst={'SFU':'hb_sfu_'+q,'SU':'hb_su_'+q}.get(eng)
            engine_rule['engines'][f'{eng}_{q}']=dict(tap=f'lg_{q}_{stage}',instance=inst,owner=owner,
                required_port_groups=need,physical_port_groups=None,
                status='OPEN: no pin/leaf plan yet' if inst else 'OPEN: engine not yet bound in contract')
            if eng=='SU':
                rec=engine_rule['engines'][f'SU_{q}'];rec['physical_port_groups']=need
                rec['status']=('SOURCE MET (%d pg_clk groups, db4f2facb)%s; pins open'%(need,
                               '' if need==4 else ', BANK_GROUP 0x43221100 provisional (bank 7 alone) pending GEO-H RG5 readback'))
    qs=('SW','SE','NE','NW')
    for i,q in enumerate(qs):
        edge('ring_cw_'+q,('hb_vms_'+q,'cw_out'),('hb_vms_'+qs[(i+1)%4],'cw_in'))
        edge('ring_ccw_'+q,('hb_vms_'+q,'ccw_out'),('hb_vms_'+qs[(i-1)%4],'ccw_in'))
        if 'hb_coll_'+q in modules:
            edge('collective_cw_'+q,('hb_coll_'+q,'pr_cw_o'),('hb_coll_'+qs[(i+1)%4],'pr_cw_i'))
            edge('collective_ccw_'+q,('hb_coll_'+q,'pr_ccw_o'),('hb_coll_'+qs[(i-1)%4],'pr_ccw_i'))
        edge('service_dq_'+q,('delivery_'+q,'dq'),('hb_vms_'+q,'dq'))
    if service:
        for rec in service['instances']:
            name=rec['instance'];phy='phy_'+rec['quadrant'];pcs=rec['physical_pc_ids']
            assert pcs==list(range(pcs[0],pcs[-1]+1)),(name,'non-contiguous PC mapping needs explicit bit permutation')
            for field,width in service['phy']['pc_fields'].items():
                band=modules[name]['ports'][field];hard=modules[phy]['ports'][field]
                assert band['bits']==len(pcs)*width and hard['bits']==32*width
                assert {band['direction'],hard['direction']}=={'input','output'}
                band_end=[name,field];phy_end=[phy,field,pcs[0]*width,(pcs[-1]+1)*width]
                src,dst=(band_end,phy_end) if band['direction']=='output' else (phy_end,band_end)
                edges.append(dict(name=name+'_'+field,bits=len(pcs)*width,source=src,sink=dst,
                                  clock='hbm',ready_or_credit=field in ('k_rdy','kr_rdy'),
                                  allowed_exception='actual HBM PHY/controller boundary only'))
                connected.add((name,field))
        for q in abi['quadrants']:
            pcs=[p for rec in service['instances'] if rec['quadrant']==q for p in rec['physical_pc_ids']]
            assert sorted(pcs)==list(range(32)),(q,'duplicate or missing actual PHY PC')
            connected.update(('phy_'+q,f) for f in service['phy']['pc_fields'])
    roots=[]
    for name,mod in modules.items():
        if name=='hb_ckgen':continue
        for port,rec in mod['ports'].items():
            if port=='clk' or port.startswith('clk_') or port.endswith('_clk'):
                assert rec['direction']=='input'
                for bit in range(rec['bits']):
                    roots.append(dict(instance=name,port=port,bit=bit,source=['hb_ckgen','pll_stream'],
                                      physical_insertion_reference=None,status='NEEDS_REAL_CTS_VIEW'))
                    if name.startswith(('svc_','phy_')):roots[-1]['source']=['hb_ckgen','pll_hbm']
                connected.add((name,port))
            if port=='rst_n':
                connected.add((name,port))
    unresolved=[]
    for name,mod in modules.items():
        for port,rec in mod['ports'].items():
            if (name,port) in connected:continue
            if name=='hb_ckgen':
                if port in ('refclk','por_n'):continue # actual declared external bump boundary
                if port.startswith(('pll_','por_')):continue # other actual die domains; outside this subnet
            if name=='hb_attn_pv':
                owner='actual HG1 PV producer / attention drain calendar (H-ATTQ)'
            elif name.startswith('hb_su_'):
                owner='actual static SU arithmetic su_rq/su_wq producer (H-ELEM-B)'
            elif name.startswith('hb_sfu_'):
                owner=('actual SFU operand SRAM / SU join' if port.startswith(('vi_','ro_','side_','kv_'))
                       else 'actual SFU programme loader / CP and lane reset tree')
            elif name.startswith('hb_dbk_'):
                owner=('actual service WB band (static block reservation)' if port.startswith(('wb_','wd','wa'))
                       else 'actual static DMA dispatcher (cycle/move/issue_at/drain_at)')
            elif name=='hb_idx':
                owner=('actual service key staging (key_slot/key_index/key_lines)' if port.startswith('key_')
                       else 'actual COLL TopK injection' if port in ('tx','tx_v')
                       else 'actual INDEX programme loader / CP')
            elif port in ('cq','cr','rq','rr','wq','wq_done'):
                owner='actual static client source migration'
            elif port in ('vmstat','bank_status','hub_status','mirror_busy','ring_fault'):
                owner='actual four-quadrant status aggregate and CP consumer'
            elif name.startswith(('delivery_','svc_','phy_')):
                owner='actual PHY service band / compiler block command source'
            elif port in ('kq','kq_done'):
                owner='actual static COLL parent / VM writer'
            else:
                owner='actual VM programme SRAM calendar issuer'
            missing=sorted(set(range(rec['bits']))-parts.get((name,port),set()))
            ranges=[]
            for bit in missing:
                if ranges and ranges[-1][1]==bit:ranges[-1][1]=bit+1
                else:ranges.append([bit,bit+1])
            unresolved.append(dict(instance=name,port=port,**rec,required_owner=owner,
                bound_bits=rec['bits']-len(missing),unbound_bits=len(missing),
                unbound_ranges_half_open=ranges,status='UNBOUND_FAIL'))
    out.mkdir(parents=True,exist_ok=True)
    generated=[]
    # Same source-exact widths as the new eight ring edges and four staging
    # edges. A common-clock station is actual flop RTL, never an abstract stub.
    # Physical location, hop count and timing are deliberately NOT inferred.
    for width in (2224,2248):
        master=f'hfd_stn_v15_cc{width}'
        def port(direction,bits):
            return dict(direction=direction,bits=bits,dir_segments=[[0,bits,'in' if direction=='input' else 'out']])
        rec=dict(master=master,ports=dict(ck=port('input',1),rst=port('input',1),a=port('input',width),b=port('output',width)))
        emitter,role=stations.build(rec,{})
        mutant,_=stations.build(rec,{},mutant=True)
        (out/(master+'.sv')).write_text(stations.module_text(rec,emitter))
        (out/(master+'_mutant.sv')).write_text(stations.module_text(rec,mutant))
        (out/(master+'_ports.json')).write_text(json.dumps(rec,indent=1)+'\n')
        generated.append(dict(master=master,bits=width,role=role,latency_cycles=1,
                              sinks_per_root=width,physical_qualified=False,bench_qualified=False))
    dependency_hashes={}
    for directory in ('rtl/hbm_accel/generic/vm/static','rtl/hbm_accel/loader/service_native'):
        for dep in sorted((ROOT/directory).glob('*.sv')):
            dependency_hashes[str(dep.relative_to(ROOT))]=hashlib.sha256(dep.read_bytes()).hexdigest()
    report=dict(schema='opentallas.hbm.actual-v15-source-contract.v1',status='FAIL_UNBOUND_NATIVE_PORTS',
                source_sha256=sources,dependency_inventory_sha256=dependency_hashes,
                dependency_inventory_scope='all static VM/service RTL including benches; not a substitute for hierarchy elaboration',
                hierarchy_elaboration_required=True,
                service_qualification_rejections=service['qualification_rejections'] if service else [],
                abi_sha256=hashlib.sha256(abi_path.read_bytes()).hexdigest(),
                instances=modules,known_actual_edges=edges,clock_roots=roots,vm_slice_bind=slice_bind,
                engine_lg_port_group_rule=engine_rule,floorplan_direction='HBM D local PV (owner-approved 2026-10-15)',
                long_returns=long_returns,
                registered_station_masters=generated,logical_constant_requests=logical_constants,unbound_ports=unresolved,
                boundary_gaps=['actual 1.024ns PHY to 0.833333ns stream block CDC absent',
                               'actual mapped PHY address/endian/PC striping proof required',
                               'historical PC leaf rejected for address/clock semantics; actual block CDC replacement required'],
                unbound_count=len(unresolved),pin_only_placeholder_count=0,
                legacy_failures_disposition='77 legacy station failures remain historical; v15 validates actual source ports independently',
                qualification=dict(native_complete=False,pins=False,station_benches=False,clock_views=False,TT=False,FF=False,DRC=False),
                required_remaining=['actual client and programme command source joins','actual static COLL combined parent',
                                    'actual full service/SM/writeback composition','measured compact SM outline and all leaf views',
                                    'pin plans, physical registered stations and exact compiler stage counts','real-view die GRT0/TT/FF/DRC0'])
    (out/'contract.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(dict(actual_instances=len(modules),actual_edges=len(edges),clock_roots=len(roots),
                         unbound_ports=len(unresolved),station_masters=generated)))
    return report


def bench(out, report):
    tb=ROOT/'rtl/test/tb_hbm_v15_station.sv'
    tops=['hfd_stn_v15_cc2224','hfd_stn_v15_cc2248']
    receipt=dict(testbench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),
                 scope='source station mechanism only; no physical pin or timing qualification',runs=[])
    for mutant in (None,*tops):
        tag=mutant or 'positive'
        exe=out/(tag+'.vvp')
        files=[out/(top+('_mutant' if top==mutant else '')+'.sv') for top in tops]
        cmd=['iverilog','-g2012','-s','tb','-o',str(exe),str(tb),*map(str,files)]
        subprocess.run(cmd,check=True,capture_output=True,text=True)
        run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        log=run.stdout+run.stderr
        (out/(tag+'.log')).write_text(log)
        if mutant:
            assert run.returncode!=0 and 'station mismatch cycle=' in log,(tag,run.returncode,log)
        else:
            assert run.returncode==0 and 'V15_STATION PASS' in log,(run.returncode,log)
        receipt['runs'].append(dict(name=tag,exit=run.returncode,log=log,
            source_sha256={str(f.name):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}))
        exe.unlink()
    (out/'station_bench.json').write_text(json.dumps(receipt,indent=1)+'\n')
    for rec in report['registered_station_masters']:rec['bench_qualified']=True
    report['qualification']['station_benches']=True
    (out/'contract.json').write_text(json.dumps(report,indent=1)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--bench',action='store_true',help='run actual emitted station RTL and both bit-swap mutants')
    ap.add_argument('--inventory',action='store_true',help='allow explicit incomplete source inventory; default gate fails closed')
    args=ap.parse_args()
    report=generate(args.out)
    if args.bench:bench(args.out,report)
    raise SystemExit(0 if args.inventory else bool(report['unbound_count'] or report['boundary_gaps'] or report['logical_constant_requests']))
