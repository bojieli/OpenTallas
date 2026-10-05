def ha5_native_moe(self, xa, xb, ne=None, ke=None):
    (k, lib, m, s, g) = (self.k, self.lib, self.m, self.s, self.g)
    ne = ne or m.n_exp
    ke = ke or m.k_exp
    self.tc_stage([xa, xb])
    self.tc_words(2)
    self.tc_mma('gate', ne, 2)
    sc = self.k.op('FSQRT', lib.softplus(self.lds(S_TCR, ne)))
    b = lib.add(sc, self.ldd('gbias', 0, ne))
    v12 = lib.mask(lambda l: l < ne)
    bm = lib.select_m(v12, b, lib.u(NEG_BIG))
    cnt = lib.u(0)
    for j in range(ne):
        bj = lib.bcast(bm, j)
        gt = lib.op('FCMPGT', bj, bm)
        eq = lib.op('XOR', lib.op('OR', gt, lib.op('FCMPGT', bm, bj)), lib.u(1))
        tie = lib.op('AND', eq, lib.lanes(lambda l, j=j: 1 if l > j else 0))
        cnt = lib.op('IADD', cnt, lib.op('OR', gt, tie))
    sel = lib.op('AND', lib.op('ULT', cnt, lib.u(ke)), lib.lanes(lambda l: 1 if l < ne else 0))
    smask = lib.op('ISUB', lib.u(0), sel)
    excl = lib.op('ISUB', self.scan(sel, 16), sel)
    sm_ = lib.op('AND', sc, smask)
    tot = lib.bcast(sm_, 0)
    for i in range(1, ne):
        tot = lib.add(tot, lib.bcast(sm_, i))
    den = lib.add(tot, lib.c(1e-20))
    wgt = lib.mul(lib.div(sc, den), lib.c(m.route_scale))
    ad = lib.select_m(smask, lib.op('IADD', lib.op('SHL', excl, lib.u(2)), lib.u(S_MISC + 128)), lib.u(S_DUMMY))
    k.stsx(lib.lane(), ad, 0, 16)
    k.stsx(wgt, ad, 64, 16)
    ids = self.lds(S_MISC + 128, ke)
    wts = self.lds(S_MISC + 192, ke)
    if self.p.dbg and self.d == 0:
        self.dbg([b, ids], 7, [ne, ke])
    self.bd_x([xa, xb], 160)
    lim = lib.c(m.limit)
    nlim = lib.c(-m.limit)
    for e in (ke, *range(ke)):
        if e < ke:
            k.ufromv(9, ids, e)
            k.umuli(9, 9, self.p.ex_stride)
            self.bd_mma(f'rexp{s}', 32, 160, fp4=True, uoff=9)
        else:
            self.bd_mma(f'shexp{s}', 32, 160)
        v = lib.bf(self.lds(S_TCR, 32))
        u = lib.op('FMIN', lib.op('FMAX', lib.shfl(v, lib.lanes(lambda l: (l + 16) % NL)), nlim), lim)
        gg = lib.op('FMIN', v, lim)
        a = lib.mul(lib.silu(gg), u)
        if e < ke:
            a = lib.mul(lib.bcast(wts, e), a)
        self.stg(a, self.A('EA') + 4 * (64 * e + 16 * g), 16)
    self.allreduce('EA', 64 * (ke + 1), lambda d, i: i % 64 // 32 == d)
    y = None
    for e in (ke, *range(ke)):
        a = lib.bf(self.ldg(self.A('EA') + 256 * e, 64))
        self.bd_x([a], 64)
        if e < ke:
            k.ufromv(9, ids, e)
            k.umuli(9, 9, self.p.ex_stride)
            self.bd_mma(f'rexp{s}', 40, 64, fp4=True, uoff=9, off=self.p.ex_w2off)
        else:
            self.bd_mma(f'shexp{s}', 40, 64, off=self.p.sh_w2off)
        ye = lib.bf(self.lds(S_TCR, 40))
        if e == ke:
            shared_y = ye
        elif e == 0:
            y = ye
        else:
            y = lib.add(y, ye)
    y = lib.add(y, shared_y)
    return self.y_exchange(lib.bf(y))
