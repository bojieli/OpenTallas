# ROM read-path topology simulation

`via_rom_read.sp` is a deliberately small precharge/evaluate NOR-ROM experiment:

- a programmed cell has a drain connection to the bitline and discharges it;
- an unprogrammed cell omits that connection at the programming-via layer;
- a programmed cell behind a masked wordline remains inactive;
- simple inverters demonstrate sense polarity.

`make verify` runs ngspice and checks bitline levels, read margin, discharge delay,
polarity, and positive read energy. The MOS devices are generic level-1 models.
This settles only basic topology and test plumbing. It does **not** validate the
chosen open PDK's legal via options, array density, variation, sense offset, RC,
port width, power, or target-node speed; those require a PDK macro and extracted
corners/Monte Carlo, followed by silicon.
