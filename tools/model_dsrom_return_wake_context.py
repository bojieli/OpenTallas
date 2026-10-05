#!/usr/bin/env python3
"""Existing pinned source and Liberty extraction only; no RTL build or STA invocation."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
ROOT=Path(__file__).resolve().parents[1]
CONTRACT='3a89958cacaa742eaa0fbf716180d35530fc8d28'
JOIN='0c51556275864679b407ace696ae136208bce1b5'
def sha(b):return hashlib.sha256(b).hexdigest()
def source(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)
def groups(text,kind):
 pattern=re.compile(r'\b'+kind+r'\s*\(([^)]*)\)\s*\{')
 for m in pattern.finditer(text):
  depth=1;pos=m.end();quoted=False;escape=False
  while depth:
   if pos>=len(text):raise ValueError('unclosed '+kind)
   char=text[pos]
   if escape:escape=False
   elif char=='\\' and quoted:escape=True
   elif char=='"':quoted=not quoted
   elif not quoted:
    if char=='{':depth+=1
    elif char=='}':depth-=1
   pos+=1
  yield m.group(1).strip().strip('"'),text[m.end():pos-1]
def attribute(text,name):
 m=re.search(r'\b'+name+r'\s*:\s*([^;]+);',text)
 return m.group(1).strip().strip('"') if m else None
def tables(text):
 result={}
 for kind in ('rise_constraint','fall_constraint','cell_rise','cell_fall','rise_transition','fall_transition'):
  for _,body in groups(text,kind):
   m=re.search(r'\bvalues\s*\((.*?)\)\s*;',body,re.S)
   if not m:raise ValueError('table missing values '+kind)
   values=[[float(v.strip()) for v in row.split(',')] for row in re.findall(r'"([^"]+)"',m.group(1))]
   result[kind]=dict(index_1=re.findall(r'index_1\s*\("([^"]+)"\)',body),index_2=re.findall(r'index_2\s*\("([^"]+)"\)',body),values=values,minimum=min(v for row in values for v in row),maximum=max(v for row in values for v in row))
 return result
def arcs(text,pin):
 selected=[body for name,body in groups(text,'pin') if name==pin]
 if len(selected)!=1:raise ValueError('pin count '+pin)
 return [dict(type=attribute(body,'timing_type'),related_pin=attribute(body,'related_pin'),when=attribute(body,'when'),tables=tables(body)) for _,body in groups(selected[0],'timing')]
def model():
 pins={}
 for commit,paths in [(CONTRACT,['rtl/v41die/ot_v41_field_w17w10.sv','rtl/v41die/ot_v41_retn_w17w10.sv','rtl/v41rom/ot_v41_ret.sv','rtl/test/v41_runtime/w17_w10_field_rt_gate.cpp','tools/uarch_model.py']),(JOIN,['rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv','rtl/v41die/ot_v41_pair_w17w10_rne_wake_prepare.sv','rtl/v41rom/ot_v41_bf16_lanes2_rne_prepare.sv','rtl/v41rom/ot_v41_bmul2_rne_prepare.sv','rtl/v41rom/ot_v41_bmul_subnormal_rne_prepare.sv','results/rtl/dsrom_actual_element_rne_wake_prepare_20261002/model.json'])]:
  for path in paths:pins[path]=dict(commit=commit,sha256=sha(source(commit,path)))
 evidence_paths=['results/uarch/w10_baseline_wake/local_fit_r1/selected_cell_SS_liberty.txt','results/uarch/w10_baseline_wake/local_fit_r1/audit.json','results/uarch/w10_baseline_wake/fullmap_r2/readiness.json','results/rtl/dsrom_realfield_prerequisite_model_20261002/model.json','tools/w10_wake_physical.py','tools/w10_wake_flow.py']
 evidence={p:sha((ROOT/p).read_bytes()) for p in evidence_paths}
 selected=(ROOT/evidence_paths[0]).read_text();icg=[body for name,body in groups(selected,'cell') if name=='ICGx1_ASAP7_75t_R']
 if len(icg)!=1:raise ValueError('ICG cell count')
 ena=arcs(icg[0],'ENA');gclk=arcs(icg[0],'GCLK');clk=arcs(icg[0],'CLK')
 rom={}
 for corner in ('ss','ff','tt'):
  path='physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_'+corner+'.lib';text=(ROOT/path).read_text();evidence[path]=sha(text.encode())
  clkp=dict(groups(text,'pin'))['clk'];read=dict(groups(text,'bus'))['rd_out']
  rom[corner]=dict(path=path,time_unit=attribute(text,'time_unit'),voltage=attribute(text,'nom_voltage'),temperature=attribute(text,'nom_temperature'),min_period=float(attribute(clkp,'min_period')),min_pulse_high=float(attribute(clkp,'min_pulse_width_high')),min_pulse_low=float(attribute(clkp,'min_pulse_width_low')),CLK_to_Q=tables(read))
 real=json.loads((ROOT/evidence_paths[3]).read_text());field=real['geometry']['full_field_driver_defaults'];np=field['pair_slots'];regions=field['return_regions'];nl=2*np;levels=(nl//regions).bit_length()-1;nodes=nl-regions
 return dict(status='SOURCE_MODEL_PREPARE_ONLY_NO_PHYSICAL_OR_FIELD_BUILD',source_pins=pins,evidence_sha256=evidence,joined_hardware_commit=JOIN,gate_order=['Parent owned full-target q/BF RNE/WAKE numerical gate reported PASS; terminal receipt observed PASS, immutable parent committed verification stillpending at this preparation','Review actual fieldreturn numerical source join/model; independently assert return values/tags/errors against unchanged chunk/padded-tree golden','Review source-matched element stage4/root/leaf/ICG/ROM SSsetup60ps FFhold25ps in originalslot/pin/density context','Separate fresh bounded physical GO; no clock/physical/adoption/tokencredit untilclosure'],actual_field_return={'target_geometry':field,'macro_leaves':nl,'region_tree_levels':levels,'return_nodes':nodes,'roots':regions,'tag_codec':'{ppos[2:0],row[15:0],lo[4:0],3reserved0,nseg[4:0]}32bits','leaf_payload_bits':65,'regional_source_nodes_per_root':nl//regions-1,'node_latency_no_queue':'Siblingadd5 sourcecycles + RST1 wirestage =6cycles perlevel; bypass1+RST1=2. 7levels gives42cycles for all-sibling path before root. Queue/WAIT/skew/root matching/rounding are additional; not a full latency or drain bound.','root_buffers':{'RD':64,'RST':1,'BYPASS':1,'ROOTD':128},'storage_lower_bound_bits':nodes*(2*64*65+65+1)+regions*(128*65+128*66),'storage_scope':'Declared queue/tag/data/error storage only; nodepointer/count/adderpipe/wait/bypass and rootcontrol/indexed siblingmux cost extra, no physical area/fit credit.','return_node_output_bits_per_cycle':65*nodes,'tree_all_links_bits_per_cycle':65*(2*nodes+regions),'root_public_bits_per_cycle':regions*(1+16+3+32+16+1),'ports':'128 actual region rowports, each FP32+BF16/error/tag; hub/VM routingcapacity andreturnfanin mustuseunifiedmodel, not NP16/R4 finite gate asfullfield substitute.','golden':'Element publicpartials are true aligned golden nodes. Source ret sibling()/parent()/norm()/complete() andcanonicalBF16 conversion must independently agree with unchanged golden tree/round points; bypass mustnotreorder sums; zero padding/idle half/error propagation/reset/restart andMTPtags required.','source_join_pending':'Productionfield currentlyinstantiates oldpair withoutFIX_SECOND_ROW_INDEX/GRADUAL_RNE/WAKE_REG. Futureaddedsourcecopy mustthread all3 opt-ins default0 tosame JOIN implementation at NP8192/R128/NBF1024; no newRTL written here.','busy_scope':'field busy isOR pairbusy only; return FIFO/pipeline/root retirement cannot be inferred from it. Runtimequiet androotdrain mustaccount actualreturnstate.','clock_scope':'Field/retn/ret currentlyshareclk; returnadder is original five-stage ot_fp32_add_rne_pipe, not elementCUT379/LAT8. Do not assume measured LAT3 0.9GHz serial domain or LAT8 1.2GHz closure applies; required domain/CDC/latency contract unresolved.'},actual_wake_context={'period_ps':833,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'ICG_cell':'ICGx1_ASAP7_75t_R','ICG_SS_ENA_arcs':ena,'ICG_SS_GCLK_arcs':gclk,'ICG_SS_CLK_arcs':clk,'ICG_time_unit':'Numeric values transcribed from selectedSS cell excerpt; fullSEQ_SS libraryheader/time-unit is not in this pinned excerpt. Parent audit pins originalworkerSEQ_SS hash; require full header/artifact for absoluteSTA qualification. No substitute library used.','ICG_FF_ENA_arcs':None,'root_leaf_insertion_skew':None,'ROM_corner_arcs':rom,'ROM_capture_source_contract':'issueatN -> i1_vN -> i2x_vN+1; cap0/1 samplespreedgei2x_v atN+2. Eachbank cannot readonadjacentedges bypp_block and parity. Thus ROMreadN->bankcaptureN+2 actual2cycledata path; nextsamebankreadN+2 gives sameedgeholdcheck. Source comment andexisting SDC setup2/hold1 are consistent. Mustauditallselectedendpoints exactlymacroQ->cap0/1 only, no blanketmulticycleontags/address/CE/otherdata.','ROM_capture_declared_bits':4*274,'ROM_capture_prior_mapped_bits':1088,'ROM_capture_prior_note':'Prior fullmap1088 survivingcapturebits differs1096declared (unusedwordbitspruned); source endpoint auditrequired forcurrentjoin, do not infercurrentmappedcountsfromprior.','ROM_worst_table_2cycle_margin_before_endpoint_setup_wire_skew_ps':2*833-60-rom['ss']['CLK_to_Q']['cell_rise']['maximum'],'ENA_setup_equation':'rootclkqmax + wakeQwiremax + ENAsetupSS +60 <=833 + ICGCLKinsertion -rootCLKinsertion; separate rootgo/walk/drain->wakeD fullperiod path.','ENA_hold_equation':'rootclkqmin +wakeQwiremin >= ENAholdFF +25 +ICGCLKinsertion-rootCLKinsertion; asyncreset recovery/removal/setQ->ENA andpulsewidth required.','repair_stage4':'Exact JOIN shared bmul: s3_be[10:0]/s3_f[22:0]/s3_s plus s3_z/s3_nf Q -> combin24bitRNEencoder -> s4_yD/s4_badD underleaf3. Same5cycles, nohiddenstage; include guard/sticky/barrel/inc24/zero/select andfanout.','cross_leaf_paths':['free-rootFASTinputs->leaf0 FIFO/walker','leaf0addrCE->leaf4..7ROM','leaf4..7ROMQ->leaf0cap0/1 (source2cycle)','leaf0cap/control->leaf1 quantizedterm/leaf3BFboundary','leaf1term->leaf2chain','leaf2chain->leaf3pair','leaf3tree->leaf0 publicregister->freeclkfieldreturn'],'source_legal_DRAIN':'OPEN: DRAIN127 loaded whilego_e/walkbusy; segmentQD8/pipelinedreturnpriority needsfulllegalunitoccupancy proof. Paced1/2unitfixture andextraWAKEedge do not proveuniversal127. Need boundsfromcfgmapper validity, LV5, MTPparity andactualeventarbitration before admittingphysical/token.', 'previous_physical_hold':'local_fit_r1 CAPTURE_PIN_BAND_OVERFLOW_PHYSICAL_HOLD andfullmap structural-only remainpreserved; sourcejoin isnotqualifiedbythem. Originaloutline/density/I/O/clockuncertainty/pinband mustnotrelaxwithout explicitpricedreview.'},execution={'field_build_authorized':False,'STA_PNR_authorized':False,'resources':'Model/source preparation only. Physicalshape/slot/source/tool/corner/routing model andmemory/thread/headroom/caps must be separately boundbefore GO. Fleet drain forbids new tasks/builds/routes/queued stages on ot-pve2 and ot-pve3; existing tasks finish normally. Owner has none. New work local/ot-pve1/ot-agidock128 only under measured headroom. NewVM maybeusedonlyaftermatchingtools/sourceandhardcaps;96GiBfleetbudget/94GiBsingle/24GiBreserve/48aggregate threads metadata requirecoordination.'},claims={'fullfield_return_PASS':False,'SS_FF':False,'physical':False,'fulltoken':False,'adoption':False})
if __name__=='__main__':print(json.dumps(model(),indent=2,sort_keys=True))
