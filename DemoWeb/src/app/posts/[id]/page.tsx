import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ArrowLeftIcon, PencilIcon } from "lucide-react";

import { CommentSection } from "@/components/comment-section";
import { DeletePostButton } from "@/components/delete-post-button";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { formatDateTime } from "@/lib/format";
import { getPost } from "@/lib/posts";

export default function PostPage({ params }: PageProps<"/posts/[id]">) {
  return (
    <div className="grid gap-4">
      <Link
        href="/"
        className={buttonVariants({
          variant: "ghost",
          size: "sm",
          className: "w-fit",
        })}
      >
        <ArrowLeftIcon />
        목록으로
      </Link>
      <Suspense
        fallback={<div className="h-64 animate-pulse rounded-xl bg-muted" />}
      >
        <PostDetail params={params} />
      </Suspense>
    </div>
  );
}

async function PostDetail({
  params,
}: Pick<PageProps<"/posts/[id]">, "params">) {
  const { id } = await params;
  const post = await getPost(Number(id));
  if (!post) notFound();

  const edited = post.updatedAt !== post.createdAt;

  return (
    <>
      <Card>
        <CardHeader className="border-b">
          <CardTitle className="text-xl break-words sm:text-2xl">
            {post.title}
          </CardTitle>
          <CardDescription className="flex flex-wrap gap-x-3 gap-y-1">
            <span>{post.author}</span>
            <span>작성 {formatDateTime(post.createdAt)}</span>
            {edited && <span>수정 {formatDateTime(post.updatedAt)}</span>}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="min-h-40 leading-relaxed break-words whitespace-pre-wrap">
            {post.content}
          </div>
        </CardContent>
        <CardFooter className="justify-end gap-2 border-t">
          <Link
            href={`/posts/${post.id}/edit`}
            className={buttonVariants({ variant: "outline" })}
          >
            <PencilIcon />
            수정
          </Link>
          <DeletePostButton id={post.id} title={post.title} />
        </CardFooter>
      </Card>
      <CommentSection postId={post.id} />
    </>
  );
}
