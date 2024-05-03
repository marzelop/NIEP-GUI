# Installation
To install the application, you need to have Python installed on your computer. Then, you can run the install.sh script and it will install all Python dependencies and setup some files. You can specify a virtual enviroment for the installation, otherwise it will install all the dependencies globally. You can run the following command:
```sh
./install.sh [venv_path]
```
If the optional `venv_path` argument is empty, it will install globally. If the `venv_path` is not empty, but it does not have a `venv_path/bin/activate` file, the script will create the virtual enviroment and install all the dependencies in the enviroment.
Then, you can run the following command to use the virtual enviroment:
```sh
source <venv_path>/bin/activate
```
When you are in a enviroment with all the dependencies installed, you can run the application with the following command:
```sh
python3 app.py
```
or
```sh
./app.py
```
if you have a virtual enviroment at `./venv`.
