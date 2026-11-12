"""CLAND-FACEWIN-1 11-11: the writer-face (fstart) relay window leaves FIRM FT bit sites / hard cores for the nearest free
segment of its face (QC cbn_q01__cldd6ea846: rsf_o window on the 64 FT bit sites of a00 stage 7, 3_3 "no legal
nonoverlapping row/site ... writer-face:rsf_o"); a clear window, or one beside only its own local-reset window, is
unchanged; with no free window within reach it stays and the reason is recorded."""
import landing_place as LP


def ft_column(x0, x1, y1):
    """one FT stage of lower-left bit sites on 2.16-um columns x0..x1, rows 0..y1 (QC a00 stage 7 form)"""
    pts, x = [], x0
    while x <= x1 + 1e-9:
        pts += [[x, round(0.27 * k, 2)] for k in range(int(y1 / 0.27) + 1)]
        x += 2.16
    return {'name': 'a00', 'bit_site_cell_um': [1.404, 0.27], 'bit_sites_um': [pts]}


def vehicle(pin_xy, ft=None, local_resets=(), cores=()):
    return {'outline_um': [1200.0, 2500.0], 'hard_cores': list(cores), 'ft_slots': [ft] if ft else [],
            'clock': {'landing_writer_start': {'depth': 1, 'branches': {'rsf_o': {'stages': [
                          {'xy_um': [600.0, 300.0], 'raw_reset': 'rst_n_t0'}]}}},
                      'landing_local_resets': [{'name': n, 'xy_um': xy} for n, xy in local_resets],
                      'landing_contract': {'pins': [{'name': 'cland_fstart_out_rsf_o', 'dir': 'out', 'xy_um': pin_xy}]}}}


def face(t):
    LP.FACE_WINDOW_NOTES.clear()
    return next(r for _, r, tag in LP._writer_start_groups(t) if tag == 'writer-face:rsf_o')


def test_clear_window_unchanged():
    assert face(vehicle([237.088, 2.656])) == [232.768, 0.0, 241.408, 8.64]
    assert LP.FACE_WINDOW_NOTES == []


def test_own_local_reset_window_alone_is_not_a_blocker():
    t = vehicle([237.088, 2.656], local_resets=[('start_3', [237.09, 2.66])])
    assert face(t) == [232.768, 0.0, 241.408, 8.64]
    assert LP.FACE_WINDOW_NOTES == []


def test_window_on_ft_bit_sites_moves_along_the_face():
    ft = ft_column(233.28, 239.76, 9.0)
    t = vehicle([237.088, 2.656], ft=ft, local_resets=[('start_3', [237.09, 2.66])])
    assert LP.face_window_blockers(t, [232.768, 0.0, 241.408, 8.64]) == ['ft']
    r = face(t)
    assert r != [232.768, 0.0, 241.408, 8.64]
    assert r[1] == 0.0 and abs(r[3] - r[1] - 8.64) < 1e-6           # same face row band (S edge), same size
    assert LP.face_window_blockers(t, r, [LP._status_reset_groups(t)[0][1]]) == []
    assert abs((r[0] + r[2]) / 2 - 237.088) <= LP.FACE_WINDOW_REACH_UM
    assert len(LP.FACE_WINDOW_NOTES) == 1 and 'moved' in LP.FACE_WINDOW_NOTES[0] and 'ft' in LP.FACE_WINDOW_NOTES[0]


def test_hard_core_blocks_and_moves():
    core = {'inst': 'u_c', 'origin_um': [225.0, 0.0], 'outline_um': [20.0, 30.0]}
    r = face(vehicle([237.088, 2.656], cores=[core]))
    assert r[2] <= 225.0 - 4.32 + 1e-6 or r[0] >= 245.0 + 4.32 - 1e-6 or r[1] >= 30.0 + 4.32 - 1e-6


def test_no_free_window_within_reach_is_kept_and_recorded():
    ft = ft_column(150.0, 330.0, 80.0)      # FT sites cover the face +-90 um and 80 um deep: nothing within 60 um
    t = vehicle([237.088, 2.656], ft=ft)
    assert face(t) == [232.768, 0.0, 241.408, 8.64]
    assert len(LP.FACE_WINDOW_NOTES) == 1 and 'kept' in LP.FACE_WINDOW_NOTES[0]
