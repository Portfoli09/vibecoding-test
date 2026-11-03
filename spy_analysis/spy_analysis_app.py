"""
SPY(S&P500 ETF) 과거 데이터 분석 GUI 앱 (PyQt6 + Pandas + Matplotlib)

동작 순서
1. [CSV 열기]로 인베스팅닷컴 형식의 'SPY 과거 데이터.csv'를 고른다. (작업 폴더에 있으면 시작할 때 자동으로 연다)
2. 파일을 읽으면 바로 클렌징한다. 과정은 [클렌징 로그] 탭에서 볼 수 있다.
3. 시작일·종료일을 정하고 [분석 실행]을 누르면 그 기간으로 분석해서
   요약 카드 / 종가 차트 / 대시보드 / 연도별 표 / 분석 리포트 / 정제 데이터 탭이 채워진다.
4. 지금 보고 있는 차트는 PNG로, 정제한 데이터는 CSV로 저장할 수 있다.

분석 로직은 spy_analysis.py에 있고, 이 파일은 화면만 담당한다.
설치: pip install -r requirements.txt
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import pandas as pd
from PyQt6.QtCore import QAbstractTableModel, QDate, QModelIndex, Qt
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDateEdit,
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
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import spy_analysis as sa

DEFAULT_START = QDate(2000, 1, 1)
DEFAULT_END = QDate(2019, 12, 31)

# 미국 시장 관례에 맞춰 상승은 초록, 하락은 빨강 (차트 색과 같다)
UP_COLOR = "#34d399"
DOWN_COLOR = "#f87171"
FLAT_COLOR = "#94a3b8"

# 앱 배경에 맞춘 matplotlib 어두운 테마
matplotlib.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "figure.facecolor": "#0f172a",
    "axes.facecolor": "#0f172a",
    "savefig.facecolor": "#0f172a",
    "axes.edgecolor": "#475569",
    "axes.labelcolor": "#cbd5e1",
    "axes.titlecolor": "#f1f5f9",
    "text.color": "#e2e8f0",
    "xtick.color": "#94a3b8",
    "ytick.color": "#94a3b8",
    "grid.color": "#334155",
    "legend.facecolor": "#1e293b",
    "legend.edgecolor": "#334155",
})


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
QLabel#statName { color: #94a3b8; font-weight: 600; background: transparent; }
QLabel#statValue { font-size: 22px; font-weight: 800; color: #f1f5f9; background: transparent; }
QLabel#statSub { color: #64748b; font-size: 11px; background: transparent; }

QLineEdit, QDateEdit {
    background: #0f172a; border: 2px solid #334155; border-radius: 10px;
    padding: 7px 12px; color: #f1f5f9; selection-background-color: #2563eb;
}
QLineEdit:focus, QDateEdit:focus { border: 2px solid #60a5fa; }
QDateEdit::drop-down { border: none; width: 24px; }
QCalendarWidget QWidget { background: #1e293b; color: #e2e8f0; }
QCalendarWidget QAbstractItemView { selection-background-color: #2563eb; }

QPushButton {
    border: none; border-radius: 10px; padding: 9px 18px;
    font-weight: 700; color: white;
}
QPushButton:disabled { background: #334155; color: #64748b; }
QPushButton#openButton { background: #475569; }
QPushButton#openButton:hover { background: #64748b; }
QPushButton#runButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);
}
QPushButton#runButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #a78bfa);
}
QPushButton#runButton:disabled { background: #334155; }
QPushButton#pngButton { background: #0ea5e9; }
QPushButton#pngButton:hover { background: #38bdf8; }
QPushButton#pngButton:disabled { background: #334155; }
QPushButton#csvButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #10b981);
}
QPushButton#csvButton:hover { background: #34d399; }
QPushButton#csvButton:disabled { background: #334155; }

QTabWidget::pane {
    background: rgba(30, 41, 59, 0.92); border: 1px solid #334155;
    border-radius: 14px; top: -1px;
}
QTabBar::tab {
    background: transparent; color: #94a3b8; font-weight: 700;
    padding: 9px 18px; margin-right: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px;
}
QTabBar::tab:selected { background: #1e293b; color: #93c5fd; border-bottom: 3px solid #3b82f6; }
QTabBar::tab:hover:!selected { color: #e2e8f0; }

QToolBar { background: #cbd5e1; border: none; border-radius: 8px; padding: 2px; }
QToolBar QLabel { color: #0f172a; background: transparent; }

QPlainTextEdit {
    background: #0f172a; border: none; border-radius: 10px; padding: 8px;
    color: #e2e8f0; font-family: "D2Coding", "Consolas", "맑은 고딕"; font-size: 12px;
}
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }

QTableWidget, QTableView {
    background: #0f172a; alternate-background-color: #162036;
    border: none; border-radius: 10px; gridline-color: transparent;
    selection-background-color: #1d4ed8; selection-color: white;
}
QTableWidget::item, QTableView::item { padding: 6px; border-bottom: 1px solid #1e293b; }
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

QLabel#statusLabel { color: #94a3b8; background: transparent; }
"""


def resource_path(name: str) -> str:
    """PyInstaller로 묶인 exe에서는 임시 폴더(sys._MEIPASS)에서, 아니면 스크립트 폴더에서 파일을 찾는다."""
    base = getattr(sys, "_MEIPASS", str(Path(__file__).resolve().parent))
    return str(Path(base) / name)


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
    if title:
        label = QLabel(title)
        label.setObjectName("cardTitle")
        layout.addWidget(label)
    add_shadow(card)
    return card, layout


def sign_color(value) -> str:
    if value is None or pd.isna(value) or value == 0:
        return FLAT_COLOR
    return UP_COLOR if value > 0 else DOWN_COLOR


def capture(func, *args):
    """print로 리포트를 쓰는 분석 함수의 출력을 문자열로 받아 온다."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        result = func(*args)
    return result, buf.getvalue().strip()


class StatCard(QFrame):
    """요약 지표 하나(이름 / 큰 값 / 보조 설명)를 보여 주는 카드."""

    def __init__(self, name: str):
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        title = QLabel(name)
        title.setObjectName("statName")
        self.value = QLabel("-")
        self.value.setObjectName("statValue")
        self.sub = QLabel(" ")
        self.sub.setObjectName("statSub")
        layout.addWidget(title)
        layout.addWidget(self.value)
        layout.addWidget(self.sub)
        add_shadow(self, blur=18, alpha=90)

    def set(self, text: str, sub: str = " ", color: str = "#f1f5f9") -> None:
        self.value.setText(text)
        self.value.setStyleSheet(f"color: {color};")
        self.sub.setText(sub)


class DataFrameModel(QAbstractTableModel):
    """5,000행이 넘는 정제 데이터를 빠르게 보여 주기 위한 pandas 표 모델."""

    PERCENT_COLS = {"Change"}

    def __init__(self, df: pd.DataFrame | None = None):
        super().__init__()
        self.df = df if df is not None else pd.DataFrame()

    def set_frame(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self.df = df
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.df)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.df.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        value = self.df.iat[index.row(), index.column()]
        col = self.df.columns[index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(value, pd.Timestamp):
                return f"{value:%Y-%m-%d}"
            if col in self.PERCENT_COLS:
                return f"{value:+.2%}"
            if col == "Volume":
                return f"{value:,.0f}"
            if isinstance(value, float):
                return f"{value:,.2f}"
            return str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole and not isinstance(value, pd.Timestamp):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ForegroundRole and col in self.PERCENT_COLS:
            return QColor(sign_color(value))
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self.df.columns[section])
        return str(section + 1)


class ChartTab(QWidget):
    """matplotlib 캔버스 + 확대/이동 도구 막대."""

    def __init__(self, figsize, min_height: int | None = None):
        super().__init__()
        self.figure = Figure(figsize=figsize, layout="constrained")  # 창 크기가 바뀌어도 여백 자동 조정
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self))
        if min_height:
            # 대시보드처럼 세로로 긴 차트는 스크롤해서 본다
            self.canvas.setMinimumHeight(min_height)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(self.canvas)
            layout.addWidget(scroll)
        else:
            layout.addWidget(self.canvas)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 SPY 과거 데이터 분석기")
        self.setWindowIcon(QIcon(resource_path("app.ico")))
        self.resize(1360, 900)

        self.clean_df: pd.DataFrame | None = None   # 클렌징만 끝난 전체 데이터
        self.result_df: pd.DataFrame | None = None  # 선택 기간으로 분석한 데이터

        # 상단 배너
        banner = QFrame()
        banner.setObjectName("banner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 16, 24, 16)
        title_box = QVBoxLayout()
        title = QLabel("📊 SPY 과거 데이터 분석기")
        title.setObjectName("bannerTitle")
        sub = QLabel("S&P500 ETF 일봉 CSV · 클렌징 → Pandas 다각도 분석 → 차트")
        sub.setObjectName("bannerSub")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        banner_layout.addLayout(title_box)
        banner_layout.addStretch()
        self.count_badge = QLabel("데이터 없음")
        self.count_badge.setObjectName("countBadge")
        banner_layout.addWidget(self.count_badge)
        add_shadow(banner)

        # 컨트롤 카드: 파일 / 기간 / 실행·저장 버튼
        control_card, control_layout = make_card("⚙️ 데이터 · 분석 기간")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        file_label = QLabel("CSV 파일")
        file_label.setObjectName("fieldLabel")
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("SPY 과거 데이터 CSV 파일을 열어 주세요")
        self.open_button = QPushButton("📂 CSV 열기")
        self.open_button.setObjectName("openButton")
        self.open_button.clicked.connect(self.choose_file)
        grid.addWidget(file_label, 0, 0)
        grid.addWidget(self.path_edit, 0, 1, 1, 5)
        grid.addWidget(self.open_button, 0, 6)

        start_label = QLabel("시작일")
        start_label.setObjectName("fieldLabel")
        end_label = QLabel("종료일")
        end_label.setObjectName("fieldLabel")
        self.start_edit = self.make_date_edit(DEFAULT_START)
        self.end_edit = self.make_date_edit(DEFAULT_END)
        self.run_button = QPushButton("▶ 분석 실행")
        self.run_button.setObjectName("runButton")
        self.run_button.clicked.connect(self.run_analysis)
        self.png_button = QPushButton("🖼 차트 PNG 저장")
        self.png_button.setObjectName("pngButton")
        self.png_button.clicked.connect(self.save_png)
        self.csv_button = QPushButton("💾 정제 CSV 저장")
        self.csv_button.setObjectName("csvButton")
        self.csv_button.clicked.connect(self.save_csv)
        grid.addWidget(start_label, 1, 0)
        grid.addWidget(self.start_edit, 1, 1)
        grid.addWidget(end_label, 1, 2)
        grid.addWidget(self.end_edit, 1, 3)
        grid.addWidget(self.run_button, 1, 4)
        grid.addWidget(self.png_button, 1, 5)
        grid.addWidget(self.csv_button, 1, 6)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        control_layout.addLayout(grid)

        # 요약 지표 카드
        self.stats = {key: StatCard(name) for key, name in [
            ("period", "분석 기간"), ("total", "누적 수익률"), ("cagr", "연평균(CAGR)"),
            ("vol", "연환산 변동성"), ("sharpe", "샤프지수"), ("mdd", "최대낙폭(MDD)"),
        ]}
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        for card in self.stats.values():
            stats_row.addWidget(card)

        # 결과 탭
        self.tabs = QTabWidget()
        self.close_tab = ChartTab((14, 6))
        self.dash_tab = ChartTab((16, 14), min_height=1150)
        self.yearly_table = self.make_yearly_table()
        self.report_text = self.make_text_view()
        self.clean_text = self.make_text_view()
        self.data_model = DataFrameModel()
        self.data_view = QTableView()
        self.data_view.setModel(self.data_model)
        self.data_view.setAlternatingRowColors(True)
        self.data_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.data_view.verticalHeader().setDefaultSectionSize(30)
        self.data_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.tabs.addTab(self.close_tab, "📈 종가 차트")
        self.tabs.addTab(self.dash_tab, "🧭 대시보드")
        self.tabs.addTab(self.wrap(self.yearly_table), "📅 연도별 성과")
        self.tabs.addTab(self.wrap(self.report_text), "📝 분석 리포트")
        self.tabs.addTab(self.wrap(self.clean_text), "🧹 클렌징 로그")
        self.tabs.addTab(self.wrap(self.data_view), "🗂 정제 데이터")
        self.tabs.currentChanged.connect(self.update_buttons)

        self.status_label = QLabel("CSV 파일을 열어 주세요.")
        self.status_label.setObjectName("statusLabel")

        central = QWidget()
        central.setObjectName("central")
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 12)
        root.setSpacing(14)
        root.addWidget(banner)
        root.addWidget(control_card)
        root.addLayout(stats_row)
        root.addWidget(self.tabs, 1)
        root.addWidget(self.status_label)
        self.setCentralWidget(central)

        self.update_buttons()
        if sa.DEFAULT_CSV.exists():
            self.load_file(sa.DEFAULT_CSV)

    # ---------------- 위젯 생성 도우미 ----------------
    def make_date_edit(self, date: QDate) -> QDateEdit:
        edit = QDateEdit(date)
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd")
        return edit

    def make_text_view(self) -> QPlainTextEdit:
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return view

    def make_yearly_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        return table

    @staticmethod
    def wrap(widget: QWidget) -> QWidget:
        """탭 안쪽에 여백을 준다."""
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(widget)
        return box

    def update_buttons(self) -> None:
        loaded = self.clean_df is not None
        analyzed = self.result_df is not None
        self.run_button.setEnabled(loaded)
        self.start_edit.setEnabled(loaded)
        self.end_edit.setEnabled(loaded)
        self.csv_button.setEnabled(loaded)
        self.png_button.setEnabled(analyzed and self.tabs.currentIndex() in (0, 1))

    # ---------------- 동작 ----------------
    def choose_file(self) -> None:
        start_dir = str(Path(self.path_edit.text()).parent) if self.path_edit.text() else str(sa.DEFAULT_CSV.parent)
        path, _ = QFileDialog.getOpenFileName(self, "SPY CSV 열기", start_dir, "CSV 파일 (*.csv)")
        if path:
            self.load_file(Path(path))

    def load_file(self, path: Path) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            df, log = capture(sa.load_and_clean, path)
        except Exception as e:  # 형식이 다른 CSV 등은 메시지로 알린다
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "불러오기 실패", f"CSV를 읽지 못했습니다.\n\n{e}")
            return
        QApplication.restoreOverrideCursor()
        if df.empty:
            QMessageBox.warning(self, "불러오기 실패", "유효한 행이 하나도 없습니다.")
            return

        self.clean_df = df
        self.path_edit.setText(str(path))
        self.clean_text.setPlainText(log)
        self.data_model.set_frame(df.reset_index())
        self.count_badge.setText(f"{len(df):,} 거래일")

        # 날짜 선택 범위를 데이터 범위로 제한하고, 기본값(2000-01 ~ 2019-12)을 그 안으로 맞춘다
        first = QDate(df.index[0].year, df.index[0].month, df.index[0].day)
        last = QDate(df.index[-1].year, df.index[-1].month, df.index[-1].day)
        for edit in (self.start_edit, self.end_edit):
            edit.setDateRange(first, last)
        self.start_edit.setDate(max(DEFAULT_START, first))
        self.end_edit.setDate(min(DEFAULT_END, last))
        self.status_label.setText(
            f"✅ {path.name} 클렌징 완료 · {df.index[0]:%Y-%m-%d} ~ {df.index[-1]:%Y-%m-%d}, {len(df):,}행")
        self.run_analysis()

    def run_analysis(self) -> None:
        if self.clean_df is None:
            return
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        part = self.clean_df.loc[start:end]
        if len(part) < 30:
            QMessageBox.information(self, "기간이 너무 짧음",
                                    f"선택한 기간의 거래일이 {len(part)}일입니다. 30거래일 이상으로 골라 주세요.")
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            (df, yearly, monthly_ret), report = capture(sa.analyze, part)
            sa.plot_close(self.close_tab.figure, df, start, end)
            self.close_tab.canvas.draw()
            sa.plot_dashboard(self.dash_tab.figure, df, yearly, monthly_ret)
            self.dash_tab.canvas.draw()
        finally:
            QApplication.restoreOverrideCursor()

        self.result_df = df
        self.report_text.setPlainText(report)
        self.fill_yearly(yearly)
        self.fill_stats(sa.summarize(df))
        self.status_label.setText(f"📊 {start} ~ {end} 분석 완료 · {len(df):,} 거래일")
        self.update_buttons()

    def fill_stats(self, s: dict) -> None:
        rec = f"회복 {s['recover_day']:%Y-%m-%d}" if s["recover_day"] is not None else "미회복"
        self.stats["period"].set(f"{s['days']:,}일", f"{s['start']:%Y-%m-%d} ~ {s['end']:%Y-%m-%d}")
        self.stats["total"].set(f"{s['total']:+.1%}", f"{s['first']:.2f} → {s['last']:.2f} (배당 제외)",
                                sign_color(s["total"]))
        self.stats["cagr"].set(f"{s['cagr']:+.2%}", "가격 기준 연복리", sign_color(s["cagr"]))
        self.stats["vol"].set(f"{s['vol']:.1%}", "일간 수익률 표준편차 × √252")
        self.stats["sharpe"].set(f"{s['sharpe']:.2f}", "무위험 수익률 0% 가정")
        self.stats["mdd"].set(f"{s['mdd']:.1%}", f"{s['peak_day']:%Y.%m} → {s['mdd_day']:%Y.%m} · {rec}",
                              DOWN_COLOR)

    def fill_yearly(self, yearly: pd.DataFrame) -> None:
        cols = ["연도", "시가", "종가", "최고", "최저", "수익률", "변동성", "MDD", "평균거래량_M"]
        headers = ["연도", "연초 종가", "연말 종가", "최고가", "최저가", "연간 수익률", "변동성", "연중 MDD",
                   "평균 거래량(백만)"]
        data = yearly.reset_index()[cols]
        table = self.yearly_table
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(data))
        bold = QFont()
        bold.setBold(True)
        for r, row in enumerate(data.itertuples(index=False)):
            for c, (col, value) in enumerate(zip(cols, row)):
                if col == "연도":
                    text = str(value)
                elif col in ("수익률", "변동성", "MDD"):
                    text = f"{value:+.2%}" if col == "수익률" else f"{value:.2%}"
                else:
                    text = f"{value:,.2f}"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col == "연도"
                                      else Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == "수익률":
                    item.setForeground(QColor(sign_color(value)))
                    item.setFont(bold)
                elif col == "MDD":
                    item.setForeground(QColor(DOWN_COLOR))
                table.setItem(r, c, item)

    def save_png(self) -> None:
        tab = self.close_tab if self.tabs.currentIndex() == 0 else self.dash_tab
        name = "spy_close_chart.png" if tab is self.close_tab else "spy_dashboard.png"
        path, _ = QFileDialog.getSaveFileName(self, "차트 저장", str(sa.BASE / name), "PNG 이미지 (*.png)")
        if path:
            tab.figure.savefig(path, dpi=150)
            self.status_label.setText(f"🖼 저장 완료: {path}")

    def save_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "정제 데이터 저장", str(sa.BASE / "spy_cleaned.csv"),
                                              "CSV 파일 (*.csv)")
        if path:
            self.clean_df.to_csv(path, encoding="utf-8-sig")
            self.status_label.setText(f"💾 저장 완료: {path}")


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
