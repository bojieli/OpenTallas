import sys,json,gzip,hashlib,math
from pathlib import Path
import numpy as np
ROOT=Path('/home/ubuntu/OpenTallas-hbrom-cluster-20261005');sys.path.insert(0,str(ROOT/'tools'))
import hbrom_global_screen as S
Ipath=ROOT/'results/uarch/hbrom/g0_inputs.json.gz';Ppath=ROOT/'results/rtl/w19_hbm_tp96_program_oreduce.json'
I=json.load(gzip.open(Ipath,'rt'));P=json.load(open(Ppath));M,D=S.compile_matrices(I,P)
def geometry(fmt,k):
 L={'fp4':8,'fp8':4,'bf16':64}[fmt];U=1 if fmt=='bf16' else 32
 assert k%(8*U)==0,(fmt,k)
 C=k//(8*U);G=(C+L-1)//L;A=[min(L,C-g*L) for g in range(G)]
 assert all(L%a==0 for a in A),(fmt,k,A)
 F=[L//a for a in A];assert all(8%f==0 for f in F),(fmt,k,F)
 return L,U,G,A,F
cases=[];shapes={}
for sm in [16,32]:
 for rotate in [False,True]:
  cur=np.zeros((96,sm),dtype=np.int64)
  for t,o in M:
   cnt=np.array([b-a for a,b in o['rows']],dtype=np.int64);tile=cnt[:,None]//sm+(np.arange(sm)[None,:]<cnt[:,None]%sm)
   if rotate:
    key=S.re.sub(r'\.w[123]\.weight$','',t['name']);shift=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%sm;tile=np.roll(tile,shift,axis=1)
   L,U,G,A,F=geometry(o['fmt'],o['k']);rpr=sum(8//f for f in F);cur+=tile*rpr
   shapes[(o['fmt'],o['k'])]=max(shapes.get((o['fmt'],o['k']),0),int(tile.max()))
  pairs=(cur+8191)//8192*4;area=pairs.sum(axis=1)*2*I['macro']['area_mm2'];maxp=int(pairs.max())
  cases.append({'tp':96,'sms_per_rank':sm,'rotation':rotate,'compact_records':int(cur.sum()),'allocated_pairs_total':int(pairs.sum()),'max_pairs_per_sm':maxp,'max_raw_rom_mm2_per_rank':float(area.max()),'min_raw_rom_mm2_per_rank':float(area.min()),'max_mux_inputs_per_stream':maxp//4,'uniform_exact_pool_raw_rom_mm2_per_rank':maxp*sm*2*I['macro']['area_mm2'],'uniform_power2_pool_raw_rom_mm2_per_rank':2**math.ceil(math.log2(maxp//4))*4*sm*2*I['macro']['area_mm2'],'pool_end_unused_records':int((pairs//4*8192-cur).sum()),'whole_row_pool_boundary_required':False,'tensor_alignment_records':1,'qualified':False})
checks=[];testlines=0;readtotal=0
for (fmt,k),maxrows in sorted(shapes.items()):
 L,U,G,A,F=geometry(fmt,k);readcount=0;lines=0
 # Include every actual busiest-sm rowcount and smaller counts, not just one representative.
 for R in range(1,maxrows+1):
  first=[];seen=set();cache={};occmax=0;live={};lastmisscycle={};readcycle=0;waveoffset=0
  for wb in range(0,R*G,8):
   expectedwave=0
   for t in range(8):
    for s in range(8):
     item=wb+s
     if item>=R*G:continue
     r,g=divmod(item,G);f=F[g];p=t//f;key=(r,g,p);v=A[g]
     if t%f==0:
      assert key not in seen;seen.add(key);first.append(key)
      # Symbolic payload atoms encode original(row,group,t,lane); proves exact lane identity.
      payload=[(r,g,tt,j) for tt in range(p*f,(p+1)*f) for j in range(v)]
      assert len(payload)==L
      cache[s]=(key,payload);expectedwave+=1
      if f>1:live[s]=key
     assert cache[s][0]==key
     start=(t%f)*v
     got=cache[s][1][start:start+v]+[None]*(L-v)
     want=[(r,g,t,j) if j<v else None for j in range(L)]
     assert got==want
     lines+=1
     occmax=max(occmax,len(live))
     if t%f==f-1:live.pop(s,None)
   assert not live
   assert expectedwave==sum(8//F[(wb+s)%G] for s in range(8) if wb+s<R*G)
  assert len(seen)==R*sum(8//f for f in F)
  assert lines>=R*G*8
  readcount+=len(seen)
 checks.append({'format':fmt,'K':k,'rows_checked_inclusive':[1,maxrows],'groups':G,'valid_lanes_per_group':A,'responses_per_compact_record':F,'native_records_per_row':G*8,'compact_records_per_row':sum(8//f for f in F),'symbolic_expansion_equal':True,'firstuse_keys_unique':True,'all_payload_atoms_covered':True,'last_test_tail_context_highwater':occmax})
 testlines+=lines;readtotal+=readcount
pins=[Ipath,Ppath,ROOT/'tools/hbrom_global_screen.py',ROOT/'tools/w19_sm_real_ops.py',ROOT/'rtl/gpu/ot_gpu_issue.sv',Path(__file__)]
d={'schema':'opentallas.hbrom.global_firstuse_layout.v1','architecture_only':True,'qualified':False,'source_pins':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},'mapped_matrix_count':len(M),'cases':cases,'symbolic_mapping_checks':checks,'symbolic_native_lines_checked':testlines,'symbolic_unique_reads_checked':readtotal,'bijection':{'domain':'Unique compact keys(row,group,floor(t/fanout[group])) over the actual native wave,t,slot traversal.','construction':'Visit valid native requests in wave,t,slot order. At t%fanout[group]==0 assign next consecutive physical-record ordinal and store exactlyL validatoms in t-major/lane-major order. Later fanout-1 responses read the slot context, never a new immutable copy.','injectivity':'Each row/group item belongs to exactlyonewave/slot; firstmiss t values0,fanout,...7 are distinct packedrecord keys.','surjectivity':'Everyreal atom belongs to exactlyonegroup,t,lane and therefore exactlyone packedrecord; eachrecordfirstmiss is visited by native schedule.','exactness':'Expand selected t slice into original active code/scale lanes; fill inactive lanes with literalzero. This matches w19_sm_real_ops line construction bitwise without modifying reductions or computeissueorder.','immutable_replication_factor':1,'scope':'Mapped matrixshapes only, all have timeuniform validlanes and integral fanout dividing8. Source scales and executionwo_a obligations unchanged.'},'address_generation':{'physical_address':'descriptor_compact_base + global_firstmiss_ordinal','pool':'physical_record_address >>13 selects fourstream pool; address[12:0] chooses8192logical records. Parity address[0] picks alternating macro; remaining12bits macro row.','no_per_record_LUT':True,'arbitrary_native_seek':'Must reconstruct waveprefix+prior t firstmiss popcounts+current slotprefix; simple sequential generator avoids randomseek cost.','wave_prefix':'Sum over earlier waves and their active slots of8/fanout; equivalently complete rows compactrecords plus partialgroup prefix.','pattern':'For slot s assigned groupg, fanout is1,2,4,8. firstmissmask[t][s]=valid[s] and(t&(fanout[s]-1))==0. 8t×8slots mask64bits; optional prefixcounts fit8×7bits; total120bits percurrent wave pattern.','retained_control':'8slots×(valid1+fanout_log2_2+group8+row16)=216rawbits; compact32bitbase+32bitordinal;128bitpatternregister allowance.','pool_crossing':'A row/tensor/wave may cross8192record boundaries; keys remain consecutive. Storage records remain whole1096bitfourword records. Existing whole-row allocator restriction removed analytically, not a golden arithmetic change.'},'bank_proof':{'assumptions':['Successive firstmiss reads launch in assigned ordinal order, at mostone percycle.','Pool address arithmetic correctly selects physical macros; no unrelated read client steals port.','No new descriptor reuses an inflight context; descriptor transition respects bankrecurrence.'],'within_pool':'Successive firstmissordinals alternate bankparity. Same physical macro is revisited only afteratleasttwo readlaunches; atmostone launch/cycle ensures>=2cycles recurrence. Nativehits addidle time and cannot shorten recurrence.','pool_boundary':'Next ordinal crosses to a different physicalpair; oldmacro recurrence cannot conflict.','descriptor_boundary':'If samepool/sameparity as precedingdescriptor, insertone launchbubble or wait alreadyrequired completion/epochdrain. Charge atmostone launchcycle perdescriptor unless actualdrainproves it hidden.','guarantee':'Eliminates samebank consecutivefirstmiss launchconflicts for serializedfirstuse schedule. Does not prove contextavailability or native no-bubble delivery.'},'finite_context_contract':{'tail_contexts':8,'protected_bits_per_context':1296,'native_response_output_max_bytes_per_cycle':136,'lifetime':'Reserve slotcontext before issuing its firstmiss; retain until last associatednative line has been expanded and copied into protectedresponse staging. Consumer neednot alreadyexecute it.','do_not_overwrite':'Wavew+1 same slot can launch onlyafterwavew last expansioncopied and allolderinflight writes for slotretired. Storewave/epoch tag with context and inflight destination.','single_wave_restriction':'Simplest8contextpolicy forbidsnextwave firstreads until allcurrentwave outputsare materialized. Payscoldrefill latency everywave; do not claimonlyone startuppertensor.','latency_hiding_candidate':'Morewave contextbanks or earlynextwaveprefetch into a distinctresponse/read buffer can hide refill; everybit, credit and staleepochcheck mustbe priced. Existingbulk ring canholdexpandedpreviouswave, but cannotreplace futurecompactcontexts beforeexpansion.','physical_read_pipeline_latency_sweep_cycles':[17,24,30],'context_capacity_bytes':1296*8/8,'wave_native_output_max_records':64,'pipeline_metadata':'At leastL inflight destinations at1read/cycle, eachincludingepoch,wave,slot,packedoffset,requestidentity. No reuse untilassociated destinationcredit free.'},'analytical_cost_allowance':{'base_compact_decoder_and_16request_queue_mm2_per_sm':.0232389376,'extra_firstuse_generator_raw_state_bits':408,'extra_firstuse_generator_protected_register_bits_allowance':504,'extra_firstuse_logic_footprint_mm2_assumed':.003,'generator_total_extra_mm2_assumed':504*.2916/.5/1e6+.003,'inflight_metadata_bits_each_assumed':72,'L30_inflight_bits':2160,'L30_inflight_register_footprint_mm2':2160*.2916/.5/1e6,'two_wave_context_extra_bits_if_selected':10368,'two_wave_context_extra_register_footprint_mm2':10368*.2916/.5/1e6,'caution':'Area is analyticalregister/mux allowance, notphysicalmeasurement; protect mutablemetadata. Do notdoublecountpipelinequeue statealreadyin sourcepath. Full contextualrouting, clocktree, reset/control and ECClogic needpricing.'},'startup_model':{'cold_first_response_cycles':'ActualROM/pool pipelineL + localexpansionstages(ifnotalreadyinL) + responseprotocol. Nativephasealignment0..7 additional cycles.','single_wave_extra_bubbles_upper_bound':'Perwave refillL plusphasealignment unless actual overlapproved; numberwaves=ceil(rows*groups/8).','conditional_firstuse_reads_per_cycle':1,'native_output_records_per_cycle_max':1,'TPOT_credit':None,'why_not_done':'Bijective layoutandbankrecurrenceproved analytically; finitecontext and pipeline scheduling remains mapping contributor obligation.'},'storage_scope':'Onlymappedexecutabletensors. Deferred/sourcearchive,derivedtables,config,anddedicatedservicecapacityremain unchanged.'}
Path('/tmp/hbrom-global-firstuse-layout.json').write_text(json.dumps(d,indent=2)+'\n')
for c in cases:print(c['sms_per_rank'],c['rotation'],c['max_pairs_per_sm'],round(c['max_raw_rom_mm2_per_rank'],3),round(c['uniform_exact_pool_raw_rom_mm2_per_rank'],3))
print('symbolic lines',testlines,'records',readtotal)
