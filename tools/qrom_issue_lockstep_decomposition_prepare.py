#!/usr/bin/env python3
"""Source-qualified control proof decomposition preparation; no solver launch."""
import argparse,hashlib,json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=ROOT/'results/uarch/qwen_rom_issue_lockstep_terminal_20261003/raw/literal.sv'
PARAM={'NW':18,'AW':24,'PRW':14,'IL':8,'NB_GT':14}
def number(expr):
 s=expr.replace('$clog2(IL)','3')
 for k,v in PARAM.items():s=re.sub(r'\b'+k+r'\b',str(v),s)
 if not re.fullmatch(r'[0-9+\- ()]+',s):raise ValueError('unbound width '+expr)
 return eval(s,{'__builtins__':{}},{})
def prepare():
 snapshot=RAW.parent.parent/"source-inputs"
 sys.path.insert(0,str(snapshot/"tools"))
 from qwen_rom_issue_lockstep_gate import source
 raw=RAW.read_text();actual=source()
 if raw!=actual:raise ValueError('current extracted source differs pinned original generated literal')
 control=raw.split('module source_boundary',1)[0]
 # Exclude automatic-function temporaries, retain every actual control state register.
 body=control.split(');',1)[1]
 body=re.sub(r'/\*.*?\*/|//[^\n]*','',body,flags=re.S)
 decl=re.sub(r'function automatic.*?endfunction','',body,flags=re.S)
 rows=[dict(name=n,width=w,elements=1,bits=w) for n,w in [('wrom_re',1),('kv_re',1),('wrom_addr',24)]]
 for m in re.finditer(r'\breg\s*(\[[^\]]+\])?\s*([^;]+);',decl):
  width=1
  if m[1]:hi,lo=m[1][1:-1].split(':');width=number(hi)-number(lo)+1
  for name in m[2].split(','):
   n=re.fullmatch(r'\s*(\w+)\s*(?:\[\s*0\s*:\s*([^\]]+)\])?\s*',name)
   if not n:raise ValueError('unparsed source reg '+name)
   count=number(n[2])+1 if n[2] else 1
   rows.append(dict(name=n[1],width=width,elements=count,bits=width*count))
 names={r['name'] for r in rows}
 needed={'active','pend','pcnt','split_fault','t','k','j','t_last','k_last','tiles_r','ktot_r','k_r','wsrc_r','split_r','cur','base_k','base_t','ts_r','ots_r','tsh','osh','tsg_a','otsg_a','pr_a','kpad_a','kc_a','tstep_r','ot_step'}
 if not needed<=names:raise ValueError('state inventory missing '+str(needed-names))
 cells=[]
 for m in re.finditer(r'(ot_qwen_w12_kadd|ot_qwen_w12_ksum)\s*#\((.*?)\)\s+(\w+)\s*\((.*?)\);',control,re.S):
  typ,param,inst,ports=m.groups();w=re.search(r'\.W\(([^)]+)\)',param)
  if not w:raise ValueError('unbound actual operator width')
  rowsn=re.search(r'\.N\(([^)]+)\)',param)
  cells.append(dict(module=typ,instance=inst,width=number(w[1]),rows=number(rowsn[1]) if rowsn else None,source_ports=ports,
    replacement_allowed=False,required_lemma='same actual module/parameters + bitexact input equality at delayed qualified edge implies output equality; prove operator circuit before replacing cut cone'))
 if len(cells)!=16:raise ValueError('expected actual14prefix-adders+2sums')
 return dict(schema='QROM_LITERAL_LOCKSTEP_SOURCE_DECOMPOSITION_PREP_V1',scope='same control-only projection as original; not whole engine/ready owner/provider/datapath/physical proof',
  solver_launched=False,proof_pass=False,old_induction_restart=False,source_literal_sha256=hashlib.sha256(raw.encode()).hexdigest(),
  source_sha256={p:hashlib.sha256((snapshot/p).read_bytes()).hexdigest() for p in ['rtl/hdc/ot_qwen_w12_matvec.sv','rtl/hdc/ot_qwen_me_array_w12.sv','rtl/hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv','rtl/hdc/ot_qwen_w12_arith.sv','rtl/hdc/ot_hdc_delay.sv','tools/qwen_rom_issue_lockstep_gate.py','tools/qwen_rom_literal_launch_pipeline_gate.py']},
  parameters=dict(BD=1,IREG=1,XVM=0,KV_PREP=3,SMIN=6,GT=6144,PART_root=2,PART_tile=1,IL=8),
  exact_control_registers=rows,control_declared_bits=sum(r['bits'] for r in rows),arithmetic_operator_instances=cells,
  coupled_state_candidate=dict(status='PREPARATION_ONLY_NOT_PROVED',delay_edges=1,
    relation='tile state at t equals root state at t-1 only under source-derived initialization/use qualifiers',
    phase=['active','pend','pcnt','split_fault','wrom_re','kv_re'],
    instruction_and_loop_state=[r['name'] for r in rows if r['name'] not in {'active','pend','pcnt','split_fault','wrom_re','kv_re','wrom_addr','tsh','osh','pr_a','kpad_a','tsg_a','otsg_a','kc_a','tstep_r','ot_step','k_r','nb_step','lb_step'}],
    pipeline_stage1=['tsh','osh','pr_a','kpad_a'],pipeline_stage2=['tsg_a','otsg_a','kc_a','nb_step','lb_step'],pipeline_stage3=['tstep_r','ot_step','k_r'],
    qualifications=['phase after shared reset and one delayed edge','command and loop seeds after matched accepted go; hold while idle/pend unless actual source writes','stage validity derived from last accepted instruction age and actual every-edge updates; never force unreset values to zero','wrom_addr compared only under actual qualified ROM read'],
    no_behavior_restriction=True,no_added_input_hold=True,arbitrary_binary_go_and_payload_retained=True,
    note='DYN retention/whole caller behavior not extracted by this control-only projection; separate source obligation remains open'),
  initialization=dict(initial_reset_required=True,binary_input_contract_only=True,unreset_instruction_and_term_regs=True,
    no_zero_initialization_substitution=True,source_term_pipeline_depth=3,IL8_first_boundary_use_must_be_proved=True,
    full_delayed_register_equality_before_qualification_not_assumed=True),
  decomposition=[dict(id='P0',goal='retain accepted go=go&&ready and all379 instruction bits +128 x bits delayed exactly1; reset-valid sampling, every-edge inputs',proof_source='literal launch source proof prerequisite; no independent ready substitute'),
    dict(id='P1',goal='accepted instruction fields/counters/cur seed relation after actual root acceptance reaches tile; root go while active/pend ignored',state='all command-latched fields plus t/k/j/t_last/k_last/cur/base/x/address seed; not just7bit exported state'),
    dict(id='P2',goal='qualified tsh/osh/pr_a/kpad_a -> tsg/otsg/kc -> tstep/ot_step/k_r correspondence; model exact3stage age',state='invalid/unreset terms excluded only under proven valid-age/use predicates; actual first IL8 boundary deadline'),
    dict(id='P3',goal='actual prefix-add/sum circuit contracts at18/19/24/38bit widths; same source operands at one-edge relation',state='all16 operator cuts retain parameters/sign/truncation and bitexact inputs; no free unconstrained output assumptions'),
    dict(id='P4',goal='full strengthened state recurrence active/pend/prep/k/t/j/last/address under P0-P3; delayed read strobes and qualified ROM address',state='hold commands/DYN-related retained fields remain source-bound; source legal binary inputs unchanged'),
    dict(id='P5',goal='one-step coupled-state preservation only; global induction/reachability composition remains deferred',state='actual owned-ready/globalbroadcast/provider/current datapath and physical pin context remain open')],
  engine_data_arithmetic_removed=False,control_address_arithmetic_removed=False,
  arithmetic_shared_or_abstracted_before_exact_lemma=False,
  model_scope=dict(verification_only=True,new_RTL=False,hardware_area_delta=0,hardware_ports_delta=0,hardware_cycles_delta=0,
    actual_solver_resource_bound=None,heavy_solver_build_admission=False,one_step_only=True,critical_path=False,cheap_cut_gate_next='source extraction/operator/initialization obligations first; no replay of56stepolithic induction'),
  mutant_obligations=['ungated go broadcast rejected','KV_PREP mismatch rejected','379bit payload bit/order mutant rejected','retained-field update under unaccepted ib rejected','premature3stage term validity rejected','wrong18/19/24/38width or truncation arithmetic rejected'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('exclusive preparation output required')
 a.output.write_text(json.dumps(prepare(),indent=2,sort_keys=True)+'\n')
