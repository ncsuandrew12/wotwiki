#!/bin/bash
# Copyright 2025 ncsuandrew12
# Modifications Copyright to their individual contributors
# Licensed under the MIT License
# SPDX-License-Identifier: MIT
set -ex

# 1184 was the highest ID number at the time this script was created.
# Before running, double-check by visiting https://www.theoryland.com/intvmain.php?i=1185
for i in $(seq 1 1184); do
    rm -f $i.html
    wget "https://www.theoryland.com/intvmain.php?i=$i" -O$i.html -t3
    sleep 3
done
