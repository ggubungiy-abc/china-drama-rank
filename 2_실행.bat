@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PORT=8000"

echo ============================================
echo   중국 드라마 순위 - 실행
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
    echo   먼저 [1_최초설치.bat] 을 실행해 주세요.
    echo.
    pause
    exit /b 1
)

rem ---- 1단계: 데이터 수집 ----
echo [1/2] 도우반에서 순위를 수집합니다. 1~2분 걸립니다...
echo.
%PY% scripts\fetch_rankings.py
set "FETCH_RESULT=%errorlevel%"
echo.

if not "%FETCH_RESULT%"=="0" (
    echo --------------------------------------------
    echo   수집에 실패했습니다.
    echo.
    if exist "data\rankings.json" (
        echo   직전에 받아둔 데이터로 사이트를 띄웁니다.
    ) else (
        echo   보여줄 데이터가 아직 없습니다.
        echo   위 로그에 "HTTP 403" 이 보이면 도우반이 접속을
        echo   막은 것이니, 잠시 뒤 다시 시도해 보세요.
        echo.
        pause
        exit /b 1
    )
    echo --------------------------------------------
    echo.
)

rem ---- 2단계: 로컬 서버 ----
echo [2/2] 로컬 서버를 켭니다.
echo.
echo   주소: http://localhost:%PORT%
echo   종료: 이 창에서 Ctrl+C 를 누르거나 창을 닫으세요.
echo.

start "" http://localhost:%PORT%
%PY% -m http.server %PORT%

endlocal
