#!/usr/bin/env python3
"""Generate fail-closed S81 controller/OD boundary sheets from pinned Git objects.

No SDC emission, physical run, main-tree mutation, or dependency on tiled files
being checked out. The source commits must be available in this repository.
"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'results/rtl/s81_ph_20261006/boundary_bindings'

class Evidence:
    def __init__(self, repo, refs): self.repo,self.refs,self.pins=repo,refs,{}
    def read(self, key, path):
        rev=self.refs.get(key,key)
        b=subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=self.repo)
        self.pins[f'{rev}:{path}']=hashlib.sha256(b).hexdigest()
        return b
    def text(self,key,path): return self.read(key,path).decode()
    def json(self,key,path):
        b=self.read(key,path)
        return json.loads(gzip.decompress(b) if path.endswith('.gz') else b)

def module(s,name):
    s=re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
    m=re.search(r'\bmodule\s+'+re.escape(name)+r'\b(.*?)\bendmodule\b',s,re.S)
    if not m: raise ValueError(f'missing module {name}')
    return m.group(1)

def ports(s,name):
    header=module(s,name).split(');',1)[0]
    out={}
    pat=r'\b(input|output|inout)\s+(?:(?:wire|reg)\s+)?(?:\[(\d+)\s*:\s*(\d+)\]\s*)?(\w+)'
    for direction,hi,lo,n in re.findall(pat,header):
        out[n]=dict(port=n,dir=direction,bits=abs(int(hi)-int(lo))+1 if hi else 1)
    if not out:raise ValueError(f'no literal ANSI ports in {name}')
    return out

def groups(s,kind):
    # Balanced Liberty groups; quoted strings contain no braces in these sources.
    pat=re.compile(r'\b'+kind+r'\s*\(\s*(?:"([^"]*)"|([^)]*?))\s*\)\s*\{')
    for m in pat.finditer(s):
        depth=1;i=m.end()
        while depth:
            if i>=len(s): raise ValueError('unbalanced Liberty')
            depth+=(s[i]=='{')-(s[i]=='}');i+=1
        yield (m.group(1) if m.group(1) is not None else m.group(2)),s[m.end():i-1]

def arcs(lib,bases,widths=None):
    if not re.search(r'time_unit\s*:\s*"1ps"',lib):raise ValueError('unsupported time unit')
    result={}
    # Some PHY buses carry timing directly; routed ETM buses contain pin groups.
    # Count the latter through their pins only, avoiding a synthetic extra bus pin.
    direct_buses=[(n,b) for n,b in groups(lib,'bus') if not re.search(r'\bpin\s*\(',b)]
    for pin,body in list(groups(lib,'pin'))+direct_buses:
        base=pin.split('[')[0]
        if base not in bases:continue
        for _,tim in groups(body,'timing'):
            typ=re.search(r'timing_type\s*:\s*(\w+)',tim)
            rel=re.search(r'related_pin\s*:\s*"([^"]+)"',tim)
            if not typ or not rel or not typ[1].startswith(('hold_','setup_')):continue
            key=(base,typ[1],rel[1]);rec=result.setdefault(key,dict(port=base,timing_type=typ[1],related_pin=rel[1],pins=[],values=[]))
            nums=[]
            for v in re.findall(r'values\s*\((.*?)\)\s*;',tim,re.S):
                nums.extend(float(n) for n in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?',v))
            rec['pins'].extend([f'{pin}[{b}]' for b in range(widths[base])] if widths and '[' not in pin and base in widths else [pin]);rec['values'].extend(nums)
    return [dict(port=r['port'],timing_type=r['timing_type'],related_pin=r['related_pin'],pin_count=len(set(r['pins'])),
                 table_min_ps=min(r['values']),table_max_ps=max(r['values']),
                 use='Tabulated boundary constraints; select with actual slew. Routed ETMs include internal receiver clock paths.')
            for r in result.values()]

def check(sheets,expected):
    errors=[]
    for name,sh in sheets.items():
        pp={p['port']:p for p in sh['interfaces']}
        if set(pp)!=set(expected[name]):errors.append(f'{name}: port coverage')
        for n,p in pp.items():
            e=expected[name].get(n,{})
            for k in ['dir','bits','clock_domain','adjacent_endpoint','receiver_clock_arrival_ps']:
                if p.get(k)!=e.get(k):errors.append(f'{name}.{n}: {k}')
        if sh.get('policy') != dict(setup_uncertainty_ps=60,hold_uncertainty_ps=25,hold_io_ps=50,accept_ss_ps=15,accept_ff_ps=15):errors.append(f'{name}: policy changed')
        if any(v is not None for v in sh['budgets'].values()):errors.append(f'{name}: unmeasured budget')
        if sh.get('timing_ready') or sh.get('closure_claim'):errors.append(f'{name}: missing receiver evidence cannot authorize timing')
        if name=='dsfd_svcio_od' and sh['output_clock_relation'] != 'ck rising -> inverted of falling -> receiver fi0 falling':errors.append('OD capture polarity')
    return errors

def generate(e,case):
    base='rtl/dsrom_sys/s81_ph/'
    ctrl=e.text('tile',base+'ctrl/dsfd_ctrl_pc.sv')
    tiles=e.text('tile',base+'svc/ot_s81ph_svc_io_tiles.sv')
    svc=e.text('tile',base+'svc/dsfd_svc_pc.sv')
    stn=e.text('tile',base+'svc/dsfd_svc_stn.sv')
    top=e.text('tile',base+'dsfd_ctrl.sv')
    comp=e.json('tile','physical/s81_ph_views/ctrl/composition.json')
    sc=e.json('tile','physical/s81_ph_views/svc/composition.json')
    pinorder=e.json('tile','results/rtl/s81_ph_20261006/ctrl/phy_dfi_order.json')
    phy='physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5'
    meta=e.json('tile',phy+'.json')
    phyports=ports(e.text('tile',phy+'_bb.v'),'ot_hbm3e_phy_v41x_aw30_e8p5')
    cp,op,sp,tp=ports(ctrl,'dsfd_ctrl_pc'),ports(tiles,'dsfd_svcio_od'),ports(svc,'dsfd_svc_pc'),ports(stn,'dsfd_svc_stn')
    for connection in ['.rq(rq[g*341 +: 341])','.rk(rk[g])','.wd(wd[g])','.r_data(rd[g*256 +: 256])','.r_tag(rd[8192 + g*17 +: 17])','.r_beat(rd[8736 + g*4 +: 4])','assign rd[8895:8864] = rv;']:
        assert connection in top,connection
    phy_names=[n for n in cp if n.startswith(('k_','kr_'))]
    assert len([i for i in comp['instances'] if i['master']=='dsfd_ctrl_pc'])==32
    assert len([i for i in sc['instances'] if i['master']=='dsfd_svc_pc'])==32
    ci=pinorder.index('clk');assert re.search(r'assign\s+phy\['+str(ci)+r'\]\s*=\s*ckh\s*;',top)
    for n,p in cp.items():
        p['clock_domain']='hbm_clk' if n in phy_names or n=='ckh' else ('async_reset' if n=='rst' else 'core_clk')
        p['clock_port']='ckh' if p['clock_domain']=='hbm_clk' else ('cks' if n!='rst' else None)
        p['receiver_clock_arrival_ps']=None;p['timing_ready']=False
        if n in phy_names:
            assert phyports[n]['bits']==32*p['bits']
            assert phyports[n]['dir']!=p['dir']
            p['adjacent_endpoint']=dict(master=meta['name'],port=n,per_pc_slice_bits=p['bits'],clock='clk',edge='rising',
                clock_binding=f'dsfd_ctrl.ckh -> phy[{ci}] -> PHY.clk',evidence_grade='assumed IP boundary; exact logical mapping')
            # Validate literal bit mapping through the 22238-bit composition.
            for bit in range(32*p['bits']):
                nm=f'{n}[{bit}]';ix=pinorder.index(nm)
                lhs,rhs=(f'phy[{ix}]',f'p_{n}[{bit}]') if p['dir']=='output' else (f'p_{n}[{bit}]',f'phy[{ix}]')
                assert f'assign {lhs} = {rhs};' in top,(n,bit)
        elif n in ['rq','rk','wd','rv','r_data','r_tag','r_beat']:
            assert sp[n]['bits']==p['bits'] and sp[n]['dir']!=p['dir']
            p['adjacent_endpoint']=dict(master='dsfd_svc_pc',instance='u_pc[p]',port=n,clock='ck',edge='rising',evidence_grade='RTL plus declared composition; no assembled routed join')
        elif n.startswith(('ci_','co_')):
            p['adjacent_endpoint']=dict(master='dsfd_ctrl_pc / dsfd_ctrl_ctr / tie',mapping='co_w=co_e; PCs 0..15 chain west-to-centre, 31..16 east-to-centre; outer ci inputs tied 01; co_e unused in generated top',clock='cks',edge='rising')
        else:p['adjacent_endpoint']=None
    for n,p in op.items():
        p['clock_domain']='async_reset' if n=='rst' else ('forwarded_core_clk_inverted' if n=='of' else 'core_clk')
        p['clock_port']='ck' if n!='rst' else None;p['receiver_clock_arrival_ps']=None;p['timing_ready']=False
        if n in ['od','of']:
            p['adjacent_endpoint']=dict(master='dsfd_stnh_514x1',port='di0' if n=='od' else 'fi0',clock='fi0',edge='falling',evidence_grade='pinned historical die netlist; current v6 join still requires verification')
        elif n in ['od_v','od_d','od_r']:
            peer={'od_v':'od_ev','od_d':'od_ed','od_r':'od_er'}[n]
            assert p['bits']==4*tp[peer]['bits'] and p['dir']!=tp[peer]['dir']
            p['adjacent_endpoint']=dict(master='dsfd_svc_stn',port=peer,instances=['u_stn_q0[0]','u_stn_q1[0]','u_stn_q2[0]'],direct_quadrant=3,
                clock='ck',edge='rising',evidence_grade='composition declaration only; Q3 RTL/physical receiver absent')
        elif n=='bad':
            ad=ports(tiles,'dsfd_svcio_ad');assert ad['fi']['bits']==p['bits'] and ad['fi']['dir']=='input'
            assert '.fi(bad_od)' in tiles
            p['adjacent_endpoint']=dict(master='dsfd_svcio_ad',instance='u_io.u_ad',port='fi',clock='ck',edge='rising',evidence_grade='tiled RTL composition')
        else:p['adjacent_endpoint']=None
    assert 'ot_fwd_clk_inv u_of (.a(ck[0]), .y(of[0]))' in tiles
    # Cross-check all literal widths with physical pin inventory; directions are
    # sourced from RTL, not the broken historical direction inference.
    for name,pp in [('dsfd_ctrl_pc',cp),('dsfd_svcio_od',op)]:
        inv=e.json('tile',f'physical/s81_ph_views/ports/contract/{name}/ports.json')['ports']
        assert set(inv)==set(pp),(name,set(inv)^set(pp))
        for n,p in pp.items():assert len(inv[n]['pins'])==p['bits'],(name,n)
    pre='results/rtl/budgets_20261006/'
    die=e.json('budget',pre+'inputs/die_models/s81_layer.json.gz')
    plan=e.json('budget',pre+'clock_plan/s81_layer.json.gz')
    measured=e.json('budget',pre+'measured_insertion.json')
    old=e.json('budget',pre+'sheets/dsfd_ctrl_pc.json')
    diffs=[]
    for p in old['interfaces']:
        n=p['port']
        if n in cp:
            changed={k:[p.get(k),cp[n].get(k)] for k in ['bits','dir','clock_domain'] if p.get(k)!=cp[n].get(k)}
            if changed:diffs.append(dict(port=n,changes=changed))
    buses=[b for b in die['buses'] if b[0].startswith(('coNE_d0','coNE_f0','rd_NE','dfi_NE'))]
    assert any(b[2]==514 and ['svc_NE','od','?'] in b[3] and ['f_coNE_1','di0','in'] in b[3] for b in buses)
    glue=e.text('die','results/rtl/dsrom_s81_fulldie_20261004/r9m215khdc/dsfd_glue.sv')
    g=module(glue,'dsfd_stnh_514x1')
    assert '.fclk_i(fi0[0])' in g and '.i_d(di0[513:512])' in g
    prim=e.text('die','rtl/common/ot_fwd_link_stage.sv');assert 'negedge fclk_i' in prim
    # Routed receiver ETMs are useful evidence, but not assembled boundary timing.
    libarcs={}
    for corner in ['ss','ff']:
        for name,path,ref,bases in [
            ('PHY',phy+'_'+corner+'.lib','tile',set(phy_names)),
            ('svc_pc',f'physical/s81_ph_views/closed/dsfd_svc_pc/dsfd_svc_pc_{corner}.lib','tile',set(cp)),
            ('svc_stn',f'physical/s81_ph_views/closed/dsfd_svc_stn/dsfd_svc_stn_{corner}.lib','tile',{'od_er'}),
            ('station',f'physical/s81_die_views/views/dsfd_stnh_514x1/dsfd_stnh_514x1_{corner}.lib','die',{'di0'})]:
            libarcs[name+'_'+corner]=arcs(e.text(ref,path),bases,{n:p['bits'] for n,p in phyports.items()} if name=='PHY' else None)
    assert next(x for x in libarcs['PHY_ff'] if x['port']=='k_wdata' and x['timing_type']=='hold_rising')['pin_count']==8192
    assert next(x for x in libarcs['station_ff'] if x['port']=='di0' and x['timing_type']=='hold_falling')['pin_count']==514
    # Current v6 case is a hashed read-only excerpt, not the stale budget die.
    generator=e.read('die','tools/dsrom_s81_fulldie.py')
    assert hashlib.sha256(generator).hexdigest()==case['generator_sha256']
    bindings={}
    for stack in ['SW','SE','NW','NE']:
        src='svc_'+stack; cinst='ctrl_'+stack; phinst='phy_'+stack
        node=case['instances'][src]['ports']
        data_peers=[x for x in case['nets'][node['od']] if x[0]!=src]
        clock_peers=[x for x in case['nets'][node['of']] if x[0]!=src]
        assert len(data_peers)==len(clock_peers)==1
        assert data_peers[0][0]==clock_peers[0][0] and data_peers[0][1]=='di0' and clock_peers[0][1]=='fi0'
        receiver=data_peers[0][0];master=case['instances'][receiver]['master']
        assert case['widths'][node['od']]==514 and case['widths'][node['of']]==1
        assert case['instances'][phinst]['ports']['clk']==f'n_dfi_{stack}[{ci}]'
        bindings[stack]=dict(receiver_instance=receiver,receiver_master=master,data_port='di0',clock_port='fi0',capture_edge='falling',
            data_net=node['od'],clock_net=node['of'],ctrl_rd_width=case['widths']['n_rd_'+stack],ctrl_rtl_rd_width=ports(top,'dsfd_ctrl')['rd']['bits'],
            missing_ctrl_ports=[n for n in ['rq','rk','wd'] if n not in case['instances'][cinst]['ports']])
        gm=module(glue,master);assert '.fclk_i(fi0[0])' in gm and '.i_d(di0[513:512])' in gm
        for corner in ['ss','ff']:
            key=master+'_'+corner
            if key not in libarcs:
                libarcs[key]=arcs(e.text('die',f'physical/s81_die_views/views/{master}/{master}_{corner}.lib'),{'di0'})
            assert any(a['timing_type']=='hold_falling' and a['pin_count']==514 for a in libarcs[key])
    for n in ['od','of']:
        op[n]['adjacent_endpoint']=dict(by_stack={k:dict(instance=v['receiver_instance'],master=v['receiver_master'],
            port='di0' if n=='od' else 'fi0',clock='fi0',edge='falling') for k,v in bindings.items()},
            evidence_grade='exact v6 die-netlist connection; tile-to-slab assembly and routed timing remain open')
    sheets={}
    for name,pp in [('dsfd_ctrl_pc',cp),('dsfd_svcio_od',op)]:
        sheets[name]=dict(schema='opentallas.s81.boundary_sheet.v1',master=name,status='BLOCKED_RECEIVER_TIMING',timing_ready=False,closure_claim=False,
            not_drop_in_budget_sdc=True,interfaces=list(pp.values()),
            policy=dict(setup_uncertainty_ps=60,hold_uncertainty_ps=25,hold_io_ps=50,accept_ss_ps=15,accept_ff_ps=15),
            clocks=({'core_clk':dict(port='cks',period_ps=833.3333333333334),'hbm_clk':dict(port='ckh',physical_min_period_ps=900,bench_period_ps=1024,selected_die_period_ps=None)} if name=='dsfd_ctrl_pc' else {'core_clk':dict(port='ck',period_ps=833.3333333333334)}),
            budgets=dict(input_delay_ss_ps=None,output_delay_ss_ps=None,input_min_delay_ff_ps=None,output_min_delay_ff_ps=None),
            reason='Unknown actual receiver clock/wire/slew, not zero; no SDC may be generated from this sheet')
    sheets['dsfd_svcio_od']['output_clock_relation']='ck rising -> inverted of falling -> receiver fi0 falling'
    missing=[
        'Current v6 die still connects ctrl rd as 8864 bits vs RTL 8896, and omits rq/rk/wd: repaired assembled tile/slab netlist with all valid/credit bits and clock/reset packing is required.',
        'Per-PC ctrl.ckh -> PHY.clk routed wire/clock arrival, selected die HBM period, and qualified licensed-IP timing. The assumed PHY metadata nominal FF hold is 27.060841 ps, not 15; actual Liberty constraint selection requires data/clock slew.',
        'Per-PC ctrl.cks versus svc_pc.ck SS/FF entry arrivals and uncertainty at actual adjacent pins; legacy slab clock plan has no tile leaves.',
        'OD ck -> of rising/falling delay and slew after real CTS/inverter; paired of->fi0 and od->di0 routed RC, receiver ETM source match, and generated-clock edge propagation.',
        'The pinned svc_stn ETMs expose no extracted od_er setup/hold arcs; receiver coverage must be resolved, not treated as zero. OD quadrant Q3 producer/ready receiver RTL and timing; actual station-chain-to-OD placements/wires for Q0..2 and bad->AD.fi routed clock pair.',
        'Die-context STA using the corrected per-port and per-domain binding, retained 60/25 and 50ps IO policy; no BCmin from the transmitting tile substituted for receiver arrival.']
    model=dict(current_v6_bindings=bindings,current_v6_case_sha256=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest(),source_marker_note='remote SOURCE_COMMIT is older than generator bytes; generator hash matches pinned die commit',schema='opentallas.s81.boundary_model.v1',timing_ready=False,closure_claim=False,added_cycles=0,
        hold_equation='C_launch + CQ_min_ETM + D_data_min >= C_capture + H_receiver_ETM + U_hold',
        setup_equation='C_launch + CQ_max_ETM + D_data_max <= next_capture_edge + C_capture - S_receiver_ETM - U_setup',
        convention='ETM constraints include internal receiver clock-tree delay; do not add standalone CTS insertion to ETM hold/setup again.',
        od_capture='falling of inverted forwarded clock corresponds to source ck rising; do not substitute a generic half-period or independent vclk',
        phy_timing_grade=meta['timing_grade'],phy_claim_boundary=meta['claim_boundary'],phy_timing=meta['timing'],
        missing_evidence=missing,legacy_budget_differences=diffs,historical_die_source=die['source_commit'],historical_buses=buses,
        slab_clock_evidence={k:dict(insertion_ss_ff=v,region=plan['sink_region'].get(k)) for k,v in plan['sink_insertion'].items() if k.startswith(('ctrl_NE/','svc_NE/','phy_NE/'))},
        measured_calibrations={k:v for k,v in measured['blocks'].items() if k in ['dsfd_ctrl_pc','dsfd_svcio_od','dsfd_svc_pc','dsfd_svc_stn','dsfd_stnh_514x1','dsfd_stnv_514x1']},
        receiver_liberty_arcs=libarcs)
    expected={n:{k:copy.deepcopy(v) for k,v in pp.items()} for n,pp in [('dsfd_ctrl_pc',cp),('dsfd_svcio_od',op)]}
    assert not check(sheets,expected)
    negatives={}
    for name,change in [
        ('zero_width',lambda x:x['dsfd_ctrl_pc']['interfaces'][0].update(bits=0)),
        ('reverse_rq',lambda x:next(p for p in x['dsfd_ctrl_pc']['interfaces'] if p['port']=='rq').update(dir='output')),
        ('phy_on_core',lambda x:next(p for p in x['dsfd_ctrl_pc']['interfaces'] if p['port']=='k_v').update(clock_domain='core_clk')),
        ('borrow_transmitter_insertion',lambda x:next(p for p in x['dsfd_ctrl_pc']['interfaces'] if p['port']=='k_v').update(receiver_clock_arrival_ps=196)),
        ('wrong_od_edge',lambda x:x['dsfd_svcio_od'].update(output_clock_relation='rising')),
        ('invent_budget',lambda x:x['dsfd_ctrl_pc']['budgets'].update(output_min_delay_ff_ps=-15)),
        ('relax_uncertainty',lambda x:x['dsfd_ctrl_pc']['policy'].update(hold_uncertainty_ps=0)),
        ('invent_closure',lambda x:x['dsfd_ctrl_pc'].update(timing_ready=True))]:
        mutant=copy.deepcopy(sheets);change(mutant);errors=check(mutant,expected);assert errors;negatives[name]=dict(rejected=True,errors=errors)
    return sheets,model,dict(binding_checks='PASS',assembled_die_compatibility=('FAIL' if any(v['ctrl_rd_width']!=v['ctrl_rtl_rd_width'] or v['missing_ctrl_ports'] for v in bindings.values()) else 'WIDTH_AND_PORT_CHECKS_PASS'),
        assembly_conflicts={k:{n:v[n] for n in ['ctrl_rd_width','ctrl_rtl_rd_width','missing_ctrl_ports']} for k,v in bindings.items()},
        timing_qualification='BLOCKED',negative_controls=negatives)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,default=ROOT);ap.add_argument('--sources',type=Path,default=DEFAULT/'sources.json');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--case-excerpt',type=Path,default=DEFAULT/'current_v6_case.json');ap.add_argument('--require-timing',action='store_true');a=ap.parse_args()
    e=Evidence(a.repo,json.loads(a.sources.read_text()));sheets,model,checks=generate(e,json.loads(a.case_excerpt.read_text()))
    a.out.mkdir(parents=True,exist_ok=True)
    for name,d in {**sheets,'model':model,'checks':checks,'source_pins':dict(refs=e.refs,sha256=e.pins,input_sha256={str(p.name):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.sources,a.case_excerpt]})}.items():
        (a.out/(name+'.json')).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    print(json.dumps(checks));return 2 if a.require_timing else 0
if __name__=='__main__':raise SystemExit(main())
