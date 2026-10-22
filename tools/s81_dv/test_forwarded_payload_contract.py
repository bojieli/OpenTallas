"""Landing payload must exclude receiver reset and selector input trees."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dv_rvcase import forwarded_payload_width


def test_selected_landing_and_relay_payloads():
    for master, width in [('dsfd_dvland_276', 276), ('dsfd_dvland_276l', 276),
                          ('dsfd_dvland_pvrd', 562), ('dsdv_svc_busland_16', 16),
                          ('dsdv_svc_busland_2133', 2133), ('dsdv_pv_local_land_276', 276),
                          ('dsfd_dvrly_276_SN', 276), ('dsfd_dvrlyh_70_NS', 70)]:
        assert forwarded_payload_width(master) == width


def test_no_inferred_contract_for_unknown_or_near_match():
    for master in ['dsfd_dvland_new', 'dsfd_dvland_276_wrong', 'some_tile_276', 'dsdv_hostb_landing']:
        assert forwarded_payload_width(master) is None


def test_contract_uses_emitted_standin_cell_and_exact_closed_master():
    from dv_rvcase import forwarded_payload_contracts
    insts = [('dsdv_svc_busland_805','ld_dn',{},{}),
             ('dsfd_dvland_276l','ld_xr',{},{}),
             ('unknown','u_other',{},{})]
    kinds = {'ld_dn':'standin','ld_xr':'closed','u_other':'standin'}
    assert forwarded_payload_contracts(insts,kinds,{'ld_dn':'rv_ld_dn','u_other':'rv_other'}) == {
        'rv_ld_dn':805,'dsfd_dvland_276l':276}


def test_corner_hook_updates_step_artifact_before_equalization(tmp_path):
    from dv_rvcase import install_controller_corner_repair
    # die_repair_tcl returns only a source command; its generated artifact owns
    # the equalization call. Hooking that return fragment misses the call.
    path = tmp_path/'die_repeaters_step.tcl'
    path.write_text('source /work/die_repeaters.tcl\not_die_rep_fclk_equalize /work/fclk {n*_fck*} {BUFx8}\n')
    install_controller_corner_repair(tmp_path)
    text = path.read_text()
    assert text.index('s81_ctrl_corner_repair') < text.index('ot_die_rep_fclk_equalize')
    assert (tmp_path/'ctrl_corner.tcl').is_file()
