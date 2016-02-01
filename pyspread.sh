#!/bin/bash

# Calls pyspread from top level folder of extracted tarball

export PYTHONPATH=$PYTHONPATH:./pyspread:~/prog/Phoenix
python3.5 ./pyspread/src/pyspread.py $@
