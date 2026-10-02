"""Read-only static contract audit; no simulator rerun or source modification."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path('/tmp/opentallas-dsrom-actual-element-prepare-20261001')
WORK=Path('/tmp/dsrom-actual-element-r2-bounded-build-r1-20261002')
OUT=Path('/tmp/dsrom-actual-element-r2-bounded-run-r1-20261002')
SOURCE='4e38326d6f361bc85e660f48c59c355e2bb95274'
sha=lambda b:hashlib.sha256(b).hexdigest()
path='rtl/v41rom/ot_v41_rom_elem_w10.sv'
raw=subprocess.check_output(['git','show',SOURCE+':'+path],cwd=ROOT)
text=raw.decode()
assert "s_row[NSEG + cfg_a_e[SW-1:0] - 1] <= cfg_d_e[15:0];" in text
assert '2NSEG+1+s' in text
cpp=(ROOT/'rtl/test/dsrom_actual_element_rom.cpp').read_text()
assert 'return (ph==4 ? 0x8000 : 0x200)+(k-17);' in cpp
bench=(ROOT/'rtl/test/tb_dsrom_actual_element_gate_r2.sv').read_text()
assert 'r_prow[15:0]<16\'h100 || r_prow[15:0]>16\'h107' in bench
assert 'r_pseg[4:0]!=0 || r_pnseg[4:0]!=1 || r_ppos[2:0]>=np' in bench
assert '{r_pv,r_pval,r_prow,r_pseg,r_pnseg,r_perr,r_ppos,r_busy,r_fault,r_quiet}' in bench
mapping=[dict(cfg_a=a,documented_s_row_index=8+(a-17),implemented_s_row_index=(7+(a&7))&15,synthetic_row_word_phase1=hex(0x200+a-17)) for a in range(17,25)]
assert [m['implemented_s_row_index'] for m in mapping]==[8,9,10,11,12,13,14,7]
assert mapping[-1]['documented_s_row_index']==15
srow=[None]*16
for k in range(8):srow[k]=0x100+k
for m in mapping:srow[m['implemented_s_row_index']]=int(m['synthetic_row_word_phase1'],16)
assert srow[7]==0x207 and srow[15] is None
findings=[]
for case in ('q','bfcolumn'):
    for side in ('ref_dut','cand_dut'):
        pattern=re.compile(r'__VdlyDim0__tb_'+case+r'__DOT__test__DOT__'+side+r'__DOT__u_e__DOT__s_row__v1\s*=\s*(.*?);',re.S)
        found=None
        for p in sorted((WORK/('obj_'+case)).glob('*.cpp')):
            data=p.read_text();match=pattern.search(data)
            if match:
                found=(p,data,match);break
        assert found,'missing generated second-row assignment'
        p,data,match=found;expression=re.sub(r'\s+',' ',match[1]).strip()
        assert '0x0000000fU' in expression and '(IData)(7U)' in expression and '(7U &' in expression
        start=data.rfind('\n',0,match.start())+1;end=data.find('\n',match.end())
        line=data[:start].count('\n')+1
        name=case+'_'+side+'_config_index_excerpt.cpp.txt'
        with (OUT/name).open('x') as f:
            f.write('Generated file: '+str(p)+'\nFull generated file SHA256: '+sha(p.read_bytes())+'\nFirst excerpt line: '+str(line)+'\n'+data[start:end]+'\n')
        findings.append(dict(case=case,side=side,file=str(p),sha256=sha(p.read_bytes()),line=line,expression=expression,excerpt=name))
record=dict(status='PROVEN_SHARED_CONFIGURATION_INDEX_CONTRACT_MISMATCH',method='Source plus generated-C++ static inspection only; no simulator retry',source_commit=SOURCE,source_path=path,source_sha256=sha(raw),geometry=dict(NSEG=8,SW=3,NB=2),documented_contract='cfg_a=2*NSEG+1+s loads row of segment s in second macro at s_row[NSEG+s]',mapping=mapping,phase1_s_row_after_all_25_cfg_words_static=['unwritten' if v is None else hex(v) for v in srow],first_macro_segment7_documented_row='0x107',first_macro_segment7_static_actual_row='0x207',second_macro_segment7_documented_index=15,second_macro_segment7_implementation_index=7,generated_findings=findings,assertion_expectation=dict(macro0_row_range=['0x100','0x107'],macro0_segment_index=0,macro0_segments_in_row=1,macro0_position_less_than='np, phase1 np=1',predicate_not_indexed_by_phase=True,macro1_checks='No complete row/order scoreboard. Only phase4 idle-macro pv check plus reference/candidate miter.'),differential_comparison='Full pv,pval,prow,pseg,pnseg,perr,ppos,busy,fault,quiet compared on original vs candidate before contract scoreboard; includes both macros and invalid-cycle payloads. Not an independent golden reference.',legal_stimulus_contract='Eight segments and eight disjoint one-unit classes, valid slot range NCH16/NCHB8, one sub-block, np1, FP8 halves both present; cfg_a24 is the documented legal final second-macro row address. No reduced RTL geometry.',confidence=dict(shared_source_decode_defect='PROVEN from literal indexing and both generated DUT namespaces for both cases',explanation_of_runtime_assertion='HIGH, consistent with failure at first FP8 phase drain; logs do not print individual row/seg/nseg/pos operands, so exact triggering field is inferred, not directly captured'),qualification=False,fixture_only_label=False,RTL_or_helper_changes=False)
with (OUT/'source_contract_audit.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(status=record['status'],generated_dut_assignments_verified=len(findings),cfg24_actual_index=7,cfg24_expected_index=15,confidence=record['confidence'])))
