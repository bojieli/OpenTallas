#!/usr/bin/env python3
"""Stage a read-only routed-flat versus single-ETM clock coverage coupon.

No qualification waiver: endpoint identities and real related pairs are exported
from current pair_skew.tcl. Raw pair differences carry no CRPR credit and are
not signoff verdicts. A missing/hidden child graph remains unqualified.
"""
import argparse, json, re, hashlib, ast
from pathlib import Path

EXTRACT = r'''
set_propagated_clock [all_clocks]
source /coupon/clock_family.tcl
set ::ot_ps_lib_only 1
source /coupon/pair_skew.tcl
unset ::ot_ps_lib_only
puts "COUPON_WNS_SETUP [sta::worst_slack_cmd max]"
puts "COUPON_WNS_HOLD [sta::worst_slack_cmd min]"
ot_ps_zero_unc
set ::ot_ps_method tag
sta::worst_slack_cmd max
sta::worst_slack_cmd min
set ::ot_ps_R [ot_ps_regs]
lassign [ot_ps_related $::ot_ps_R] pairs np nx nd
set f [open /coupon/OUT/endpoints.tsv w]
puts $f "reference\tclock_pin\tclock\tlate_ps\tearly_ps\tedge"
dict for {ref row} $::ot_ps_R {puts $f "$ref\t[join $row \t]"}
close $f
set f [open /coupon/OUT/related_pairs.tsv w]
puts $f "launch\tcapture_setup\tdata_pin\traw_setup_ps\traw_hold_ps\tcapture_hold"
dict for {key row} $pairs {puts $f [join $row \t]}
close $f
set f [open /coupon/OUT/coverage.tsv w]
puts $f "register_clock_references\t[dict size $::ot_ps_R]"
puts $f "data_pins\t$nd"
puts $f "related_pairs\t$np"
puts $f "inter_clock_pairs_skipped\t$nx"
puts $f "no_clock_arrival\t$::ot_ps_noarr"
close $f
puts "COUPON_COMPLETE refs=[dict size $::ot_ps_R] pairs=$np data=$nd missing=$::ot_ps_noarr"
exit
'''

def stage(fixture, out, repo):
    out.mkdir(parents=True, exist_ok=True)
    text=(fixture/'6_final.v').read_text()
    declarations=re.findall(r'^\s*(?:input|output|inout)\s+[^;]+;',text,re.M)
    names=[re.sub(r'\[[^]]+\]', '',d).split()[-1].rstrip(';') for d in declarations]
    assert len(names)==len(set(names)) and 'ck' in names
    wrapper='module coupon_etm('+','.join(names)+');\n'+'\n'.join(declarations)+'\nqfd_dv_s5_su8_rst3 u_child ('+','.join(f'.{n}({n})' for n in names)+');\nendmodule\n'
    (out/'etm.v').write_text(wrapper)
    sdc=(fixture/'6_final.sdc').read_text()
    assert '833.0000' in sdc and '60.0000' in sdc and '25.0000' in sdc
    assert not re.search(r'get_(?:pins|cells)',sdc), 'Internal constraints need explicit hierarchical mapping'
    (out/'etm.sdc').write_text(sdc.replace('current_design qfd_dv_s5_su8_rst3','current_design coupon_etm'))
    for source in ['tools/die_plan/pair_skew.tcl','physical/common_flow/clock_family.tcl']:
        (out/Path(source).name).write_bytes((repo/source).read_bytes())
    parsed=ast.parse((repo/'tools/die_plan/signoff.py').read_text())
    loader=next(ast.literal_eval(n.value) for n in parsed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXACT_TIMING_LIBRARIES_TCL' for t in n.targets))
    (out/'library_loader.tcl').write_text(loader)
    jobs=[]
    for corner in ['tt','ff']:
        for mode in ['flat','etm']:
            key=f'{mode}_{corner}';(out/key).mkdir(exist_ok=True)
            setup=f'source /coupon/library_loader.tcl\not_lib_load {corner.upper()} /coupon/{key}/libraries.json /fixture/config.mk\n'
            if mode=='flat':
                setup+='read_db /fixture/6_final.odb\nread_sdc /fixture/6_final.sdc\nread_spef /fixture/6_final.spef\n'
            else:
                setup+=f'read_liberty /fixture/views/qfd_dv_s5_su8_rst3_{corner}.lib\nread_verilog /coupon/etm.v\nlink_design coupon_etm\nread_sdc /coupon/etm.sdc\n'
            (out/f'{key}.tcl').write_text(setup+EXTRACT.replace('/OUT/',f'/{key}/'))
            jobs.append(f'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /coupon/{key}.tcl > /coupon/{key}/openroad.log 2>&1 && grep -q \'^COUPON_COMPLETE\' /coupon/{key}/openroad.log')
    (out/'run.sh').write_text('#!/bin/bash\nset -uo pipefail\nstatus=0\n'+''.join(f'{j} || status=1\n' for j in jobs)+'exit "$status"\n')
    inputs=['6_final.odb','6_final.spef','6_final.sdc','6_final.v','views/qfd_dv_s5_su8_rst3_tt.lib','views/qfd_dv_s5_su8_rst3_ff.lib']
    manifest={'fixture':str(fixture),'scope':'READ_ONLY_METHOD_COUPON_NOT_CHILD_QUALIFICATION','clock_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'related_pair_method':'native combinational fanin; raw late-early, no CRPR credit','sha256':{p:hashlib.sha256((fixture/p).read_bytes()).hexdigest() for p in inputs}}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def collect(out):
    result={'scope':'METHOD_COUPON_ONLY_NOT_CHILD_QUALIFICATION','corners':{}}
    for corner in ['tt','ff']:
        modes={}
        for mode in ['flat','etm']:
            p=out/f'{mode}_{corner}'
            if not (p/'coverage.tsv').is_file():
                modes[mode]={'status':'INCOMPLETE'};continue
            fields=dict(line.split('\t',1) for line in (p/'coverage.tsv').read_text().splitlines())
            fields={k:int(v) for k,v in fields.items()}
            log=(p/'openroad.log').read_text()
            fields['status']='COMPLETE' if 'COUPON_COMPLETE' in log else 'INCOMPLETE'
            rows=[line.split('\t') for line in (p/'endpoints.tsv').read_text().splitlines()[1:]]
            for ix,name in [(3,'late'),(4,'early')]:
                values=[float(r[ix]) for r in rows]
                fields[name+'_ps']={'min':min(values),'max':max(values)} if values else None
            fields['wns_ps']={kind:float(value)*1e12 for kind,value in re.findall(r'COUPON_WNS_(SETUP|HOLD) ([-+0-9.eE]+)',log)}
            modes[mode]=fields
        result['corners'][corner]=modes
    (out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--collect',action='store_true');p.add_argument('--fixture',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);a=p.parse_args();collect(a.out) if a.collect else stage(a.fixture,a.out,a.repo)
