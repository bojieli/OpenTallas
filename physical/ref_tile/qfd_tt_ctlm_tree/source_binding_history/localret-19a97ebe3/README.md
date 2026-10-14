# Unqualified native local-return candidate 19a97ebe3

Gate public-root size passes but candidate is UNQUALIFIED. Actual final4_1_cts.odb,4_cts.sdc WC=TT/BC=FF native ENA setup−102.90ps/hold+517.92ps. TT gate diagnostic−39.57ps is not the related-corner proof. The native ENA data path is short (CQ53.77,INV14.90,wire0.04ps) but its launch clock853.38ps is far later than nativeICG CLK154.08ps. No exception or invented phase was used. Plain-port overall worst output path in domains.log is diagnostic only; flow uses actual io_ref boundary replay.

Final TT primary628clockpins=626FF+2programRAM,842.54..866.17ps,mean855.13. Native gated9817clockpins=9813FF+4tagRAM,722.91..755.82ps,mean737.26. Total10439FF+6RAM remains unchanged. OnlyTWO private stationFF survive synthesis and move to gated domain, not all95logical bits. The earlier logical-width95-bit idleclock reduction estimate is not a physical result. Actual two-pin idle reduction estimate is2*(30814−154)=61320edges; watts/capacitance/leakage unmeasured.

Initial measured native subtree719.004882ps came from unbufferedICG CLK1996.174561ps. After primary buffering, native subtree is755.820862−154.079544=601.741318ps, so the frozen static insertion estimate overstates by117.26ps. Primary balance prints syntheticICG target using stale insertion; final real two-domain spread143.26ps exposes the mismatch. The successor must update the ICG leaf from actual current input/sink propagation during every standard primary spine balance iteration, then prove final WC/BC native setup/hold and both domains.

Source/spec/job files frozen during gate. Public CLOSED head module SHA4ed49b6a30b942c2231c5a54f59c12fdfbb21d75a6568d0b28a02569c04d8737 unchanged. No leaf submission or parent qualification.
