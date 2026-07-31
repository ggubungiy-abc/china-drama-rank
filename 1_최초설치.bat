@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ============================================
echo   중국 드라마 순위 - 최초 설치
echo ============================================
echo.

rem ---- 파이썬 찾기 ----
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [오류] 파이썬을 찾을 수 없습니다.
    echo.
    echo   https://www.python.org/downloads/ 에서 파이썬을 설치한 뒤
    echo   다시 실행해 주세요.
    echo   설치할 때 "Add Python to PATH" 를 반드시 체크하세요.
    echo.
    pause
    exit /b 1
)

echo 사용할 파이썬: %PY%
%PY% --version
echo.

echo 필요한 라이브러리를 설치합니다...
echo.
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [오류] 설치에 실패했습니다.
    echo   인터넷 연결을 확인하고 다시 실행해 주세요.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   설치가 끝났습니다.
echo   이제 [2_실행.bat] 을 실행하세요.
echo ============================================
echo.
pause
