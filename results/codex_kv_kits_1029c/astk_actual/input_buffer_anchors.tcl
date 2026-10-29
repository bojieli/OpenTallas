# Move only source-identified data input buffers beside their own fixed face FFs.
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach i [$b getInsts] {$i setPlacementStatus FIRM}
set c [$b findInst {input2001}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(69.120000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input2000}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(67.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1999}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.356000 * $u)}] [expr {round(66.420000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1998}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(66.420000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1997}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(65.610000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1996}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.734000 * $u)}] [expr {round(65.070000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1995}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.382000 * $u)}] [expr {round(64.530000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1994}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(63.720000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1993}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.220000 * $u)}] [expr {round(62.910000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1992}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(62.370000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1990}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(61.830000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1989}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.302000 * $u)}] [expr {round(60.750000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1988}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(60.480000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1987}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.112000 * $u)}] [expr {round(59.670000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1986}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(58.860000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1985}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(58.320000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1984}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(57.240000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1983}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(56.970000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1982}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(56.160000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1981}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(55.890000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1979}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(55.350000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1978}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(54.540000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1977}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.842000 * $u)}] [expr {round(54.000000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1976}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.058000 * $u)}] [expr {round(53.190000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1975}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.896000 * $u)}] [expr {round(52.920000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1974}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(51.840000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1973}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.356000 * $u)}] [expr {round(51.030000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1972}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(50.490000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1971}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.626000 * $u)}] [expr {round(49.950000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1970}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.220000 * $u)}] [expr {round(49.140000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1968}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.248000 * $u)}] [expr {round(48.060000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1967}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(47.790000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1966}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.166000 * $u)}] [expr {round(47.250000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1965}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(46.440000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1964}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.518000 * $u)}] [expr {round(45.900000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1963}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.518000 * $u)}] [expr {round(45.360000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1962}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.978000 * $u)}] [expr {round(44.550000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1961}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.356000 * $u)}] [expr {round(44.010000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1960}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(43.200000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1959}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(42.390000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1957}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(41.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1956}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.356000 * $u)}] [expr {round(41.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1955}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(40.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1954}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(39.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1953}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(39.150000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1920}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.058000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1919}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.734000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1918}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.328000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1917}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.194000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1916}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.302000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1915}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.328000 * $u)}] [expr {round(174.690000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1914}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.220000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1912}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.058000 * $u)}] [expr {round(174.690000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1911}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.816000 * $u)}] [expr {round(172.800000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1910}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.328000 * $u)}] [expr {round(171.720000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1909}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(172.530000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1908}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(170.910000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1907}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.140000 * $u)}] [expr {round(170.910000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1906}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.112000 * $u)}] [expr {round(170.100000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1905}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.842000 * $u)}] [expr {round(169.290000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1904}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(168.750000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1903}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.220000 * $u)}] [expr {round(168.210000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1901}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(167.670000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1900}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.896000 * $u)}] [expr {round(166.860000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1899}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.842000 * $u)}] [expr {round(166.320000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1898}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(165.780000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1897}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(164.700000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1896}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(163.620000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1895}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.194000 * $u)}] [expr {round(163.080000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1894}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.842000 * $u)}] [expr {round(162.810000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1893}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(162.270000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1892}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(161.730000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1890}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(161.460000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1889}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.220000 * $u)}] [expr {round(160.110000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1888}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(159.570000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1887}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.140000 * $u)}] [expr {round(159.030000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1886}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(157.950000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1885}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.518000 * $u)}] [expr {round(157.410000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1884}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.950000 * $u)}] [expr {round(156.870000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1883}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(156.060000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1882}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(155.520000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1881}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.708000 * $u)}] [expr {round(154.980000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1879}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.626000 * $u)}] [expr {round(154.440000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1878}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(153.900000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1877}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(153.090000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1876}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.978000 * $u)}] [expr {round(152.010000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1875}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.382000 * $u)}] [expr {round(151.200000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1874}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(150.930000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1873}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(150.930000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1872}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.464000 * $u)}] [expr {round(149.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1871}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(149.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1870}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.734000 * $u)}] [expr {round(148.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1868}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(147.150000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1867}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.328000 * $u)}] [expr {round(147.150000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1866}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(146.340000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1865}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.842000 * $u)}] [expr {round(145.530000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1864}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(144.990000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1863}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(144.450000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1862}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(143.910000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1861}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(143.370000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1860}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.734000 * $u)}] [expr {round(142.290000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1859}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(141.750000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1857}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(140.940000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1856}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.978000 * $u)}] [expr {round(140.400000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1855}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(139.590000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1854}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(139.050000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1853}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(138.780000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1852}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(137.970000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1851}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.950000 * $u)}] [expr {round(137.160000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1850}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.302000 * $u)}] [expr {round(136.350000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1849}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(135.810000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1848}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(135.000000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1845}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.302000 * $u)}] [expr {round(134.190000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1844}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.518000 * $u)}] [expr {round(133.380000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1843}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.950000 * $u)}] [expr {round(133.380000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1842}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(132.570000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1841}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.708000 * $u)}] [expr {round(131.760000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1840}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(130.950000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1839}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.734000 * $u)}] [expr {round(130.410000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1838}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.896000 * $u)}] [expr {round(129.870000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1837}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.708000 * $u)}] [expr {round(129.060000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1836}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.058000 * $u)}] [expr {round(128.520000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1834}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.356000 * $u)}] [expr {round(127.710000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1833}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(127.170000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1832}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(126.630000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1831}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(125.820000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1830}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(125.280000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1829}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(124.470000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1828}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.978000 * $u)}] [expr {round(123.930000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1827}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(123.120000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1826}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(122.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1825}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(122.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1823}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.950000 * $u)}] [expr {round(121.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1822}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(120.690000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1821}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(119.880000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1820}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(119.070000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1819}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.328000 * $u)}] [expr {round(119.070000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1818}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.356000 * $u)}] [expr {round(117.990000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1817}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.626000 * $u)}] [expr {round(117.180000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1816}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(116.640000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1815}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(115.830000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1814}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.464000 * $u)}] [expr {round(115.290000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1812}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.626000 * $u)}] [expr {round(114.480000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1811}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.166000 * $u)}] [expr {round(113.940000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1810}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(113.400000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1809}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(112.590000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1808}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(112.050000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1807}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(111.510000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1806}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(110.700000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1805}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(109.890000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1804}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(109.350000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1803}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(108.540000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1801}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(108.000000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1800}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(107.190000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1799}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(106.650000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1798}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(106.110000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1797}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(105.300000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1796}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(104.760000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1795}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(103.950000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1794}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(103.410000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1793}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.788000 * $u)}] [expr {round(102.600000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1792}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(102.060000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1790}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(101.250000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1789}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(100.710000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1788}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(100.170000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1787}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(99.360000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1786}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(98.820000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1785}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.058000 * $u)}] [expr {round(98.280000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1784}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(97.470000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1783}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(96.660000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1782}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(96.120000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1781}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(95.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1779}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(94.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1778}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(93.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1777}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(93.420000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1776}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.194000 * $u)}] [expr {round(92.880000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1775}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(92.340000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1774}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(91.530000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1773}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(90.720000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1772}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.842000 * $u)}] [expr {round(90.180000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1771}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.328000 * $u)}] [expr {round(89.370000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1770}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(88.830000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1768}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(88.020000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1767}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(87.480000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1766}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.140000 * $u)}] [expr {round(86.940000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1765}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(86.400000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1764}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.708000 * $u)}] [expr {round(85.590000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1763}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(84.780000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1762}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.870000 * $u)}] [expr {round(84.240000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1761}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(83.430000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1760}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.762000 * $u)}] [expr {round(82.890000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1759}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.626000 * $u)}] [expr {round(82.080000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1757}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(81.810000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1756}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(81.000000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1755}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(80.190000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1754}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(79.650000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1753}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(78.840000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1752}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(78.300000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1751}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.896000 * $u)}] [expr {round(77.760000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1750}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.924000 * $u)}] [expr {round(76.950000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1749}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(76.140000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1748}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(75.600000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1746}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.680000 * $u)}] [expr {round(74.790000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1745}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(74.790000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1744}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(73.980000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1743}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.274000 * $u)}] [expr {round(73.170000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1742}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(72.360000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1741}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(71.550000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1740}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(183.870000 * $u)}] [expr {round(71.010000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1739}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(185.004000 * $u)}] [expr {round(70.200000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1738}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.572000 * $u)}] [expr {round(69.660000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1737}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(184.410000 * $u)}] [expr {round(68.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1128}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(5.724000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1127}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(29.700000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1126}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(29.376000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1125}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(30.024000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1124}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.512000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1123}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.836000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1122}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.512000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1121}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.674000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1120}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.782000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1119}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(26.352000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1118}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(24.192000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1117}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(7.938000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1116}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(27.810000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1115}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(26.676000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1114}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.134000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1113}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(26.622000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1112}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(26.298000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1111}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(26.082000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1110}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(28.998000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1109}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(25.650000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1108}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(25.380000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1107}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(25.920000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1106}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(7.020000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1105}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(25.002000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1104}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(25.326000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1103}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(24.894000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1102}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(25.596000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1101}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(23.922000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1100}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(23.220000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1099}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(23.220000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1098}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(23.274000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1097}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(22.950000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1096}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(22.302000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1095}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(6.048000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1094}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(22.410000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1093}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(22.140000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1092}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(22.032000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1091}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(21.222000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1090}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(20.736000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1089}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(21.222000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1088}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(21.492000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1087}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(21.762000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1086}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(21.762000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1085}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(20.574000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1084}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(7.776000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1083}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(20.196000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1082}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(20.088000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1081}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(20.844000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1080}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(18.792000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1079}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(19.494000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1078}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(18.900000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1077}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(19.170000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1076}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(19.494000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1075}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(18.576000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1074}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(19.818000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1073}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(5.832000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1072}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(18.900000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1071}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(19.764000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1070}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(16.956000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1069}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(16.416000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1068}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(16.632000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1067}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(16.416000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1066}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(15.984000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1065}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(15.930000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1064}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(15.066000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1063}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(15.714000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1062}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(6.534000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1061}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.796000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1060}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.202000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1059}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.472000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1058}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(13.554000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1057}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.202000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1056}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.688000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1055}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.310000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1054}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(14.040000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1053}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.420000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1052}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(13.824000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1051}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(5.508000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1050}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.852000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1049}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.204000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1048}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(10.260000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1047}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.474000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1046}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(11.610000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1045}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.474000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1044}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(10.908000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1043}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.204000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1042}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(12.096000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1041}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(10.260000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1040}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(4.752000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1039}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(9.450000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1038}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(10.530000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1037}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(9.882000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1036}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(9.396000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1035}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(7.938000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1034}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(9.234000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1033}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(8.100000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1032}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(41.040000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1031}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(38.988000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1030}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(37.422000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1029}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(38.448000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1028}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(38.016000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1027}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(39.042000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1026}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(37.962000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1025}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(37.152000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1024}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(10.044000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1023}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(38.394000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1022}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(39.852000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1021}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(36.396000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1020}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(35.910000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1019}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(35.964000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1018}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(35.046000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1017}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(36.450000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1016}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(35.640000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1015}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(34.236000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1014}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(34.830000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1013}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(8.802000 * $u)}] [expr {round(174.960000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1012}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(34.452000 * $u)}] [expr {round(175.230000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1011}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(33.750000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1010}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.130000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1009}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(34.344000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1008}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.832000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1007}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(33.966000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1006}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.886000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1005}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.562000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1004}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.562000 * $u)}] [expr {round(175.500000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1003}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.292000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1002}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(8.262000 * $u)}] [expr {round(175.770000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1001}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(31.482000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input1000}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(30.456000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input999}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(32.616000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input998}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(31.050000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input997}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(29.808000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input996}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(30.942000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input995}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(30.672000 * $u)}] [expr {round(176.040000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input994}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(30.780000 * $u)}] [expr {round(176.580000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input993}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(30.294000 * $u)}] [expr {round(176.310000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input992}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(29.376000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input991}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(4.482000 * $u)}] [expr {round(176.850000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input990}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(4.482000 * $u)}] [expr {round(90.990000 * $u)}]
$c setPlacementStatus FIRM
set c [$b findInst {input989}]
if {$c eq "NULL"} {error "missing exact input buffer"}
$c setPlacementStatus PLACED
$c setLocation [expr {round(4.428000 * $u)}] [expr {round(90.720000 * $u)}]
$c setPlacementStatus FIRM
