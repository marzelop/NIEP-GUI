#!/bin/bash

PIP_DEP=("pyside6" "networkx" "matplotlib")

if [ $# -gt 0 ]
then
	if [ $# -gt 1 ]
	then
		echo "Muitos argumentos."
		echo "Uso: ./install.sh [venv_path]"
		exit 1
	fi
	VENV="$1"
fi

if [ -n $VENV ]
then
	echo "Instalando no ambiente $VENV"
	source "$VENV"/bin/activate
fi

# Instala as dependências do pip
for DEP in ${PIP_DEP[@]}
do
	pip install $DEP
done
