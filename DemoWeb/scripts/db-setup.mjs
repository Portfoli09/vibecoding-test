// Neon(PostgreSQL)에 게시판 테이블을 만들고, 비어 있으면 초기 데이터를 넣는다.
// 실행: npm run db:setup  (DATABASE_URL은 .env.local에서 읽는다)
import { readFile } from "node:fs/promises";
import path from "node:path";

import { neon } from "@neondatabase/serverless";

const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL이 설정되지 않았습니다. .env.local을 확인해 주세요.");
  process.exit(1);
}
const sql = neon(url);

await sql`
  CREATE TABLE IF NOT EXISTS posts (
    id         SERIAL PRIMARY KEY,
    title      VARCHAR(100) NOT NULL,
    author     VARCHAR(20)  NOT NULL,
    content    TEXT         NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
  )`;
await sql`
  CREATE TABLE IF NOT EXISTS comments (
    id         SERIAL PRIMARY KEY,
    post_id    INTEGER      NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author     VARCHAR(20)  NOT NULL,
    content    TEXT         NOT NULL,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
  )`;
await sql`CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments (post_id)`;
console.log("테이블 준비 완료 (posts, comments)");

const [{ count }] = await sql`SELECT count(*)::int AS count FROM posts`;
if (count > 0) {
  console.log(`이미 게시글 ${count}개가 있어 초기 데이터는 넣지 않습니다.`);
  process.exit(0);
}

const data = (await loadJsonStore()) ?? sampleData();

await sql.transaction([
  ...data.posts.map(
    (p) => sql`
      INSERT INTO posts (id, title, author, content, created_at, updated_at)
      VALUES (${p.id}, ${p.title}, ${p.author}, ${p.content}, ${p.createdAt}, ${p.updatedAt})`,
  ),
  ...data.comments.map(
    (c) => sql`
      INSERT INTO comments (id, post_id, author, content, created_at)
      VALUES (${c.id}, ${c.postId}, ${c.author}, ${c.content}, ${c.createdAt})`,
  ),
  // id를 직접 넣었으므로 시퀀스를 최댓값 다음으로 맞춘다.
  sql`SELECT setval(pg_get_serial_sequence('posts', 'id'), COALESCE((SELECT max(id) FROM posts), 0) + 1, false)`,
  sql`SELECT setval(pg_get_serial_sequence('comments', 'id'), COALESCE((SELECT max(id) FROM comments), 0) + 1, false)`,
]);
console.log(
  `초기 데이터 입력 완료: 게시글 ${data.posts.length}개, 댓글 ${data.comments.length}개 (${data.source})`,
);

// 이전 버전에서 쓰던 data/posts.json이 있으면 그대로 옮긴다.
async function loadJsonStore() {
  const file = path.join(process.cwd(), "data", "posts.json");
  try {
    const store = JSON.parse(await readFile(file, "utf8"));
    return {
      posts: store.posts ?? [],
      comments: (store.comments ?? []).filter((c) =>
        (store.posts ?? []).some((p) => p.id === c.postId),
      ),
      source: "data/posts.json에서 가져옴",
    };
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

function sampleData() {
  const base = Date.UTC(2026, 9, 1);
  const authors = ["관리자", "김개발", "이디자인", "박기획"];
  const posts = Array.from({ length: 23 }, (_, i) => {
    const id = i + 1;
    const createdAt = new Date(base + i * 36 * 60 * 60 * 1000).toISOString();
    return {
      id,
      title: id === 1 ? "게시판에 오신 것을 환영합니다" : `샘플 게시글 ${id}번입니다`,
      author: authors[i % authors.length],
      content:
        id === 1
          ? "DemoWeb 게시판입니다.\n\n글쓰기 버튼으로 새 글을 작성하고, 상세 화면에서 수정하거나 삭제할 수 있습니다."
          : `샘플 게시글 ${id}번의 본문입니다.\n페이지네이션 확인을 위해 자동으로 생성되었습니다.`,
      createdAt,
      updatedAt: createdAt,
    };
  });
  const comments = [
    { author: "김개발", content: "첫 댓글입니다. 반갑습니다!" },
    { author: "이디자인", content: "댓글 기능도 잘 동작하네요." },
  ].map((c, i) => ({
    id: i + 1,
    postId: 1,
    ...c,
    createdAt: new Date(base + (i + 1) * 60 * 60 * 1000).toISOString(),
  }));
  return { posts, comments, source: "샘플 데이터" };
}
