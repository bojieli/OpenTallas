#!/usr/bin/env python3
"""Audit a generic NAND basis and mask domain; never map or allocate a field."""
from decimal import Decimal as D
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools.w10_q_constructive_area_bound import count_gates

def require(ok,why):
    if not ok:raise ValueError(why)

def nand(a,b):return (~(a&b))&15

def or_basis_witness():
    # Four rows encode (A,B)=00,01,10,11. Give the search free constants too.
    base=[0,15,12,10];target=14
    hits=[]
    for a,b in itertools.product(base,repeat=2):
        g1=nand(a,b)
        if g1==target:hits.append([g1])
        for c,d in itertools.product(base+[g1],repeat=2):
            g2=nand(c,d)
            if g2==target:hits.append([g1,g2])
    require(not hits,'two NANDs unexpectedly implement independent-input OR')
    g1=nand(12,12);g2=nand(10,10);g3=nand(g1,g2)
    require(g3==target,'three-NAND positive witness fails')
    return dict(inputs_truth_masks={'A':12,'B':10},target_OR_truth_mask=14,
        all_up_to_two_gate_acyclic_NAND2_networks_exhausted=True,
        free_constants_allowed=[0,15],two_gate_implementations=0,
        three_gate_positive_truth_masks=[g1,g2,g3],
        qualification='Generic independent input OR, NAND2 only, no free complemented input; not a mapped lower bound for the whole coarse netlist.')

def build():
    inventory=json.loads((ROOT/'results/uarch/w10_q_elaboration_inventory_r1/inventory.json').read_text())
    construction=json.loads((ROOT/'results/uarch/w10_q_elaboration_inventory_r1/construction.json').read_text())
    raw=Path(inventory['inputs']['netlist']['path']).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==inventory['inputs']['netlist']['sha256'],'coarse source pin drift')
    cells=json.loads(raw)['modules']['ot_v41_rom_elem_q_wake_w10']['cells'].values()
    ors=[c for c in cells if c['type']=='$or']
    output_bits=sum(int(c['parameters'].get('Y_WIDTH','0'),2) or len(c['connections']['Y']) for c in ors)
    current=count_gates({'type':'$or','connections':{'A':[1],'B':[2],'Y':[3]}})
    require(current==2,'construction coefficient changed; review updated source')
    nand_area=D(construction['palette']['nand']['area_um2'])
    local_delta=D(output_bits)*nand_area
    placed_delta=2*local_delta
    return dict(schema='opentallas.w10.q.mask.nand.basis.audit.v1',
        mask_fix='Explicit combined Q/BF [128,7168] domain check before any source/allocator calls; no assertions, clamp or geometry change.',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            'tools/w17_conservative_geometry_search.py','tests/test_w17_geometry_mask_domain.py',
            'results/quality/w10_q_mask_basis_audit_20261001/reproduce.py','tests/test_w10_q_nand_basis_audit.py',
            'tools/w10_q_constructive_area_bound.py','tools/uarch_model.py',
            'results/uarch/w10_q_elaboration_inventory_r1/inventory.json',
            'results/uarch/w10_q_elaboration_inventory_r1/construction.json']},
        historical_construction_pin='6da3c7a60af782e769f9e4c62c44e1f0d13b0fd6',
        coarse_netlist_sha256=inventory['inputs']['netlist']['sha256'],
        OR_basis_witness=or_basis_witness(),
        source_defect=dict(operator='$or',current_NAND2_per_generic_output_bit=current,
            necessary_NAND2_for_independent_inputs_without_complements=3,
            observed_operator_cells=len(ors),charged_output_bits=output_bits),
        local_repricing_sensitivity=dict(additional_NAND2=output_bits,
            additional_standard_cell_um2=str(local_delta),additional_50pct_placement_um2=str(placed_delta),
            hypothetical_OR_only_adjusted_pair_mm2=str((D(construction['conditional_50pct_cell_plus_macro_budget_um2'])+placed_delta)/D(1000000)),
            additional_q1024_reservation_mm2=str(placed_delta/D(1000000)*1024),
            qualification='Replace generic OR2 coefficient by OR3 only. Not a complete corrected construction, actual netlist minimum, power or timing qualification.'),
        unresolved_firstprinciples=['Shared complements/constant folding not proven by isolated per-operator costs',
            'Signed/bidirectional shift and multiport/reset lowering have coefficients but no emitted equivalent NAND construction',
            'Actual fanout, wire, ICG load, clock phase and contextual SS/FF remain outside Boolean gate counts'],
        original_records_preserved=True,geometry_default_receipt_byte_identical=True,
        construction_tool_and_record_unchanged=True,physical_admission=False,jobs_launched=0,
        ram_whole_candidate_pin='64c6bffe0442cdf9126a6eaac752591b6a8e8389',
        coordination='Ram owns whole composition; join any later corrected construction/power receipt explicitly. Do not promote original generic OR coefficient as a proven bound or duplicate allocator/RTL.')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(build(),indent=2)+'\n')
