@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

echo ============================================
echo   수집한 데이터를 깃허브에 올리기
echo ============================================
echo.
echo   GitHub Actions 가 도우반에 차단당할 때
echo   대신 쓰는 방법입니다.
echo   내 PC에서 수집한 결과만 올립니다.
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

rem ---- 깃 확인 ----
git --version >nul 2>nul
if errorlevel 1 (
    echo [오류] git 을 찾을 수 없습니다.
    echo   https://git-scm.com/download/win 에서 설치한 뒤 다시 실행해 주세요.
    echo.
    pause
    exit /b 1
)

if not exist ".git" (
    echo [오류] 이 폴더는 아직 깃 저장소가 아닙니다.
    echo.
    echo   깃허브에서 저장소를 만든 뒤, 그 주소로 아래를 한 번 실행하세요.
    echo     git init
    echo     git remote add origin https://github.com/사용자명/저장소명.git
    echo     git branch -M main
    echo.
    pause
    exit /b 1
)

rem ---- 1단계: 수집 ----
echo [1/2] 순위를 수집합니다...
echo.
%PY% scripts\fetch_rankings.py
if errorlevel 1 (
    echo.
    echo [중단] 수집에 실패해서 올리지 않았습니다.
    echo   기존 데이터를 그대로 두는 편이 안전합니다.
    echo.
    pause
    exit /b 1
)
echo.

rem ---- 2단계: 커밋 및 푸시 ----
echo [2/2] 깃허브에 올립니다...
echo.

git add data

git diff --cached --quiet
if not errorlevel 1 (
    echo   바뀐 내용이 없어 올리지 않았습니다.
    echo   ^(도우반 순위가 지난번과 같으면 정상입니다^)
    echo.
    pause
    exit /b 0
)

git commit -m "데이터 갱신 (로컬 수집)"
if errorlevel 1 (
    echo.
    echo [오류] 커밋에 실패했습니다.
    echo   깃 사용자 정보가 없으면 아래를 한 번 실행하세요.
    echo     git config --global user.name "이름"
    echo     git config --global user.email "메일주소"
    echo.
    pause
    exit /b 1
)

git push
if errorlevel 1 (
    echo.
    echo [오류] 푸시에 실패했습니다.
    echo   로그인 정보나 저장소 주소를 확인해 주세요.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   완료되었습니다.
echo   1~2분 뒤 깃허브 페이지에 반영됩니다.
echo ============================================
echo.
pause
