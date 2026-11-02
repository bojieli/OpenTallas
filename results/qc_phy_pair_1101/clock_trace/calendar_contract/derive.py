"""Derive disabled FDI source/model constraints from the selected native body.

No programme date, source plan, RTL selection, or physical phase is invented.
The phase map is an ideal diagnostic condition, not a sign-off aperture.
"""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated'
OUT.mkdir(exist_ok=True)
source=ROOT/'inputs/ot_coll_static_linkcal.sv'
text=source.read_text()
anchor='u_x (.clk(lck), .rs_n(rs_l), .d(slot), .q(r_slot));'
assert text.count(anchor)==1
assert 'module ot_coll_lcal_tx' in text
mutant=text.replace(anchor,"u_x (.clk(lck), .rs_n(rs_l), .d(1'b0), .q(r_slot));")
(OUT/'mutant_zero_calendar_slot.sv').write_text(mutant)

# Match frozen qc_vehicle: core posedge416ps + n*833ps; declared FDI
# posedge500ps + m*1000ps. Its relative phase repeats after1000 core edges.
core,link,offset=833,1000,84
rows=[]
for edge in range(1000):
    delta=(offset-core*edge)%link
    status='IDEAL_CAPTURE' if 0<delta<core else 'EDGE_COINCIDENT' if delta in (0,core) else 'IDEAL_MISS'
    rows.append(dict(core_edge_mod1000=edge,next_fdi_edge_ps=delta,classification=status))
eligible=[r['core_edge_mod1000'] for r in rows if r['classification']=='IDEAL_CAPTURE']
missed=[r['core_edge_mod1000'] for r in rows if r['classification']=='IDEAL_MISS']
coincident=[r['core_edge_mod1000'] for r in rows if r['classification']=='EDGE_COINCIDENT']
assert rows[100]['classification']=='IDEAL_CAPTURE'
assert rows[101]['classification']=='IDEAL_MISS'
trace=json.loads((ROOT/'inputs/current_transport_trace.json').read_text())
calls=json.loads((ROOT/'inputs/selected_face_calls.json').read_text())
assert [r['parameters']['PHY'] for r in calls]==[367,343,369]
assert all(r['parameters']['SAFE']==0 and r['parameters']['TOK_REG']==0 for r in calls)
peers=[2,1,0]
parts=['io_serdes','io_serdes_1','io_serdes_2']
tx={p:next(r for r in trace['lanes'] if r['dst']==p and r['width']==597) for p in parts}
rx={p:next(r for r in trace['lanes'] if r['src']==p and r['width']==597) for p in parts}
calendar_rows=[]
for index,(part,call) in enumerate(zip(parts,calls)):
    peer=parts[peers[index]]
    tw,rw=tx[peer],rx[part]
    folded_ends=len(tw['macro_pin_reg_ends'])+len(rw['macro_pin_reg_ends'])
    known=223+tw['bound_stages']+rw['bound_stages']-folded_ends
    cp=call['parameters']
    calendar_rows.append(dict(face=index,peer_face=peers[index],selected_parameters=cp,
        peer_tx_bound_stages=tw['bound_stages'],own_rx_bound_stages=rw['bound_stages'],
        macro_fdi_cycles=223,folded_hard_register_ends=folded_ends,
        hypothetical_station_only_all_FDI_component_cycles=known,
        selected_PHY_minus_hypothetical_component=cp['PHY']-known,
        new_CA_START_extra_link_cycles=None,new_PHY_calendar=None,
        core_relay_age_difference=cp['PEER_R']-cp['R'],
        corresponding_FDI_age_correction=None))
roles=[]
for row in trace['boundary_stations']+trace['third_path_forwarding_stations']:
    roles.append(dict(partition=row['partition'],instance=row['instance'],
                      width=row['payload_width'],epoch_width=1,
                      proposed_clock_source='clk_serdes',
                      reset_release_domain='FDI_REQUIRED_UNBOUND',
                      start_epoch='FDI_REQUIRED_UNBOUND'))
result=dict(schema='opentallas.qc_fdi_calendar_contract.v1',enabled=False,emit_allowed=False,
            source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            selected_native=dict(module='ot_coll_lcal_tx',KC=4,KW=2,SAFE_RING=0,LAND_CORE=0,
                                 authority='frozen bd55/current82190c1ff+f79c1e228 native face SAFE0/TOK_REG0'),
            existing_clock_source='clk_serdes',public_clock_ports_added=0,public_clock_ports_removed=0,
            proposed_typed_station_roles=roles,
            hardware_added_ff=None,added_start_reset_ff=None,
            exact_new_calendar=None,FDI_START_epoch=None,programme_reprice=None,
            selected_face_calls=calls,calendar_component_equations=calendar_rows,
            component_equation='PHY_j = 223 + (TX_peer-1) + (RX_self-1) + U_j, only under hypothetical all-FDI station clocking; U_j unjoined',
            configured_diagnostic_clocks=dict(core_period_ps=core,core_posedge0_ps=416,
                fdi_period_ps=link,fdi_posedge0_ps=500,physical_phase_qualified=False),
            ideal_phase_period=dict(core_edges=1000,fdi_edges=833,time_ps=833000),
            ideal_capture_residues=eligible,ideal_miss_residues=missed,
            edge_coincident_residues=coincident,witness_phase_rows=[rows[100],rows[101]],
            required_contract=['real source relationship and per-token phase/setup-hold aperture',
                'qualified FDI START/reset release epoch and opposite-peer slot relationship',
                'per-bus FDI roles through 15 boundary and 95 FT groups plus CA/FCLK/FSTART/reset',
                'new PHY/LX calendar with explicit link-edge/core-edge units and source programme dates'],
            claim='Constraint and actual native pulse counterexample only; no executable programme or source rewrite')
(OUT/'contract.json').write_text(json.dumps(result,indent=2)+'\n')
print('FDI_PHASE_CONSTRAINT',len(eligible),'ideal-capture',len(missed),'ideal-miss',len(coincident),'coincident')
