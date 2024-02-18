#!/bin/bash
# Clone our image onto SD cards on sda, sdb, etc.  Argument $1 is the
# host name prefix.  Cards are assigned drive numbers in the order
# they are plugged in, so plug them in in order a, b, c, d.
#
# FWIW, rpi-clone can't run in parallel because of a fixed mount point.
if [ "$#" -ne 1 ]; then
  echo "Usage: clone.sh hostname_base"
  exit 1
fi

sudo rpi-clone sda -U -L $1"a" -s $1"a"
sudo rpi-clone sdb -U -L $1"b" -s $1"b"
sudo rpi-clone sdc -U -L $1"c" -s $1"c"
sudo rpi-clone sdd -U -L $1"d" -s $1"d"
