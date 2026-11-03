import { MessageCircleIcon } from "lucide-react";

import { CommentForm } from "@/components/comment-form";
import { DeleteCommentButton } from "@/components/delete-comment-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDateTime } from "@/lib/format";
import { listComments } from "@/lib/posts";

export async function CommentSection({ postId }: { postId: number }) {
  const comments = await listComments(postId);

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center gap-2 text-base">
          <MessageCircleIcon className="size-4" />
          댓글 {comments.length}
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-6">
        {comments.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            아직 댓글이 없습니다. 첫 댓글을 남겨 보세요.
          </p>
        ) : (
          <ul className="divide-y">
            {comments.map((comment) => (
              <li key={comment.id} className="flex gap-2 py-3 first:pt-0">
                <div className="min-w-0 flex-1">
                  <p className="text-sm">
                    <span className="font-medium">{comment.author}</span>
                    <span className="ml-2 text-xs text-muted-foreground">
                      {formatDateTime(comment.createdAt)}
                    </span>
                  </p>
                  <p className="mt-1 text-sm leading-relaxed break-words whitespace-pre-wrap">
                    {comment.content}
                  </p>
                </div>
                <DeleteCommentButton postId={postId} id={comment.id} />
              </li>
            ))}
          </ul>
        )}
        <CommentForm postId={postId} />
      </CardContent>
    </Card>
  );
}
