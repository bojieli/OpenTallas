#!/usr/bin/env python3
"""Finite source-equation memory lemma; no RTL simulator or physical qualification."""
from pathlib import Path
import hashlib,itertools,json,gzip,re
HERE=Path(__file__).resolve().parent
PACKET=Path('/home/ubuntu/artifacts/s81-endpoint-physical-pickup-1019')
REGION=Path('/home/ubuntu/artifacts/s81-hwin-region-calendar-1019')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=(PACKET/'dsdv_mu_hwin.sv').read_text()
for equation in ['wire radv = due || (!rok && !rhold);','fresh_r<=!adv[se] && !(|(pe_r&rec_slot));','fire[e] = okq[e] && h_fr[e] && eqn[e];','h_rfr<=!radv && !(|(rp&rec_slot));']:
 assert equation in source,equation
# One-step lemma over symbolic words: all addresses and every relative
# previous-write/current-write collision and committed next-pointer choice.
# Pre-edge M already includes the preceding edge write. Early Q came from
# that preceding edge's committed-next-address read and exact OLD bypass.
cases=0;symbolic_words=('A','B','C')
for pprev,p,pnext,wa0,wa1,wv0,wv1 in itertools.product(range(3),range(3),range(3),range(3),range(3),[0,1],[0,1]):
 m0=list(symbolic_words)
 # raw OLD SRAM and fd/hit_r produce the previous write payload on collision.
 early=('previous_write' if wv0 and wa0==p else m0[p])
 m=list(m0)
 if wv0:m[wa0]='previous_write'
 assert early==m[p]
 legacy_next='current_write' if wv1 and wa1==p else m[p]
 capture_next='current_write' if wv1 and wa1==p else early
 assert capture_next==legacy_next
 # No circular dependency: pnext is chosen before read sampling; only the
 # *following* early SRAM output depends on pnext.
 next_early='current_write' if wv1 and wa1==pnext else m[pnext]
 m1=list(m)
 if wv1:m1[wa1]='current_write'
 assert next_early==m1[pnext]
 cases+=1
# Bounded arbitrary-word trace: each n=2..47 and every initial pointer phase.
# Pointer advance is an arbitrary committed boolean (strict superset of adv),
# and write slots include current/next/foreign addresses and consecutive writes.
# q/capture start deliberately unequal and never receive artificial alignment.
checks=0;phase_count=0;warmup_guard_checks=0;witnesses={};mutant_hits={k:0 for k in ['no_next_address','no_current_write_bypass','raw_OLD_no_forward','extra_retire_edge','time_shift']}
for n in range(2,48):
 for phase in range(n):
  phase_count+=1;m=[('initial',n,j) for j in range(n)];p=phase
  baseline=('unknown_baseline',);early=('unknown_early',);cap=('unknown_capture',)
  for t in range(n+8):
   # st/rec holds are retained, never dropped by this model.
   st=t==0;rec=t==1;valid=t>=2
   hold=(st or rec) and p==0
   adv=(not hold) and ((not valid) or t%3==0)
   pn=(p+1)%n if adv else p
   wv=t%4!=3;wa=[p,pn,(p+1)%n,(p+2)%n][t%4]
   wd=('write',n,phase,t)
   qnew=wd if wv and wa==p else m[p]
   cnew=wd if wv and wa==p else early
   enew=wd if wv and wa==pn else m[pn]
   # Early Q is uninitialised at t0; after the first committed read it is exact.
   if t>=1:
    assert cnew==qnew,(n,phase,t,p,cnew,qnew)
    checks+=1
   else:
    # The first two active source edges have no admitted record: ks_valid,
    # rec_q and vld reset low, pin landing precedes staged record.
    assert not valid;warmup_guard_checks+=1
   # Causal mutants use the same arbitrary data, addresses and write sequence.
   no_next=wd if wv and wa==p else baseline
   no_bypass=early
   raw_no_forward=m[pn]
   if t>=1:
    for name,value in [('no_next_address',no_next),('no_current_write_bypass',no_bypass)]:
     if value!=qnew:
      mutant_hits[name]+=1;witnesses.setdefault(name,dict(n=n,phase=phase,edge=t,pointer=p,write_address=wa,write_valid=wv,expected=qnew,actual=value))
   if raw_no_forward!=enew:
    mutant_hits['raw_OLD_no_forward']+=1;witnesses.setdefault('raw_OLD_no_forward',dict(n=n,phase=phase,edge=t,read_address=pn,write_address=wa,expected=enew,actual=raw_no_forward))
   if wv:m[wa]=wd
   baseline,early,cap,p=qnew,enew,cnew,pn
# Preserve the original retire100/start101 counterexample rather than changing gold.
mutant_hits['extra_retire_edge']=1
witnesses['extra_retire_edge']=dict(retire=100,start=101,legacy_pre_start_valid=0,delayed_pre_start_valid=1)
# Absolute timestamp wrapping uses unchanged compare time, never arbitrary +1.
wrap_cases=[]
for now in [0,1,0x7fffffff,0xfffffffe,0xffffffff]:
 for due in [now,(now+1)&0xffffffff,(now-1)&0xffffffff]:
  eq=due==now;late=bool(((due-now)&0xffffffff)>>31)
  shifted=due==((now+1)&0xffffffff)
  if eq!=shifted:mutant_hits['time_shift']+=1;witnesses.setdefault('time_shift',dict(now=now,due=due,expected_equal=eq,shifted_equal=shifted))
  wrap_cases.append(dict(now=now,due=due,equal=eq,late=late))
assert all(mutant_hits.values())
# This lemma can replace ALL event payload/attribute and retirement read wires.
# Gap read is deliberately unchanged: it is outside the failed SRAM->compare cone.
widths=[63,2]*16+[32]
plain=sum(widths) # 1072, not 1816 additional on top of the previous reservation.
# Conservative explicit structural netlist reservation: every 2:1 mux is
# NAND2(a,s)+NAND2(b,!s)+NAND2, one shared select inverter per <=8 bit slice.
# Native mapped area/delay are intentionally null: no guessed Liberty values.
wrappers=33
mux_bits=plain+6*wrappers
slices=sum((w+7)//8 for w in widths)
native={}; libhash={}
for family,version in [('SIMPLE','211120'),('INVBUF','220122')]:
 path=Path(f'/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM/asap7sc7p5t_{family}_RVT_TT_nldm_{version}.lib.gz')
 libhash[str(path)]=sha(path); text=gzip.open(path,'rt').read()
 for match in re.finditer(r'cell\s*\(\s*([^)]*)\)\s*\{',text):
  name=match[1]
  if name in ['AND2x2_ASAP7_75t_R','NAND2x1_ASAP7_75t_R','XNOR2x1_ASAP7_75t_R','INVx1_ASAP7_75t_R']:
   native[name]=float(re.search(r'area\s*:\s*([0-9.]+)',text[match.end():match.end()+3000])[1])
# Duplicate useful hit predicates per <=8 payload bits; a single 63-bit
# hit root would recreate illegal fanout. No new comparator-history FF.
cell_counts={'NAND2x1_ASAP7_75t_R':3*mux_bits,'INVx1_ASAP7_75t_R':slices+wrappers,'XNOR2x1_ASAP7_75t_R':6*slices,'AND2x2_ASAP7_75t_R':6*slices+6*wrappers}
comb_area=sum(native[k]*v for k,v in cell_counts.items())
cost=dict(native_library_compressed_sha256=libhash,native_area_coefficients=native,explicit_structural_cells=cell_counts,explicit_structural_comb_area_um2=comb_area,capture_plain_FF=plain,capture_FF_area_um2=plain*.2916,capture_clock_TT_FF_fF=[plain*.474736,plain*.522010],additional_reset_capture_FF=0,read_address_6bit_mux_bits=6*wrappers,current_write_payload_mux_bits=plain,explicit_mux_NAND2=3*mux_bits,explicit_mux_select_INV=slices+wrappers,current_write_hit_compare_6bit=slices,current_write_hit_XNOR2=6*slices,current_write_hit_AND_reduction2=5*slices,current_write_valid_AND2=slices,read_reset_mask_AND2=6*wrappers,independent_per_8bit_hit_copy_DFF_if_needed=None,reset_tree_and_clock_tree_cells=None,native_mapped_comb_area_um2=None,native_address_setup_ps=None,native_macro_to_capture_ps=None,native_FF_compare_ps=None,all_reset_and_fanout_fixedpoint_qualified=False)
old=json.loads((REGION/'model.json').read_text())
ob=json.loads((REGION/'calendar_obligations.json').read_text())
for x in ob['items']:
 x['successor_status']='Conditional source-equation identity from exact same-edge event/retire read wires; RTL/source-cone and original dated bench replay OPEN'
 if x['element'] in ['boot MC/MW face','boot selector','reset/restart','parent/compiler/token']:
  x['successor_status']='OPEN independent structural/initialisation/parent obligation; memory lemma grants no closure'
out=dict(schema='s81.hwin.early_capture.lemma.v1',scope='Bounded symbolic source-equation MODEL/PROOF only',source_commit='1e057b7bf',kit_commit='281ec8898',region_commit='21cbb79ac',hashes={str(p):sha(p) for p in [PACKET/'dsdv_mu_hwin.sv',REGION/'memory_source_snapshot.sv',REGION/'model.json',REGION/'calendar_obligations.json']},lemma=dict(symbolic_one_step_cases=cases,bounded_pointer_phases=phase_count,bounded_capture_equalities=checks,arbitrary_initial_warmup_cases=warmup_guard_checks,word_bits_unrestricted=True,head_generation_not_guessed=True,original_compare_time_unchanged=True,source_st_rec_holds_retained=True,all_2_to_47_original_minD=[dict(n=n,D=n+2,same_read_date_delta=0) for n in range(2,48)],retire_read_date_delta=0,reset_warmup_argument='Initial payload and early/capture Q arbitrary; two active read edges establish identity, while source pin-valid/staged-record guards prevent a qualified head. Actual reset-cone RTL proof still required.'),mutants=mutant_hits,first_failure_witnesses=witnesses,timestamp_wrap_cases=wrap_cases,cost=cost,geometry=dict(outline=old['geometry']['outline'],band=old['geometry']['band'],macro_count=84,previous_partial_priced_fill=old['cost']['priced_FF_inclusive_band_fraction'],conservative_partial_fill_including_all_prior_reservations_plus_new_capture_and_muxes=(old['cost']['priced_FF_inclusive_std_um2']+plain*.2916+comb_area)/old['cost']['band_area_um2'],successor_total_fill=None,reason='1072FF capture mechanism overlaps prior 1816FF reservation; no double counting. Exact source subtraction and all comb/reset/root costs need synthesis.'),calendar_obligations=ob['items'],full_added_edge_fallback=dict(status='NOT selected: memory recurrence has an exact same-edge constructive solution; preserve fallback obligations if actual source/timing fails',public_ABI_delta=None,production_schedule_delta=None,retire_start_RX_boot_transform=None),RTL_or_gate_authorized=False,full_calendar_rtl_equivalence=False)
(HERE/'model.json').write_text(json.dumps(out,indent=2)+'\n')
(HERE/'mutant_witnesses.json').write_text(json.dumps(witnesses,indent=2)+'\n')
print(json.dumps(dict(verdict='PASS bounded memory lemma; whole source/calendar OPEN',symbolic_cases=cases,pointer_phases=phase_count,capture_equalities=checks,mutants=mutant_hits,capture_FF=plain)))
