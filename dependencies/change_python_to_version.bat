@echo off
echo "Changing Python Extension to use %1"
FTYPE Python.CompiledFile="%1\python.exe" "%%1" %%*
FTYPE Python.File="%1\python.exe" "%%1" %%*
FTYPE Python.NoConFile="%1\pythonw.exe" "%%1" %%*