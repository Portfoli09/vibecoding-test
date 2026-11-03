import Link from "next/link";
import { Suspense } from "react";

import { PostPagination } from "@/components/post-pagination";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { listPosts } from "@/lib/posts";

export default function HomePage({ searchParams }: PageProps<"/">) {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">게시판</h1>
        <p className="text-sm text-muted-foreground">
          자유롭게 글을 남겨 주세요.
        </p>
      </div>
      <Suspense fallback={<ListSkeleton />}>
        <PostList searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function PostList({
  searchParams,
}: Pick<PageProps<"/">, "searchParams">) {
  const { page: rawPage } = await searchParams;
  const requested = Number(Array.isArray(rawPage) ? rawPage[0] : rawPage);
  const { items, total, page, totalPages } = await listPosts(
    Number.isInteger(requested) ? requested : 1,
  );

  if (total === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          아직 게시글이 없습니다. 첫 글을 작성해 보세요!
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <p className="text-sm text-muted-foreground">
        전체 {total.toLocaleString()}개 · {page}/{totalPages} 페이지
      </p>

      {/* 데스크톱: 표 */}
      <Card className="hidden py-0 sm:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16 text-center">번호</TableHead>
              <TableHead>제목</TableHead>
              <TableHead className="w-32">작성자</TableHead>
              <TableHead className="w-28 text-right">작성일</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((post) => (
              <TableRow key={post.id}>
                <TableCell className="text-center text-muted-foreground">
                  {post.id}
                </TableCell>
                <TableCell className="max-w-0">
                  <div className="flex items-center gap-1.5">
                    <Link
                      href={`/posts/${post.id}`}
                      className="truncate font-medium hover:underline"
                    >
                      {post.title}
                    </Link>
                    <CommentCount count={post.commentCount} />
                  </div>
                </TableCell>
                <TableCell className="truncate">{post.author}</TableCell>
                <TableCell className="text-right text-muted-foreground tabular-nums">
                  {formatDate(post.createdAt)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* 모바일: 목록 */}
      <ul className="divide-y rounded-xl border sm:hidden">
        {items.map((post) => (
          <li key={post.id}>
            <Link
              href={`/posts/${post.id}`}
              className="block px-4 py-3 hover:bg-muted/50"
            >
              <div className="flex items-center gap-1.5">
                <p className="truncate font-medium">{post.title}</p>
                <CommentCount count={post.commentCount} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {post.author} · {formatDate(post.createdAt)}
              </p>
            </Link>
          </li>
        ))}
      </ul>

      <PostPagination page={page} totalPages={totalPages} />
    </>
  );
}

function CommentCount({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <span
      className="shrink-0 text-xs font-medium text-primary/70 tabular-nums"
      aria-label={`댓글 ${count}개`}
    >
      [{count}]
    </span>
  );
}

function ListSkeleton() {
  return (
    <div className="grid gap-2" aria-busy="true" aria-label="불러오는 중">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="h-10 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  );
}
