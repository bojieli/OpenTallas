"""Default-off companion-runtime DSpark commit/rollback over real KV word banks.

No model is loaded and no prediction is invented. Caller feeds draft/target
identities and the existing RTL accept leaf's actual result. All owned rank/layer
write drains precede rollback; token/frame leases survive commit until every
owner reports last-consumer terminal AND reverse. A backend must provide these
actual receipts; absence holds the transaction, never synthesizes readiness.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class MemoryOwner:
    rank: int
    layer: int
    words: np.ndarray
    layout: object
    tmax: int = 8192

    @property
    def key(self):
        return self.rank, self.layer

    def addresses(self, position):
        # Existing companion single-layer KV image: packed K columns, V rows.
        return np.array([fn(0, h, position, d) for fn in (self.layout.k_elem, self.layout.v_elem)
                         for h in range(self.layout.KV) for d in range(self.layout.HD)], dtype=np.int64)


class Transaction:
    def __init__(self, owners, *, enabled=False, layers=36):
        self.enabled = enabled
        self.owners = tuple(owners)
        if not self.owners or len({o.key for o in self.owners}) != len(self.owners):
            raise ValueError('duplicate or missing KV owner')
        if {o.rank for o in self.owners} != {0, 1, 2, 3}:
            raise ValueError('TP4 owner cohort required')
        if {o.key for o in self.owners} != {(r, l) for r in range(4) for l in range(layers)}:
            raise ValueError('every layer needs every TP rank')
        for o in self.owners:
            if o.words.dtype != np.uint32 or o.words.ndim != 1:
                raise ValueError('rollback must preserve exact uint32 memory words')
        if any(np.shares_memory(a.words, b.words) for i, a in enumerate(self.owners) for b in self.owners[i+1:]):
            raise ValueError('distinct rank/layer banks must not alias')
        self.lease = None
        self.used_leases = set()

    def begin(self, lease, start, pending, drafts=None):
        if not self.enabled:
            raise ValueError('DSpark loop is default-off')
        if self.lease is not None or lease in self.used_leases:
            raise ValueError('owned or reused transaction lease')
        tokens = (pending, *(drafts if drafts is not None else (0, 0, 0)))
        if len(tokens) != 4 or any(not 0 <= t < 151936 for t in tokens):
            raise ValueError('B4 Qwen token geometry required')
        if start < 0:
            raise ValueError('negative position')
        snapshots = {}
        for owner in self.owners:
            rows = []
            for j in range(4):
                if start + j >= owner.tmax:
                    raise ValueError('verify block exceeds KV window')
                addresses = owner.addresses(start + j)
                if np.any(addresses < 0) or np.any(addresses >= owner.words.size):
                    raise ValueError('KV address outside owned bank')
                rows.append((addresses, owner.words[addresses].copy()))
            snapshots[owner.key] = rows
        self.lease, self.start, self.tokens = lease, start, tokens
        self.drafts_ready = drafts is not None
        self.targets = {}
        self.snapshots, self.drained, self.terminals = snapshots, set(), set()
        self.committed = None
        self.used_leases.add(lease)

    def _owned(self, lease, key=None):
        if self.lease is None or lease != self.lease:
            raise ValueError('transaction identity mismatch')
        if key is not None and key not in self.snapshots:
            raise ValueError('unknown rank/layer owner')

    def drafted(self, lease, drafts):
        self._owned(lease)
        drafts = tuple(drafts)
        if self.drafts_ready or self.targets or len(drafts) != 3 or any(not 0 <= t < 151936 for t in drafts):
            raise ValueError('invalid or duplicate drafter result')
        self.tokens = (self.tokens[0], *drafts)
        self.drafts_ready = True

    def target(self, lease, rank, slot, token):
        self._owned(lease)
        if not self.drafts_ready or self.committed is not None or not 0 <= rank < 4 or not 0 <= slot < 4 or (rank, slot) in self.targets or not 0 <= token < 151936:
            raise ValueError('invalid/duplicate/late target')
        self.targets[rank, slot] = token

    def write_drain(self, lease, key):
        self._owned(lease, key)
        self.drained.add(key)

    def commit(self, lease, *, accepted, n_emit, bonus):
        """Consume the actual accept-leaf output; restore rejected rows bitwise."""
        self._owned(lease)
        if self.committed is not None or set(self.targets) != {(r, j) for r in range(4) for j in range(4)}:
            raise ValueError('accept requires one complete fresh verify block')
        if self.drained != set(self.snapshots):
            raise ValueError('KV writes still outstanding; rollback is held')
        targets = tuple(self.targets[0, j] for j in range(4))
        if any(self.targets[r, j] != targets[j] for r in range(4) for j in range(4)):
            raise ValueError('TP4 verify argmax replicas disagree')
        exact = 0
        while exact < 3 and self.tokens[exact + 1] == targets[exact]:
            exact += 1
        if (accepted, n_emit, bonus) != (exact, exact + 1, targets[exact]):
            raise ValueError('actual accept output disagrees with greedy prefix')
        for owner in self.owners:
            for addresses, before in self.snapshots[owner.key][n_emit:]:
                owner.words[addresses] = before
        self.committed = {'emitted': tuple(targets[j] for j in range(n_emit)),
                          'next_position': self.start + n_emit, 'pending': bonus,
                          'retained_slots': n_emit}
        return dict(self.committed)

    def terminal(self, lease, key, *, consumer_done, reverse_done):
        self._owned(lease, key)
        if self.committed is None or not consumer_done or not reverse_done:
            raise ValueError('real last-consumer terminal and reverse required')
        self.terminals.add(key)

    def release(self, lease):
        self._owned(lease)
        if self.committed is None or self.terminals != set(self.snapshots):
            raise ValueError('frame/token lease retained until every real terminal')
        result = dict(self.committed)
        self.lease = None
        self.snapshots = {}
        self.targets = {}
        self.tokens = ()
        self.committed = None
        return result


def serial_step(transaction, backend, lease, start, pending):
    """One loop iteration using actual owner's engine and terminal interfaces.

    The backend implements draft/verify/accept_leaf/emit/terminal_receipts over
    its existing serial engine. It returns real rank/layer drain receipts from
    verify, and terminal_receipts only after emit's last consumer plus reverse.
    This function never creates predictions or substitutes an inference path.
    Missing interfaces raise while retaining the owned transaction, so a caller
    cannot recycle a frame after a partial/failed step.
    """
    if not transaction.enabled:
        raise ValueError('DSpark loop is default-off')
    if transaction.lease is not None:
        raise ValueError('previous frame still owned')
    transaction.begin(lease, start, pending)
    drafted = backend.draft(lease, start, pending)
    transaction._owned(drafted['lease'])
    transaction.drafted(drafted['lease'], drafted['tokens'])
    verified = backend.verify(lease, start, transaction.tokens)
    transaction._owned(verified['lease'])
    for rank, tokens in verified['targets'].items():
        for slot, token in enumerate(tokens):
            transaction.target(lease, rank, slot, token)
    for owner in verified['write_drained']:
        transaction.write_drain(lease, owner)
    leaf = backend.accept_leaf(lease, transaction.tokens,
                               tuple(transaction.targets[0, j] for j in range(4)))
    transaction._owned(leaf['lease'])
    committed = transaction.commit(leaf['lease'], accepted=leaf['accepted'],
                                   n_emit=leaf['n_emit'], bonus=leaf['bonus'])
    backend.emit(lease, committed['emitted'])
    for receipt_lease, owner, consumer_done, reverse_done in backend.terminal_receipts(lease):
        transaction.terminal(receipt_lease, owner, consumer_done=consumer_done, reverse_done=reverse_done)
    return transaction.release(lease)
