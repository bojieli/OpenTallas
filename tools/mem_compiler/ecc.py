"""SECDED code and ROM signature (MISR/CRC) shared by the ROM compiler, the BIST RTL and the tests.

SECDED (extended Hamming), systematic, for any data width ``k``::

    codeword = { overall_parity, check[r-1:0], data[k-1:0] }   (data in the low bits)

Data bit ``j`` carries the ``j``-th positive integer that is not a power of two
(3, 5, 6, 7, 9, ...) as its Hamming position; check bit ``i`` is the parity of
the data bits whose position has bit ``i`` set; the overall parity bit makes
the whole codeword even.  ``rtl/dft/ot_rom_secded_dec.sv`` implements the same
position table, so the two are checked against each other bit for bit.

Signature: a CRC-32 (polynomial 0x04C11DB7, not reflected, initial value
0xFFFFFFFF, no final XOR) clocked over every stored bit of the ROM, word by
word in ascending address order, each word least-significant bit first.  It
is a multiple-input signature register in all but name: the ROM BIST folds a
whole word per clock with the same result.
"""
from __future__ import annotations

CRC_POLY = 0x04C11DB7
CRC_INIT = 0xFFFFFFFF


def check_bits(k: int) -> int:
    r = 1
    while (1 << r) < k + r + 1:
        r += 1
    return r


def positions(k: int) -> list[int]:
    out, p = [], 3
    while len(out) < k:
        if p & (p - 1):
            out.append(p)
        p += 1
    return out


def codeword_bits(k: int) -> int:
    return k + check_bits(k) + 1


def encode(data: int, k: int) -> int:
    r = check_bits(k)
    pos = positions(k)
    chk = 0
    for j in range(k):
        if (data >> j) & 1:
            chk ^= pos[j]
    chk &= (1 << r) - 1
    word = data | (chk << k)
    overall = bin(word).count("1") & 1
    return word | (overall << (k + r))


def decode(word: int, k: int) -> tuple[int, str]:
    """Returns (corrected data, status) with status in ok / corrected / uncorrectable."""
    r = check_bits(k)
    pos = positions(k)
    data = word & ((1 << k) - 1)
    stored = (word >> k) & ((1 << r) - 1)
    calc = 0
    for j in range(k):
        if (data >> j) & 1:
            calc ^= pos[j]
    syn = (calc ^ stored) & ((1 << r) - 1)
    overall = bin(word & ((1 << (k + r + 1)) - 1)).count("1") & 1
    if syn == 0 and overall == 0:
        return data, "ok"
    if overall == 1:
        if syn == 0 or not (syn & (syn - 1)):
            return data, "corrected"          # the error was in a check or parity bit
        if syn in pos:
            return data ^ (1 << pos.index(syn)), "corrected"
        return data, "uncorrectable"          # odd-weight error beyond one bit
    return data, "uncorrectable"


def crc_word(state: int, word: int, width: int) -> int:
    for i in range(width):
        fb = ((state >> 31) & 1) ^ ((word >> i) & 1)
        state = (state << 1) & 0xFFFFFFFF
        if fb:
            state ^= CRC_POLY
    return state


def signature(words: list[int], width: int) -> int:
    s = CRC_INIT
    for w in words:
        s = crc_word(s, w, width)
    return s


def crc_matrices(width: int) -> tuple[list[int], list[int]]:
    """Per output bit i: next[i] = parity(state & a[i]) ^ parity(word & b[i]) for one ``width``-bit word."""
    a = [0] * 32
    b = [0] * 32
    for j in range(32):  # response to each state bit, word = 0 (the map is linear with CRC_INIT folded out)
        s = _crc_word_linear(1 << j, 0, width)
        for i in range(32):
            if (s >> i) & 1:
                a[i] |= 1 << j
    for j in range(width):
        s = _crc_word_linear(0, 1 << j, width)
        for i in range(32):
            if (s >> i) & 1:
                b[i] |= 1 << j
    return a, b


def _crc_word_linear(state: int, word: int, width: int) -> int:
    return crc_word(state, word, width)


def signature_fast(words: list[int], width: int) -> int:
    a, b = crc_matrices(width)
    s = CRC_INIT
    for w in words:
        n = 0
        for i in range(32):
            if (bin(s & a[i]).count("1") ^ bin(w & b[i]).count("1")) & 1:
                n |= 1 << i
        s = n
    return s
