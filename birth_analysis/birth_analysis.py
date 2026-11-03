"""대한민국 출생 통계(KOSIS: 출생아수, 합계출산율, 자연증가 등) 클랜징 + 분석 + 시각화.

사용법:
    python birth_analysis.py [엑셀 파일 경로]      # 콘솔 리포트 + PNG
    python birth_analysis_app.py                    # PyQt6 GUI
결과물은 이 스크립트와 같은 폴더의 output/ 에 저장된다.
"""
import sys
from pathlib import Path

import matplotlib.ticker as mticker
import pandas as pd
from matplotlib.figure import Figure

DEFAULT_PATH = Path(r"C:\Users\user\Downloads\출생아수__합계출산율__자연증가_등.xlsx")
BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "output"

# 차트 색 (GUI 어두운 배경 기준. 글자·축 색은 matplotlib rcParams를 따른다)
LINE_COLOR = "#3b82f6"
DEATH_COLOR = "#f97316"
UP_COLOR = "#34d399"
DOWN_COLOR = "#f87171"
REF_COLOR = "#94a3b8"

# 원본 행 이름 -> 분석용 컬럼명 (단위는 이름에서 떼어 내고 주석으로 남김)
COLUMN_MAP = {
    "출생아수(명)": "births",               # 명
    "자연증가건수(명)": "natural_increase",  # 명 (출생 - 사망)
    "조출생률(천명당)": "crude_birth_rate",  # 인구 1천 명당
    "자연증가율(천명당)": "natural_increase_rate",  # 인구 1천 명당
    "합계출산율(명)": "tfr",                 # 여성 1명당
    "출생성비(명)": "sex_ratio",             # 여아 100명당 남아
}
KOR_LABEL = {
    "births": "출생아수(명)",
    "natural_increase": "자연증가(명)",
    "crude_birth_rate": "조출생률(‰)",
    "natural_increase_rate": "자연증가율(‰)",
    "tfr": "합계출산율",
    "sex_ratio": "출생성비",
    "deaths_est": "사망자수 추정(명)",
}


# ---------------------------------------------------------------- 1. 클랜징
def load_and_clean(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0, header=None)
    print(f"[원본] shape={raw.shape} (행=지표, 열=연도인 가로형 구조)")

    # 첫 행이 연도 헤더, 첫 열이 지표명 -> 지표명을 인덱스로 두고 전치해 '연도 x 지표' 롱 형태로
    header = raw.iloc[0, 1:]
    df = raw.iloc[1:].set_index(0)
    df.columns = header
    df.index = df.index.astype(str).str.strip()
    df = df.T

    # 연도: '1970.0' 같은 float/문자 -> int
    df.index = pd.to_numeric(df.index, errors="coerce")
    df = df[df.index.notna()]
    df.index = df.index.astype(int)
    df.index.name = "year"
    df.columns.name = None

    # 컬럼명 정리 (알 수 없는 지표는 경고 후 원래 이름 유지)
    unknown = [c for c in df.columns if c not in COLUMN_MAP]
    if unknown:
        print(f"[경고] 매핑되지 않은 지표: {unknown}")
    df = df.rename(columns=COLUMN_MAP)

    # KOSIS 결측 표기('-', '…', 'x', 공백, 천단위 콤마) 처리 후 숫자형 변환
    df = df.apply(lambda s: pd.to_numeric(
        s.astype(str).str.replace(",", "").str.strip()
         .replace({"-": None, "…": None, "x": None, "": None, "nan": None}),
        errors="coerce"))

    # 정렬, 중복 연도 제거, 1970~2025 범위만
    before = len(df)
    df = df[~df.index.duplicated(keep="last")].sort_index().loc[1970:2025]
    print(f"[중복/범위 정리] {before} -> {len(df)}개 연도")

    # 결측치 보고 + 연속 데이터이므로 선형 보간 (보간한 칸은 기록)
    na = df.isna().sum()
    print("[결측치]", "없음" if na.sum() == 0 else na[na > 0].to_dict())
    if na.sum():
        df = df.interpolate(method="linear", limit_direction="both")

    # 정수여야 하는 '명' 단위 컬럼은 Int64로
    for c in ("births", "natural_increase"):
        df[c] = df[c].round().astype("Int64")

    # 값 범위 검증 (이상치 플래그만 하고 삭제하지 않음)
    checks = {
        "births > 0": df["births"] > 0,
        "0 < tfr < 10": df["tfr"].between(0, 10, inclusive="neither"),
        "90 <= sex_ratio <= 130": df["sex_ratio"].between(90, 130),
        "births >= natural_increase": df["births"] >= df["natural_increase"],
    }
    for name, ok in checks.items():
        bad = df.index[~ok].tolist()
        print(f"[검증] {name}: {'OK' if not bad else f'위반 연도 {bad}'}")

    # 파생 변수: 사망자수 = 출생아수 - 자연증가
    df["deaths_est"] = (df["births"] - df["natural_increase"]).astype("Int64")
    return df


# ---------------------------------------------------------------- 2. 분석
def section(title: str):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def analyze(df: pd.DataFrame) -> dict:
    res = {}
    b = df["births"].astype(float)

    section("1) 기술 통계")
    print(df.describe().T.round(2).rename(index=KOR_LABEL).to_string())

    section("2) 출생아수 정점·최저점·전체 변화")
    peak_y, low_y = b.idxmax(), b.idxmin()
    first, last = df.index.min(), df.index.max()
    print(f"최대: {peak_y}년 {b[peak_y]:,.0f}명 / 최소: {low_y}년 {b[low_y]:,.0f}명")
    print(f"{first}년 대비 {last}년: {b[last] / b[first] * 100:.1f}% 수준 "
          f"({b[last] - b[first]:+,.0f}명)")
    print(f"연평균 증감률(CAGR {first}~{last}): {cagr(b) * 100:.2f}%")

    section("3) 전년 대비 증감 — 가장 크게 줄어든/늘어난 해")
    yoy = pd.DataFrame({"증감(명)": b.diff(), "증감률(%)": b.pct_change() * 100}).dropna()
    print("감소폭 상위 5\n", yoy.nsmallest(5, "증감(명)").round(1).to_string())
    print("\n증가폭 상위 5\n", yoy.nlargest(5, "증감(명)").round(1).to_string())
    down = yoy["증감(명)"] < 0
    groups = (down != down.shift()).cumsum()
    runs = down[down].groupby(groups[down]).apply(lambda s: (len(s), s.index[-1]))
    if len(runs):
        longest, end_year = max(runs, key=lambda r: (r[0], r[1]))
        print(f"\n최장 연속 감소: {longest}년 연속 (~{end_year}년까지)")
    else:
        print("\n연속 감소 구간 없음")
    res["yoy"] = yoy

    section("4) 연대별 평균")
    decade = df.groupby(df.index // 10 * 10).agg(
        출생아수_평균=("births", "mean"),
        합계출산율_평균=("tfr", "mean"),
        출생성비_평균=("sex_ratio", "mean"),
        자연증가_합계=("natural_increase", "sum"),
    )
    decade.index = [f"{d}년대" for d in decade.index]
    print(decade.round(2).to_string())
    res["decade"] = decade

    section("5) 합계출산율 주요 임계점 첫 진입 연도")
    for label, cond in [("대체출산율(2.1) 미만", df["tfr"] < 2.1),
                        ("초저출산(1.3) 미만", df["tfr"] < 1.3),
                        ("1.0 미만", df["tfr"] < 1.0)]:
        yrs = df.index[cond]
        print(f"{label}: {yrs.min() if len(yrs) else '해당 없음'}년"
              + (f" (이후 {len(yrs)}개 연도)" if len(yrs) else ""))
    print(f"최저 합계출산율: {df['tfr'].idxmin()}년 {df['tfr'].min():.3f}")

    section("6) 인구 데드크로스 (사망 > 출생)")
    neg = df.index[df["natural_increase"] < 0]
    if len(neg):
        print(f"자연증가가 처음 마이너스가 된 해: {neg.min()}년 "
              f"(출생 {df.loc[neg.min(), 'births']:,} < 사망 {df.loc[neg.min(), 'deaths_est']:,})")
        print(f"{neg.min()}~{last} 누적 자연감소: {df.loc[neg, 'natural_increase'].sum():,}명")
    print(df[["births", "deaths_est", "natural_increase"]].loc[2015:]
          .rename(columns=KOR_LABEL).to_string())

    section("7) 출생성비 — 정상 범위(103~107) 이탈 연도")
    out = df.loc[~df["sex_ratio"].between(103, 107), "sex_ratio"]
    print(out.to_string() if len(out) else "없음")
    print(f"최고: {df['sex_ratio'].idxmax()}년 {df['sex_ratio'].max()}")
    print("※ 원자료 주석: 1970~2014년 출생성비는 2016.12 재추계로 수치가 변경됨")

    section("8) 지표 간 상관계수 (Pearson)")
    corr = df.astype(float).corr().round(3).rename(index=KOR_LABEL, columns=KOR_LABEL)
    print(corr.to_string())
    res["corr"] = corr

    section("9) 최근 반등 여부 (2023 → 2025)")
    print(df.loc[2022:, ["births", "tfr", "crude_birth_rate"]]
          .assign(출생_전년비=lambda d: d["births"].astype(float).pct_change().mul(100).round(1))
          .rename(columns=KOR_LABEL).to_string())

    return res


def cagr(s: pd.Series) -> float:
    """첫 해 -> 마지막 해 연평균 증감률."""
    years = s.index[-1] - s.index[0]
    return (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1 if years else 0.0


def summarize(df: pd.DataFrame) -> dict:
    """GUI 요약 카드에 쓰는 핵심 수치."""
    b = df["births"].astype(float)
    neg = df.index[df["natural_increase"] < 0]
    return {
        "first": df.index[0], "last": df.index[-1],
        "births_first": b.iloc[0], "births_last": b.iloc[-1],
        "ratio": b.iloc[-1] / b.iloc[0], "cagr": cagr(b),
        "peak_year": b.idxmax(), "peak": b.max(),
        "low_year": b.idxmin(), "low": b.min(),
        "tfr_last": df["tfr"].iloc[-1], "tfr_min_year": df["tfr"].idxmin(), "tfr_min": df["tfr"].min(),
        "dead_cross": neg.min() if len(neg) else None,
        "natural_loss": int(df.loc[neg, "natural_increase"].sum()) if len(neg) else 0,
    }


# ---------------------------------------------------------------- 3. 그래프
def _style(ax, ylabel: str):
    # '명', '%' 같은 짧은 단위는 눕히지 않고 가로로 쓴다
    if len(ylabel) <= 3:
        ax.set_ylabel(ylabel, rotation=0, ha="right", va="center")
    else:
        ax.set_ylabel(ylabel)
    ax.grid(axis="y", linewidth=0.8, alpha=0.6)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)


def plot_births(fig: Figure, df: pd.DataFrame, start: int = 1970, end: int = 2025):
    """start~end년 출생아수 라인 그래프."""
    fig.clear()
    ax = fig.add_subplot()
    s = df.loc[start:end, "births"].astype(float)
    ax.plot(s.index, s.values, color=LINE_COLOR, linewidth=2, marker="o", markersize=3.5)

    # 선택적 직접 라벨: 시작·정점·최저점·최근값만 (연도 -> x오프셋, y오프셋, 정렬)
    marks = {s.idxmax(): (8, 2, "left"), s.idxmin(): (0, -24, "center"),
             s.index[-1]: (0, 14, "center"), s.index[0]: (-4, 24, "left")}
    for year, (dx, dy, ha) in marks.items():
        y = s[year]
        ax.scatter(year, y, s=60, color=LINE_COLOR, edgecolor=fig.get_facecolor(), linewidth=1.5, zorder=3)
        ax.annotate(f"{year}년 {y / 10_000:,.1f}만 명", (year, y), textcoords="offset points",
                    xytext=(dx, dy), ha=ha, fontsize=10)

    ax.set_title(f"대한민국 연간 출생아수 ({start}–{end})", loc="left", fontsize=15, fontweight="bold", pad=14)
    _style(ax, "출생아수 (만 명)")
    ax.set_xlabel("연도")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v / 10_000:,.0f}"))
    ax.set_ylim(0, s.max() * 1.15)
    ax.set_xlim(start - 2, end + 2)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=12, integer=True))
    fig.text(0.01, 0.01, "자료: 통계청 「인구동향조사」 (KOSIS)", fontsize=9, color=REF_COLOR)


def plot_dashboard(fig: Figure, df: pd.DataFrame, start: int = 1970, end: int = 2025):
    """합계출산율 / 출생·사망 / 전년비 증감률 / 출생성비 2x2 대시보드."""
    fig.clear()
    d = df.loc[start:end]
    (a1, a2), (a3, a4) = fig.subplots(2, 2)

    a1.plot(d.index, d["tfr"], color=LINE_COLOR, linewidth=2)
    # 1.3과 1.0은 붙어 있어서 1.0 라벨은 선 아래에 단다
    for v, label, va in [(2.1, "대체출산율 2.1", "bottom"), (1.3, "초저출산 1.3", "bottom"), (1.0, "1.0", "top")]:
        a1.axhline(v, color=REF_COLOR, linestyle="--", linewidth=1)
        a1.text(d.index[0], v, f" {label}", va=va, ha="left", fontsize=9, color=REF_COLOR)
    a1.set_title("합계출산율 (여성 1명당)", loc="left", fontweight="bold")
    _style(a1, "명")

    a2.plot(d.index, d["births"] / 10_000, color=LINE_COLOR, linewidth=2, label="출생아수")
    a2.plot(d.index, d["deaths_est"].astype(float) / 10_000, color=DEATH_COLOR, linewidth=2, label="사망자수")
    neg = d.index[d["natural_increase"] < 0]
    if len(neg):
        a2.axvline(neg.min(), color=REF_COLOR, linestyle=":", linewidth=1)
        a2.annotate(f"{neg.min()}년 데드크로스", (neg.min(), d.loc[neg.min(), "births"] / 10_000),
                    textcoords="offset points", xytext=(-6, 30), ha="right", fontsize=9)
    a2.legend(loc="upper right", frameon=False)
    a2.set_title("출생아수 vs 사망자수", loc="left", fontweight="bold")
    _style(a2, "만 명")

    pct = d["births"].astype(float).pct_change().mul(100).dropna()
    a3.bar(pct.index, pct.values, color=[UP_COLOR if v >= 0 else DOWN_COLOR for v in pct.values], width=0.8)
    a3.axhline(0, color=REF_COLOR, linewidth=0.8)
    a3.set_title("출생아수 전년 대비 증감률", loc="left", fontweight="bold")
    _style(a3, "%")

    a4.axhspan(103, 107, color=UP_COLOR, alpha=0.12, label="정상 범위 103~107")
    a4.plot(d.index, d["sex_ratio"], color=LINE_COLOR, linewidth=2)
    a4.legend(loc="upper right", frameon=False)
    a4.set_title("출생성비 (여아 100명당 남아)", loc="left", fontweight="bold")
    _style(a4, "명")

    for ax in (a1, a2, a3, a4):
        ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=8, integer=True))


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH
    OUT_DIR.mkdir(exist_ok=True)
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    df = load_and_clean(path)
    df.to_csv(OUT_DIR / "births_clean.csv", encoding="utf-8-sig")
    print(f"[클랜징 결과 저장] {OUT_DIR / 'births_clean.csv'}")

    res = analyze(df)
    res["yoy"].to_csv(OUT_DIR / "births_yoy.csv", encoding="utf-8-sig")
    res["decade"].to_csv(OUT_DIR / "decade_summary.csv", encoding="utf-8-sig")

    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Malgun Gothic"   # 한글 폰트 (Windows)
    plt.rcParams["axes.unicode_minus"] = False
    fig = plt.figure(figsize=(12, 6), layout="constrained")
    plot_births(fig, df)
    fig.savefig(OUT_DIR / "births_1970_2025.png", dpi=150)
    print(f"\n[그래프 저장] {OUT_DIR / 'births_1970_2025.png'}")
    plt.show()


if __name__ == "__main__":
    main()
