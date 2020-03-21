@echo on
set python=%1
set sqlalchemy=%2
set logbook=%3

set PATH=%PATH%;%python%;%python%\Scripts;%python%\Lib;%python%\Bin;C:\Mingw\bin;C:\Mingw

easy_install pip

pip install sqlalchemy==0.9.8
pip install logbook==0.7.0