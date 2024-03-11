#!/bin/bash

# Generate the qrc_resources.py file required to run the application
pyside6-rcc -o resources_rc.py resources.qrc
