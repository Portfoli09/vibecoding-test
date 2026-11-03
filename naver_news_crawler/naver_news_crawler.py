"""
네이버 검색 결과에서 신문기사 내용을 크롤링하는 GUI 앱 (PyQt6 + requests + BeautifulSoup4)

동작 순서
1. 검색어를 입력하고 [크롤링 시작]을 누르면 네이버 검색 결과 페이지를 가져온다.
2. 페이지 안의 '네이버뉴스' 기사 링크(n.news.naver.com/mnews/article/...)를 모은다.
3. 각 기사 페이지에 들어가 제목 / 언론사 / 작성일 / 본문을 추출해 표에 추가한다.
4. 표에서 기사를 선택하면 본문이 오른쪽에 표시되고, 결과를 엑셀(.xlsx) 또는 CSV로 저장할 수 있다.

설치: pip install PyQt6 requests beautifulsoup4 openpyxl
"""

import csv
import html
import os
import re
import sys
import time
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

SEARCH_BASE_URL = "https://search.naver.com/search.naver"

# 콤보박스 표시 이름 -> 네이버 검색의 where 파라미터
SEARCH_TYPES = {
    "뉴스검색 (기사 수 많음)": "news",
    "통합검색 (기사 수 적음)": "nexearch",
}

HEADERS = {
    # 브라우저처럼 보이도록 User-Agent를 지정하지 않으면 차단되거나 빈 페이지가 올 수 있다.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Referer": "https://www.naver.com/",
}

# 네이버뉴스 기사 주소 형식: https://n.news.naver.com/mnews/article/{언론사ID}/{기사ID}
ARTICLE_LINK_RE = re.compile(r"https://n\.news\.naver\.com/mnews/article/\d+/\d+")

FIELDS = ["title", "press", "date", "url", "body"]
FIELD_LABELS = ["제목", "언론사", "작성일", "URL", "본문"]


# ---------------------------------------------------------------------------
# 크롤링 로직
# ---------------------------------------------------------------------------

def build_search_url(query: str, where: str) -> str:
    params = {"where": where, "sm": "top_hty", "fbm": "0", "ie": "utf8", "query": query}
    return f"{SEARCH_BASE_URL}?{urlencode(params)}"


def get_soup(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def collect_article_links(search_url: str) -> list[str]:
    """검색 결과 페이지에서 네이버뉴스 기사 링크를 중복 없이 순서대로 수집한다."""
    soup = get_soup(search_url)
    links = []
    for a in soup.find_all("a", href=True):
        match = ARTICLE_LINK_RE.match(a["href"])
        if match and match.group() not in links:
            links.append(match.group())

    # 일부 기사 링크는 <a> 태그가 아니라 스크립트(JSON) 안에 들어 있으므로 원문 전체에서도 찾는다.
    for link in ARTICLE_LINK_RE.findall(str(soup)):
        if link not in links:
            links.append(link)
    return links


def text_of(soup: BeautifulSoup, selector: str) -> str:
    tag = soup.select_one(selector)
    return tag.get_text(" ", strip=True) if tag else ""


def parse_article(url: str) -> dict:
    """네이버뉴스 기사 페이지에서 제목, 언론사, 작성일, 본문을 추출한다."""
    soup = get_soup(url)

    title = text_of(soup, "h2#title_area") or text_of(soup, "h2.media_end_head_headline")

    press_tag = soup.select_one("a.media_end_head_top_logo img")
    press = press_tag.get("alt", "") if press_tag else ""

    date_tag = soup.select_one("span.media_end_head_info_datestamp_time")
    date = date_tag.get("data-date-time", date_tag.get_text(strip=True)) if date_tag else ""

    body_tag = soup.select_one("article#dic_area") or soup.select_one("#dic_area")
    body = ""
    if body_tag:
        # 사진 설명, 기자 정보 등 본문이 아닌 요소 제거
        for junk in body_tag.select("span.end_photo_org, em.img_desc, div.vod_player_wrap, script, style"):
            junk.decompose()
        body = body_tag.get_text("\n", strip=True)

    return {"title": title, "press": press, "date": date, "url": url, "body": body}


def save_csv(articles: list[dict], path: str) -> None:
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않도록 BOM 포함
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(articles)


def save_excel(articles: list[dict], path: str, query: str = "") -> None:
    """기사 목록을 서식이 적용된 엑셀(.xlsx) 파일로 저장한다."""
    wb = Workbook()
    ws = wb.active
    ws.title = "뉴스"

    header_fill = PatternFill("solid", start_color="1F2A44")
    header_font = Font(name="맑은 고딕", bold=True, color="FFFFFF", size=11)
    stripe_fill = PatternFill("solid", start_color="F3F6FB")
    thin = Side(style="thin", color="D0D7E2")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    body_font = Font(name="맑은 고딕", size=10)

    ws.append(["No."] + FIELD_LABELS)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    ws.row_dimensions[1].height = 24

    for i, article in enumerate(articles, 1):
        # 엑셀 셀 하나에는 최대 32,767자까지만 들어간다.
        ws.append([i] + [article[key][:32000] for key in FIELDS])
        row = ws.max_row
        for cell in ws[row]:
            cell.font = body_font
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column in (2, 6))
            if i % 2 == 0:
                cell.fill = stripe_fill
        ws.cell(row, 1).alignment = Alignment(horizontal="center", vertical="top")

        url_cell = ws.cell(row, 5)
        url_cell.hyperlink = article["url"]
        url_cell.font = Font(name="맑은 고딕", size=10, color="1A73E8", underline="single")
        ws.row_dimensions[row].height = 90

    for col, width in zip("ABCDEF", [6, 50, 14, 20, 45, 100]):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    if query:
        wb.properties.title = f"네이버 뉴스 - {query}"
    wb.save(path)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

STYLE_SHEET = """
QMainWindow, QWidget#central {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1e1b4b);
}
QWidget { color: #e2e8f0; font-family: "맑은 고딕", "Malgun Gothic"; font-size: 13px; }

QFrame#banner {
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:0.5 #db2777, stop:1 #f97316);
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
QLabel#cardTitle { font-size: 14px; font-weight: 700; color: #c4b5fd; background: transparent; }
QLabel#fieldLabel { color: #94a3b8; font-weight: 600; background: transparent; }

QLineEdit, QComboBox {
    background: #0f172a; border: 2px solid #334155; border-radius: 10px;
    padding: 8px 12px; color: #f1f5f9; selection-background-color: #7c3aed;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid #a855f7; }
QLineEdit:disabled, QComboBox:disabled { color: #64748b; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox QAbstractItemView {
    background: #1e293b; border: 1px solid #475569; color: #e2e8f0;
    selection-background-color: #7c3aed;
}

QPushButton {
    border: none; border-radius: 10px; padding: 9px 18px;
    font-weight: 700; color: white;
}
QPushButton:disabled { background: #334155; color: #64748b; }
QPushButton#startButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #ec4899);
}
QPushButton#startButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a78bfa, stop:1 #f472b6);
}
QPushButton#stopButton { background: #ef4444; }
QPushButton#stopButton:hover { background: #f87171; }
QPushButton#stopButton:disabled { background: #334155; }
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
    selection-background-color: #6d28d9; selection-color: white;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #1e293b; }
QHeaderView::section {
    background: #1e293b; color: #c4b5fd; font-weight: 700;
    border: none; border-bottom: 2px solid #7c3aed; padding: 8px;
}
QTableCornerButton::section { background: #1e293b; border: none; }

QTextBrowser {
    background: #0f172a; border: none; border-radius: 10px; padding: 10px;
}

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #475569; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #a855f7; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #475569; border-radius: 5px; min-width: 30px; }

QSplitter::handle { background: transparent; width: 10px; }

QProgressBar {
    background: #1e293b; border: none; border-radius: 8px; height: 16px;
    text-align: center; color: white; font-weight: 700; font-size: 11px;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:0.5 #ec4899, stop:1 #f97316);
}
QLabel#statusLabel { color: #94a3b8; background: transparent; }
"""

# 기사 본문 보기 창에 쓰는 HTML 템플릿
ARTICLE_HTML = """
<div style="font-family:'맑은 고딕'; line-height:170%;">
  <span style="background:#7c3aed; color:white; padding:3px 10px; font-weight:bold;">&nbsp;{press}&nbsp;</span>
  &nbsp;<span style="color:#94a3b8;">🕒 {date}</span>
  <h2 style="color:#f8fafc; margin-top:12px;">{title}</h2>
  <p><a href="{url}" style="color:#f472b6;">🔗 원문 기사 열기</a></p>
  <hr style="border:0; background:#334155; height:1px;">
  <div style="color:#cbd5e1; font-size:14px;">{body}</div>
</div>
"""

EMPTY_HTML = """
<div style="text-align:center; color:#64748b; margin-top:80px; font-size:15px;">
  <p style="font-size:42px;">📰</p>
  <p>왼쪽 목록에서 기사를 선택하면<br>본문이 여기에 표시됩니다.</p>
  <p style="font-size:12px;">더블클릭하면 브라우저에서 원문이 열립니다.</p>
</div>
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


class CrawlWorker(QThread):
    """네트워크 요청이 GUI를 멈추지 않도록 별도 스레드에서 크롤링한다."""

    links_found = pyqtSignal(int)          # 수집한 링크 수
    article_ready = pyqtSignal(int, dict)  # (진행 번호, 기사)
    article_failed = pyqtSignal(str, str)  # (링크, 오류 메시지)
    failed = pyqtSignal(str)               # 검색 페이지 자체를 못 가져온 경우

    def __init__(self, search_url: str):
        super().__init__()
        self.search_url = search_url

    def run(self) -> None:
        try:
            links = collect_article_links(self.search_url)
        except requests.RequestException as e:
            self.failed.emit(str(e))
            return

        self.links_found.emit(len(links))
        for i, link in enumerate(links, 1):
            if self.isInterruptionRequested():
                return
            try:
                self.article_ready.emit(i, parse_article(link))
            except requests.RequestException as e:
                self.article_failed.emit(link, str(e))
            time.sleep(0.5)  # 서버에 부담을 주지 않도록 요청 간격을 둔다


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📰 네이버 뉴스 크롤러")
        self.resize(1280, 800)

        self.articles: list[dict] = []
        self.worker: CrawlWorker | None = None
        self.last_query = ""

        # 상단 배너: 앱 제목 + 수집 기사 수 배지
        banner = QFrame()
        banner.setObjectName("banner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 16, 24, 16)
        title_box = QVBoxLayout()
        title_label = QLabel("📰  NAVER NEWS CRAWLER")
        title_label.setObjectName("bannerTitle")
        sub_label = QLabel("검색어 하나로 네이버 뉴스 기사를 모으고, 읽고, 엑셀로 저장하세요")
        sub_label.setObjectName("bannerSub")
        title_box.addWidget(title_label)
        title_box.addWidget(sub_label)
        self.count_badge = QLabel("0 건")
        self.count_badge.setObjectName("countBadge")
        banner_layout.addLayout(title_box, 1)
        banner_layout.addWidget(self.count_badge)
        add_shadow(banner, blur=30, alpha=150)

        # 검색 카드: 검색어, 검색 종류, 버튼
        self.query_edit = QLineEdit("반도체")
        self.query_edit.setPlaceholderText("🔍  검색어를 입력하세요")
        self.query_edit.returnPressed.connect(self.start_crawl)

        self.type_combo = QComboBox()
        self.type_combo.addItems(SEARCH_TYPES.keys())

        self.start_button = self.make_button("🚀  크롤링 시작", "startButton", self.start_crawl)
        self.stop_button = self.make_button("⏹  중지", "stopButton", self.stop_crawl)
        self.excel_button = self.make_button("📊  엑셀 저장", "excelButton", self.save_excel_file)
        self.csv_button = self.make_button("📄  CSV 저장", "csvButton", self.save_csv_file)
        self.stop_button.setEnabled(False)
        self.excel_button.setEnabled(False)
        self.csv_button.setEnabled(False)

        search_card, search_layout = make_card("검색 설정")
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        query_label = QLabel("검색어")
        query_label.setObjectName("fieldLabel")
        search_row.addWidget(query_label)
        search_row.addWidget(self.query_edit, 1)
        search_row.addWidget(self.type_combo)
        search_row.addWidget(self.start_button)
        search_row.addWidget(self.stop_button)
        search_row.addSpacing(16)
        search_row.addWidget(self.excel_button)
        search_row.addWidget(self.csv_button)
        search_layout.addLayout(search_row)

        # 기사 목록 카드
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["제목", "언론사", "작성일"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self.show_selected_article)
        self.table.cellDoubleClicked.connect(self.open_in_browser)

        list_card, list_layout = make_card("📋  기사 목록")
        list_layout.addWidget(self.table)

        # 본문 보기 카드
        self.body_view = QTextBrowser()
        self.body_view.setOpenExternalLinks(True)
        self.body_view.setHtml(EMPTY_HTML)

        body_card, body_layout = make_card("📖  기사 본문")
        body_layout.addWidget(self.body_view)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(list_card)
        splitter.addWidget(body_card)
        splitter.setSizes([700, 560])

        # 하단: 진행 상황
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.status_label = QLabel("✨ 준비 완료 — 검색어를 입력하고 크롤링을 시작하세요")
        self.status_label.setObjectName("statusLabel")

        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)
        layout.addWidget(banner)
        layout.addWidget(search_card)
        layout.addWidget(splitter, 1)
        layout.addLayout(bottom)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)

    def make_button(self, text: str, name: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    # --- 크롤링 제어 -------------------------------------------------------

    def start_crawl(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
            return
        if self.worker and self.worker.isRunning():
            return

        self.last_query = query
        self.articles.clear()
        self.table.setRowCount(0)
        self.body_view.setHtml(EMPTY_HTML)
        self.count_badge.setText("0 건")
        self.progress.setValue(0)
        self.status_label.setText(f"🔎 '{query}' 검색 결과에서 기사 링크를 찾는 중...")
        self.set_running(True)

        url = build_search_url(query, SEARCH_TYPES[self.type_combo.currentText()])
        self.worker = CrawlWorker(url)
        self.worker.links_found.connect(self.on_links_found)
        self.worker.article_ready.connect(self.on_article_ready)
        self.worker.article_failed.connect(self.on_article_failed)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def stop_crawl(self) -> None:
        if self.worker:
            self.worker.requestInterruption()
            self.status_label.setText("⏳ 중지하는 중...")

    def set_running(self, running: bool) -> None:
        has_results = not running and bool(self.articles)
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.query_edit.setEnabled(not running)
        self.type_combo.setEnabled(not running)
        self.excel_button.setEnabled(has_results)
        self.csv_button.setEnabled(has_results)

    # --- 워커 시그널 처리 ---------------------------------------------------

    def on_links_found(self, count: int) -> None:
        self.progress.setMaximum(max(count, 1))
        self.status_label.setText(f"📥 기사 링크 {count}개 발견, 본문 수집 중...")

    def on_article_ready(self, index: int, article: dict) -> None:
        self.articles.append(article)
        row = self.table.rowCount()
        self.table.insertRow(row)

        title_item = QTableWidgetItem(article["title"])
        title_item.setToolTip(article["title"])
        press_item = QTableWidgetItem(article["press"])
        press_item.setForeground(QColor("#f472b6"))
        bold = QFont()
        bold.setBold(True)
        press_item.setFont(bold)
        date_item = QTableWidgetItem(article["date"])
        date_item.setForeground(QColor("#94a3b8"))

        for col, item in enumerate([title_item, press_item, date_item]):
            self.table.setItem(row, col, item)

        self.count_badge.setText(f"{len(self.articles)} 건")
        self.progress.setValue(index)
        self.status_label.setText(f"📥 {index}/{self.progress.maximum()} 수집 중...")

    def on_article_failed(self, link: str, message: str) -> None:
        self.progress.setValue(self.progress.value() + 1)
        self.status_label.setText(f"⚠️ 실패: {link} ({message})")

    def on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "오류", f"검색 페이지를 가져오지 못했습니다.\n{message}")

    def on_finished(self) -> None:
        self.set_running(False)
        self.status_label.setText(f"✅ 완료: 총 {len(self.articles)}개 기사를 수집했습니다")

    # --- 결과 보기 / 저장 ---------------------------------------------------

    def show_selected_article(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        article = self.articles[rows[0].row()]
        paragraphs = "".join(
            f"<p>{html.escape(line)}</p>" for line in article["body"].splitlines() if line.strip()
        )
        self.body_view.setHtml(
            ARTICLE_HTML.format(
                press=html.escape(article["press"] or "언론사"),
                date=html.escape(article["date"]),
                title=html.escape(article["title"]),
                url=html.escape(article["url"]),
                body=paragraphs or "<p>(본문을 찾지 못했습니다)</p>",
            )
        )

    def open_in_browser(self, row: int, _column: int) -> None:
        QDesktopServices.openUrl(QUrl(self.articles[row]["url"]))

    def default_filename(self, ext: str) -> str:
        return f"naver_news_{self.last_query or 'result'}_{time.strftime('%Y%m%d_%H%M')}.{ext}"

    def save_excel_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀로 저장", self.default_filename("xlsx"), "엑셀 파일 (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        self.save_with(lambda: save_excel(self.articles, path, self.last_query), path)

    def save_csv_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", self.default_filename("csv"), "CSV 파일 (*.csv)"
        )
        if not path:
            return
        self.save_with(lambda: save_csv(self.articles, path), path)

    def save_with(self, save_func, path: str) -> None:
        try:
            save_func()
        except OSError as e:
            # 엑셀에서 같은 파일을 열어 둔 경우 PermissionError가 난다.
            QMessageBox.critical(self, "오류", f"저장하지 못했습니다. 파일이 열려 있는지 확인하세요.\n{e}")
            return
        self.status_label.setText(f"💾 저장 완료: {path}")
        QMessageBox.information(self, "저장 완료", f"{len(self.articles)}개 기사를 저장했습니다.\n{path}")

    def closeEvent(self, event) -> None:
        # 창을 닫을 때 실행 중인 스레드를 정리한다.
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
