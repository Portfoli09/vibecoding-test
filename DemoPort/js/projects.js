// 프로젝트 데이터. 여기만 수정하면 프로젝트 카드가 바뀝니다.
// category: "python" | "web" | "ios"
// links: 비워두면 해당 링크는 표시되지 않습니다.
window.PROJECTS = [
  {
    title: "업무 자동화 봇",
    category: "python",
    description: "반복되는 엑셀 정리와 리포트 메일 발송을 자동화한 Python 스크립트. 주간 작업 시간을 크게 줄였습니다.",
    tags: ["Python", "Pandas", "openpyxl", "스케줄링"],
    links: { github: "", demo: "" }
  },
  {
    title: "REST API 서버",
    category: "python",
    description: "FastAPI로 만든 회원·게시판 API. JWT 인증과 자동 문서화(OpenAPI)를 적용했습니다.",
    tags: ["FastAPI", "SQLite", "JWT"],
    links: { github: "", demo: "" }
  },
  {
    title: "반응형 랜딩 페이지",
    category: "web",
    description: "프레임워크 없이 HTML5·CSS Grid·Vanilla JS로 구현한 반응형 랜딩 페이지. 웹 접근성을 고려해 설계했습니다.",
    tags: ["HTML5", "CSS3", "JavaScript"],
    links: { github: "", demo: "" }
  },
  {
    title: "습관 트래커 iOS 앱",
    category: "ios",
    description: "SwiftUI와 Core Data로 만든 습관 기록 앱. 위젯과 로컬 알림을 지원합니다.",
    tags: ["Swift", "SwiftUI", "Core Data", "WidgetKit"],
    links: { github: "", appstore: "" }
  }
];
