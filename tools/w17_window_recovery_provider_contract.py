"""Model-only recovery receipt contract; no RTL provider or timer implementation."""
from dataclasses import dataclass

ACTORS = frozenset({'WINDOW', 'MUX', 'KARB', 'BACKEND', 'WRITE_INTENT',
                    'WRITE_VISIBLE', 'DELIVERY_FENCE'})


def window_tag(tag):
    """Actual TAG17: K=1 at bit16, WINDOW=00 at bits15:14."""
    if type(tag) is not int or not 0 <= tag < 1 << 17:
        raise ValueError('TAG17 required')
    return tag >> 14 == 4


@dataclass(frozen=True)
class OwnerSnapshot:
    lease: int
    revision: int
    owner_reads: int = 0
    owner_writes: int = 0
    owner_queued: int = 0
    owner_returns: int = 0
    owner_offer: int = 0
    owner_pipeline: int = 0
    latent_intents: int = 0
    owner_ack_pending: int = 0
    invisible_writes: int = 0
    other_client_entries: int = 0
    other_invisible_writes: int = 0
    other_pending_delivery: int = 0
    other_latent_intents: int = 0
    frozen: bool = True
    publication_invalid: bool = True

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name in ('frozen', 'publication_invalid'):
                if type(value) is not bool:
                    raise ValueError(name)
            elif type(value) is not int or value < 0:
                raise ValueError(name)
        if self.lease >= 1 << 64 or self.revision >= 1 << 64:
            raise ValueError('identity exhaustion')

    def owner_empty(self):
        # q/r/offer overlap is deliberate: predicates, not summed credits.
        return self.frozen and self.publication_invalid and not any(
            getattr(self, name) for name in self.__dataclass_fields__
            if not name.startswith('other_') and name not in ('lease', 'revision',
                            'frozen', 'publication_invalid'))


@dataclass(frozen=True)
class ModelReceipt:
    actor: str
    lease: int
    revision: int
    empty: bool = True

    def __post_init__(self):
        if self.actor not in ACTORS or type(self.empty) is not bool:
            raise ValueError('receipt actor/verdict')
        if any(type(v) is not int or not 0 <= v < 1 << 64
               for v in (self.lease, self.revision)):
            raise ValueError('receipt identity')


def model_restart_predicate(snapshot, receipts, *, lease, revision,
                            no_future_delivery, shared_reset=False, reset_domain_fence=False):
    """Hypothetical fresh receipts only. This does NOT authorize actual RTL."""
    return (snapshot.lease == lease and snapshot.revision == revision
            and snapshot.owner_empty() and len(receipts) == len(ACTORS)
            and all(isinstance(r, ModelReceipt) and r.empty
                    and r.lease == lease and r.revision == revision
                    for r in receipts)
            and {r.actor for r in receipts} == ACTORS
            and no_future_delivery is True
            and (not shared_reset or (reset_domain_fence is True
                 and not any(getattr(snapshot, n) for n in snapshot.__dataclass_fields__
                             if n.startswith('other_')))))


def actual_admission():
    return False  # No implemented lease-bound providers for these receipts.


def fault_write_action(state, *, accepted_block, same_edge_grant=False,
                       withdraw_receipt=False):
    """Future protocol obligation, not a claim current source can cancel."""
    if state not in ('IDLE', 'WC', 'WC_DONE', 'WS', 'WS_DONE'):
        raise ValueError('write state required')
    if not accepted_block:
        if state != 'IDLE' or same_edge_grant:
            raise ValueError('accepted intent missing')
        return 'withdraw_producer_offer_then_cancel'
    if state == 'IDLE':
        raise ValueError('inconsistent accepted intent')
    if state in ('WC_DONE', 'WS_DONE') or same_edge_grant:
        return 'drain_accepted_write_to_visible_receipt'
    if withdraw_receipt:
        return 'cancel_unaccepted_sector_invalidate_row_and_stage'
    return 'retain_intent_until_withdraw_receipt_or_drain'


@dataclass(frozen=True)
class LivenessBounds:
    accept: int
    service: int
    response_ready: int
    visible: int
    fence: int

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in self.__dict__.values()):
            raise ValueError('explicit positive bounds required')

    def conservative_cycles(self, read_leases, write_intents):
        if not (type(read_leases) is int and 0 <= read_leases <= 8
                and type(write_intents) is int and 0 <= write_intents <= 32):
            raise ValueError('bounded owner population required')
        # Each service bound includes all shared interference/refresh. Serial
        # summation is conservative; no assumed speed or independent overlap.
        return (read_leases * (self.accept + self.service + self.response_ready)
                + write_intents * (self.accept + self.service + self.visible)
                + 1 + self.fence)  # registered final-offer clear then fence


def timeout_action():
    return 'alarm_keep_frozen_preserve_all_owned_entries'


PROVIDERS = {
 'WINDOW': {
  'actual': ['state', 'refill_pending', 'refill_issued', 'refill_received',
             'fault', 'm_v/m_rdy', 's_v/s_rdy', 'row_valid', 'stage_valid'],
  'limitation': 'FR_PIPE bookkeeping stops on fault although s_rdy remains high; pending zero alone is not a receipt.',
  'required': 'WINDOW_OWNER_DRAIN_ACK(lease,revision): exact read retire/cancel ledger, frozen ingress, no latent write intent, publication invalidated.'},
 'MUX': {
  'actual': ['w_v/w_rdy', 'c_v/c_rdy', 'p_v/p_rdy', 'm_v/m_rdy', 's_v/s_tag/s_rdy', 'w_sv/w_srdy', 'w_wr_done'],
  'limitation': 'Nested combinational mux has no lease ledger. w_wr_done is forwarded; CKV/RoPE writes are disabled in this source.',
  'required': 'MUX_OWNER_DRAIN_ACK: withdraw WINDOW offer, include same-edge handshake, no retained WINDOW response/completion; other owners may continue.'},
 'KARB': {
  'actual': ['k_v/k_rdy', 'h_v/h_rdy/h_tag/h_we', 'r_v/r_rdy/r_tag', 'k_rsp_v/k_rsp_rdy', 'kw_out[p]', 'bw_out[p]', 'k_wr_done'],
  'limitation': 'kw_out covers K writes to issue ACK, not reads, WINDOW identity or physical visibility. Direct PIPE_OUT=0/PIPE_RSP=0 has no extra holding registers.',
  'required': 'KARB_OWNER_DRAIN_ACK: owner accepted/retired ledger; no WINDOW offer or outstanding write-completion obligation. If pipeline parameters change include g_pipe.v_q and u_rsp holding state.'},
 'BACKEND': {
  'actual': ['q_n/q_rp/q_tag/q_we', 'r_n/r_rp/r_tag', 'h_sched/h_tcol', 'rsp_v/rsp_tag/rsp_rdy', 'wr_done'],
  'limitation': 'Filter ring live entries by TAG17 K=1, owner00; h_sched aliases Q head, rsp_v aliases R head. Whole q_n/r_n zero is stronger than WINDOW-owner zero. No exported owner-drain port or full generation identity.',
  'required': 'BACKEND_OWNER_DRAIN_ACK: no owner Q/R/scheduled/registered offer or pending issue ACK, exact accepted identity ledger; sample after registered offer clears.'},
 'WRITE_INTENT': {
  'actual': ['producer state/blk_v/blk_ready/idle', 'WINDOW state WC/WC_DONE/WS/WS_DONE', 'grant', 'done_write', 'block_valid/row_valid/stage_valid'],
  'limitation': 'Producer EMPTY can precede source writes. Current WC_DONE creates WS after fault, and WS_DONE publishes without fault gate; current source has no cancel/intent-drain control.',
  'required': 'WINDOW_WRITE_INTENT_DRAIN_ACK: cancel only withdrawn unaccepted sector with handshake exclusion; drain granted sector and accepted block follow-up unless separately cancelled; invalidate publication under fault.'},
 'WRITE_VISIBLE': {
  'actual': ['idx wr_done', 'h_tcol', 'last_wr', 'CWL_PS', 'BURST_PS', 'CLK_PS'],
  'limitation': 'wr_done is column-issue/mem[] commit; physical tail is not an exported completion. last_wr timing history is not per-owner completion identity.',
  'required': 'BACKEND_WRITE_VISIBLE_DRAIN_ACK: all accepted owner writes acknowledged and physically visible, identity/order preserved; physical provider must specify tail/error completion. No timer implemented.'},
 'DELIVERY_FENCE': {
  'actual': ['same clk/rn path', 'idx registered rsp_v', 'direct nested mux/KARB routing'],
  'limitation': 'No FREEZE/FENCE lease request/ACK endpoint. Quiet cycles cannot exclude arbitrarily delayed duplicate/stale delivery or same-tag512 ghost.',
  'required': 'DELIVERY_FENCE_ACK(lease,revision): closed exactly-once delivery through every boundary, no future old-lease return/completion; otherwise carry nonwrapping identity end-to-end.'}
}

FENCE_STEPS = [
 'Freeze WINDOW admission and publication; latch lease/revision and capture concurrent handshakes before deciding cancellation.',
 'Withdraw unaccepted offers with explicit exclusion receipt, or drain only the pre-fault accepted block obligations. Invalidate affected row/stage.',
 'Retire/cancel exact identities at all hops; keep accepting owned responses despite fault; wait for all accepted write visible receipts.',
 'Wait for final registered offer/ACK to clear; collect fresh owner-empty receipts at same lease/revision. Other-owner work may remain.',
 'Close transport exactly-once fence and collect no-future-delivery ACK. Any late arrival invalidates receipts and preserves fault.',
 'Commit owner-local restart only after every receipt; advance lease/epoch, rebuild invalid publication. Shared rn reset instead needs every client/stack in its reset domain drained.'
]

NASH_HANDOFF = {
 'timer_decision': 'DEFER: no timer implementation authorized before healthy causal read-safety composition.',
 'healthy_dependency': 'Nash must bind final WC/WS issue/ACK order to each actual subsequent same-PC read schedule and its WR-to-RD constraint, including sector PC mapping, scale-last ordering, injection allocation and interference. Logical row publication need not itself mean physical drain if every consuming read is safely delayed.',
 'recovery_dependency': 'Even if healthy read safety passes, recovery must obtain WRITE_VISIBLE plus delivery fence; restart/reset cannot rely on a subsequent RD enforcing turnaround.',
 'requested_owner_response': 'Return source-pinned causal ordering proof or counterexample and exact required publication condition before selecting any healthy timer.',
 'coordination_status': 'Durable handoff only; no direct agent-message capability and no Nash acknowledgement asserted.',
 'healthy_timer_cost_if_needed': 'Prior 7-cycle/4-bit proposal remains conditional at CLK_PS1000, not implemented or selected.',
 'liveness': 'Finite bounds must cover accept fairness, backend service incl refresh/other clients, downstream ready, physical completion and fence. MAXSKIP16 and lowest-PC selection alone do not supply this contract. Unbounded holding/starvation implies no finite completion bound; timeout preserves ownership.'
}
