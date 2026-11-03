export const LIMITS = {
  title: 100,
  author: 20,
  content: 5000,
  comment: 1000,
} as const;

export type PostFields = {
  title: string;
  author: string;
  content: string;
};

export type FieldErrors = Partial<Record<keyof PostFields, string>>;

export function readPostFields(formData: FormData): PostFields {
  const get = (key: string) => String(formData.get(key) ?? "").trim();
  return {
    title: get("title"),
    author: get("author"),
    content: get("content"),
  };
}

export function validatePost(fields: PostFields): FieldErrors {
  const errors: FieldErrors = {};
  if (!fields.title) errors.title = "제목을 입력해 주세요.";
  else if (fields.title.length > LIMITS.title)
    errors.title = `제목은 ${LIMITS.title}자 이하로 입력해 주세요.`;

  if (fields.author.length > LIMITS.author)
    errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;

  if (!fields.content) errors.content = "본문을 입력해 주세요.";
  else if (fields.content.length > LIMITS.content)
    errors.content = `본문은 ${LIMITS.content.toLocaleString()}자 이하로 입력해 주세요.`;

  return errors;
}

export type CommentFields = {
  author: string;
  content: string;
};

export type CommentErrors = Partial<Record<keyof CommentFields, string>>;

export function readCommentFields(formData: FormData): CommentFields {
  const get = (key: string) => String(formData.get(key) ?? "").trim();
  return { author: get("author"), content: get("content") };
}

export function validateComment(fields: CommentFields): CommentErrors {
  const errors: CommentErrors = {};
  if (fields.author.length > LIMITS.author)
    errors.author = `작성자는 ${LIMITS.author}자 이하로 입력해 주세요.`;

  if (!fields.content) errors.content = "댓글 내용을 입력해 주세요.";
  else if (fields.content.length > LIMITS.comment)
    errors.content = `댓글은 ${LIMITS.comment.toLocaleString()}자 이하로 입력해 주세요.`;

  return errors;
}
