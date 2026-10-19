@echo off
call "%~dp0build_win_dynamic.bat" %*
exit /b %ERRORLEVEL%
