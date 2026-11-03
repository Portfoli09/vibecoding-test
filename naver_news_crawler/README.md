# 네이버 뉴스 크롤러

검색어로 네이버 뉴스 기사를 수집해 표로 보여 주고, 엑셀(.xlsx)·CSV로 저장하는 Windows 앱입니다.

## 사용자용 (exe 실행)

1. `NaverNewsCrawler.zip`의 압축을 풉니다.
2. `NaverNewsCrawler.exe`를 더블클릭합니다. (파이썬 설치 불필요)
3. 검색어 입력 → [🚀 크롤링 시작] → [📊 엑셀 저장]

> 처음 실행할 때 "Windows의 PC 보호" 창이 뜨면 **추가 정보 → 실행**을 누르세요.
> 코드 서명이 없는 exe에 Windows가 공통으로 띄우는 경고입니다.
> exe 하나에 모든 파일을 묶은 방식이라 첫 실행에 몇 초 걸릴 수 있습니다.

## 개발자용

### 소스로 실행

```bash
pip install -r requirements.txt
python naver_news_crawler.py
```

### exe 빌드

```bash
build.bat
```

빌드 전용 가상환경(`.venv`)을 만들어 필요한 패키지만 설치한 뒤 PyInstaller로 빌드합니다.

| 결과물 | 설명 |
| --- | --- |
| `dist\NaverNewsCrawler.exe` | 실행파일 (약 38MB) |
| `dist\NaverNewsCrawler.zip` | 배포용 압축 파일 |

### 파일 구성

| 파일 | 역할 |
| --- | --- |
| `naver_news_crawler.py` | 앱 본체 (크롤링 + PyQt6 GUI) |
| `make_icon.py` | 앱 아이콘 `app.ico` 생성 |
| `build.bat` | exe 빌드 + zip 생성 |
| `requirements.txt` | 실행에 필요한 패키지 |
