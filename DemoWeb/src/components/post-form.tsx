"use client";

import Link from "next/link";
import { useActionState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { PostFormState } from "@/lib/actions";
import { LIMITS, type PostFields } from "@/lib/validation";

type Props = {
  action: (state: PostFormState, formData: FormData) => Promise<PostFormState>;
  initialValues?: PostFields;
  submitLabel: string;
  cancelHref: string;
};

const EMPTY: PostFields = { title: "", author: "", content: "" };

export function PostForm({
  action,
  initialValues = EMPTY,
  submitLabel,
  cancelHref,
}: Props) {
  const [state, formAction, pending] = useActionState(action, {
    values: initialValues,
    errors: {},
  });
  const { values, errors } = state;

  return (
    // key로 서버 응답마다 다시 마운트해 defaultValue가 최신 입력값을 반영하게 한다.
    <form action={formAction} noValidate className="grid gap-5" key={JSON.stringify(values)}>
      {state.message && (
        <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {state.message}
        </p>
      )}

      <div className="grid gap-2">
        <Label htmlFor="title">
          제목 <span className="text-destructive">*</span>
        </Label>
        <Input
          id="title"
          name="title"
          defaultValue={values.title}
          maxLength={LIMITS.title}
          placeholder="제목을 입력하세요"
          aria-invalid={!!errors.title}
          aria-describedby={errors.title ? "title-error" : undefined}
          autoFocus
        />
        {errors.title && (
          <p id="title-error" className="text-sm text-destructive">
            {errors.title}
          </p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="author">작성자</Label>
        <Input
          id="author"
          name="author"
          defaultValue={values.author}
          maxLength={LIMITS.author}
          placeholder="비워 두면 '익명'으로 표시됩니다"
          aria-invalid={!!errors.author}
          aria-describedby={errors.author ? "author-error" : undefined}
          className="sm:max-w-xs"
        />
        {errors.author && (
          <p id="author-error" className="text-sm text-destructive">
            {errors.author}
          </p>
        )}
      </div>

      <div className="grid gap-2">
        <Label htmlFor="content">
          본문 <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="content"
          name="content"
          defaultValue={values.content}
          maxLength={LIMITS.content}
          placeholder="내용을 입력하세요"
          rows={12}
          aria-invalid={!!errors.content}
          aria-describedby={errors.content ? "content-error" : undefined}
          className="min-h-60"
        />
        {errors.content && (
          <p id="content-error" className="text-sm text-destructive">
            {errors.content}
          </p>
        )}
      </div>

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Link href={cancelHref} className={buttonVariants({ variant: "outline" })}>
          취소
        </Link>
        <Button type="submit" disabled={pending}>
          {pending ? "저장 중…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
