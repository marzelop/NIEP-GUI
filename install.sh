#!/bin/bash

PIP_DEP=("pyside6" "networkx" "matplotlib")

if [ $# -gt 0 ]
then
	if [ $# -gt 1 ]
	then
		echo "Too many arguments."
		echo "Usage: ./install.sh [venv_path]"
		exit 1
	fi
	VENV="$1"
fi

if [ ! -z $VENV ]
then
	echo "Installing in the enviroment $VENV"
	if [ ! -f "$VENV/bin/activate" ]
	then
		echo "Creating virtual enviroment $VENV"
		python3 -m venv $VENV
		if [ $? -ne 0 ]
		then
			echo "Error on creating virtual enviroment. Aborting."
			exit 2
		fi
	fi
	source "$VENV"/bin/activate
fi

# Instala as dependências do pip
for DEP in ${PIP_DEP[@]}
do
	pip3 install $DEP
done

echo "Generating qrc_resources.py"
./gen_resources.sh
echo "Finished."
