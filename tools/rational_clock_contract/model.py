"""Isolated QCOLL clock contract. Never imports or changes production flow."""
from fractions import Fraction as F
from pathlib import Path
import hashlib, json
VERSION = 'qcoll-rational-clock-v1'
SOURCES = ['rtl/physical/ot_qfd_ucie_six_five.sv',
           'rtl/physical/ot_qfd_collective_static_io.sv',
           'rtl/physical/ot_qfd_collective_static_io_production.sv']
CORE = F(2500, 3)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def contract(root):
    return dict(schema=VERSION, source_sha256={p:digest(root/p) for p in SOURCES},
        parent_period_ps=5000, ratios={'core':6,'fdi':5},
        reset_first_edge_delta_ps=[str(-CORE),str(CORE)],
        roots={'gearbox_core_ck':'core','fdi_ck':'fdi',
               **{f'fdi_rx_ck[{i}]':'fdi' for i in range(3)}},
        timing_policy='ordinary_related_max_and_min_no_exceptions',
        shared_input_roots={'shared_rx':['fdi_ck','fdi_rx_ck[0]','fdi_rx_ck[1]','fdi_rx_ck[2]'],
                            'shared_rx_valid':['fdi_ck']},
        physical_phase_evidence=None, per_root_phi_minus_R_evidence=None,
        release_verdict='UNQUALIFIED')

def validate(c, root):
    if c['schema'] != VERSION or c['parent_period_ps'] != 5000 or c['ratios'] != {'core':6,'fdi':5}:
        raise ValueError('wrong source-bound clock ratio')
    if c['reset_first_edge_delta_ps'] != [str(-CORE),str(CORE)]:
        raise ValueError('unproved reset/phase window')
    if c['source_sha256'] != {p:digest(root/p) for p in SOURCES}:
        raise ValueError('source pin mismatch')
    if c['roots'] != contract(root)['roots'] or c['shared_input_roots'] != contract(root)['shared_input_roots']:
        raise ValueError('root or shared-input ownership mismatch')
    if c['timing_policy'] != 'ordinary_related_max_and_min_no_exceptions':
        raise ValueError('unproved timing exception')
    return True

def windows(early_read_edges=0):
    """Exact per-bit event obligations, including overwrites; units picoseconds.

    C_n = n*2500/3, F_n = delta+n*1000. Enumerate one block:
    state repeats every LCM(2 TX banks,3 RX banks)=6 blocks/30 ns.
    All four differences are affine in delta, so endpoints prove the full
    continuous reset-origin interval [-2500/3,+2500/3], not only sampled phases.
    Positive guards remain before CQ, setup/hold, RC, uncertainty and clock skew.
    """
    fragments=[]
    for bit in range(3588):
        j,k=bit//598,bit//1043
        row=dict(bit=bit,word=j,beat=k,
            tx_setup_ps=F(5000+1000*k)-(j+early_read_edges)*CORE-CORE,
            tx_hold_ps=(12+j)*CORE-F(5000+1000*k)-CORE,
            rx_setup_ps=(24+j-early_read_edges)*CORE-F(10000+1000*k)-CORE,
            rx_hold_ps=F(25000+1000*k)-(24+j)*CORE-CORE)
        fragments.append(row)
    keys=['tx_setup_ps','tx_hold_ps','rx_setup_ps','rx_hold_ps']
    minima={key:str(min(row[key] for row in fragments)) for key in keys}
    if min(F(v) for v in minima.values()) <= 0:
        raise ValueError('enabled read collides with write or overwrite')
    # Preserve the exact intervals where word and beat remain the same.
    packed=[]
    for row in fragments:
        if packed and (packed[-1]['word'],packed[-1]['beat'])==(row['word'],row['beat']):
            packed[-1]['bit_hi']=row['bit']
        else:
            packed.append(dict(bit_lo=row['bit'],bit_hi=row['bit'],word=row['word'],beat=row['beat'],
                               **{key:str(row[key]) for key in keys}))
    return dict(minimum_guards_ps=minima, fragments=packed,
        tx_flop_bits=7176,rx_flop_bits=10764,bank_payload_flop_bits=17940,
        declared_root_flop_bits=dict(gearbox_core_ck=7789,fdi_ck=1058,rx_roots=[3588,3588,3588]),
        declared_total_flop_bits_before_synthesis=19611,
        core_payload_bits_per_5ns=3588,physical_FDI_bits_per_5ns=5215,
        active_FDI_bits_per_5ns=4172,payload_Gbps=717.6,
        enabled_window_proof='exact affine endpoint bounds; NOT STA exceptions')

def clocks_tcl(delta=F(0)):
    """Standalone virtual 200 MHz common-PLL source, 1.2/1.0 GHz outputs.

    Edge shifts explicitly represent F0 phase. PLL source is a fixture only.
    No generated-clock waveform is accepted as physical PLL evidence.
    """
    delta=F(delta)
    if abs(delta)>CORE:raise ValueError('phase outside proved reset window')
    s='create_clock -name pll_ref -period 5000 [get_ports pll_ref]\n'
    s+='create_generated_clock -name core -master_clock pll_ref -source [get_ports pll_ref] -multiply_by 6 [get_ports core_ck]\n'
    shifts=' '.join(f'{float(delta-x):.12f}' for x in (0,2000,4000))
    for name in ['fdi_ck','rx0_ck','rx1_ck','rx2_ck']:
        s+=f'create_generated_clock -name {name} -master_clock pll_ref -source [get_ports pll_ref] -edges {{1 2 3}} -edge_shift {{{shifts}}} [get_ports {name}]\n'
    s+='set_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\n'
    return s

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    out=root/'results/arch/qwen_rational_clock_contract_1015'
    out.mkdir(parents=True,exist_ok=True)
    c=contract(root);validate(c,root)
    (out/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
    (out/'model.json').write_text(json.dumps(windows(),indent=2)+'\n')
