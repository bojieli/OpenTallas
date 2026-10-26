"""Bind only the static link's actual bump lanes to their incoming clock feed.

This establishes source connectivity, not a native receiver or reset-phase proof.
The caller explicitly opts in; ordinary bumps retain their existing clock rule.
"""
import re


def source_clock(model, bid, eps):
    match = re.fullmatch(r'lnk_fwd_(epoch|lrst)(?:__fo\d+)?', bid)
    if not match:
        return None
    kind = match[1]
    source = ('bump_fwd_' + kind, 'o')
    # QW-GEN5 g5 first GEN: the epoch strobe fans out to d2d_rom AND (lnk_fwd_epoch__fo1) to sys_face's run anchor
    # (sys_face_bind.py 'fwd_epoch'); both are actual static-link captures of the bump signal
    allowed = {('d2d_rom', 'fwd_epoch'), ('sys_face', 'fwd_epoch')} if kind == 'epoch' else {('d2d_rom', 'fwd_link_rst_n')}
    if len(eps) != 2 or tuple(eps[0]) != source or tuple(eps[1]) not in allowed:
        raise ValueError(f'bump feed clock {bid}: wrong source/destination {eps}')
    by = {i.name: i for i in model['insts']}
    for name, master in [('bump_fwd_' + kind, 'qfd_sigbump'), ('ckb_rom', 'qfd_ckbump'),
                         ('clk_rx', 'qfd_clkrx')]:
        if name not in by or by[name].master != master:
            raise ValueError(f'bump feed clock {bid}: missing actual {name}/{master}')
    feeds = [b for b in model['buses'] if b[0] == 'pll_fwd']
    if len(feeds) != 1:
        raise ValueError(f'bump feed clock {bid}: absent or duplicate pll_fwd')
    _, cls, width, pins = feeds[0]
    core = model.get('g5_clocking', {}).get('core_feed')
    if core:
        # QW-GEN5 g5: the die core clock enters at the centre bump (pll_core -> clk_rx.pll_fwd); the corner bump's
        # pll_fwd net then carries ONLY the static link's bump hop-0 stations (source-synchronous with its bumps)
        cores = [b for b in model['buses'] if b[0] == 'pll_core']
        if len(cores) != 1 or cores[0][3] != [(core['inst'], 'pll_ck'), ('clk_rx', 'pll_fwd')] or \
                by.get(core['inst']) is None or by[core['inst']].master != 'qfd_ckbump':
            raise ValueError(f'bump feed clock {bid}: core feed pll_core lacks actual centre bump -> receiver topology')
        if cls != 'clock_trunk' or width != 1 or pins[0] != ('ckb_rom', 'pll_ck') or \
                pins.count(('ckb_rom', 'pll_ck')) != 1 or ('clk_rx', 'pll_fwd') in pins:
            raise ValueError(f'bump feed clock {bid}: pll_fwd lacks actual scalar link-bump topology (core feed mode)')
        return 'pll_fwd'
    if cls != 'clock_trunk' or width != 1 or pins[0] != ('ckb_rom', 'pll_ck') or \
            pins.count(('ckb_rom', 'pll_ck')) != 1 or pins.count(('clk_rx', 'pll_fwd')) != 1:
        raise ValueError(f'bump feed clock {bid}: pll_fwd lacks actual scalar bump/receiver topology')
    return 'pll_fwd'


def bind_source(model, lane, eps):
    """Set the source before reset-calendar finalization and clock-region refile."""
    clock = source_clock(model, lane['bid'], eps)
    if clock is None:
        return False
    lane['src_ck'] = clock
    lane['src_basis'] = 'actual ckb_rom.pll_ck feed shared with clk_rx.pll_fwd; no regional hop-0 root'
    lane['source_feed_contract'] = dict(
        schema='opentallas.qwen.bump-source-feed.v1', clock=clock,
        physical_qualification_eligible=False,
        owed=['native physical receiver/feed arrival', 'source-domain reset release and epoch calendar'])
    return True
