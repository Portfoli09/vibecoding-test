"""
네이버페이 증권(https://stock.naver.com/market/stock/kr)의 코스피200 데이터를 크롤링하는 GUI 앱
(PyQt6 + requests)

stock.naver.com 은 Next.js 로 만든 페이지라서, 처음 받는 HTML 에는 지수 값이나 종목 표가 들어 있지 않고
브라우저가 자바스크립트로 아래 JSON API 를 호출해 화면을 채운다.
그래서 BeautifulSoup 으로 HTML 을 파싱해서는 코스피200 숫자를 얻을 수 없고, 이 앱은 페이지가 실제로 사용하는 API 를 직접 호출해 데이터를 가져온다.

  - 지수 시세     : https://polling.finance.naver.com/api/realtime/domestic/index/KPI200
  - 구성종목 목록 : https://m.stock.naver.com/api/index/KPI200/enrollStocks?page=N&pageSize=50

동작 순서
1. [불러오기]를 누르면 코스피200 지수 시세와 구성종목 전체(시가총액 순)를 가져온다.
2. 위쪽 카드에 지수 현재가 / 전일비 / 시가·고가·저가가, 아래 표에 구성종목이 표시된다.
3. 종목명·코드로 검색하거나 열 제목을 눌러 정렬할 수 있고, 행을 더블클릭하면 종목 페이지가 열린다.
4. [자동 갱신]을 켜면 30초마다 다시 불러오고, 결과를 엑셀(.xlsx) 또는 CSV로 저장할 수 있다.

설치: pip install PyQt6 requests openpyxl
"""

import csv
import os
import sys
import time

import requests
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

PAGE_URL = "https://stock.naver.com/market/stock/kr"
INDEX_API_URL = "https://polling.finance.naver.com/api/realtime/domestic/index/KPI200"
STOCKS_API_URL = "https://m.stock.naver.com/api/index/KPI200/enrollStocks"
STOCK_PAGE_URL = "https://stock.naver.com/domestic/stock/{code}/price"
PAGE_SIZE = 50  # API 가 허용하는 최대값 (100 이상은 400 에러)
AUTO_REFRESH_MS = 30_000

HEADERS = {
    # User-Agent 를 지정하지 않으면 차단되거나 빈 응답이 올 수 있다.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": PAGE_URL,
}

# 구성종목 컬럼: (표/파일 헤더, API 필드)
STOCK_COLUMNS = [
    ("종목코드", "itemCode"),
    ("종목명", "stockName"),
    ("현재가", "closePrice"),
    ("전일비", "compareToPreviousClosePrice"),
    ("등락률(%)", "fluctuationsRatio"),
    ("거래량", "accumulatedTradingVolume"),
    ("거래대금(백만)", "accumulatedTradingValue"),
    ("시가총액(억)", "marketValue"),
    ("기준시각", "localTradedAt"),
]
TEXT_FIELDS = ("itemCode", "stockName", "localTradedAt")
STOCK_LABELS = [label for label, _ in STOCK_COLUMNS]

MARKET_STATUS = {"OPEN": "장중", "CLOSE": "장마감", "PREOPEN": "장전"}

# 한국 증시 관례: 상승은 빨강, 하락은 파랑
UP_COLOR = "#f43f5e"
DOWN_COLOR = "#3b82f6"
FLAT_COLOR = "#94a3b8"


# ---------------------------------------------------------------------------
# 크롤링
# ---------------------------------------------------------------------------

def to_number(text):
    """'1,234.5' 같은 문자열을 숫자로 바꾼다. 숫자가 아니면 원래 값을 돌려준다."""
    try:
        value = float(str(text).replace(",", ""))
    except ValueError:
        return text
    return int(value) if value.is_integer() else value


def fetch_index() -> dict:
    """코스피200 지수 시세를 가져온다."""
    resp = requests.get(INDEX_API_URL, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    data = resp.json()["datas"][0]
    return {
        "지수명": data["stockName"],
        "현재가": to_number(data["closePrice"]),
        "전일비": to_number(data["compareToPreviousClosePrice"]),
        "등락률(%)": to_number(data["fluctuationsRatio"]),
        "시가": to_number(data["openPrice"]),
        "고가": to_number(data["highPrice"]),
        "저가": to_number(data["lowPrice"]),
        "거래량": data["accumulatedTradingVolume"],
        "거래대금": data["accumulatedTradingValue"],
        "장상태": data["marketStatus"],
        "기준시각": data["localTradedAt"],
    }


def fetch_stocks_page(page: int) -> list[dict]:
    """코스피200 구성종목 한 페이지(시가총액 순)를 가져온다."""
    params = {"page": page, "pageSize": PAGE_SIZE}
    resp = requests.get(STOCKS_API_URL, headers=HEADERS, params=params, timeout=10)
    resp.raise_for_status()
    rows = []
    for item in resp.json():
        row = {}
        for label, field in STOCK_COLUMNS:
            value = item.get(field, "")
            row[label] = value if field in TEXT_FIELDS else to_number(value)
        rows.append(row)
    return rows


def save_csv(stocks: list[dict], path: str) -> None:
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않는다.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STOCK_LABELS)
        writer.writeheader()
        writer.writerows(stocks)


def save_excel(index: dict, stocks: list[dict], path: str) -> None:
    """구성종목(시트1)과 지수 시세(시트2)를 서식이 적용된 엑셀(.xlsx) 파일로 저장한다."""
    wb = Workbook()
    header_fill = PatternFill("solid", start_color="1F2A44")
    header_font = Font(name="맑은 고딕", bold=True, color="FFFFFF", size=11)
    stripe_fill = PatternFill("solid", start_color="F3F6FB")
    thin = Side(style="thin", color="D0D7E2")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    body_font = Font(name="맑은 고딕", size=10)

    def write_sheet(ws, headers, rows, widths):
        ws.append(headers)
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border
        ws.row_dimensions[1].height = 24
        for i, row in enumerate(rows, 1):
            ws.append([row[h] for h in headers])
            for cell in ws[ws.max_row]:
                cell.font = body_font
                cell.border = border
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "#,##0.00" if isinstance(cell.value, float) else "#,##0"
                if i % 2 == 0:
                    cell.fill = stripe_fill
        for col, width in enumerate(widths, 1):
            ws.column_dimensions[ws.cell(1, col).column_letter].width = width
        ws.freeze_panes = "A2"

    ws = wb.active
    ws.title = "구성종목"
    write_sheet(ws, STOCK_LABELS, stocks, [10, 18, 12, 10, 10, 14, 15, 14, 28])
    # 전일비 / 등락률을 상승은 빨강, 하락은 파랑으로 칠한다.
    for row in ws.iter_rows(min_row=2, min_col=4, max_col=5):
        for cell in row:
            if isinstance(cell.value, (int, float)) and cell.value:
                cell.font = Font(name="맑은 고딕", size=10, color="E11D48" if cell.value > 0 else "2563EB")
    ws.auto_filter.ref = ws.dimensions

    if index:
        write_sheet(wb.create_sheet("지수"), list(index.keys()), [index], [12] * 9 + [10, 28])

    wb.properties.title = "코스피200"
    wb.save(path)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

STYLE_SHEET = """
QMainWindow, QWidget#central {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #172554);
}
QWidget { color: #e2e8f0; font-family: "맑은 고딕", "Malgun Gothic"; font-size: 13px; }

QFrame#banner {
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:0.5 #7c3aed, stop:1 #db2777);
}
QLabel#bannerTitle { font-size: 24px; font-weight: 800; color: white; background: transparent; }
QLabel#bannerSub { font-size: 12px; color: rgba(255,255,255,0.85); background: transparent; }
QLabel#countBadge {
    background: rgba(255,255,255,0.22); color: white; border-radius: 14px;
    padding: 6px 16px; font-weight: 700; font-size: 14px;
}

QFrame#card {
    background: rgba(30, 41, 59, 0.92);
    border: 1px solid #334155;
    border-radius: 14px;
}
QLabel#cardTitle { font-size: 14px; font-weight: 700; color: #93c5fd; background: transparent; }
QLabel#fieldLabel { color: #94a3b8; font-weight: 600; background: transparent; }
QLabel#indexName { font-size: 15px; font-weight: 700; color: #f1f5f9; background: transparent; }
QLabel#indexPrice { font-size: 34px; font-weight: 800; background: transparent; }
QLabel#indexChange { font-size: 16px; font-weight: 700; background: transparent; }
QLabel#statName { color: #94a3b8; background: transparent; }
QLabel#statValue { font-size: 14px; font-weight: 700; color: #f1f5f9; background: transparent; }
QLabel#marketBadge {
    background: #334155; color: #e2e8f0; border-radius: 10px;
    padding: 3px 10px; font-weight: 700; font-size: 12px;
}

QLineEdit {
    background: #0f172a; border: 2px solid #334155; border-radius: 10px;
    padding: 8px 12px; color: #f1f5f9; selection-background-color: #2563eb;
}
QLineEdit:focus { border: 2px solid #60a5fa; }
QCheckBox { background: transparent; font-weight: 600; spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 5px;
    border: 2px solid #475569; background: #0f172a;
}
QCheckBox::indicator:checked { background: #3b82f6; border: 2px solid #60a5fa; }

QPushButton {
    border: none; border-radius: 10px; padding: 9px 18px;
    font-weight: 700; color: white;
}
QPushButton:disabled { background: #334155; color: #64748b; }
QPushButton#loadButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
}
QPushButton#loadButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #a78bfa);
}
QPushButton#loadButton:disabled { background: #334155; }
QPushButton#excelButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
}
QPushButton#excelButton:hover { background: #34d399; }
QPushButton#excelButton:disabled { background: #334155; }
QPushButton#csvButton { background: #0ea5e9; }
QPushButton#csvButton:hover { background: #38bdf8; }
QPushButton#csvButton:disabled { background: #334155; }

QTableWidget {
    background: #0f172a; alternate-background-color: #162036;
    border: none; border-radius: 10px; gridline-color: transparent;
    selection-background-color: #1d4ed8; selection-color: white;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #1e293b; }
QHeaderView::section {
    background: #1e293b; color: #93c5fd; font-weight: 700;
    border: none; border-bottom: 2px solid #3b82f6; padding: 8px;
}
QTableCornerButton::section { background: #1e293b; border: none; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #475569; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #60a5fa; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #475569; border-radius: 5px; min-width: 30px; }

QProgressBar {
    background: #1e293b; border: none; border-radius: 8px; height: 16px;
    text-align: center; color: white; font-weight: 700; font-size: 11px;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #ec4899);
}
QLabel#statusLabel { color: #94a3b8; background: transparent; }
"""


def resource_path(name: str) -> str:
    """PyInstaller로 묶인 exe에서는 임시 폴더(sys._MEIPASS)에서, 아니면 스크립트 폴더에서 파일을 찾는다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def add_shadow(widget: QWidget, blur: int = 24, alpha: int = 120) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


def make_card(title: str) -> tuple[QFrame, QVBoxLayout]:
    """둥근 모서리와 그림자가 있는 카드 패널을 만든다."""
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 14)
    layout.setSpacing(10)
    label = QLabel(title)
    label.setObjectName("cardTitle")
    layout.addWidget(label)
    add_shadow(card)
    return card, layout


def change_color(value) -> str:
    if not isinstance(value, (int, float)) or value == 0:
        return FLAT_COLOR
    return UP_COLOR if value > 0 else DOWN_COLOR


def format_number(value) -> str:
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


class NumericItem(QTableWidgetItem):
    """'1,234' 처럼 표시하면서도 열 정렬은 숫자 크기로 되도록 하는 표 셀."""

    def __init__(self, value):
        super().__init__(format_number(value))
        self.value = value
        self.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def __lt__(self, other):
        if isinstance(other, NumericItem):
            a = self.value if isinstance(self.value, (int, float)) else float("-inf")
            b = other.value if isinstance(other.value, (int, float)) else float("-inf")
            return a < b
        return super().__lt__(other)


class CrawlWorker(QThread):
    """네트워크 요청이 GUI를 멈추지 않도록 별도 스레드에서 크롤링한다."""

    index_ready = pyqtSignal(dict)        # 지수 시세
    page_ready = pyqtSignal(int, list)    # (페이지 번호, 구성종목 목록)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            self.index_ready.emit(fetch_index())
            page = 1
            while not self.isInterruptionRequested():
                rows = fetch_stocks_page(page)
                self.page_ready.emit(page, rows)
                if len(rows) < PAGE_SIZE:
                    break
                page += 1
                time.sleep(0.3)  # 서버에 부담을 주지 않도록 요청 간격을 둔다
        except (requests.RequestException, KeyError, ValueError) as e:
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📈 코스피200 크롤러")
        self.resize(1280, 820)

        self.index: dict = {}
        self.stocks: list[dict] = []
        self.pending: list[dict] = []  # 불러오는 중인 구성종목 (다 받은 뒤 표에 한 번에 반영)
        self.worker: CrawlWorker | None = None

        # 상단 배너: 앱 제목 + 종목 수 배지
        banner = QFrame()
        banner.setObjectName("banner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 16, 24, 16)
        title_box = QVBoxLayout()
        title_label = QLabel("📈  KOSPI 200 CRAWLER")
        title_label.setObjectName("bannerTitle")
        sub_label = QLabel("네이버페이 증권의 코스피200 지수와 구성종목 시세를 모으고, 엑셀로 저장하세요")
        sub_label.setObjectName("bannerSub")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        self.count_badge = QLabel("0 종목")
        self.count_badge.setObjectName("countBadge")
        banner_layout.addLayout(title_box, 1)
        banner_layout.addWidget(self.count_badge)
        add_shadow(banner, blur=30, alpha=150)

        # 지수 카드: 현재가 / 전일비 + 시가·고가·저가·거래량·거래대금
        index_card, index_layout = make_card("📊  코스피200 지수")
        self.index_name = QLabel("코스피 200")
        self.index_name.setObjectName("indexName")
        self.market_badge = QLabel("-")
        self.market_badge.setObjectName("marketBadge")
        self.index_price = QLabel("-")
        self.index_price.setObjectName("indexPrice")
        self.index_change = QLabel("")
        self.index_change.setObjectName("indexChange")
        self.index_time = QLabel("")
        self.index_time.setObjectName("statName")

        name_row = QHBoxLayout()
        name_row.addWidget(self.index_name)
        name_row.addWidget(self.market_badge)
        name_row.addStretch(1)
        price_box = QVBoxLayout()
        price_box.addLayout(name_row)
        price_box.addWidget(self.index_price)
        price_box.addWidget(self.index_change)
        price_box.addWidget(self.index_time)

        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(28)
        stats_grid.setVerticalSpacing(6)
        self.stat_labels: dict[str, QLabel] = {}
        for i, key in enumerate(["시가", "고가", "저가", "거래량", "거래대금"]):
            name = QLabel(key)
            name.setObjectName("statName")
            value = QLabel("-")
            value.setObjectName("statValue")
            stats_grid.addWidget(name, 0, i)
            stats_grid.addWidget(value, 1, i)
            self.stat_labels[key] = value

        index_row = QHBoxLayout()
        index_row.addLayout(price_box, 1)
        index_row.addLayout(stats_grid, 2)
        index_layout.addLayout(index_row)

        # 조작 카드: 검색, 불러오기, 자동 갱신, 저장
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  종목명 또는 종목코드로 검색")
        self.search_edit.textChanged.connect(self.apply_filter)

        self.load_button = self.make_button("🔄  불러오기", "loadButton", self.start_crawl)
        self.auto_check = QCheckBox(f"자동 갱신 ({AUTO_REFRESH_MS // 1000}초)")
        self.auto_check.toggled.connect(self.toggle_auto_refresh)
        self.excel_button = self.make_button("📊  엑셀 저장", "excelButton", self.save_excel_file)
        self.csv_button = self.make_button("📄  CSV 저장", "csvButton", self.save_csv_file)
        self.excel_button.setEnabled(False)
        self.csv_button.setEnabled(False)

        control_card, control_layout = make_card("구성종목")
        control_row = QHBoxLayout()
        control_row.setSpacing(10)
        search_label = QLabel("검색")
        search_label.setObjectName("fieldLabel")
        control_row.addWidget(search_label)
        control_row.addWidget(self.search_edit, 1)
        control_row.addWidget(self.load_button)
        control_row.addWidget(self.auto_check)
        control_row.addSpacing(16)
        control_row.addWidget(self.excel_button)
        control_row.addWidget(self.csv_button)
        control_layout.addLayout(control_row)

        # 구성종목 표
        self.table = QTableWidget(0, len(STOCK_LABELS) + 1)
        self.table.setHorizontalHeaderLabels(["순위"] + STOCK_LABELS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # 정렬을 켜면 Qt 기본값(0번 열 내림차순)으로 정렬되므로, 처음에는 순위 오름차순으로 맞춘다.
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.open_in_browser)
        control_layout.addWidget(self.table, 1)

        # 하단: 진행 상황
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.status_label = QLabel("✨ 준비 완료 — [불러오기]를 눌러 코스피200 데이터를 가져오세요")
        self.status_label.setObjectName("statusLabel")

        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)
        layout.addWidget(banner)
        layout.addWidget(index_card)
        layout.addWidget(control_card, 1)
        layout.addLayout(bottom)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(AUTO_REFRESH_MS)
        self.refresh_timer.timeout.connect(self.start_crawl)

        # 앱을 켜면 바로 한 번 불러온다.
        QTimer.singleShot(0, self.start_crawl)

    def make_button(self, text: str, name: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    # --- 크롤링 제어 -------------------------------------------------------

    def start_crawl(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.pending = []
        self.progress.setRange(0, 0)  # 전체 페이지 수를 모르므로 '진행 중' 애니메이션으로 표시
        self.status_label.setText("🔎 코스피200 지수 시세를 가져오는 중...")
        self.set_running(True)

        self.worker = CrawlWorker()
        self.worker.index_ready.connect(self.on_index_ready)
        self.worker.page_ready.connect(self.on_page_ready)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def toggle_auto_refresh(self, checked: bool) -> None:
        if checked:
            self.refresh_timer.start()
            self.start_crawl()
        else:
            self.refresh_timer.stop()

    def set_running(self, running: bool) -> None:
        has_results = not running and bool(self.stocks)
        self.load_button.setEnabled(not running)
        self.excel_button.setEnabled(has_results)
        self.csv_button.setEnabled(has_results)

    # --- 워커 시그널 처리 ---------------------------------------------------

    def on_index_ready(self, index: dict) -> None:
        self.index = index
        color = change_color(index["전일비"])
        arrow = "▲" if color == UP_COLOR else "▼" if color == DOWN_COLOR else "−"

        self.index_name.setText(index["지수명"])
        self.market_badge.setText(MARKET_STATUS.get(index["장상태"], index["장상태"]))
        self.index_price.setText(format_number(index["현재가"]))
        self.index_price.setStyleSheet(f"color: {color};")
        self.index_change.setText(
            f"{arrow} {format_number(abs(index['전일비']))}   ({index['등락률(%)']:+.2f}%)"
        )
        self.index_change.setStyleSheet(f"color: {color};")
        self.index_time.setText(f"🕒 {index['기준시각'][:19].replace('T', ' ')} 기준")
        for key, label in self.stat_labels.items():
            label.setText(format_number(index[key]))

    def on_page_ready(self, page: int, rows: list) -> None:
        self.pending.extend(rows)
        self.status_label.setText(f"📥 구성종목 {page}페이지 수집 완료 (누적 {len(self.pending)}종목)")

    def on_failed(self, message: str) -> None:
        self.status_label.setText(f"⚠️ 불러오기 실패: {message}")
        if not self.refresh_timer.isActive():
            QMessageBox.critical(self, "오류", f"데이터를 가져오지 못했습니다.\n{message}")

    def on_finished(self) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        if self.pending:
            self.stocks = self.pending
            self.fill_table()
            self.status_label.setText(
                f"✅ 완료: 구성종목 {len(self.stocks)}개를 불러왔습니다 ({time.strftime('%H:%M:%S')})"
            )
        self.set_running(False)

    # --- 표 / 저장 ----------------------------------------------------------

    def fill_table(self) -> None:
        bold = QFont()
        bold.setBold(True)
        selected_code = self.selected_code()

        self.table.setSortingEnabled(False)  # 행을 채우는 동안 정렬이 끼어들지 않도록
        self.table.setRowCount(len(self.stocks))
        for row, stock in enumerate(self.stocks):
            color = QColor(change_color(stock["전일비"]))
            items = [NumericItem(row + 1)]
            for label, field in STOCK_COLUMNS:
                value = stock[label]
                if field == "localTradedAt":
                    item = QTableWidgetItem(str(value)[11:19])
                    item.setForeground(QColor(FLAT_COLOR))
                elif field in TEXT_FIELDS:
                    item = QTableWidgetItem(str(value))
                else:
                    item = NumericItem(value)
                items.append(item)

            items[1].setForeground(QColor(FLAT_COLOR))
            items[2].setFont(bold)
            items[2].setData(Qt.ItemDataRole.UserRole, stock["종목코드"])
            for col in (3, 4, 5):  # 현재가, 전일비, 등락률
                items[col].setForeground(color)
            items[5].setText(f"{stock['등락률(%)']:+.2f}" if isinstance(stock["등락률(%)"], float) else items[5].text())
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

        self.count_badge.setText(f"{len(self.stocks)} 종목")
        self.apply_filter()
        self.restore_selection(selected_code)

    def selected_code(self) -> str:
        rows = self.table.selectionModel().selectedRows()
        return self.table.item(rows[0].row(), 1).text() if rows else ""

    def restore_selection(self, code: str) -> None:
        # 자동 갱신 후에도 보고 있던 종목이 선택된 채로 남도록 한다.
        if not code:
            return
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == code:
                self.table.selectRow(row)
                return

    def apply_filter(self) -> None:
        keyword = self.search_edit.text().strip().lower()
        for row in range(self.table.rowCount()):
            code = self.table.item(row, 1).text()
            name = self.table.item(row, 2).text().lower()
            self.table.setRowHidden(row, bool(keyword) and keyword not in name and keyword not in code)

    def open_in_browser(self, row: int, _column: int) -> None:
        code = self.table.item(row, 1).text()
        QDesktopServices.openUrl(QUrl(STOCK_PAGE_URL.format(code=code)))

    def default_filename(self, ext: str) -> str:
        return f"kospi200_{time.strftime('%Y%m%d_%H%M')}.{ext}"

    def save_excel_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀로 저장", self.default_filename("xlsx"), "엑셀 파일 (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self.save_with(lambda: save_excel(self.index, self.stocks, path), path)

    def save_csv_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", self.default_filename("csv"), "CSV 파일 (*.csv)"
        )
        if not path:
            return
        self.save_with(lambda: save_csv(self.stocks, path), path)

    def save_with(self, save_func, path: str) -> None:
        try:
            save_func()
        except OSError as e:
            # 엑셀에서 같은 파일을 열어 둔 경우 PermissionError가 난다.
            QMessageBox.critical(self, "오류", f"저장하지 못했습니다. 파일이 열려 있는지 확인하세요.\n{e}")
            return
        self.status_label.setText(f"💾 저장 완료: {path}")
        QMessageBox.information(self, "저장 완료", f"{len(self.stocks)}개 종목을 저장했습니다.\n{path}")

    def closeEvent(self, event) -> None:
        # 창을 닫을 때 실행 중인 스레드를 정리한다.
        self.refresh_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(5000)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 스타일시트가 모든 OS에서 같은 모양으로 적용되도록
    app.setStyleSheet(STYLE_SHEET)
    icon_path = resource_path("app.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
