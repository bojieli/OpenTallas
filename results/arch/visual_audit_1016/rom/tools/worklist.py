import json,collections
d=json.load(open('results/arch/visual_audit_1016/rom/findings.json'))
F={x['id']:x for x in d['findings']}
# id: (owner, gain, dependency, helper scope)
W={
'QC-01':('Q-COMPUTE-DIE','closure: 92 illegal cells -> 0 (768-instance NK tile)','QC-11 lint exemption before r4','helper: r4 NK repitch kit + gate; target DPL 0, W band >=40 um'),
'QC-02':('Q-COMPUTE-DIE','closure: 53 illegal cells -> 0 (NL tile)','QC-11','helper: NL tap glue into empty NE slot + ROM-top band widen; gate'),
'QC-11':('Q-COMPUTE-DIE','unblocks QC-01/02 r4 gate (3 lint channel FAILs)','none','helper: extend abutted_stack lint to E-W pin-free abutment + test; 1 small PR'),
'D-QC-02':('Q-COMPUTE-DIE','closure: removes 1,585-terminal reset net (r2b2 worst path -13.3 us) if not already fixed in FULL mode','r2h1/r2h2 GEN output','helper: read r2h* GEN reset_over_500 + fix xcol/xcol_e rst_n INOUT in generated LEF'),
'D-QC-01':('Q-COMPUTE-DIE','area: candidate (a) -53 mm2 done at plan level; (b) centre trim up to ~25 mm2 more','r2hs GEN/GRT; producer masters for the area above su64','helper: run r2hs GEN+GRT; second helper: price centre trim (b)'),
'QC-05':('Q-DVM+LINK','closure: native capture 502 ps -> <=190 (route pending)','xt10 route','helper: collect xt10 route + native audit; N-band congestion check'),
'QC-04':('Q-DVM+LINK','timing: r1 hold S band 76 ps late; r4 gate clock ins 417-501/spread 84 over the 300/80 rule','r5 gate','helper: r5 gate->route + native audit; cancel r4 if r5 is clean'),
'QC-06':('Q-ELEM','timing: SS -333 ps path from bottom ROM (~450 um reach); 729 N pins at 9.6/um','none','helper: crom_g re-kit: spread N face on M5(+M3), clock at column centre or 2x3 ROM arrangement; gate'),
'QC-07':('Q-ELEM','closure: newest full-tile runs failed hold; channel 19 um / row gaps 16 um congested','none','helper: band_lanes re-place macro columns (centre channel ~40 um) + gate'),
'QC-08':('Q-ELEM','timing (small): NW-corner clock on 194x216 tile','none','fold into next cbuf_g touch'),
'QC-09':('Q-ELEM','area: fill 0.148 on 345.6x216 (shrink ~-40% per instance)','instance count / die slot','helper: scale-leaf own outline ~200x216 if instanced; else skip'),
'QC-10':('Q-ELEM','area (low): fill 0.198; optional 260x216','none','skip unless die area binds'),
'QKV-01':('Q-KVSYS-DIE','closure: PV column 321.9 um too tall for north slot; south spine 1,287 um vs 1,598 needed','kvs11 trial; relay re-plan','helper A: zero inter-slice gap screen (8,294 um) + case; helper B: split-PV case with south arrays shifted ~160 um'),
'QKV-03':('Q-KVSYS-DIE','closure: 45 GRT overflows in 20 um SRAM channel (M4 34, M5 11)','none (tile cap M5: widen channel, no M6)','helper: d2d_static re-place SRAMs (channel >=40 um or outer-edge SRAMs) + gate'),
'QKV-04':('Q-KVSYS-DIE','closure/congestion: every KV relay at 20.9 pins/um M4-only (rly_2089 x61, 1025 x252, 1048 x82)','die abstract generator','helper: relay abstract regen <=8 pins/um/layer, two layers; re-run kvs case'),
'QKV-07':('Q-KVSYS-DIE','timing/congestion: ahub_core N 1,345 pins at 8.9/um half on M3; parent q8 failed hold','none','helper: ahub_core re-pin (half zh to S/W, M5+M7->M5+M3 cap) + parent gate'),
'D-QK-01':('Q-KVSYS-DIE','area: spine S 13.9 + N 12.1 + corners 10.1 mm2 empty (~36 mm2)','QKV-01 decision','same helper as QKV-01 B'),
'D-QK-02':('Q-KVSYS-DIE','timing: astk->ectl_c links up to 9.06 mm inside a 220x9,675 um strip','parent hardening plan','helper: segment astk/land into ~1.2 mm replicated segments (plan + one segment gate)'),
'QKV-13':('Q-KVSYS-DIE','timing: in->reg -69.5 ps, one reset flop -> 8,940 loads','none (running in loop as submitted)','helper: replicate rp[] per bank group (<=256 loads), outline ~160x180; re-gate'),
'QKV-02':('Q-ELEM','closure: ectl_a manual recovery stuck at 4 DRT shorts for 53+ iterations','none','helper: ectl_a re-pin kit (row buses split over both SRAMs, rs on two layers) + gate'),
'QKV-05':('Q-ELEM','closure (bind): routed embgw has 4,143 pins + N face vs die abstract 3,541 pins, no N face; E/W 8.7-8.9/um','die abstract','helper: re-pin embgw from die LEF + gate'),
'QKV-06':('Q-ELEM','timing+area: E 617 pins squeezed into 46% of face; fill 0.24 -> shrink 246x173 -> ~200x150 (~-30%)','none','helper: ctrl_pc re-pin + shrink + gate (128 instances: ~1.6 mm2 saved)'),
'QKV-10':('Q-ELEM','timing: pv_join r5 FF -5.2 ps after route (hold ECO running); E 1,540 pins at 9.4/um','r5 ECO result','helper: if ECO fails, move y output off E; re-gate'),
'QKV-11':('Q-ELEM','timing/congestion: ectl A/B/C row pins misaligned (B left half, A right half) -> parent faces jog','none','helper: align A/B/C row pin x columns + parent check'),
'QKV-08':('Q-ELEM','timing: astk_pv_tp8 fill 0.60, N/S 9.4/um, NE-corner clock','none','helper: grow ~180x130 + spread N/S + centre clock; gate'),
'QKV-09':('Q-ELEM','timing: lane8 (2,048 inst) native launch 233 ps on 30 pins; NW-corner clock, fill 0.635','none','helper: lane8 clock to E-face centre, util <=0.55; gate + native audit'),
'QKV-12':('Q-ELEM','small: pv_ctl S 10.6/um, host_ctl fill 0.12, land_emb_ifw hot window','none','fold into next touch'),
'S81F-01':('S-DIE','timing: rly_283/266_EW (3,042 inst) launch 243/237 ps from wrapping inputs; ~835k bits facing away','c26b GEN audit; S-NET+FILL L/U + WE views','helper: score c26b relay_face_audit.json; second helper (S-NET+FILL): build 283/266 WE + L/U kits'),
'D-S81-02':('S-DIE','timing: 451-terminal column reset nets; INOUT abstracts','c26b GEN (--col-reset-tree, --lef-pin-dir)','same c26b scoring helper'),
'D-S81-01':('S-DIE','area: hub band 161/315 mm2 white; HC_T ~10 mm from VM','hub v2 regeneration (gen26a failed twice)','helper: hub compaction study (HC tower on VM E face, SU_S under VM), price mm2 returned'),
'S81F-03':('S-DIE','timing: LL nodes (2,417 inst) a/b still 18.4 pins/um in 7 um of W face, density 2.03','S-NET+FILL re-kit','helper (S-NET+FILL): node a/b to E face, >=30 um span, clock at centroid'),
'S81F-04':('S-DIE','timing: die-side 152 um cfg/go_e jog + 896 bit-reversed bundles (tile part fixed)','die placement','helper: co-place cfg7 under qbank_S.i_cfg; mirror qbank_S/q element with the FN pair'),
'S81F-05':('S-DIE','timing: qbank_S (1,898 inst) W-end clock on 60 um tile; N half empty; 896 reversed','with S81F-04 mirror fix','helper: qbank_S clock to S-face centre, height ~18 um; gate'),
'S81F-06':('S-DIE','congestion: 156 bundles jog 74 um in a 6.2 um channel (536_SN vs sstn x2)','sstn window request (S-NET+FILL)','helper: window alignment in generator'),
'S81F-07':('S-DIE','timing: rly_15_* 42-100% facing away, up to 338 um','S81F-01 generator fix','covered by c26b scoring helper'),
'S81F-08':('S-DIE','timing: small relays 100% facing away (63_EW load 697 um behind)','S81F-01','covered by c26b scoring helper'),
'S81F-09':('S-DIE','timing: m2l hr launch 380 / capture 485 ps; SW-corner clock; 35% empty','none','helper: hr_W1 canonical re-kit: clock at sink centroid, ~158x100 um; gate + native'),
'S81F-13':('S-DIE','congestion: 82 um jog in a 6.3 um gap xstg_515 -> bk_collector_c1 (tile native fixed: 356 -> 126 ps)','die placement','helper: align o window with bk_collector cSW or open gap >=36 um'),
'S81F-14':('S-DIE','small timing: rly_63_* in/out bands offset ~4.5 um -> jog on every straight hop (21,000+ inst)','S-NET+FILL re-kit','helper: centre i/o band in the 63_* family kits'),
'S81F-15':('S-DIE','area: ~2.2 mm2 of 1-6% fill narrow relays/stations','die netlist bundle merge (phase-3 dedupe)','helper: dedupe plan, later'),
'S81F-10':('S-NET+FILL','congestion: 3,855 stations at 20.8 pins/um (every M4 track)','S-DIE plan with --stn-pin-pitch2 (c26b)','helper: route stnh/stnv_86x1 2-track views'),
'S81F-11':('S-NET+FILL','area: sstn fill 0.107 -> halve width (~90 um)','gen26a/c26b pin windows','helper: sstn re-cut after c26b'),
'S81F-02':('S-ELEM-PQ','closure (bind): 68,864 die bits unbound (cfifo without xd2/xf2)','v2 RTL','helper: close cfifo v2 + rebind; place x2 under sinf x2i'),
'S81H-01':('S-ELEM-PQ','closure: 22,965 hold violations from 4 unbalanced CTS roots','none','helper: host_c single-root clocking (or retime at ck_ingest->ck) + n5 route'),
'S81H-02':('S-ELEM-PQ','closure: FLOORPLAN_MARGIN at 66% util','c10 RTL','helper: c10 kit at <=57% util + gate'),
'S81H-03':('S-ELEM-PQ','timing: bf_front c9 now TT -35.73 / FF -7.86; W/E 10.4 pins/um in 37% of face; SW clock','none','helper: c10 re-pin W/E full face, split N bus, centre clock; gate'),
'S81H-04':('S-ELEM-PQ','area+congestion: vm_boundary 74% empty, SW knot from mismatched W/E bit order; 151 -> ~60 um width','none','helper: align W/E bit order + shrink; gate'),
'S81H-12':('S-ELEM-PQ','area (low): ctrl_pc fill 0.14','none','fold into next touch'),
'S81H-14':('S-VM','closure: wfc_ctl refused (unsynchronised core->serial CDC: x43f, vm_fault, x34f)','none','helper: RTL CDC fix (static-schedule capture in core domain) + bench + gate'),
'D-S81-03':('S-VM','closure risk: VM cut exactly 0.600 (no margin), 98,672 leaf links >500 um','VM parent kit','helper: move 4-6k bits S/N -> E (E 6,987 vs S 19,288) in the parent kit; re-measure cut'),
'S81H-08':('S-VM','timing (residual): field4 W i_sel wall (672 pins one M4 column)','S-DIE pin grant','helper: i_sel W+S split kit if input hold tight'),
'S81H-09':('S-VM','area: control4 fill 0.19 -> 194 -> ~130 um (~8,000 um2 x4)','S-DIE slot change','re-pack item with the VM parent kit'),
'S81H-05':('S-FUNC','area: ctfl_nt 88% empty (576 um wide, pins in 20%)','none','fold into next HC re-kit'),
'S81H-07':('S-FUNC','small timing: ctfn/ctfs/ctfnq3 flops walled on N face (p90 density 1.12-1.14)','none','only if HC row timing tightens'),
}
by=collections.defaultdict(list)
for k,(o,g,dep,h) in W.items():
    x=F.get(k); 
    if not x: continue
    r=x.get('round'); s=r.get('2',{}) if isinstance(r,dict) else {}
    by[o].append((x['severity'],k,x['master'][:55],s.get('outcome','open') if s else 'open',g,dep,h))
order=['Q-COMPUTE-DIE','Q-DVM+LINK','Q-ELEM','Q-KVSYS-DIE','S-DIE','S-NET+FILL','S-ELEM-PQ','S-VM','S-FUNC']
out=['# VIS-ROM worklist: every open finding, grouped by owner (2026-10-16 ~03:30 PT)','',
 'For parallel execution, use one helper per item. Sev: 1 = blocks closure, 2 = costs timing/congestion/area, 3 = waste/low. "partial" = owner already partly fixed it.',
 'Gains are the measured figure from the audit (see `findings.json` for full evidence and images); closure items are counted as closure, not ps.','']
n=0
for o in order:
    L=sorted(by.get(o,[]))
    if not L: continue
    out+=[f'## {o} ({len(L)} items)','','| sev | id | item | state | expected gain | dependency | suggested helper |','|---|---|---|---|---|---|---|']
    for sev,k,m,st,g,dep,h in L:
        out.append(f'| {sev} | {k} | {m} | {st} | {g} | {dep} | {h} |'); n+=1
    out.append('')
out.insert(4,f'Total open items: {n}. Closure-blocking status is tracked separately in `status.md`.\n')
open('results/arch/visual_audit_1016/rom/worklist.md','w').write('\n'.join(out)+'\n')
json.dump({o:sorted(by[o]) for o in by},open('/tmp/visrom/worklist_by_owner.json','w'))
print(n,{o:len(by[o]) for o in by})
