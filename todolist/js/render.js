import { formatKorean, previousKey } from './date.js';

const $ = (id) => document.getElementById(id);

const EMPTY_MESSAGES = {
  all: '오늘 할 일을 추가해 보세요',
  active: '진행 중인 할일이 없어요',
  done: '아직 완료한 할일이 없어요',
};

const FILTERS = {
  all: () => true,
  active: (t) => !t.done,
  done: (t) => t.done,
};

// view: { date, filter, editingId, todos, pending, storageOk }
export function render(view) {
  const { date, filter, editingId, todos, pending, storageOk } = view;
  const doneCount = todos.filter((t) => t.done).length;
  const total = todos.length;

  $('date').textContent = formatKorean(date);

  renderProgress(doneCount, total);
  $('storage-notice').hidden = storageOk;
  renderBanner(pending, date);

  for (const btn of document.querySelectorAll('.filter')) {
    btn.setAttribute('aria-pressed', String(btn.dataset.filter === filter));
  }

  const visible = todos.filter(FILTERS[filter]);
  $('list').replaceChildren(...visible.map((t) => renderItem(t, t.id === editingId)));

  const empty = $('empty');
  empty.hidden = visible.length > 0;
  empty.textContent = total === 0 ? EMPTY_MESSAGES.all : EMPTY_MESSAGES[filter];

  $('remaining').textContent = `남은 일 ${total - doneCount}개`;
  $('clear-done').disabled = doneCount === 0;
}

function renderProgress(doneCount, total) {
  const percent = total === 0 ? 0 : Math.round((doneCount / total) * 100);
  const allDone = total > 0 && doneCount === total;

  $('progress-bar').style.width = `${percent}%`;
  $('progress-track').setAttribute('aria-valuenow', String(percent));
  $('progress-text').textContent =
    total === 0 ? '아직 할일이 없어요'
    : allDone ? `${doneCount} / ${total} 완료 · 오늘 할 일을 모두 끝냈어요 🎉`
    : `${doneCount} / ${total} 완료`;
  document.querySelector('.progress').classList.toggle('complete', allDone);
}

function renderBanner(pending, date) {
  $('carry-banner').hidden = pending.length === 0;
  if (pending.length === 0) return;
  const yesterday = previousKey(date);
  const label = pending.every((t) => t.date === yesterday) ? '어제' : '지난 날';
  $('carry-text').textContent = `${label} 못 한 일 ${pending.length}개가 남아 있어요`;
}

function renderItem(todo, editing) {
  const li = document.createElement('li');
  li.className = todo.done ? 'todo done' : 'todo';
  li.dataset.id = todo.id;

  const check = document.createElement('input');
  check.type = 'checkbox';
  check.className = 'todo-check';
  check.checked = todo.done;
  check.setAttribute('aria-label', `'${todo.text}' 완료`);
  li.append(check);

  if (editing) {
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'todo-edit';
    input.value = todo.text;
    input.maxLength = 100;
    input.setAttribute('aria-label', '할일 수정');
    li.append(input);
  } else {
    const text = document.createElement('span');
    text.className = 'todo-text';
    text.textContent = todo.text;
    li.append(text);
    li.append(actionButton('todo-edit-btn', '✎', `'${todo.text}' 수정`));
  }

  li.append(actionButton('todo-delete', '×', `'${todo.text}' 삭제`));
  return li;
}

function actionButton(className, symbol, label) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = `todo-action ${className}`;
  btn.textContent = symbol;
  btn.setAttribute('aria-label', label);
  return btn;
}
