import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('repaired',ROOT/'tools/w17_window_actual_producer_cancel_declaration_repair.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
s2=importlib.util.spec_from_file_location('old',ROOT/'tools/w17_window_actual_producer_cancel_prepare.py');old=importlib.util.module_from_spec(s2);s2.loader.exec_module(old)

def test_original_bug_is_preserved_and_new_declarations_are_real():
 _,bad,_,_,_=old.candidate()
 assert bad.startswith('module does not drive')
 with pytest.raises(ValueError):m.validate_declarations(bad)
 _,good,_,_,_=m.candidate()
 assert good.startswith('`timescale 1ns/1ps\nmodule '+m.NAME+'_cancel #(')
 assert m.validate_declarations(good)==[m.NAME+'_cancel',m.NAME+'_cancel_legacy',m.NAME+'_cancel_enabled']
 assert 'module does not drive' not in good


def test_anchor_skips_comment_word_and_requires_unique_declaration():
 raw=m.origin(m.PRODUCER);real=m.extract_declared_module(raw)
 assert real.startswith('module '+m.NAME+' #(')
 assert m.extract_declared_module('// module misleading\n'+raw)==real
 with pytest.raises(ValueError):m.extract_declared_module(raw.replace('module '+m.NAME,'// module '+m.NAME))
 with pytest.raises(ValueError):m.extract_declared_module(raw+'\n'+real)
 with pytest.raises(ValueError):m.extract_declared_module(raw.replace('endmodule','// endmodule'))


def test_default_inverse_equals_actual_module_and_semantics_unchanged():
 _,text,real,legacy,enabled=m.candidate()
 assert legacy.replace(m.NAME+'_cancel_legacy',m.NAME,1)==real
 _,bad,_,_,bad_enabled=old.candidate()
 assert enabled==bad_enabled[bad_enabled.index('module '+m.NAME+'_cancel_enabled'):]
 old_clean='\n'.join(line for line in bad.splitlines() if line!='module does not drive the old scalar KVT write port.')+'\n'
 assert text=='`timescale 1ns/1ps\n'+old_clean
 assert 'parameter integer OPT_CANCEL = 0' in text
 assert (m.OUT/'ot_hdc_v41x_window_kv_blocks_cancel.sv').read_text()==text

@pytest.mark.parametrize('rogue',['module does not drive old port.','module wrong #(','module '+m.NAME+'_cancel_enabled NOT_A_HEADER'])
def test_invalid_declaration_mutants_rejected(rogue):
 _,text,_,_,_=m.candidate()
 with pytest.raises(ValueError):m.validate_declarations(rogue+'\n'+text)


def test_source_hooks_price_unchanged_no_vm_gate_or_new_state():
 p=m.plan();assert p==old.plan()
 e=p['unified_compatible_entry'];assert e['prepared_local_ack_state_bits']==2 and e['future_suffix_and_freeze_state_bits']==8
 assert e['concrete_subtotal_bits']==10 and e['prior_conservative_local_adapter_envelope_bits']==19
 assert 'Continue raw QE reads/arithmetic/VM writes until source idle' in str(p['core_hooks'])
