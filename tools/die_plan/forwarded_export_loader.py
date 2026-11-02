#!/usr/bin/env python3
"""Prepare an optional post-CTS estimated-RC T41 observer session; never run EDA."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import forwarded_export_observer as F
import signoff as S


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(kit, out, enabled=False, odb='4_cts.odb', module='s81p_slice_station__t41'):
    kit, out = Path(kit).resolve(), Path(out).resolve()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.odb', odb):
        raise ValueError('one exact checkpoint basename required')
    config = (kit/'config.mk').read_text()
    def value(key):
        rows=re.findall(r'^\s*(?:export\s+)?'+key+r'\s*=\s*([0-9.]+)\s*$',config,re.M)
        if len(rows)!=1:raise ValueError('missing/ambiguous declared '+key)
        return float(rows[0])
    tt, ff = value('OT_VCLK_TT'), value('OT_VCLK_FF')
    request=F.request(kit/'constraint.sdc',kit/'run/results/asap7/dp_slice_station__t41/base/1_2_yosys.v',module)
    sources={str(p.relative_to(kit)):sha(p) for p in [kit/'config.mk',kit/'constraint.sdc',kit/'setRC_rcx.tcl',Path(request['netlist']['path'])]}
    if '# OT_CORE_TAP_CORNER_FILE' in (kit/'constraint.sdc').read_text():
        raise ValueError('T41 loader scope requires no undeclared corner overlay')
    total=sum(len(e['bits'])*2 for e in request['exports'])
    out.mkdir(parents=True,exist_ok=True)
    packet=dict(schema='opentallas.forwarded_export_loader.PREP.v1',enabled=enabled,qualification='NOT_ASSERTED',
                status='PREP_ONLY_NO_EDA',kit=str(kit),checkpoint_basename=odb,input_sha256=sources,
                observer_sha256=sha(F.__file__),pair_helper_sha256=sha(Path(F.__file__).with_name('pair_skew.tcl')),
                loader_sha256=sha(__file__),signoff_module_sha256=sha(S.__file__),
                signoff_library_loader_sha256=hashlib.sha256(S.EXACT_TIMING_LIBRARIES_TCL.encode()).hexdigest(),
                query_limit=total,parasitics='POST_CTS_PLACEMENT_ESTIMATE_NOT_ROUTED_OR_EXTRACTED',
                TT_vclk_ps=tt,FF_vclk_ps=ff,default_verdicts_and_constraints='UNCHANGED',request=request)
    packet['session_sha256']={}
    for corner in ('tt','ff'):
        dest=out/corner;dest.mkdir(exist_ok=True)
        if not enabled:
            script='# Observer loader OFF; no EDA or timing queries.\n'
        else:
            guards='\n'.join('if {[lindex [exec sha256sum -- '+F.literal('/work/'+name)+'] 0] ne '+F.literal(digest)+'} {error {selected T41 input changed: '+name+'}}' for name,digest in sources.items())
            # Same declared corner-specific virtual IO reference as normal postcts_gate.
            ff_overlay=''
            if corner=='ff':
                ff_overlay='set so_vclk [lmap c [all_clocks] {if {[llength [get_property $c sources]]} continue;set c}]\nif {[llength $so_vclk]!=1 || [get_full_name [lindex $so_vclk 0]] ne "vclk"} {error {sole declared virtual IO reference absent}}\nproc so {args} {puts [join $args { }]}\n'+S.FF_BOUND_TCL.replace('@FF_BOUND@',str(ff))+'\n'
            script='if {[file exists /out/t41_export_witness]} {error {fresh observer output directory required}}\n'+guards+'\n'+S.EXACT_TIMING_LIBRARIES_TCL+f'\not_lib_load {corner.upper()} /out/libraries.json\n'
            script+='set fp [open /out/runtime_inputs.tsv w]\n'
            script+='foreach p [list /base/'+odb+' /work/config.mk /work/constraint.sdc /work/setRC_rcx.tcl] {puts $fp "$p\\t[lindex [exec sha256sum -- $p] 0]"}\nclose $fp\n'
            script+='read_db /base/'+odb+'\nread_sdc /work/constraint.sdc\n'+ff_overlay
            script+='source /work/setRC_rcx.tcl\nestimate_parasitics -placement\nset_propagated_clock [all_clocks]\n'
            script+='puts {OT_T41_RC_BASIS POST_CTS_PLACEMENT_ESTIMATE_NOT_ROUTED_OR_EXTRACTED}\n'
            script+=F.emit(request,'/out/t41_export_witness',total,True)
            script+='if {![file isfile /out/t41_export_witness/counts.tsv]} {error {requested T41 observation failed; no coverage granted}}\n'
            script+=r'''
set fp [open /out/t41_export_witness/counts.tsv r]
set counts [dict create]
foreach line [split [read $fp] "\n"] {
  if {$line ne ""} {lassign [split $line "\t"] k v;dict set counts $k $v}
}
close $fp
foreach k {errors missing limited} {
  if {[dict get $counts $k]!=0} {error {requested T41 observation incomplete; no coverage granted}}
}
'''
        (dest/'session.tcl').write_text(script)
        packet['session_sha256'][corner]=hashlib.sha256(script.encode()).hexdigest()
        (dest/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    (out/'PREP.json').write_text(json.dumps(packet,indent=2)+'\n')
    return packet


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kit',required=True);p.add_argument('--out',required=True)
    p.add_argument('--enable',action='store_true');p.add_argument('--odb',default='4_cts.odb')
    a=p.parse_args();r=prepare(a.kit,a.out,a.enable,a.odb)
    print(r['status'],r['parasitics'],r['query_limit'])

if __name__=='__main__':main()
