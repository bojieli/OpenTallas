"""Finite DC resistor surrogate only. Units: um, kohm, mA, V."""
import json, math, hashlib, re
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
src=json.loads((P/'model.json').read_text())
old=json.loads((P/'input/c634_model.json').read_text())
R={k:v['r_kohm_um'] for k,v in src['analytical_RC_coefficients'].items()}
VR=src['via_R_kohm']
raw=(P/'input/current_setRC.tcl').read_text()
for layer,value in R.items():
    assert math.isclose(value,float(re.search(r'set_layer_rc -layer '+layer+r' -resistance (\S+)',raw).group(1)),rel_tol=1e-12)
for via,value in VR.items():
    assert math.isclose(value,float(re.search(r'set_layer_rc -via '+via+r' -resistance (\S+)',raw).group(1)),rel_tol=1e-12)
def capped_max(coeff,total,caps):
    if total<0 or any(c<0 for c in caps) or sum(caps)<total-1e-12: raise ValueError('infeasible current/caps')
    left=total; value=0.; alloc=[0.]*len(coeff)
    for i in sorted(range(len(coeff)),key=lambda i:coeff[i],reverse=True):
        take=min(left,caps[i]); value+=coeff[i]*take; alloc[i]=take;left-=take
    return value,alloc
out={'status':'PARAMETERIZED_DC_SURROGATE_NOT_SUPPLY_ADEQUACY','source_commit':'spread192 proposed geometry from exact5de','families':{},'controls':{}}
for family,f in src['families'].items():
    H=f['outline_nm'][1]/1000
    ff={'nets':{},'conditional_cost':{k:f[k] for k in ['contact_count','new_lower_via_count','V4_count','north_attachment_apron_area_um2','core_reserved_interface_area_um2','analytical_core_remaining_area_um2','required_core_density_multiplier','outline_area_delta_from_c634_um2','state_bit_delta','cycle_delta']},'outline_nm':f['outline_nm'],'four_M5_port_rectangles_nm':[]}
    for net in ('VDD','VSS'):
        contacts=[a for a in f['contact_ledger'] if a['net']==net]
        y=[]; branches=[]; detail=[]
        for a in contacts:
            v={t['type']:t['center_nm'] for t in a['via_stacks']}
            yy=v['VIA45'][1]/1000;y.append(yy)
            # Scalar centerline resistor representation: M1 port is its center/V1,
            # V1/V2 coincident, M3 joins actual separated V2/V3 centers.
            lengths={'M1':0.,'M2':abs(v['VIA12'][0]-v['VIA23'][0])/1000,'M3':abs(v['VIA23'][1]-v['VIA34'][1])/1000,'M4':abs(v['VIA34'][0]-v['VIA45'][0])/1000}
            b=sum(VR[k] for k in ('V1','V2','V3','V4'))+sum(lengths[k]*R[k]*(24/120 if k=='M4' else 1) for k in lengths)
            # Explicit finite endpoint-interface variant: farthest end of 84nm
            # M1 pad lies 42nm from center. Not a characterized core impedance.
            endpoint_extra=.042*R['M1']
            branches.append(b)
            detail.append({'id':a['id'],'tap_y_um':yy,'centerline_lengths_um':lengths,'branch_R_kohm':b,'M1_endpoint_variant_extra_R_kohm':endpoint_extra,'full_rail_R_kohm':(a['c634_rail_unchanged_nm'][2]-a['c634_rail_unchanged_nm'][0])/1000*R['M4']*24/120,'unused_rail_arms_have_no_load_in_this_interface_model':True,'full_5de_guard_path_R_kohm':next(z for z in f['path_R_inventory'] if z['id']==a['id'])['N_or_S_port_to_M1_port_full_height_bound_R_kohm']})
        n=len(y); rho=R['M5']
        K=np.array([[rho*min(a,b)*(H-max(a,b))/H for b in y] for a in y])
        Z=K+np.diag(branches)
        # Independent segmented-resistor nodal solve, not formula tautology.
        order=np.argsort(y); ys=[0.]+[y[i] for i in order]+[H]
        G=np.zeros((n,n))
        for k in range(n+1):
            conductance=1/(rho*(ys[k+1]-ys[k]))
            if k>0:G[k-1,k-1]+=conductance
            if k<n:G[k,k]+=conductance
            if 0<k<n:G[k-1,k]-=conductance;G[k,k-1]-=conductance
        inv=np.linalg.inv(G); oracle=K[np.ix_(order,order)]
        error=float(np.max(np.abs(inv-oracle))); assert error<1e-12
        assert np.min(Z)>=0 and np.min(np.linalg.eigvalsh(Z))>0
        uniform=np.sum(Z,axis=1)/n
        hotspot=float(np.max(Z)); where=np.unravel_index(np.argmax(Z),Z.shape)
        caps=[1/n]*n
        for row in Z:
            val,alloc=capped_max(row,1,caps);assert abs(val-sum(row)/n)<1e-12
        single_K=rho*np.minimum(np.array(y)[:,None],np.array(y)[None,:])
        singleZ=single_K+np.diag(branches) # south only, north open
        ff['nets'][net]={'interface_count':n,'interfaces':detail,'Z_kohm':Z.tolist(),'shared_trunk_K_kohm':K.tolist(),'uniform_current_max_drop_V_per_mA':float(max(uniform)),'arbitrary_nonnegative_total_current_max_drop_V_per_mA':hotspot,'hotspot_observation_id':contacts[where[0]]['id'],'hotspot_injection_id':contacts[where[1]]['id'],'M1_endpoint_variant_hotspot_V_per_mA':hotspot+.042*R['M1'],'south_only_north_open_hotspot_V_per_mA':float(np.max(singleZ)),'independent_nodal_inverse_error_kohm':error,'total_M5_trunk_R_kohm':rho*H,'centerline_branch_R_range_kohm':[min(branches),max(branches)],'shared_trunk_adversarial_bound_kohm':rho*H/4,'single_end_full_height_bound_kohm':rho*H,'port_reaction_formula':'south=sum_i I_i*(H-y_i)/H; north=sum_i I_i*y_i/H; each nonnegative; sum=I_total'}
        trunk=next(z for z in f['new_actual_supply_metal'] if z['role']=='full_height_internal_supply_trunk' and z['net']==net)['rect_nm'];x0,_,x1,h=trunk
        ff['four_M5_port_rectangles_nm'] += [{'net':net,'face':'S','rect_nm':[x0,0,x1,84]},{'net':net,'face':'N','rect_nm':[x0,h-84,x1,h]}]
    ff['uniform_supply_plus_return_V_per_mA']=sum(a['uniform_current_max_drop_V_per_mA'] for a in ff['nets'].values())
    ff['adversarial_supply_plus_return_V_per_mA']=sum(a['arbitrary_nonnegative_total_current_max_drop_V_per_mA'] for a in ff['nets'].values())
    ff['M1_endpoint_supply_plus_return_V_per_mA']=ff['adversarial_supply_plus_return_V_per_mA']+2*.042*R['M1']
    ff['conditional_TT_signal_access_full_toggle_energy_fj']=old['families'][family]['corner_costs']['tt']['all_nonclock_plus_complete_clock_energy_fj']
    ff['width_proposals_not_geometry_changes']=[{'width_factor':q,'M5_total_area_um2':2*H*.024*q,'M5_delta_area_um2':2*H*.024*(q-1),'same_center_trunk_VDD_VSS_gap_nm':192-24*q,'fails_retained_72nm_parallel_gap':192-24*q<72,'best_continuum_adversarial_loop_bound_V_per_mA':sum(max(n['centerline_branch_R_range_kohm']) for n in ff['nets'].values())+2*R['M5']*H/(4*q)} for q in (1,2,3)]
    out['families'][family]=ff
out['controls']={'nodal_inverse_vs_Green_function':'PASS both nets/families <1e-12 kohm','positive_definite_passive_Z':'PASS','uniform_caps_recover_uniform_distribution':'PASS','negative_current_refused':False,'infeasible_caps_refused':False,'disconnected_lower_V3':'open branch has no finite DC solution for positive current; refuses finite drop','equal_supply_and_return_currents':'required independently on each net; VSS is not free ground at core'}
for name,args in [('negative_current_refused',([1.],-1,[1.])),('infeasible_caps_refused',([1.],2,[1.]))]:
    try:capped_max(*args)
    except ValueError:out['controls'][name]=True
    assert out['controls'][name]
# A removed VIA34 leaves a positive-current M1 load node electrically open.
Gopen=np.array([[1.,0.],[0.,0.]])
try:
    np.linalg.solve(Gopen,np.array([0.,1.]))
    raise AssertionError('open positive-current port incorrectly solved')
except np.linalg.LinAlgError:
    out['controls']['removed_VIA34_singular_positive_current_system']='PASS actual solve refuses'
# Both-end feeding must reduce each transfer coefficient versus south-only.
for family,ff in out['families'].items():
    for net,z in ff['nets'].items():
        ys=np.array([v['tap_y_um'] for v in z['interfaces']]); H=src['families'][family]['outline_nm'][1]/1000
        both=np.array(z['shared_trunk_K_kohm']); south=R['M5']*np.minimum(ys[:,None],ys[None,:])
        assert np.all(south>=both-1e-12)
        assert max(ys)<H and min(ys)>0
out['controls']['loss_of_north_feed_increases_every_shared_transfer']='PASS'
(P/'current_analysis.json').write_text(json.dumps(out,indent=2)+'\n')
summary={k:{q:v[q] for q in ['uniform_supply_plus_return_V_per_mA','adversarial_supply_plus_return_V_per_mA','M1_endpoint_supply_plus_return_V_per_mA']} for k,v in out['families'].items()}
(P/'current_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
