#!/usr/bin/env python3
"""Real static TP8 return/status mechanism on the current compiler programme.

This produces component observations, not a bound-die status receipt. The
compiler's measured_qwen_1019 contract selects LU53/LS378 and return age2;
current physical plan/START qualification remains separate.
"""
import hashlib,importlib.util,json,os,re,subprocess,sys
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/tok-verify-2')
D=Path('/srv/opentallas-scratch2/claude/tok-verify-2/collective_return')
D.mkdir(exist_ok=True);os.chdir(W)
sys.path[:0]=[str(W/'tools'),str(W/'tools/qwen_layerbench'),str(W/'rtl/test/qwen_dv')]
import toksim_compose as T
import qwen_coll_tp8_static_links_bench as C
import dv_bench2 as B
inp=json.loads((W/'results/token_pass/measured_qwen_1019/inputs.json').read_text())
captures=[];original=T.L.compose
def capture(*a,**kw):
 r=original(*a,**kw)
 if kw.get('tile_mode')=='measured' and 'die_edges' in kw:captures.append(r)
 return r
T.L.compose=capture
price=T.compose(inp,variant='asbuilt')
native=captures[-1]
(D/'native_programme.json').write_text(json.dumps(native,indent=2)+'\n')
xc=[e for e in native['events']if ': XC tag ' in e['label']]
assert len(xc)==2 and all('tag 0 ' in e['label']for e in xc),xc
# Exact lower_xc: W5 chain entry -> measured cc age2 -> command lane2 ->
# command pin register1. Programme is never greedily moved to a vacant edge.
ages=T.L.M.load_ages() if hasattr(T.L.M,'load_ages') else json.loads((W/T.L.M.STN_AGES).read_text())
cc_age=ages['xc_cc']
commands=[(int(e['edge_w5'])+cc_age+2+1,0)for e in xc]
prog=C.mu_prog(commands,[256,256],53,378,False)
(D/'programme_context.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),input_file='results/token_pass/measured_qwen_1019/inputs.json',input_sha256=hashlib.sha256((W/'results/token_pass/measured_qwen_1019/inputs.json').read_bytes()).hexdigest(),native_xc=xc,component_programme=prog,constructor_variant='asbuilt',declared_contract=dict(LU=53,LS=378,cc_lane=2,return_lane=2,xc_cc_age=cc_age),physical_bound_receipt=False,reason='Selected logical compiler input contract only; current physical source/START/return-lane binding is unavailable. Priced ctlm plan XC-after-END is not the emitted native programme.'),indent=2)+'\n')
tb=(W/'rtl/test/tb_coll_tp8_static_links.sv').read_text()
assert tb.count('module tb_coll_tp8_static_links ')==1
tb=tb.replace('endmodule',(D/'status_observer.sv').read_text()+'\nendmodule',1)
# Both actual emitted lower_xc calls currently use tag0. Preserve that exact
# field, rather than silently assigning the fixture's historical tags0/1.
tb=tb.replace('TAGBASE | pm',"32'd0").replace('(TAGBASE | cm)',"32'd0")
private_tb=D/'tb_coll_tp8_static_links.sv';private_tb.write_text(tb)
sources=C.SRC[:-1]+[private_tb]
sources += [W/s for s in B.SRCS2 if not s.endswith('tb_qfd_dv2.sv')]
sources += [W/s for s in (W/'rtl/test/qwen_dv/tt_ctlm_dv_sources.f').read_text().splitlines()if s]
sources += [W/'rtl/qwen_dv/qfd_dv_slice2_lpf_parts_rsafe.sv',W/'rtl/qwen_dv/qfd_dv_reset_tree.sv']
sources=list(dict.fromkeys(sources));seen=set();selected=[]
for p in sources:
 mods=set(re.findall(r'^module\s+(\w+)',p.read_text(),re.M))
 if mods and mods<=seen:continue
 if mods&seen:
  # The slice's guarded SRAM file groups32x546 (already supplied by the
  # collective's actual physical macro model) and32x64. Retain the exact
  # remaining32x64 module, with its collision checker unchanged.
  assert p.name=='sram_model.sv' and mods=={'ot_sram_1r1w_32x546_m1','ot_sram_1r1w_32x64_m1'},p
  text=p.read_text();remaining=sorted(mods-seen)
  body='\n'.join(re.search(r'(?m)^module\s+'+re.escape(n)+r'\b[\s\S]*?\bendmodule\b',text).group()for n in remaining)
  private=D/'slice_unique_sram.sv';private.write_text('`timescale 1ns/1ps\n'+body+'\n')
  (D/'sram_source_selection.json').write_text(json.dumps(dict(original=str(p),original_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),retained_modules=remaining,reason='Avoid duplicate32x546 model; complete32x64 module copied byte-for-byte with collision checker'),indent=2)+'\n')
  p=private;mods=set(remaining)
 seen.update(mods);selected.append(p)
C.SRC=selected
(D/'sources.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in selected},indent=2)+'\n')
exe=C.build(D,53,378,0,0,0,qfd=True,relays=(8,8,8,8))
vec=D/'vec';C.vectors(vec,[256,256],prog,1000)
pw=C.program_words(prog,[256,256],cmd_pin_stages=1,start=40)
pw=[(ad,0 if ad in (1,3)else word)for ad,word in pw]
(vec/'pw.hex').write_text(''.join(f'{ad:03x}{word:016x}\n'for ad,word in pw))
records=[]
for name,negative in [('actual',False),('last_skew_control',True)]:
 args=[str(exe),f'+VEC={vec}','+NMSG=2',f'+NPW={len(pw)}','+START=40']
 if negative:args.append('+STATUS_LAST_DELAY=1')
 r=subprocess.run(args,cwd=W,capture_output=True,text=True)
 log=r.stdout+r.stderr;(D/(name+'.log')).write_text(log)
 raw=[dict(zip(('edge','message','ar_land','ar_last'),map(int,m)))for m in re.findall(r'SS5_RAW edge=(\d+) message=(-?\d+) ar_land=(\d+) ar_last=(\d+)',log)]
 done=[int(x)for x in re.findall(r'SS5_CTL_DONE edge=(\d+)',log)]
 real_ok=r.returncode==0 and any(x.strip()=='PASS'for x in log.splitlines())
 ok=real_ok and ((len(done)!=2)if negative else len(done)==2)
 rec=dict(name=name,expectation='negative caught'if negative else'component pass',passed=ok,collective_payload_gate=real_ok,raw_ss5=raw,ctl_done_edges=done,physical_bound_receipt=False,native_calendar_qualified=False)
 records.append(rec);print(json.dumps(rec,indent=2),flush=True)
(D/'component_receipt.json').write_text(json.dumps(dict(schema='opentallas.qwen.collective-status-component.v1',cases=records,qualified_bound_receipt=False),indent=2)+'\n')
sys.exit(0 if all(r['passed']for r in records)else 1)
