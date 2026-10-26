"""Emit a plan-only native STA clock model; never invokes CTS/GRT or timing ECO.

Stable aliases preserve a manifest to every actual sink/master/planned node.
SPEF uses merged planned RC only; actual receiver caps come from TT/FF liberty.
The synthetic netlist has no functional timing/signoff meaning.
"""
import json
import re
from pathlib import Path

import core_infra as CI
import core_infra_wire as CW


def liberty_ports(text,master):
    def body(start):
        a=text.index('{',start);n=1;j=a+1
        while n:
            n+=(text[j]=='{')-(text[j]=='}');j+=1
        return text[a+1:j-1]
    cell=body(text.index('cell ('+master+')'))
    out=[]
    for m in re.finditer(r'(?<!pg_)\bpin\s*\(([^)]+)\)\s*\{',cell):
        # body() operates on the original liberty, so locate this local pin.
        i=m.end();depth=1;j=i
        while depth:depth+=(cell[j]=='{')-(cell[j]=='}');j+=1
        pin=cell[i:j-1];direction=re.search(r'\bdirection\s*:\s*(input|output|inout)',pin)
        if direction:out.append(dict(name=m.group(1).strip('"'),direction=direction[1],clock=bool(re.search(r'\bclock\s*:\s*true',pin))))
    if not out:raise CI.InfraError('no logical liberty ports for '+master)
    return out


def _vword(word):
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',word):return word
    if any(c.isspace() for c in word):raise CI.InfraError('whitespace in liberty identifier')
    return '\\'+word+' '


def emit_model(sl,data,outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    plan=CI.compile_slice(sl);tree=plan['core_tree'];nodes=tree['nodes'];cells={q['name']:q for q in plan['cells']};routing=data['routing_model']
    aliases={n['name']:f'b{i}' for i,n in enumerate(nodes)};net_by={n['name']:f'n{i}' for i,n in enumerate(nodes)};children={n['name']:[] for n in nodes};leaves={};leaf_by={}
    for n in nodes:
        if n['parent'] in children:children[n['parent']].append(n['name'])
    for leaf in tree['leaves']:
        for sink in leaf['sinks']:
            if sink in leaf_by:raise CI.InfraError('duplicate planned STA sink '+sink)
            leaf_by[sink]=leaf['node'];leaves.setdefault(leaf['node'],[]).append(sink)
    sinks=sorted(leaf_by);sink_alias={s:f'f{i}' for i,s in enumerate(sinks)}
    rtl=['module clock_plan_model(input ck, output ['+str(len(sinks)-1)+':0] q);','wire '+', '.join(net_by.values())+';'];manifest=[]
    for n in nodes:
        source='ck' if n['parent'].startswith('port:') else net_by[n['parent']]
        rtl.append(f"{n['master']} {aliases[n['name']]} (.A({source}), .Y({net_by[n['name']]}));")
    for i,sink in enumerate(sinks):
        terminal=data['terminal_cells'][sink];master=terminal['master'];clockpin=terminal['pin'];ports=data['master_pins'][master];connections=[];first_output=True
        if not any(q['name']==clockpin and q['direction']=='input' for q in ports):raise CI.InfraError('clock pin absent from liberty '+sink)
        for pin in ports:
            name=pin['name']
            if name==clockpin:value=net_by[leaf_by[sink]]
            elif pin['direction']=='input':value="1'b1" if re.search(r'(RESET|SET|RST).*N$|[RS]N$',name,re.I) else "1'b0"
            elif pin['direction']=='output':
                value=f'q[{i}]' if first_output else '';first_output=False
            else:raise CI.InfraError('unsupported model inout '+master+'.'+name)
            connections.append('.'+_vword(name)+'('+value+')')
        rtl.append(master+' '+sink_alias[sink]+' ('+', '.join(connections)+');')
        manifest.append(dict(actual_sink=sink,alias=sink_alias[sink]+'/'+clockpin,master=master,leaf=leaf_by[sink]))
    rtl.append('endmodule');(out/'model.v').write_text('\n'.join(rtl)+'\n')
    spef=['*SPEF "IEEE 1481-1998"','*DESIGN "clock_plan_model"','*DATE "PLAN ONLY"','*VENDOR "OpenTallas"','*PROGRAM "core_infra_sta"','*VERSION "1"','*DESIGN_FLOW "PIN_CAP NONE"','*DIVIDER /','*DELIMITER :','*BUS_DELIMITER [ ]','*T_UNIT 1 PS','*C_UNIT 1 PF','*R_UNIT 1 OHM','*L_UNIT 1 HENRY'];wire_reports=[]
    def net(name,driver,targets,points,profile,terminal_layers):
        if not profile.get('merge_collinear'):raise CI.InfraError('plan STA requires merged conductor network')
        profile=dict(profile)
        if profile.get('via_resistance_kohm') is not None:profile['terminal_layers']=terminal_layers
        rc=CW.rooted_rc(points,[0.]*len(targets),**profile)
        spef.extend([f'*D_NET {name} {rc["wire_cap_ff"]/1000:.12g}','*CONN',('*P ' if driver=='ck' else '*I ')+driver+' '+('I' if driver=='ck' else 'O')])
        spef.extend('*I '+p+' I' for p in targets);spef.append('*CAP')
        spef.extend(f'{i+1} {name}:{node} {c/1000:.12g}' for i,(node,c) in enumerate(rc['rc_capacitors_ff']));spef.append('*RES');idx=1
        for a,b,r in rc['rc_resistors_kohm']:
            spef.append(f'{idx} {name}:{a} {name}:{b} {r*1000:.12g}');idx+=1
        for pin,node in zip([driver]+targets,rc['terminal_nodes']):
            spef.append(f'{idx} {pin} {name}:{node} 1e-6');idx+=1
        spef.append('*END');wire_reports.append(dict(net=name,wire_um=rc['wire_um'],wire_cap_ff=rc['wire_cap_ff'],cycles=rc['network_cycles'],overlap_removed_um=rc['overlap_removed_um'],via_count=rc['via_count'],via_model=rc['via_model']))
    roots=[n for n in nodes if n['parent'].startswith('port:')]
    if len(roots)!=1:raise CI.InfraError('single model clock entry required')
    finite_vias=routing['nonleaf'].get('via_resistance_kohm') is not None
    def pin_layer(master,pin):
        return data['master_pin_layers'][master][pin] if finite_vias else 1
    root=roots[0];entry=sl['islands'][0]['clock_pin']['xy_um']
    entry_layer=int(sl['islands'][0]['clock_pin']['layer'].lstrip('M'))
    net('ck','ck',[aliases[root['name']]+':A'],[entry,cells[root['name']]['xy_um']],routing['nonleaf'],[entry_layer,pin_layer(root['master'],'A')])
    for n in nodes:
        name=n['name'];profile=routing.get('nodes',{}).get(name,routing['nonleaf' if children[name] else 'leaf'])
        targets=[aliases[q]+':A' for q in children[name]]+[sink_alias[q]+':'+data['terminal_cells'][q]['pin'] for q in leaves.get(name,[])]
        points=[cells[name]['xy_um']]+[cells[q]['xy_um'] for q in children[name]]+[data['points'][q] for q in leaves.get(name,[])]
        layers=[pin_layer(n['master'],'Y')]+[pin_layer(cells[q]['master'],'A') for q in children[name]]+[pin_layer(data['terminal_cells'][q]['master'],data['terminal_cells'][q]['pin']) for q in leaves.get(name,[])]
        net(net_by[name],aliases[name]+':Y',targets,points,profile,layers)
    (out/'plan.spef').write_text('\n'.join(spef)+'\n')
    meta=dict(schema='opentallas.core_clock_plan_sta.v1',model_only=True,nodes=aliases,sinks=manifest,leaf_groups=tree['leaves'],wire_nets=wire_reports,input_slew_ps=0,limitations=['Synthetic clock model only; no functional or release timing meaning.','Actual TT/FF receiver pin caps come from library, not SPEF pin-cap duplication.','Via R uses declared per-layer values when supplied; via C=0, coupling/pin-access and full capacity remain open.','No measured timing input or per-leaf correction; no CTS/GRT or physical data moves.'])
    (out/'model_manifest.json').write_text(json.dumps(meta,indent=1))
    tcl=['set c $::env(CORNER)','set P /OpenROAD-flow-scripts/flow/platforms/asap7','read_lef $P/lef/asap7_tech_1x_201209.lef','read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef','foreach f [glob /work/macros/*.lef] {read_lef $f}','foreach f [glob $P/lib/NLDM/*_RVT_${c}_*] {read_liberty $f}','set lo [string tolower $c]','foreach f [glob /work/macros/*_${lo}.lib] {read_liberty $f}','read_verilog /work/model.v','link_design clock_plan_model','create_clock -name core -period 833 [get_ports ck]','set_clock_uncertainty -setup 60 [get_clocks core]','set_clock_uncertainty -hold 25 [get_clocks core]','set_clock_transition 0 [get_clocks core]','set_delay_calculator dmp_ceff_elmore','puts PLAN_STA_CALCULATOR_dmp_ceff_elmore','read_spef /work/plan.spef','set_propagated_clock [all_clocks]','report_worst_slack -max','puts "PLAN_STA_DELAY_API [info commands *delay*]"','set f [open /work/arrivals_${c}.tsv w]']
    for row in manifest:
        tcl+=['set pin [get_pins '+CI.word(row['alias'])+']',
              'set value [get_property $pin arrival_max_rise]',
              f'puts $f [format "%s\\t%s" {CI.word(row["actual_sink"])} $value]']
    tcl+=['close $f','puts "PLAN_STA_DONE $c MODEL_ONLY NO_CTS_NO_GRT"'];(out/'model.tcl').write_text('\n'.join(tcl)+'\n')
    return meta
