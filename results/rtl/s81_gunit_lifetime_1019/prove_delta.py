from pathlib import Path
import subprocess,json,hashlib
root=Path(__file__).resolve().parents[3]
p='rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l5.sv'
old=subprocess.check_output(['git','-C',str(root),'show','d9ef2759827ab649e467ad5cb7e171f3e97c696f:'+p]).decode()
new=(root/p).read_text()
a=old.index('        reg [2:0] hit;'); b=old.index('    end else begin : g_tbl_legacy',a)
c=new.index('        if (TABLE_LIFETIME_SAFE) begin : g_lifetime_safe');d=new.index('    end else begin : g_tbl_legacy',c)
legacy=new[new.index('        reg [2:0] hit;',c):d]
assert legacy==old[a:b]+'        end\n', 'default-off legacy guard changed'
normalized=new[:c]+old[a:b]+new[d:]
normalized=normalized.replace('parameter integer FANOUT_SAFE = `OT_S81_GUNIT_FANOUT_SAFE,\n    parameter integer TABLE_LIFETIME_SAFE = 0\n','parameter integer FANOUT_SAFE = `OT_S81_GUNIT_FANOUT_SAFE\n')
assert normalized==old,'non-guard source changed'
r={'baseline_commit':'d9ef2759827ab649e467ad5cb7e171f3e97c696f','candidate_source_sha256':hashlib.sha256(new.encode()).hexdigest(),'all_non_guard_source_byte_identical':True,'default_off_legacy_guard_byte_identical':True,'writes_reads_selectors_resets_arithmetic_and_capture_ages_unchanged':True,'new_guard_state_bits':12,'old_guard_state_bits':3,'mapped_fanout_and_physical_reset_census':'OPEN'}
(Path(__file__).resolve().parent/'source_delta.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
