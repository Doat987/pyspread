#!/bin/bash

# Calls pyspread from top level folder of extracted tarball

export PYTHONPATH=$PYTHONPATH:~/prog/Phoenix:./pyspread
python3.5 ./pyspread/src/pyspread.py $@
