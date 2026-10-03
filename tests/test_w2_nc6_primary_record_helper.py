import importlib.util,json,random,subprocess,shutil
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('helper',ROOT/'tools/w2_nc6_primary_record_helper.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

def test_exact_partition_and_record_widths():
 h.check_mapping();m=h.model();assert (m['primary_words'],m['secondary_words'],m['total_words'])==(182,37,219)
 assert m['new_state_bits']==m['new_handshakes']==m['added_pipeline_edges']==0
 assert [r['index'] for r in h.slots('prepared_write',0)]==[169,170]
 assert [r['index'] for r in h.slots('correction_context',7)]==[166,167,168]

def test_generated_source_and_model_byte_exact():
 assert h.RTL.read_text()==h.source()
 assert (h.OUT/'model.json').read_text()==json.dumps(h.model(),indent=2)+'\n'

def test_basis_every_named_record_bit():
 clean=(1<<219)-1
 for name,out,width,count in h.RECORDS:
  for instance in range(count):
   shift=0
   for row in h.slots(name,instance):
    for bit in range(row['payload_bits']):
     payload=[0]*219;payload[row['index']]=1<<bit
     assert h.values(payload,clean,0,0)[out]==1<<(instance*width+shift+bit)
    shift+=row['payload_bits']

def test_secondary_damage_not_aliased_to_primary():
 payload=[0]*219;clean=(1<<219)-1
 for i in h.MAP['secondary']:
  r=h.values(payload,clean,1<<i,1<<i);assert r['primary_clean']==1 and not r['primary_ce'] and not r['primary_bad']
 # This is not full-controller permit; its caller MUST separately qualify37.
 for i in h.MAP['primary']:
  r=h.values(payload,clean,1<<i,0);assert not r['primary_clean'] and r['primary_ce']

@pytest.mark.parametrize('bad',[-1,1<<44,True,1.25])
def test_payload_envelope_rejected(bad):
 payload=[0]*219;payload[169]=bad
 with pytest.raises(ValueError):h.values(payload,(1<<219)-1,0,0)

def make_tb():
 ports=[('primary_clean',1),('primary_ce',1),('primary_bad',1)]
 for _,name,w,c in h.RECORDS:ports.extend([(name,w*c),(name+'_clean',c)])
 lines=['module tb;','reg [9635:0] current_payload; reg [218:0] current_clean,current_ce,current_bad;']
 for name,w in ports:lines.extend([f'wire [{w-1}:0] {name};',f'wire [{w-1}:0] off_{name};'])
 inputs=['.current_payload(current_payload)','.current_clean(current_clean)','.current_ce(current_ce)','.current_bad(current_bad)']
 lines+=['ot_w2_nc6_primary_record_view #(.OPT_PROTECTION(1)) dut('+','.join(inputs+[f'.{n}({n})' for n,_ in ports])+');','ot_w2_nc6_primary_record_view disabled('+','.join(inputs+[f'.{n}(off_{n})' for n,_ in ports])+');','initial begin']
 rng=random.Random(21918237);payload=[rng.getrandbits(row['payload_bits']) for row in h.ROWS];allclean=(1<<219)-1
 def sample(p,clean,ce,bad):
  packed=sum(x<<(44*i) for i,x in enumerate(p));exp=h.values(p,clean,ce,bad)
  lines.extend([f"current_payload=9636'h{packed:x}; current_clean=219'h{clean:x}; current_ce=219'h{ce:x}; current_bad=219'h{bad:x}; #1;"])
  for name,w in ports:lines.append(f"if({name} !== {w}'h{exp[name]:x}) $fatal(1,\"{name}\");")
  for name,_ in ports:lines.append(f"if(off_{name} !== '0) $fatal(1,\"default_off\");")
 sample(payload,allclean,0,0)
 # CURRENT-code qualification for all219 words, including journals/context tails.
 for i in range(219):
  sample(payload,allclean^(1<<i),0,0)
  sample(payload,allclean,1<<i,0)
  sample(payload,allclean,0,1<<i)
 # Held values change only with the supplied current decoded record, no ready/eval state.
 changed=payload.copy();changed[96]^=1;sample(changed,allclean,0,0);sample(payload,allclean,0,0)
 lines+=['$display("PASS PRIMARY_RECORD_VIEW samples=660 default_off=1"); $finish; end','endmodule']
 return '\n'.join(lines)+'\n'

def execute(tmp,source):
 assert shutil.which('iverilog') and shutil.which('vvp')
 sv=tmp/'helper.sv';tb=tmp/'tb.sv';sv.write_text(source);tb.write_text(make_tb())
 build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp/'sim'),str(sv),str(tb)],capture_output=True,text=True)
 assert build.returncode==0,build.stderr
 run=subprocess.run(['vvp',str(tmp/'sim')],capture_output=True,text=True)
 (tmp/'build.log').write_text(build.stdout+build.stderr);(tmp/'run.log').write_text(run.stdout+run.stderr)
 return run

def test_actual_rtl_held_records_current_integrity_and_default_off(tmp_path):
 p=execute(tmp_path,h.source());assert p.returncode==0 and 'PASS PRIMARY_RECORD_VIEW' in p.stdout

@pytest.mark.parametrize('mutant',['wrong_journal_word','ignored_CE','missing_primary_scheduler'])
def test_real_source_mutants_rejected(tmp_path,mutant):
 s=h.source()
 if mutant=='wrong_journal_word':
  original='current_payload[7436 +: 44]';assert original in s;s=s.replace(original,'current_payload[7524 +: 44]',1)
 elif mutant=='ignored_CE':s=s.replace('current_clean & ~(current_ce | current_bad)','current_clean & ~current_bad')
 else:
  mask=sum(1<<i for i in h.MAP['primary']);s=s.replace(f'{mask:055x}',f'{mask^(1<<187):055x}')
 p=execute(tmp_path,s);assert p.returncode!=0 and 'FATAL' in p.stdout
