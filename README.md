# NIEP GUI
## Installation
To install the application, you need to have Python installed on your computer. Then, you can run the install.sh script and it will install all Python dependencies and setup some files. You can specify a virtual enviroment for the installation, otherwise it will install all the dependencies globally. You can run the following command:
```sh
./install.sh [venv_path]
```
If the optional `venv_path` argument is empty, it will install globally. If the `venv_path` is not empty, but it does not have a `venv_path/bin/activate` file, the script will create the virtual enviroment and install all the dependencies in the enviroment.

## Running the Application
If all requirements are met, you should be able to run the application with the following command:
```sh
python app.py
```

If you have a virtual enviroment on the path `./venv/`, you could also run the application with:
```sh
./app.py
```

## Implementation
The application was built using Python 3.10.12 using the Qt framework with the [PySide6](https://pypi.org/project/PySide6/) library to create the GUI. Also, the [NetworkX](https://networkx.org/) library was used to create and manipulate network graphs.

## Icons Used:
[Cursor icons created by Freepik - Flaticon](https://www.flaticon.com/free-icons/cursor)\
[Stop icons created by Freepik - Flaticon](https://www.flaticon.com/free-icons/stop)\
[Straight icons created by Flipicon - Flaticon](https://www.flaticon.com/free-icons/straight)\
[Plus icons created by srip - Flaticon](https://www.flaticon.com/free-icons/plus)\
