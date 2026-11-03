# PRD: 개발자 프로필 웹사이트 (DemoPort)

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 (초안) |
| 작성일 | 2026-11-03 |
| 작성자 | mang901 (wjdaudgh90@gmail.com) |
| 상태 | Draft |

---

## 1. 개요

### 1.1 목적
개발자 본인의 기술 역량, 프로젝트 경험, 연락처를 한곳에 정리해 보여주는 **개인 포트폴리오/프로필 웹사이트**를 구축한다. 채용 담당자, 협업 제안자, 클라이언트가 짧은 시간 안에 개발자의 강점을 파악하고 바로 연락할 수 있도록 하는 것이 핵심 목표다.

### 1.2 주력 기술 분야
- **Python** — 백엔드, 자동화 스크립트, 데이터 처리
- **HTML5** (CSS3 / JavaScript 포함) — 반응형 웹 프론트엔드
- **iOS 앱 개발** — Swift / SwiftUI / UIKit 기반 네이티브 앱

### 1.3 연락처
- 이메일: **wjdaudgh90@gmail.com**

---

## 2. 목표 및 성공 지표

### 2.1 목표
1. 방문자가 **10초 안에** "누구이며 무엇을 잘하는지" 파악할 수 있다.
2. 세 가지 주력 분야(Python, HTML5, iOS)별 대표 프로젝트를 명확히 보여준다.
3. 방문자가 클릭 한 번으로 이메일 연락을 시작할 수 있다.
4. 사이트 자체가 HTML5 역량을 증명하는 결과물이 된다(빠르고, 접근성 좋고, 반응형).

### 2.2 성공 지표 (KPI)
| 지표 | 목표치 |
|---|---|
| Lighthouse Performance | 90점 이상 |
| Lighthouse Accessibility | 95점 이상 |
| 첫 화면 로딩(LCP) | 2.5초 이하 |
| 모바일 레이아웃 깨짐 | 0건 (320px ~ 1920px) |
| 연락하기(메일) 클릭 전환 | 측정 후 기준치 설정 |

---

## 3. 대상 사용자

| 페르소나 | 니즈 | 주로 보는 섹션 |
|---|---|---|
| 채용 담당자 / 리크루터 | 기술 스택, 경력 요약, 이력서 다운로드 | Hero, Skills, Experience |
| 기술 면접관 / 개발 리드 | 실제 코드, 프로젝트 설계 수준 | Projects, GitHub 링크 |
| 외주 클라이언트 | 결과물 예시, 앱스토어 링크, 연락 방법 | Projects, Contact |
| 동료 개발자 | 블로그/기술 글, 오픈소스 활동 | Projects, (추후) Blog |

---

## 4. 기능 요구사항

우선순위: **P0** = MVP 필수, **P1** = 1차 출시 권장, **P2** = 추후 확장

### 4.1 Hero (첫 화면) — P0
- 이름, 한 줄 소개(예: "Python · Web · iOS를 만드는 개발자")
- 주력 기술 3개를 아이콘/뱃지로 노출
- CTA 버튼: **[프로젝트 보기]**, **[연락하기]**
- (선택) 프로필 사진 또는 일러스트

### 4.2 About (자기소개) — P0
- 3~5문장의 간단한 자기소개
- 개발 철학 / 관심 분야
- 이력서(PDF) 다운로드 버튼 — P1

### 4.3 Skills (기술 스택) — P0
카테고리별로 그룹화하여 표시한다.

| 카테고리 | 예시 항목 |
|---|---|
| Python | Python 3, FastAPI / Django / Flask, Pandas, 자동화·크롤링 |
| Web (HTML5) | HTML5, CSS3, JavaScript(ES6+), 반응형 디자인, 웹 접근성 |
| iOS | Swift, SwiftUI, UIKit, Xcode, Core Data, App Store 배포 |
| Tools | Git / GitHub, VS Code, Figma 등 |

- 숙련도는 퍼센트 바 대신 **"주력 / 실무 사용 / 학습 중"** 같은 텍스트 레벨로 표현(과장 방지)

### 4.4 Projects (포트폴리오) — P0
- 프로젝트 카드 그리드 (썸네일, 제목, 요약, 사용 기술 태그)
- **기술별 필터**: 전체 / Python / Web / iOS — P1
- 카드 클릭 시 상세 정보(모달 또는 상세 페이지) — P1
  - 문제 정의 → 해결 방법 → 담당 역할 → 결과
  - 스크린샷 / 데모 GIF
  - 링크: GitHub, 라이브 데모, App Store
- 최소 각 분야별 1개 이상, 총 3~6개 프로젝트 게재

### 4.5 Experience / Timeline (경력·학력) — P1
- 시간순 타임라인 (회사/기관, 기간, 역할, 주요 성과)

### 4.6 Contact (연락하기) — P0
- 이메일 주소 표시: **wjdaudgh90@gmail.com**
- `mailto:` 링크 버튼
- 이메일 주소 복사 버튼 — P1
- GitHub, LinkedIn 등 소셜 링크 아이콘
- 문의 폼 (Formspree 등 외부 서비스 연동) — P2
- 이메일 주소는 스팸 수집 방지를 위해 JS로 조합하거나 난독화 고려

### 4.7 공통 기능
| 기능 | 우선순위 |
|---|---|
| 상단 고정 네비게이션 + 섹션 스크롤 이동 | P0 |
| 모바일 햄버거 메뉴 | P0 |
| 다크 모드 / 라이트 모드 토글 (시스템 설정 기본값) | P1 |
| 스크롤 시 섹션 등장 애니메이션 (`prefers-reduced-motion` 존중) | P1 |
| 한국어 / 영어 전환 | P2 |
| 기술 블로그 섹션 | P2 |
| 방문자 분석 (GA4 또는 Plausible) | P2 |

---

## 5. 비기능 요구사항

### 5.1 성능
- 프레임워크 없이 **순수 HTML5 / CSS3 / Vanilla JS** 로 구현하여 가볍게 유지
- 이미지 WebP 변환 및 `loading="lazy"` 적용
- 외부 라이브러리 최소화

### 5.2 반응형
- 모바일 우선(Mobile-first) 설계
- 브레이크포인트: 480px / 768px / 1024px / 1280px

### 5.3 접근성 (WCAG 2.1 AA)
- 시맨틱 태그 사용 (`header`, `nav`, `main`, `section`, `footer`)
- 모든 이미지에 `alt` 속성
- 키보드만으로 전체 탐색 가능, 포커스 표시 유지
- 텍스트 대비 4.5:1 이상

### 5.4 SEO
- `title`, `meta description`, Open Graph / Twitter Card 태그
- `sitemap.xml`, `robots.txt`
- 구조화 데이터(JSON-LD `Person`)

### 5.5 브라우저 지원
- Chrome, Safari(iOS 포함), Edge, Firefox 최신 2개 버전

---

## 6. 기술 스택 및 구조

### 6.1 기술 스택
| 영역 | 선택 |
|---|---|
| 마크업 | HTML5 |
| 스타일 | CSS3 (CSS 변수, Flexbox, Grid) |
| 스크립트 | Vanilla JavaScript (ES6+) |
| 콘텐츠 데이터 | `data/projects.json` 로 프로젝트 정보 분리 |
| 배포 | GitHub Pages (대안: Netlify, Vercel) |
| 버전 관리 | Git / GitHub |

> 추후 Python 역량을 함께 보여주고 싶다면, 정적 사이트 생성기(예: Python 스크립트로 JSON → HTML 빌드)나 FastAPI 기반 문의 API를 확장 옵션으로 고려한다.

### 6.2 폴더 구조 (안)
```
DemoPort/
├── prd.md
├── index.html
├── css/
│   └── style.css
├── js/
│   └── main.js
├── data/
│   └── projects.json
├── assets/
│   ├── images/
│   ├── icons/
│   └── resume.pdf
├── robots.txt
└── sitemap.xml
```

---

## 7. 디자인 가이드 (초안)
- **톤**: 깔끔하고 미니멀한 개발자 감성, 여백 충분히
- **컬러**: 중립 배경 + 포인트 컬러 1개 (분야별 태그 색상은 보조로 구분)
- **타이포그래피**: 본문 Pretendard(한글) / Inter(영문), 코드 요소 JetBrains Mono
- **레이아웃**: 단일 페이지(One-page) 스크롤 구조

---

## 8. 마일스톤

| 단계 | 내용 | 산출물 |
|---|---|---|
| 1. 기획 | PRD 확정, 콘텐츠(소개글·프로젝트) 수집 | prd.md, 콘텐츠 초안 |
| 2. 디자인 | 와이어프레임, 컬러/폰트 확정 | 와이어프레임 |
| 3. MVP 개발 | P0 기능 구현 (Hero, About, Skills, Projects, Contact) | index.html 외 |
| 4. 개선 | P1 기능 (필터, 다크모드, 이력서, 타임라인) | v1.0 |
| 5. 배포 | GitHub Pages 배포, Lighthouse 점검 | 공개 URL |
| 6. 확장 | P2 기능 (블로그, 다국어, 문의 폼) | v1.x |

---

## 9. 범위 외 (Out of Scope)
- 관리자(CMS) 페이지 및 로그인 기능
- 데이터베이스 서버 운영
- 결제 기능

---

## 10. 미정 사항 (Open Questions)
- [ ] 사이트에 표시할 이름(실명 / 닉네임)
- [ ] 게재할 대표 프로젝트 목록과 각 프로젝트의 링크·스크린샷
- [ ] GitHub, LinkedIn, 블로그 등 소셜 링크 주소
- [ ] 이력서 PDF 공개 여부
- [ ] 커스텀 도메인 사용 여부
- [ ] 한국어 단일 vs 한/영 병기
