chcp 65001
@echo off
cls

:RunScript
call :SetMayaVersion
call :MakeDir
call :Cmake
pause
goto :EOF

:SetMayaVersion
set "AutodeskDirPath=C:/Program Files/Autodesk"
set /p "MayaVersion=Input Maya Version (Int):"
goto :EOF

:MakeDir
cd %~dp0
set "BuildDir=%~dp0Build\%MayaVersion%"
if not exist %BuildDir% (
    mkdir %BuildDir%
)
goto :EOF

:Cmake
pushd %BuildDir%
echo %BuildDir%
cmake ../.. -G "Visual Studio 17 2022"
goto :EOF

:EOF