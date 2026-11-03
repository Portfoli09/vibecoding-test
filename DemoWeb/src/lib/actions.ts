"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import * as posts from "@/lib/posts";
import {
  readCommentFields,
  readPostFields,
  validateComment,
  validatePost,
  type CommentErrors,
  type CommentFields,
  type FieldErrors,
  type PostFields,
} from "@/lib/validation";

export type PostFormState = {
  values: PostFields;
  errors: FieldErrors;
  message?: string;
};

function toInput(fields: PostFields): posts.PostInput {
  return { ...fields, author: fields.author || "익명" };
}

export async function createPostAction(
  _prev: PostFormState,
  formData: FormData,
): Promise<PostFormState> {
  const values = readPostFields(formData);
  const errors = validatePost(values);
  if (Object.keys(errors).length > 0) return { values, errors };

  const post = await posts.createPost(toInput(values));
  revalidatePath("/", "layout");
  redirect(`/posts/${post.id}`);
}

export async function updatePostAction(
  id: number,
  _prev: PostFormState,
  formData: FormData,
): Promise<PostFormState> {
  const values = readPostFields(formData);
  const errors = validatePost(values);
  if (Object.keys(errors).length > 0) return { values, errors };

  const post = await posts.updatePost(id, toInput(values));
  if (!post) {
    return { values, errors: {}, message: "이미 삭제된 게시글입니다." };
  }
  revalidatePath("/", "layout");
  redirect(`/posts/${id}`);
}

export async function deletePostAction(id: number) {
  await posts.deletePost(id);
  revalidatePath("/", "layout");
  redirect("/");
}

export type CommentFormState = {
  values: CommentFields;
  errors: CommentErrors;
  message?: string;
  // 등록에 성공할 때마다 바뀌어 폼을 비우는 데 쓴다.
  submitted: number;
};

export async function createCommentAction(
  postId: number,
  prev: CommentFormState,
  formData: FormData,
): Promise<CommentFormState> {
  const values = readCommentFields(formData);
  const errors = validateComment(values);
  if (Object.keys(errors).length > 0)
    return { values, errors, submitted: prev.submitted };

  const comment = await posts.createComment(postId, {
    ...values,
    author: values.author || "익명",
  });
  if (!comment) {
    return {
      values,
      errors: {},
      submitted: prev.submitted,
      message: "이미 삭제된 게시글입니다.",
    };
  }
  revalidatePath("/", "layout");
  return {
    values: { author: values.author, content: "" },
    errors: {},
    submitted: prev.submitted + 1,
  };
}

export async function deleteCommentAction(postId: number, id: number) {
  await posts.deleteComment(postId, id);
  revalidatePath("/", "layout");
}
