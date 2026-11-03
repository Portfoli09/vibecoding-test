import "server-only";

import { neon } from "@neondatabase/serverless";

export type Post = {
  id: number;
  title: string;
  author: string;
  content: string;
  createdAt: string;
  updatedAt: string;
};

export type PostInput = Pick<Post, "title" | "author" | "content">;

export type Comment = {
  id: number;
  postId: number;
  author: string;
  content: string;
  createdAt: string;
};

export type CommentInput = Pick<Comment, "author" | "content">;

export const PAGE_SIZE = 10;

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL이 설정되지 않았습니다. .env.local을 확인해 주세요.");
}

// Neon의 HTTP 드라이버: 요청마다 연결을 맺지 않아 서버리스 환경에서도 그대로 쓸 수 있다.
const sql = neon(process.env.DATABASE_URL);

// 컬럼명을 camelCase로 바꾸고 날짜는 ISO 문자열로 맞춘다(클라이언트로 그대로 넘길 수 있게).
const POST_COLUMNS = `id, title, author, content,
  to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS "createdAt",
  to_char(updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS "updatedAt"`;

const COMMENT_COLUMNS = `id, post_id AS "postId", author, content,
  to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"') AS "createdAt"`;

export async function listPosts(page: number) {
  const [{ total }] = (await sql`SELECT count(*)::int AS total FROM posts`) as {
    total: number;
  }[];
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);
  const items = (await sql.query(
    `SELECT ${POST_COLUMNS},
       (SELECT count(*)::int FROM comments c WHERE c.post_id = p.id) AS "commentCount"
     FROM posts p
     ORDER BY id DESC
     LIMIT $1 OFFSET $2`,
    [PAGE_SIZE, (current - 1) * PAGE_SIZE],
  )) as (Post & { commentCount: number })[];
  return { items, total, page: current, totalPages };
}

export async function getPost(id: number) {
  if (!Number.isSafeInteger(id)) return null;
  const rows = (await sql.query(
    `SELECT ${POST_COLUMNS} FROM posts WHERE id = $1`,
    [id],
  )) as Post[];
  return rows[0] ?? null;
}

export async function createPost(input: PostInput) {
  const rows = (await sql.query(
    `INSERT INTO posts (title, author, content) VALUES ($1, $2, $3)
     RETURNING ${POST_COLUMNS}`,
    [input.title, input.author, input.content],
  )) as Post[];
  return rows[0];
}

export async function updatePost(id: number, input: PostInput) {
  const rows = (await sql.query(
    `UPDATE posts SET title = $2, author = $3, content = $4, updated_at = now()
     WHERE id = $1
     RETURNING ${POST_COLUMNS}`,
    [id, input.title, input.author, input.content],
  )) as Post[];
  return rows[0] ?? null;
}

export async function deletePost(id: number) {
  // 댓글은 외래 키의 ON DELETE CASCADE로 함께 지워진다.
  const rows = await sql`DELETE FROM posts WHERE id = ${id} RETURNING id`;
  return rows.length > 0;
}

export async function listComments(postId: number) {
  return (await sql.query(
    `SELECT ${COMMENT_COLUMNS} FROM comments WHERE post_id = $1 ORDER BY id`,
    [postId],
  )) as Comment[];
}

export async function createComment(postId: number, input: CommentInput) {
  // 게시글이 없으면 아무것도 넣지 않고 null을 돌려준다.
  const rows = (await sql.query(
    `INSERT INTO comments (post_id, author, content)
     SELECT id, $2, $3 FROM posts WHERE id = $1
     RETURNING ${COMMENT_COLUMNS}`,
    [postId, input.author, input.content],
  )) as Comment[];
  return rows[0] ?? null;
}

export async function deleteComment(postId: number, id: number) {
  const rows =
    await sql`DELETE FROM comments WHERE id = ${id} AND post_id = ${postId} RETURNING id`;
  return rows.length > 0;
}
