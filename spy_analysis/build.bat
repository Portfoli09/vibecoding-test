@echo off
chcp 65001 > nul
rem ==========================================================
rem  SPY 과거 데이터 분석기 실행파일(.exe) 빌드 스크립트
rem  결과물: dist\SpyAnalyzer.exe, dist\SpyAnalyzer.zip
rem ==========================================================
cd /d "%~dp0"

rem 1) 빌드 전용 가상환경 (필요한 패키지만 넣어야 exe 용량이 작아진다)
if not exist .venv (
    echo [1/4] 가상환경 생성 중...
    python -m venv .venv || goto :error
)
echo [1/4] 패키지 설치 중...
.venv\Scripts\python -m pip install -q -r requirements.txt pyinstaller pillow || goto :error

rem 2) 아이콘 생성
echo [2/4] 아이콘 생성 중...
.venv\Scripts\python make_icon.py || goto :error

rem 3) PyInstaller 빌드
rem    --onefile  : exe 파일 하나로 묶기
rem    --windowed : 실행 시 검은 콘솔 창을 띄우지 않기
rem    --add-data : 창 아이콘으로 쓸 app.ico를 exe 안에 포함
rem    --exclude-module tkinter : matplotlib의 Tk 백엔드는 쓰지 않으므로 제외 (용량 절약)
rem    ※ Pillow(PIL)는 matplotlib이 이미지를 저장할 때 쓰므로 제외하면 안 된다
echo [3/4] 실행파일 빌드 중... (3~5분 걸립니다)
.venv\Scripts\python -m PyInstaller --noconfirm --clean ^
    --onefile --windowed ^
    --name SpyAnalyzer ^
    --icon app.ico ^
    --add-data "app.ico;." ^
    --exclude-module tkinter ^
    spy_analysis_app.py || goto :error

rem 4) 배포용 zip 만들기: exe + 예제 데이터(있으면). exe와 같은 폴더의 CSV는 실행 시 자동으로 열린다
echo [4/4] 배포용 zip 생성 중...
if exist "..\SPY 과거 데이터.csv" copy /y "..\SPY 과거 데이터.csv" dist\ > nul
powershell -NoProfile -Command "$files = @('dist\SpyAnalyzer.exe') + @(Get-ChildItem dist -Filter *.csv | ForEach-Object FullName); Compress-Archive -Force -Path $files -DestinationPath dist\SpyAnalyzer.zip" || goto :error

echo.
echo 빌드 완료!
echo   실행파일 : %~dp0dist\SpyAnalyzer.exe
echo   배포용   : %~dp0dist\SpyAnalyzer.zip
exit /b 0

:error
echo.
echo 빌드 실패! 위의 오류 메시지를 확인하세요.
exit /b 1
