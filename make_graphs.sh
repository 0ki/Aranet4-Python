#!/bin/bash
[ -z "$(which chart)" ] && echo "Need 'chart'. Download it from https://github.com/0ki/presentation-toolkit" && exit 1
set -e

[ ! -z "$1" ] && cd "$1" && cd -

./aranet.py -h -o "$1/history.csv"

cd "$1"

cat history.csv | cut -d \; -f 2,3 | chart plot temp.png semicolons grid show
cat history.csv | cut -d \; -f 2,4 | chart plot hum.png semicolons grid show
cat history.csv | cut -d \; -f 2,5 | chart plot press.png semicolons grid show
cat history.csv | cut -d \; -f 2,6 | chart plot co2.png semicolons grid show
