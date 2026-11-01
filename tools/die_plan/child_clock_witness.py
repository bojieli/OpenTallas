"""Retain native child clock witnesses in an existing routed export session.

This is evidence retention, not a qualification decision. Missing native inputs,
endpoints, pair files, library hashes or a corner fail the requested retention.
"""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tcl(tools, corner, libraries, inputs):
    tools=Path(tools)
    family=tools.parents[1]/'physical/common_flow/clock_family.tcl'
    # A shipped tools directory may carry the common helper beside the pair helper.
    if not family.is_file(): family=tools/'clock_family.tcl'
    body=family.read_text()+'\nset ::ot_ps_lib_only 1\n'+(tools/'pair_skew.tcl').read_text()+'\nunset ::ot_ps_lib_only\n'
    body+='set ::ot_ps_method tag\nsta::worst_slack_cmd max\nsta::worst_slack_cmd min\nset ::ot_ps_R [ot_ps_regs]\nlassign [ot_ps_related $::ot_ps_R] P np nx nd\n'
    prefix=f'/out/child_clock_{corner}'
    for suffix, header, source in [('endpoints','reference clock_pin clock late_ps early_ps edge','::ot_ps_R'),('pairs','launch capture_setup data_pin raw_setup_ps raw_hold_ps capture_hold','P'),('roots','clock_edge late_ps early_ps','::ot_ps_insertion')]:
        body+=f'set f [open {prefix}_{suffix}.tsv w]\nputs $f [join {{{header}}} \\t]\ndict for {{key row}} ${source} {{puts $f "'+('' if suffix=='pairs' else '$key\\t')+'[join $row \\t]"}\nclose $f\n'
    body+=f'set f [open {prefix}_masters.tsv w]\nputs $f \"reference\\tclock_pin\\tmaster\"\ndict for {{ref row}} $::ot_ps_R {{set pin [lindex $row 0]; set cell [get_cells -of_objects [get_pins $pin]]; puts $f \"$ref\\t$pin\\t[get_property $cell ref_name]\"}}\nclose $f\n'
    body+=f'set f [open {prefix}_counts.tsv w]\nputs $f "refs\\t[dict size $::ot_ps_R]"\nputs $f "pairs\\t$np"\nputs $f "captures\\t$nd"\nputs $f "missing\\t$::ot_ps_noarr"\nclose $f\n'
    body+=f'set f [open {prefix}_inputs.tsv w]\n'
    for kind, paths in [('liberty',libraries),('constraint',inputs)]:
        for path in paths:
            if any(c in path for c in '{}\n'): raise ValueError('Unrepresentable witness input path')
            body+=f'puts $f "{kind}\\t{path}\\t[lindex [exec sha256sum {{{path}}}] 0]"\n'
    body+='close $f\n'
    body+=f'if {{$::ot_ps_noarr != 0}} {{error "CHILD_CLOCK_WITNESS missing actual clock arrivals"}}\nputs "OT_CHILD_CLOCK_WITNESS {corner} COMPLETE"\n'
    return body


def record(out, base, name, export_record):
    out,base=Path(out),Path(base)
    native={p:sha(base/p) for p in ['6_final.odb','6_final.spef','6_final.v']}
    result={'schema':'opentallas.child_clock_witness.v1','qualification':'NOT_ASSERTED',
            'hierarchical_expansion':'NOT_ASSERTED','scope':'Actual native endpoints and related-pair witness; no CRPR credit or source/EQ waiver',
            'native':native,'corners':{}}
    for c in ['tt','ff']:
        prefix=f'child_clock_{c}'
        log=(out/f'export_{c}.log').read_text()
        if f'OT_CHILD_CLOCK_WITNESS {c} COMPLETE' not in log: raise ValueError(f'{c}: incomplete native witness')
        counts=dict(line.split('\t') for line in (out/f'{prefix}_counts.tsv').read_text().splitlines())
        counts={k:int(v) for k,v in counts.items()}
        if counts['missing'] or counts['refs']<1: raise ValueError(f'{c}: missing endpoint coverage')
        files={f'{prefix}_{k}.tsv':sha(out/f'{prefix}_{k}.tsv') for k in ['endpoints','pairs','roots','masters','counts','inputs']}
        if not (out/f'{prefix}_inputs.tsv').read_text().strip(): raise ValueError(f'{c}: missing exact input identities')
        result['corners'][c]={'counts':counts,'files':files,'exported_liberty_sha256':sha(out/f'{name}_{c}.lib'),
                              'extraction_tcl_sha256':sha(out/f'export_{c}.tcl'),
                              'constraint_sequence':export_record['sdc_sequence'][c]}
    target=out/'child_clock_witness.json'
    target.write_text(json.dumps(result,indent=2)+'\n')
    return {'path':target.name,'sha256':sha(target),'qualification':'NOT_ASSERTED'}
