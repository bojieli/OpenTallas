#!/usr/bin/env python3
"""Standalone API calibration, NOT a new macro characterization or flow hook."""
import hashlib,json,pathlib,re,subprocess
P=pathlib.Path(__file__).resolve().parent
M='ot_sram_1r1w_32x546_m1'
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
# These untouched, source-pinned TT/FF libraries deliberately have different arcs.
# The cross-PVT scene is only an API discriminator, never a signoff configuration.
hashes={c:hashlib.sha256((P/f'{M}_{c}.lib').read_bytes()).hexdigest() for c in ('tt','ff')}
(P/'native_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
(P/'probe.v').write_text(f'module probe(input clk,input en,output [545:0] q); wire [545:0] mid; {M} launch(.clk(clk),.r_ce_in(en),.rd_out(mid)); {M} capture(.clk(clk),.r_ce_in(en),.wd_in(mid),.rd_out(q)); endmodule\n')
receipts=[]
for case in ('ff_reference','tt_reference','split','swapped','missing'):
    mi='tt' if case in ('tt_reference','swapped') else 'ff'
    ma='ff' if case in ('ff_reference','swapped') else 'tt'
    if case=='missing':
        (P/'missing.log').write_text('ROLE_BINDING_REFUSED missing explicit max role; no library load or fallback\n')
        receipts.append(dict(case=case,expected_refusal=True));continue
    script='read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\nread_lef /work/'+M+'.lef\n' + ''.join(f'read_liberty /work/{M}_{c}.lib\n' for c in ('tt','ff'))
    script+='read_verilog /work/probe.v\nlink_design probe\nset_mode calibration\ncreate_clock -name core -period 2000 [get_ports clk]\nset_clock_transition 20 [all_clocks]\n'
    script+=f'define_scene CAL -mode calibration -liberty_min /work/{M}_{mi}.lib -liberty_max /work/{M}_{ma}.lib\nset_scene CAL\n'
    script+=(P/'accessor.tcl').read_text()+'\not_direct_load_scene_accessor\nputs "BINDING [ot_sta_scene_binding launch clk]"\n'
    script+='report_checks -path_delay min_max -from [get_pins {launch/rd_out[0]}] -to [get_pins {capture/wd_in[0]}] -format full_clock_expanded -digits 6\n'
    script+='puts "MIN_ARR [get_property [get_pins {launch/rd_out[0]}] arrival_min_rise]"\nputs "MAX_ARR [get_property [get_pins {launch/rd_out[0]}] arrival_max_rise]"\nexit\n'
    (P/f'{case}.tcl').write_text(script)
    run=subprocess.run(['docker','run','--rm','-v',str(P)+':/work','openroad/orfs:asap7lock',OR,'-no_init','-exit','/work/'+case+'.tcl'],capture_output=True,text=True)
    out=run.stdout+run.stderr;(P/f'{case}.log').write_text(out)
    if run.returncode or '[ERROR' in out or 'Error:' in out:raise RuntimeError(case+' tool failure '+out[-2000:])
    vals={k:float(re.search(r'^'+k+r' (\S+)',out,re.M)[1]) for k in ('MIN_ARR','MAX_ARR')}
    receipts.append(dict(case=case,min_library=mi,max_library=ma,**vals))
refs={r['case']:r for r in receipts}
for key in ('MIN_ARR','MAX_ARR'):
    expected=refs['ff_reference' if key=='MIN_ARR' else 'tt_reference'][key]
    assert abs(refs['split'][key]-expected)<1e-16,(key,refs)
assert abs(refs['split']['MIN_ARR']-refs['split']['MAX_ARR'])>1e-12
# Swapped assignment must be observed and rejected by expected-role identity,
# before a flow could accept its apparently improved hold or setup.
assert refs['swapped']['MIN_ARR']==refs['tt_reference']['MIN_ARR']
assert refs['swapped']['MAX_ARR']==refs['ff_reference']['MAX_ARR']
(P/'swapped_refusal.log').write_text('ROLE_BINDING_REFUSED min actual=TT expected=FF; max actual=FF expected=TT; observed native queried arcs swapped\n')
version=subprocess.check_output(['docker','image','inspect','openroad/orfs:asap7lock','--format','{{.Id}}'],text=True).strip()
(P/'receipt.json').write_text(json.dumps(dict(scope='native API calibration only; cross-PVT discriminatory fixture, NOT SC2 signoff',image_id=version,native_lib_sha256=hashes,cases=receipts),indent=2)+'\n')
print('TIMING_ROLE_API_CALIBRATION_PASS')
