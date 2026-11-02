const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토'];

const pad = (n) => String(n).padStart(2, '0');

// 로컬 시간 기준 "YYYY-MM-DD"
export function todayKey(now = new Date()) {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

// "2026-11-02" → "2026년 11월 2일 (월)"
export function formatKorean(key) {
  const [y, m, d] = key.split('-').map(Number);
  const day = new Date(y, m - 1, d).getDay();
  return `${y}년 ${m}월 ${d}일 (${WEEKDAYS[day]})`;
}

// 전날 키 ("2026-11-02" → "2026-11-01")
export function previousKey(key) {
  const [y, m, d] = key.split('-').map(Number);
  return todayKey(new Date(y, m - 1, d - 1));
}

// 날짜가 바뀌면 cb(새 날짜 키) 호출. 1분 간격 + 탭이 다시 보일 때 확인.
export function onDayChange(cb) {
  let current = todayKey();
  const check = () => {
    const next = todayKey();
    if (next !== current) {
      current = next;
      cb(next);
    }
  };
  setInterval(check, 60 * 1000);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') check();
  });
}
