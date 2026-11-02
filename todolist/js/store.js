const KEY = 'todolist:v1';
const BACKUP_KEY = 'todolist:backup';
export const MAX_LENGTH = 100;

let data = createDefault();
let storageOk = true;

function createDefault() {
  return { version: 1, todos: [], settings: { theme: 'system' } };
}

function newId() {
  if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
    storageOk = true;
  } catch {
    storageOk = false;
  }
}

export function load() {
  let raw;
  try {
    raw = localStorage.getItem(KEY);
  } catch {
    storageOk = false;
    return data;
  }
  if (raw === null) return data;

  try {
    const parsed = JSON.parse(raw);
    if (parsed?.version === 1 && Array.isArray(parsed.todos)) {
      data = parsed;
      return data;
    }
  } catch {
    // 아래에서 백업 후 기본값으로 시작
  }
  try {
    localStorage.setItem(BACKUP_KEY, raw);
  } catch {
    // 백업 실패는 무시
  }
  return data;
}

export const isStorageOk = () => storageOk;

export function normalizeText(text) {
  return text.trim().slice(0, MAX_LENGTH);
}

export function getTodos(date) {
  return data.todos.filter((t) => t.date === date).sort((a, b) => a.order - b.order);
}

function nextOrder(date) {
  return getTodos(date).reduce((max, t) => Math.max(max, t.order), -1) + 1;
}

function createTodo(text, date) {
  return {
    id: newId(),
    text,
    done: false,
    date,
    priority: 'normal',
    order: nextOrder(date),
    createdAt: Date.now(),
    completedAt: null,
    carriedOver: false,
  };
}

export function addTodo(text, date) {
  const value = normalizeText(text);
  if (!value) return null;
  const todo = createTodo(value, date);
  data.todos.push(todo);
  save();
  return todo;
}

export function updateTodo(id, patch) {
  const todo = data.todos.find((t) => t.id === id);
  if (!todo) return;
  Object.assign(todo, patch);
  save();
}

export function toggleTodo(id) {
  const todo = data.todos.find((t) => t.id === id);
  if (!todo) return;
  const done = !todo.done;
  updateTodo(id, { done, completedAt: done ? Date.now() : null });
}

export function removeTodo(id) {
  const index = data.todos.findIndex((t) => t.id === id);
  if (index === -1) return null;
  const [removed] = data.todos.splice(index, 1);
  save();
  return removed;
}

// 실행 취소용: 삭제했던 항목을 그대로 되돌림
export function restoreTodos(todos) {
  data.todos.push(...todos);
  save();
}

export function clearCompleted(date) {
  const removed = data.todos.filter((t) => t.date === date && t.done);
  data.todos = data.todos.filter((t) => !(t.date === date && t.done));
  save();
  return removed;
}

// 지정 날짜 이전의, 아직 이월하지 않은 미완료 항목
export function getPendingBefore(date) {
  return data.todos
    .filter((t) => t.date < date && !t.done && !t.carriedOver)
    .sort((a, b) => (a.date === b.date ? a.order - b.order : a.date.localeCompare(b.date)));
}

// 원본은 이월 표시만 남기고, 오늘 날짜로 복사본을 만든다
export function carryOver(ids, toDate) {
  for (const id of ids) {
    const original = data.todos.find((t) => t.id === id);
    if (!original || original.carriedOver) continue;
    const copy = createTodo(original.text, toDate);
    copy.priority = original.priority;
    data.todos.push(copy);
    original.carriedOver = true;
  }
  save();
}
