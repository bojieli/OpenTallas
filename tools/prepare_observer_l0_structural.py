#!/usr/bin/env python3
"""Additive L0 structural correction. Source preparation only, no compiler.

Do not embed L20 hierarchy in an L0 module even behind a false generate. The
actual retained lint failure is authority; structural tests are prerequisites.
"""
import argparse,copy,json,re
from pathlib import Path
import prepare_simulation_observation_wrapper as packet
import prepare_observer_lint_gate as closure_tool
import plan_observer_hierarchy_gate as old

OUT='results/rtl/observer_l0_structural_4e383_20261002'
COPY='rtl/test/v41_runtime/ot_v41_rt_die_sim_observe_l0_window.sv'
TOP='ot_v41_rt_die_sim_observe_l0_window'
START='// BEGIN WINDOW ONLY OBSERVER'
END='// END WINDOW ONLY OBSERVER'


def header():
    return f'    input wire [63:0] sim_obs_epoch, // host reset era; never drives engine\n    output reg sim_obs_valid,\n    output reg [{packet.BITS-1}:0] sim_obs_packet, // CKV slots reserved; API unavailable\n'


def render(original):
    fields=packet.layout();ckv=[f for f in fields if f['ckv']]
    first=min(f['offset'] for f in ckv)
    assert all(f['ckv'] for f in fields if f['offset']>=first)
    text=original.replace('module ot_v41_rt_die #(',f'module {TOP} #(\n    parameter bit SIM_OBS_ENABLE = 0,')
    text=text.replace('    input  wire              clk,',header()+'    input  wire              clk,')
    lines=[START,'`ifdef SYNTHESIS','initial $fatal(1, "simulation observer cannot be synthesized");','`endif','reg [63:0] sim_obs_cycle;',f'wire [{packet.BITS-1}:0] sim_obs_raw;','initial begin','  if (RANK < 0 || RANK > 3) $fatal(1, "observer rank envelope");','end','generate if (SIM_OBS_ENABLE) begin : g_sim_observe']
    for f in fields:
        if f['ckv']:continue
        expr="1'b0" if f['name']=='ckv_available' else f['expression']
        lines.append(f"assign sim_obs_raw[{f['offset']} +: {f['width']}] = {expr};")
    lines.extend([f"assign sim_obs_raw[{first} +: {packet.BITS-first}] = '0; // ABI padding, no observations",'end else begin',"assign sim_obs_raw = '0;",'end endgenerate','always @(posedge clk or negedge rst_n) begin',"  if (!rst_n) begin sim_obs_cycle <= 0; sim_obs_valid <= 0; sim_obs_packet <= '0; end",'  else begin',"    sim_obs_cycle <= sim_obs_cycle + 1'b1;",'    sim_obs_valid <= SIM_OBS_ENABLE && dut.rn;','    sim_obs_packet <= sim_obs_raw;','  end','end',END])
    return text.replace('endmodule','\n'+'\n'.join(lines)+'\nendmodule')


def inverse(text):
    start=text.index('\n'+START);end=text.index(END,start)+len(END)
    text=text[:start]+text[end+1:]
    return text.replace(header(),'').replace(f'module {TOP} #(\n    parameter bit SIM_OBS_ENABLE = 0,','module ot_v41_rt_die #(')


def assert_l0_only(text):
    # Check the whole module, without deleting comments or inactive branches.
    for forbidden in ['g_ckv','u_ckv','SIM_OBS_CKV_SELECTED','.CKV_SELECTED(',closure_tool.CKV_COPY]:
        if forbidden in text:raise ValueError('non-L0 hierarchy/configuration in copy: '+forbidden)
    observer_body=text[text.index(START):text.index(END)]
    for ref in re.findall(r'\bdut(?:\.\w+)+',observer_body):
        if '.g_' in ref and not ref.startswith('dut.g_packed_kv.g_window_hbm_attention.u_source'):
            raise ValueError('unsupported observer scope '+ref)


def prepare(repo):
    repo=Path(repo);out=repo/OUT
    original=packet.original(repo);corrected=render(original)
    assert inverse(corrected)==original
    assert_l0_only(corrected)
    (repo/COPY).write_text(corrected)
    prior_bytes=(repo/closure_tool.OUT/'plan.json').read_bytes();plan=json.loads(prior_bytes)
    window=plan['modes'][0];oldcopy=window['copy'];oldtop=window['top']
    inputs={path:(repo/path).read_text() if path==oldcopy else old.blob(repo,path).decode() for path in window['source_sha256']}
    inputs.pop(oldcopy);inputs[COPY]=corrected
    closure=closure_tool.closure(inputs,TOP)
    if closure['ambiguous'] or set(closure['unresolved'])-closure_tool.GUARDS:raise ValueError('unresolved original ownership')
    window['top']=TOP;window['copy']=COPY;window['parameters'].pop('SIM_OBS_CKV_SELECTED')
    window['closure']=closure
    paths=sorted(set(closure['files']+closure['support']))
    window['source_sha256']={p:old.sha(inputs[p].encode()) for p in paths}
    window['source_bytes']=sum(len(inputs[p].encode()) for p in paths)
    compilefiles=[p for p in closure['support'] if not p.endswith('.svh')]+[p for p in closure['files'] if p not in closure['support']]
    # Keep every option/parameter and real ancestor unchanged except obsolete
    # CKV observation flag, top namespace and generated WINDOW copy path.
    argv=[a.replace(oldtop,TOP).replace(oldcopy,COPY) for a in window['argv'] if a!='-GSIM_OBS_CKV_SELECTED=0']
    assert set(compilefiles)=={a for a in argv if a.endswith(('.sv','.v'))}
    window['argv']=argv
    assert plan['modes'][1]==json.loads(prior_bytes)['modes'][1]
    prior_failure=repo/'results/rtl/observer_lint_execution_4fed19018_20261002/terminal_receipt.json'
    plan.update(base_commit='277d7f2c167b279a23ab2a50f3b60cb473cc3a69',qualification='ACTUAL_PRIOR_FAIL_AUTHORITY_NEW_STRUCTURAL_CANDIDATE_NOT_LINTED',actual_failure=dict(commit='277d7f2c167b279a23ab2a50f3b60cb473cc3a69',receipt_path=str(prior_failure.relative_to(repo)),receipt_sha256=old.sha(prior_failure.read_bytes()),verdict='FAIL_RETAINED',trigger='L0 has no g_ckv/u_ckv even when conditional observer flag is constant0'),structural_correction=dict(copy=COPY,original=packet.ORIGINAL,original_sha256=old.sha(original.encode()),copy_sha256=old.sha(corrected.encode()),exact_inverse=True,default_observation=0,ckv_hierarchy_references=0,ckv_configuration_parameters=0,ckv_padding='reserved zeros with ckv_available0; typed API returns None/unavailable for each absent CKV field, never zero-qualified',packet_bits=packet.BITS,simulation_register_bits=packet.BITS+65),ckv_scope='UNCHANGED separate real L20 observer, ports and driver parameters; not compiled by this preparation',limits=['Actual prior lint FAIL overrides fake/static confidence. No new elaboration PASS claimed.','Original ancestors and failed wrapper/receipt unchanged. Only new WINDOW copy namespace and observation body introduced.','No compiler/version invocation, simulator, full build, live getter/source-list selection or hardware qualification.','Independent new GO required; old GO hash cannot authorize this new plan.','Causal service BOUND_MISSING unchanged.'])
    additional=['tools/prepare_observer_l0_structural.py','tools/observer_l0_unavailable_api.py','tools/prepare_simulation_observation_wrapper.py','tools/prepare_observer_lint_gate.py','tools/plan_observer_hierarchy_gate.py']
    plan['preparation_tools'].update({p:old.sha((repo/p).read_bytes()) for p in additional})
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    template=dict(plan_sha256=old.sha((out/'plan.json').read_bytes()),decision='PENDING',reviewer='',source_ownership_and_guard_provenance_reviewed=False,resource_caps_reviewed=False,lint_only_no_live_selection=True)
    (out/'GO.template.json').write_text(json.dumps(template,indent=2)+'\n')
    for m in plan['modes']:
        files=[a for a in m['argv'] if a.endswith(('.sv','.v'))]
        (out/(m['name']+'.f')).write_text('\n'.join(files)+'\n')
    return plan
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');a=ap.parse_args();plan=prepare(a.repo)
    print(json.dumps(dict(status=plan['qualification'],copy=plan['structural_correction'],GO='PENDING'),indent=2))
