set -e
cd /
L=/srv/opentallas-scratch2/claude/s81-types-12/leaf
W=/srv/opentallas-scratch2/claude/s81-types-13/leaf
mkdir -p $W/in $W/mp13
cp $L/eo_band.py $L/mk3b.py $L/conn.py $L/prep.sh $W/
sed -i "s#claude/s81-types-12/leaf#claude/s81-types-13/leaf#g; s/s81t12-conn/s81t13-conn/" $W/prep.sh $W/mk3b.py
A=/srv/opentallas-scratch3/claude/kw26-wave-1106/runs/s81/kit-wave/s81/e9eda32d41c/items/ot_s81sl_leaf__t7/attempt_3
test ! -L $W/in
echo "ot_s81sl_leaf__t7|$A" | bash $W/prep.sh
cat $W/in/_done.txt | cut -c1-200
ls -la $W/in/ot_s81sl_leaf__t7 | cut -c30-
sed -n 35,50p $W/eo_band.py | cut -c1-180
