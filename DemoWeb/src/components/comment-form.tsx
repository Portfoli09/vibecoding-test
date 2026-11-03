"use client";

import { useActionState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { createCommentAction, type CommentFormState } from "@/lib/actions";
import { LIMITS } from "@/lib/validation";

export function CommentForm({ postId }: { postId: number }) {
  const [state, formAction, pending] = useActionState(
    createCommentAction.bind(null, postId),
    {
      values: { author: "", content: "" },
      errors: {},
      submitted: 0,
    } satisfies CommentFormState,
  );
  const { values, errors } = state;

  return (
    // 등록 성공(submitted 증가)이나 검증 실패 때마다 다시 마운트해 defaultValue를 반영한다.
    <form
      action={formAction}
      noValidate
      className="grid gap-3"
      key={`${state.submitted}:${JSON.stringify(values)}`}
    >
      {state.message && (
        <p
          role="alert"
          className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {state.message}
        </p>
      )}
      <div className="grid gap-1.5">
        <Input
          name="author"
          aria-label="작성자"
          defaultValue={values.author}
          maxLength={LIMITS.author}
          placeholder="작성자 (비워 두면 익명)"
          aria-invalid={!!errors.author}
          className="sm:max-w-xs"
        />
        {errors.author && (
          <p className="text-sm text-destructive">{errors.author}</p>
        )}
      </div>
      <div className="grid gap-1.5">
        <Textarea
          name="content"
          aria-label="댓글 내용"
          defaultValue={values.content}
          maxLength={LIMITS.comment}
          placeholder="댓글을 입력하세요"
          rows={3}
          aria-invalid={!!errors.content}
        />
        {errors.content && (
          <p className="text-sm text-destructive">{errors.content}</p>
        )}
      </div>
      <div className="flex justify-end">
        <Button type="submit" disabled={pending}>
          {pending ? "등록 중…" : "댓글 등록"}
        </Button>
      </div>
    </form>
  );
}
