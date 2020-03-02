#!/usr/bin/env bash

set -o errexit

rm -rf venv

hash virtualenv 2>/dev/null || { echo >&2 "Virtualenv is not installed.  Aborting."; exit 1; }

virtualenv --python=python3 venv
source venv/bin/activate
pip install -r requirements.txt
