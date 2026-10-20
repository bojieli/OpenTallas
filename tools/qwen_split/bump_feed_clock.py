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
    destination = ('d2d_rom', 'fwd_epoch' if kind == 'epoch' else 'fwd_link_rst_n')
    if list(eps) != [source, destination]:
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
