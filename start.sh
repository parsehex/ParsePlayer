#!/bin/bash

source venv/bin/activate
flask --app app run --host=0.0.0.0 --debug
