# DemoWeb 게시판

Next.js(App Router) + TypeScript + shadcn/ui(Tailwind CSS)로 만든 간단한 게시판입니다.

## 기능

- 게시글 목록(제목·작성자·작성일, 페이지당 10개 페이지네이션, 모바일에서는 카드형 목록)
- 게시글 상세 / 글쓰기 / 수정 / 삭제(확인 다이얼로그)
- 댓글 작성·삭제(최대 1,000자), 목록에 댓글 수 표시
- 서버 측 입력 검증: 제목·본문 필수, 길이 제한(제목 100자, 작성자 20자, 본문 5,000자). 작성자를 비우면 '익명'
- 라이트/다크/시스템 테마 전환(next-themes)

## 실행

1. `.env.example`을 참고해 `.env.local`에 Neon 연결 문자열(`DATABASE_URL`)을 넣습니다.
2. 테이블을 만들고 초기 데이터를 넣습니다(이미 데이터가 있으면 건너뜀).

```bash
npm install
npm run db:setup
npm run dev      # http://localhost:3000
```

## 데이터 저장 방식

[Neon](https://neon.tech)(서버리스 PostgreSQL)을 `@neondatabase/serverless`의 HTTP 드라이버로 사용합니다.

- 테이블: `posts`, `comments`(`post_id` 외래 키, 게시글 삭제 시 `ON DELETE CASCADE`로 댓글도 삭제)
- 스키마와 초기 데이터: `scripts/db-setup.mjs`. DB가 비어 있을 때 예전 버전의 `data/posts.json`이 있으면 그 내용을, 없으면 샘플 글 23개를 넣습니다.
- 읽기: 서버 컴포넌트에서 `src/lib/posts.ts`로 조회합니다.
- 쓰기: Server Actions(`src/lib/actions.ts`)가 검증 후 DB를 갱신하고 `revalidatePath`로 화면을 새로 고칩니다.
