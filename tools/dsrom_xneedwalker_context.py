"""Selected DSROM x-need control context: price, then time existing parent layout.

No RTL generation, source synthesis, q-element P&R or clock relaxation. Epicurus
selects the functional source; Claude supplies an existing parent ODB/SPEF/SDC.
Only the x-need endpoint cut is reported. External arrival paths stay separate.
"""
import argparse,ast,hashlib,json,re
from pathlib import Path

# Data/enable endpoints include replicated match state and registered lookahead.
# Excludes word walker w_*, arithmetic lanes, chains and segment-tree decisions.
ENDPOINT_RE=r'(^|[./])(n_run|n_q|n_b|n_c|n_j|n_pos|nA|nB|nQ2|d_run|d_fam|d_c|d_q|d_j|d_b|d_pos|r_dp)(\[|\$|[./]|$)'
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,msg):
    if not ok:raise ValueError(msg)
def pinned(root,record):
    p=Path(record['path']);p=p if p.is_absolute() else root/p
    need(p.is_file() and sha(p)==record['sha256'],'actual pinned artifact missing/drift: '+str(p))
    return p.resolve()

def selected(selection):
    s=json.loads(Path(selection).read_text());root=Path(s['source_root']).resolve()
    need(s['source_owner']=='Epicurus','xneed functional source owner selection required')
    need(s['scope']=='DSROM xneedwalker','wrong context/source scope')
    need(type(s['source_commit']) is str and re.fullmatch('[0-9a-f]{40}',s['source_commit']),'frozen source commit')
    need(type(s['parameters']['NSEG']) is int and 2<=s['parameters']['NSEG']<=8,'actual bounded class census')
    need(s['parameters']['FAST']==1,'existing lookahead selected, no baseline substitution')
    scope=s.get('parent_instance_regex')
    need(type(scope) is str and scope.startswith('^') and len(scope)>2,'explicit selected parent instance scope required')
    re.compile(scope)
    sources={k:sha(pinned(root,dict(path=k,sha256=v))) for k,v in s['sources'].items()}
    receipt=json.loads(pinned(root,s['functional_receipt']).read_text())
    need(receipt.get('verdict')=='PASS' or receipt.get('status')=='PASS_CONTROL','selected functional terminal PASS required')
    need(receipt.get('git_commit',receipt.get('source_commit'))==s['source_commit'],'functional terminal source commit differs')
    rp=receipt.get('source_sha256',receipt.get('source_pins',{}))
    need(sources and all(rp.get(k)==v for k,v in sources.items()),'functional gate must bind selected source bytes')
    need(all(receipt.get('parameters',{}).get(k)==v for k,v in s['parameters'].items()),'selected functional parameters differ')
    latency=receipt.get('added_latency_cycles')
    need(latency is not None and s['latency']['added_latency_cycles']==latency,'latency must be actual functional receipt value')
    need(s['latency']['feedback_initiation_interval']==1,'no halved-throughput loop')
    return s,root,receipt

def price(selection):
    s,root,receipt=selected(selection);n=s['parameters']['NSEG'];hc=s['parameters'].get('HC',1)
    # FAST nA/nB/nQ2 already exist inside each element's charged full slot.
    # This ledger describes their context; it is not another storage debit.
    assignments=ast.parse((root/'tools/uarch_model.py').read_text()).body
    dff=next(ast.literal_eval(x.value) for x in assignments if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='DFF_UM2' for t in x.targets))
    state=14+(n-1).bit_length()
    lookahead=3*6*n;replicated=hc*state
    return dict(schema='dsrom-xneed-control-context-r1',source_owner='Epicurus',source_commit=s['source_commit'],
        parameters=s['parameters'],source_pins=s['sources'],functional_receipt=s['functional_receipt'],
        source_selection_sha256=sha(selection),unified_model_sha256=sha(root/'tools/uarch_model.py'),
        actual_added_latency_cycles=s['latency']['added_latency_cycles'],
        loop_initiation_interval=1,extra_iteration_cycles=0,
        token_delta_cycles=s['latency'].get('composed_token_delta_cycles'),
        token_composition='owner actual q-op fill/drain latency and producer overlap; no extra per-hit cycle or assumed zero launch',
        MACs_per_cycle=0,accepted_xneed_hits_per_cycle=1,
        x_payload_bits=s['ports']['x_payload_bits'],x_payload_bytes_per_accepted_hit=s['ports']['x_payload_bits']/8,
        x_match_identity_bits=8+3+3+1,
        lookahead_current_next_prefetch_bits=lookahead,replicated_match_state_bits=replicated,
        existing_register_area_um2=(lookahead+replicated)*dff,
        area_charge='existing source element slot once; no new hardware emitted by context tool',
        required_boundary_bits=s['ports']['x_payload_bits']+15,
        actual_match_receivers=s['ports']['match_receiver_counts'],
        replica_count=s['replicas'],mux_demux_and_buffers_area_um2=None,
        route_capacity_tracks=s['ports'].get('route_capacity_tracks'),
        complete_loaded_area_um2=None,slot_fit=None,
        endpoint_regex=ENDPOINT_RE,physical_admission=False,
        period_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
        clock_reset_producer_arrivals=s['clock_reset_producer_arrivals'],
        physical_job='scoped STA only on pinned existing parent ODB/SPEF/SDC; no new qelement timing build')

def tclpath(path):
    p=str(path);need(not any(c in p for c in '{}\n\r'),'unsafe Tcl path')
    return '{'+p+'}'

def scripts(selection, out):
    s,root,receipt=selected(selection);model=price(selection)
    need(s['clock_reset_producer_arrivals'].get('source_bound') is True,'actual clock/reset and producer arrivals absent')
    out=Path(out);need(not out.exists(),'immutable new output directory required')
    text={};pins={}
    for corner,check in (('SS','max'),('FF','min')):
        c=s['physical_context'][corner]
        need(c['source_commit']==s['source_commit'] and c['parameters']==s['parameters'],'existing parent physical source mismatch')
        need(c['corner']==corner,'actual corner mismatch')
        need(c['period_ps']==833 and c['setup_uncertainty_ps']==60 and c['hold_uncertainty_ps']==25,'clock/uncertainty must remain unchanged')
        files={key:[pinned(root,r) for r in c[key]] for key in ('lefs','liberties')}
        for key in ('odb','spef','sdc'):files[key]=pinned(root,c[key])
        pins[corner]={str(p):sha(p) for vs in files.values() for p in (vs if isinstance(vs,list) else [vs])}
        commands=[*[f'read_lef {tclpath(p)}' for p in files['lefs']],*[f'read_liberty {tclpath(p)}' for p in files['liberties']],
           f"read_db {tclpath(files['odb'])}",f"read_sdc {tclpath(files['sdc'])}",f"read_spef {tclpath(files['spef'])}",
           'set_propagated_clock [all_clocks]', 'check_setup -verbose']
        commands.append('''set pins [list]
foreach c [all_registers -cells] {
 if {[regexp -- {SCOPE} [get_full_name $c]] && [regexp -- {REGEX} [get_full_name $c]]} {
  foreach p [get_pins -of_objects $c -filter "direction==input"] {
   set nm [get_property $p lib_pin_name]
   if {$nm eq "D" || $nm eq "ENA" || $nm eq "SE"} {lappend pins $p}
  }
 }
}
if {[llength $pins]==0} {error "actual xneed endpoints absent; hierarchy/selection mismatch"}
puts "OT_XNEED_ENDPOINTS [llength $pins]"
set loop [find_timing_paths -from [all_registers -clock_pins] -to $pins -path_delay CHECK -group_path_count 1]
if {[llength $loop]==0} {error "actual internal feedback missing/unconstrained; no PASS"}
puts "OT_XNEED_INTERNAL_WS [get_property [lindex $loop 0] slack]"
puts "OT_XNEED_INTERNAL_BEGIN"
report_checks -from [all_registers -clock_pins] -to $pins -path_delay CHECK -group_path_count 10 -format full_clock_expanded -fields {fanout cap slew} -digits 3
puts "OT_XNEED_INTERNAL_END"
puts "OT_XNEED_EXTERNAL_BEGIN"
report_checks -from [all_inputs] -to $pins -path_delay CHECK -group_path_count 10 -format full_clock_expanded -fields {fanout cap slew} -digits 3
puts "OT_XNEED_EXTERNAL_END"
report_check_types -max_slew -max_capacitance -violators
puts "OT_XNEED_LOADED_NETS_BEGIN"
foreach p $pins {report_net -connections -verbose [get_nets -of_objects $p]}
puts "OT_XNEED_LOADED_NETS_END"
exit
'''.replace('REGEX',ENDPOINT_RE).replace('SCOPE',s['parent_instance_regex']).replace('CHECK',check))
        text[corner]='\n'.join(commands)
    out.mkdir(parents=True)
    (out/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
    (out/'parent_artifact_pins.json').write_text(json.dumps(pins,sort_keys=True,indent=2)+'\n')
    for c,t in text.items():(out/(c+'.tcl')).write_text(t)
    return model

def main():
    p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--model-out',type=Path);p.add_argument('--prepare',type=Path)
    a=p.parse_args();m=price(a.selection)
    if a.model_out:
        with a.model_out.open('x') as f:json.dump(m,f,sort_keys=True,indent=2);f.write('\n')
    if a.prepare:scripts(a.selection,a.prepare)
if __name__=='__main__':main()
