from pathlib import Path
import subprocess,json,re,hashlib,gzip,pickle,sys,math
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');W=Path('/srv/opentallas-scratch/claude/wt/codex-hist-bounds-2145');R=W/'results/geom_review/s81_qbs_repack_B_2233/centre_clock';R.mkdir(parents=True,exist_ok=True)
def tracked(p):return subprocess.check_output(['git','-C',str(W),'show','HEAD:'+p]).decode()
basepins='physical/die_plan/s81/inputs/core_pins/dsdv_bksel_q.json';baselef='physical/ref_tile/s81dvbk_sq_hq3/views/dsdv_bksel_q/dsdv_bksel_q.lef';T=json.loads(tracked(basepins));L=tracked(baselef);C=json.load(open(P/'repack_B_centre_complete.json'));clock=C['proposal']['clock_entry'];A=json.load(open(P/'legal_joint_B_centre.json'));B=clock['driver_bay_um'];ck=[p for p in T['pins']if p['name']=='ck'];assert len(ck)==1;oldck=dict(ck[0]);ck[0].update(layer='M5',x=clock['center_um'][0],y=clock['center_um'][1]);T['lef']=str((R/'dsdv_bksel_q_contract.lef').relative_to(W));T['pinhash']=hashlib.sha256(json.dumps(T['pins'],sort_keys=True).encode()).hexdigest()[:12];T['source']='DISABLED CONTRACT CANDIDATE centre M5 ck entry; not as-built/extracted; unchanged1802 other pin entries';T['enabled']=False
(R/'dsdv_bksel_q_core_pins.json').write_text(json.dumps(T,indent=1)+'\n')
new='''  PIN ck
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT 323.988 330.972 324.036 331.452 ;
    END
  END ck'''
pat=r'  PIN ck\n.*?  END ck';old=re.search(pat,L,re.S).group();LL=re.sub(pat,new,L,count=1,flags=re.S);assert LL.replace(new,'')==L.replace(old,'');(R/'dsdv_bksel_q_contract.lef').write_text(LL)
(R/'io_clock_override.tcl').write_text('''# DISABLED CANDIDATE ONLY: source after generated io.tcl in a new own kit.
# Same ck BTerm/net; physical contract changes and all parent references move together.
set cb [[ord::get_db_block] findBTerm {ck}]
if {$cb eq "NULL" || $cb eq ""} {error "centre clock ck BTerm missing"}
foreach bp [$cb getBPins] {odb::dbBPin_destroy $bp}
set bp [odb::dbBPin_create $cb]
$bp setPlacementStatus FIRM
set u [[ord::get_db_block] getDbUnitsPerMicron]
odb::dbBox_create $bp [[ord::get_db_tech] findLayer M5] [expr {int(round(323.988*$u))}] [expr {int(round(330.972*$u))}] [expr {int(round(324.036*$u))}] [expr {int(round(331.452*$u))}]
''')
root=clock['center_um'];oldroot=[oldck['x'],oldck['y']];pos={a['cid']:[a['origin_um'][i]+a['size_um'][i]/2 for i in(0,1)]for a in A['anchors']};pins=[p['xy']for m in C['macros'].values()for p in m['ports']if p['sig']=='CLOCK'or p['port']in('ck','clk','CLK','CK')];l1=lambda x,y:sum(abs(a-b)for a,b in zip(x,y))
rows=C['rows'];rowsbay=[r for r in rows if r['bbox_um'][1]>=B[1]-1e-6 and r['bbox_um'][3]<=B[3]+1e-6 and r['bbox_um'][0]<=B[0] and r['bbox_um'][2]>=B[2]];fixedbay=[]
for f in C['fixed']:
 b=f['bbox_um']
 if b[0]<B[2]and b[2]>B[0]and b[1]<B[3]and b[3]>B[1]:fixedbay.append(f)
# Fixed TAPs remain ordinary occupancy inside the bay, not drivers or illegal blockers of the whole event.
taparea=sum(max(0,min(B[2],f['bbox_um'][2])-max(B[0],f['bbox_um'][0]))*max(0,min(B[3],f['bbox_um'][3])-max(B[1],f['bbox_um'][1]))for f in fixedbay)
entry=clock['bbox_um'];pg5=[]
for k in range(100):
 for q in (2.064+4.32*k,2.256+4.32*k):
  if q+.06>entry[0]-3 and q-.06<entry[2]+3:pg5.append([q-.06,q+.06])
clear=min(max(b[0]-entry[2],entry[0]-b[1],0)for b in pg5)
report=dict(enabled=False,kind='sameclock_physical_entry_only',old_ck=oldck,new_ck=clock,other_pin_entries_unchanged=len(T['pins'])-1,LEF_non_ck_text_exact=True,native_track_offset_um=.012,native_track_pitch_um=.048,on_M5_XY_tracks=all(abs((v-.012)/.048-round((v-.012)/.048))<1e-8 for v in root),min_pin_width_um=.048,pin_length_um=.480,nominal_M5_PG_pair_clearance_um=round(clear,6),PG_clearance_scope='source PDN stripe pair centre convention; actual regenerated PG/via landing still required',driver_bay_rows=len(rowsbay),driver_bay_native_fixed_count=len(fixedbay),driver_bay_fixed_types=list(sorted({f['master']for f in fixedbay})),driver_bay_historical_tap_area_um2=taparea,driver_bay_nominal_row_area_um2=len(rowsbay)*(B[2]-B[0])*.270,FF_targets_inside_bay=sum(B[0]<p[0]<B[2]and B[1]<p[1]<B[3]for p in pos.values()),macro_clock_pins=len(pins),root_to_macro_clock_max_before_um=max(l1(oldroot,p)for p in pins),root_to_macro_clock_max_after_um=max(l1(root,p)for p in pins),root_to_allFF_max_before_um=max(l1(oldroot,p)for p in pos.values()),root_to_allFF_max_after_um=max(l1(root,p)for p in pos.values()),frequency_RTL_FF_count_unchanged=True,physical_buffer_price='No buffer fabricated/preplaced; bay reserves capacity for normal clock-entry buffer/CTS. Actual added cells/area and TT+FF latency priced by future clock stage.')
(R/'centre_census.json').write_text(json.dumps(report,indent=2)+'\n')
refs=dict(enabled=False,module='dsdv_bksel_q',clock_name='ck',width=1,period_ps=833,contract_core_pins=str((R/'dsdv_bksel_q_core_pins.json').relative_to(W)),contract_child_LEF=str((R/'dsdv_bksel_q_contract.lef').relative_to(W)),all_parent_instances='For every hard-core reference whose module/master is dsdv_bksel_q, replace core_pins and child LEF coherently in an own disabled plan copy; no partial parent/child switch',future_child_view='Requires fresh actual exported view from this same macro/clock event; no old insertion/signoff transfer',source_inputs=[basepins,baselef,'physical/die_plan/s81/die_plan.json','physical/die_plan/s81/plan_h2_2249.json','physical/die_plan/s81/cores/legacy/profiles/hist_pincopy_1101/spec/spec.json'],proof='PREPARED current051 sameRTL/netlist; HOLD bothlegacyterminal+ROOTauthorization, no qualification')
(R/'parent_child_binding_disabled.json').write_text(json.dumps(refs,indent=2)+'\n')
with gzip.open(R/'all31847_ff_anchors_with_clock_bay.json.gz','wt')as f:json.dump(A,f,separators=(',',':'))
with gzip.open(R/'disabled_repack_B_centre_complete.json.gz','wt')as f:json.dump(C,f,separators=(',',':'))
print(json.dumps(report,indent=2))
