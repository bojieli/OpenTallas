"""Serial SU observation ages derived from the native multirate RTL.

This prices a declared return contract. It does not prove the die lanes, PLL
phase, reset epoch, or physical closure which implement that contract.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class NativeTiming:
    read_return: int
    write_return: int

    def __post_init__(self):
        if (type(self.read_return) is not int or type(self.write_return) is not int
                or not 10 <= self.read_return or not 7 <= self.write_return <= self.read_return):
            raise ValueError("native multirate contract requires integer RR>=10 and 7<=WR<=RR")

    @staticmethod
    def serial_return(stream_return):
        # ot_hbm_su_multirate_bridge / su_multirate_compile.srd
        return (3 * stream_return + 18 + 3) // 4

    @property
    def fill_commit(self):
        # pgslice fd/fr publication followed by pinned-bank input and write.
        return self.serial_return(self.read_return) + 3

    @property
    def drain_done(self):
        # pgslice drain group selection presents the bridge write at E+4.
        return 4 + self.serial_return(self.write_return)

    def as_dict(self):
        return dict(asdict(self), fill_commit=self.fill_commit,
                    drain_done=self.drain_done, multirate=True,
                    topology_qualified=False,
                    source="ot_hbm_su_static_pgslice + ot_hbm_su_multirate_bridge")
