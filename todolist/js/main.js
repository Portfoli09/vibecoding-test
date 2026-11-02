import * as store from './store.js';
import { render } from './render.js';
import { todayKey, onDayChange } from './date.js';

const FILTER_KEY = 'todolist:filter';
const TOAST_MS = 5000;

const $ = (id) => document.getElementById(id);
const input = $('new-todo');
const list = $('list');

const ui = {
  date: todayKey(),
  filter: readFilter(),
  editingId: null,
};

function readFilter() {
  try {
    const saved = sessionStorage.getItem(FILTER_KEY);
    if (['all', 'active', 'done'].includes(saved)) return saved;
  } catch {
    // 세션 저장소를 못 쓰면 기본값
  }
  return 'all';
}

function update() {
  render({
    ...ui,
    todos: store.getTodos(ui.date),
    pending: store.getPendingBefore(ui.date),
    storageOk: store.isStorageOk(),
  });
}

// ---- 토스트 (실행 취소) ----
let toastTimer = null;
let undoAction = null;

function showToast(message, onUndo) {
  $('toast-text').textContent = message;
  $('toast').hidden = false;
  undoAction = onUndo;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(hideToast, TOAST_MS);
}

function hideToast() {
  $('toast').hidden = true;
  undoAction = null;
}

$('toast-undo').addEventListener('click', () => {
  undoAction?.();
  hideToast();
  update();
});

// ---- 추가 ----
$('add-form').addEventListener('submit', (e) => {
  e.preventDefault();
  if (store.addTodo(input.value, ui.date)) {
    input.value = '';
    update();
  }
  input.focus();
});

// ---- 수정 ----
function startEdit(id) {
  ui.editingId = id;
  update();
  const field = list.querySelector(`[data-id="${CSS.escape(id)}"] .todo-edit`);
  field?.focus();
  field?.select();
}

function finishEdit(save) {
  const id = ui.editingId;
  if (!id) return;
  const field = list.querySelector('.todo-edit');
  ui.editingId = null;
  if (save && field) {
    const text = store.normalizeText(field.value);
    if (text) store.updateTodo(id, { text });
  }
  update();
  list.querySelector(`[data-id="${CSS.escape(id)}"] .todo-edit-btn`)?.focus();
}

// ---- 목록 이벤트 (위임) ----
list.addEventListener('change', (e) => {
  if (!e.target.classList.contains('todo-check')) return;
  const id = e.target.closest('.todo').dataset.id;
  store.toggleTodo(id);
  update();
  list.querySelector(`[data-id="${CSS.escape(id)}"] .todo-check`)?.focus();
});

list.addEventListener('click', (e) => {
  const item = e.target.closest('.todo');
  if (!item) return;
  const { id } = item.dataset;

  if (e.target.closest('.todo-delete')) {
    if (ui.editingId === id) ui.editingId = null;
    const removed = store.removeTodo(id);
    update();
    if (removed) showToast('삭제됨', () => store.restoreTodos([removed]));
    input.focus();
  } else if (e.target.closest('.todo-edit-btn')) {
    startEdit(id);
  }
});

list.addEventListener('dblclick', (e) => {
  const text = e.target.closest('.todo-text');
  if (text) startEdit(text.closest('.todo').dataset.id);
});

list.addEventListener('keydown', (e) => {
  if (!e.target.classList.contains('todo-edit')) return;
  if (e.key === 'Enter') {
    e.preventDefault();
    finishEdit(true);
  } else if (e.key === 'Escape') {
    e.preventDefault();
    finishEdit(false);
  }
});

// 편집 중 다른 곳을 누르면 저장
list.addEventListener('focusout', (e) => {
  if (e.target.classList.contains('todo-edit') && ui.editingId) finishEdit(true);
});

// ---- 필터 ----
for (const btn of document.querySelectorAll('.filter')) {
  btn.addEventListener('click', () => {
    ui.filter = btn.dataset.filter;
    try {
      sessionStorage.setItem(FILTER_KEY, ui.filter);
    } catch {
      // 무시
    }
    update();
  });
}

// ---- 완료한 일 지우기 ----
$('clear-done').addEventListener('click', () => {
  const removed = store.clearCompleted(ui.date);
  update();
  if (removed.length) showToast(`완료한 일 ${removed.length}개 삭제됨`, () => store.restoreTodos(removed));
});

// ---- 미완료 이월 ----
$('carry-btn').addEventListener('click', () => {
  const ids = store.getPendingBefore(ui.date).map((t) => t.id);
  store.carryOver(ids, ui.date);
  update();
});

// ---- 날짜 변경 ----
onDayChange((key) => {
  ui.date = key;
  ui.editingId = null;
  update();
});

// ---- 시작 ----
store.load();
update();
if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) input.focus();
