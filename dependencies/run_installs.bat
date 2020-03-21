@echo on
set python=%1
set sevenzip= %2
set mingw_compressed=%3
set setuptools=%4

setx PATH "%PATH%;%python%;%python%\Scripts;%python%\Lib;%python%\Bin;C:\Mingw\bin;C:\Mingw" /M
set PATH=%PATH%;%python%;%python%\Scripts;%python%\Lib;%python%\Bin;C:\Mingw\bin;C:\Mingw

python %setuptools% install
%sevenzip% x %mingw_compressed% -oC:\
