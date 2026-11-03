"""SPY(S&P500 ETF) 과거 데이터 클렌징 + Pandas 다각도 분석.

GUI 앱(spy_analysis_app.py)이 이 모듈의 함수를 가져다 쓴다. 단독 실행도 된다.

사용법:
    python spy_analysis.py [CSV 경로]
결과 차트는 스크립트 옆 output/ 폴더에 PNG로 저장된다.
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

# PyInstaller exe로 실행하면 __file__은 임시 압축해제 폴더를 가리키므로, exe가 있는 폴더를 기준으로 삼는다
FROZEN = getattr(sys, "frozen", False)
BASE = Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent
CSV_NAME = "SPY 과거 데이터.csv"
# 같은 폴더(배포 zip) → 상위 폴더(개발 환경) 순서로 기본 CSV를 찾는다
DEFAULT_CSV = next((p for p in (BASE / CSV_NAME, BASE.parent / CSV_NAME) if p.exists()), BASE / CSV_NAME)
OUT = BASE / "output"

# 밝은 배경과 어두운 배경(GUI) 모두에서 잘 보이는 색
LINE_COLOR = "#3b82f6"
MA50_COLOR = "#f59e0b"
MA200_COLOR = "#ef4444"
UP_BAR = "#10b981"
DOWN_BAR = "#ef4444"

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)
pd.set_option("display.float_format", "{:,.2f}".format)


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ----------------------------------------------------------------------
# 1. 데이터 클렌징
# ----------------------------------------------------------------------
def parse_volume(s):
    """'52.00M' / '850K' / '1.2B' 형태 → 정수."""
    if pd.isna(s) or str(s).strip() in ("", "-"):
        return np.nan
    s = str(s).strip().replace(",", "")
    unit = {"K": 1e3, "M": 1e6, "B": 1e9}.get(s[-1].upper())
    return float(s[:-1]) * unit if unit else float(s)


def load_and_clean(path):
    section("1. 데이터 클렌징")
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    print(f"원본: {raw.shape[0]:,}행 x {raw.shape[1]}열, 컬럼 = {list(raw.columns)}")

    df = raw.rename(columns={
        "날짜": "Date", "종가": "Close", "시가": "Open", "고가": "High",
        "저가": "Low", "거래량": "Volume", "변동 %": "Change",
    })
    missing = {"Date", "Close", "Open", "High", "Low", "Volume", "Change"} - set(df.columns)
    if missing:
        raise ValueError(f"필요한 컬럼이 없습니다: {sorted(missing)}")

    # 날짜: '2019- 11- 14' 처럼 섞인 공백 제거 후 파싱
    df["Date"] = pd.to_datetime(df["Date"].str.replace(" ", ""), format="%Y-%m-%d", errors="coerce")

    # 가격: 천단위 콤마 제거 후 숫자 변환
    for c in ["Close", "Open", "High", "Low"]:
        df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")

    df["Volume"] = df["Volume"].map(parse_volume)
    df["Change"] = pd.to_numeric(df["Change"].str.replace("%", "").str.replace(",", ""), errors="coerce") / 100

    # 결측 / 중복 / 정렬
    print("\n[결측치 개수]")
    print(df.isna().sum().to_string())
    before = len(df)
    df = df.dropna(subset=["Date", "Close"])
    df = df.drop_duplicates(subset="Date", keep="first")
    df = df.sort_values("Date").set_index("Date")
    print(f"\n결측·중복 제거: {before:,} → {len(df):,}행")

    # 논리 검증: 저가 <= 시가/종가 <= 고가
    bad_ohlc = df[(df["Low"] > df[["Open", "Close"]].min(axis=1)) |
                  (df["High"] < df[["Open", "Close"]].max(axis=1))]
    print(f"OHLC 논리 오류 행: {len(bad_ohlc)}개")
    if len(bad_ohlc):
        print(bad_ohlc.head())

    # 변동 % 검증: 종가로 직접 계산한 수익률과 비교
    calc = df["Close"].pct_change()
    mismatch = (calc - df["Change"]).abs() > 0.0005
    print(f"변동 % 불일치(>0.05%p) 행: {mismatch.sum()}개 (첫 행 제외)")

    print(f"\n기간: {df.index.min():%Y-%m-%d} ~ {df.index.max():%Y-%m-%d} ({len(df):,} 거래일)")
    print("\n[클렌징 후 dtypes]")
    print(df.dtypes.to_string())
    return df


# ----------------------------------------------------------------------
# 2. 분석
# ----------------------------------------------------------------------
def summarize(df):
    """전체 성과 지표를 dict로 돌려준다 (GUI의 요약 카드에도 쓰인다)."""
    ret = df["Close"].pct_change()
    years = max((df.index[-1] - df.index[0]).days / 365.25, 1 / 365.25)
    total = df["Close"].iloc[-1] / df["Close"].iloc[0] - 1
    dd = df["Close"] / df["Close"].cummax() - 1
    mdd_day = dd.idxmin()
    peak_day = df.loc[:mdd_day, "Close"].idxmax()
    after = df.loc[mdd_day:, "Close"]
    recover = after[after >= df.loc[peak_day, "Close"]]
    return {
        "start": df.index[0], "end": df.index[-1], "days": len(df),
        "first": df["Close"].iloc[0], "last": df["Close"].iloc[-1],
        "total": total,
        "cagr": (1 + total) ** (1 / years) - 1,
        "vol": ret.std() * np.sqrt(252),
        "sharpe": ret.mean() / ret.std() * np.sqrt(252),
        "mdd": dd.min(), "peak_day": peak_day, "mdd_day": mdd_day,
        "recover_day": recover.index[0] if len(recover) else None,
    }


def analyze(df):
    df = df.copy()
    df["Return"] = df["Close"].pct_change()
    df["LogReturn"] = np.log(df["Close"]).diff()

    section("2. 기술 통계")
    print(df[["Close", "Open", "High", "Low", "Volume", "Return"]].describe().T)

    section("3. 전체 성과 요약")
    s = summarize(df)
    rec_txt = f"회복 {s['recover_day']:%Y-%m-%d}" if s["recover_day"] is not None else "(미회복)"
    print(f"시작가 {s['first']:.2f} → 종료가 {s['last']:.2f}")
    print(f"누적 수익률 : {s['total']:.2%}  (가격 기준, 배당 제외)")
    print(f"CAGR       : {s['cagr']:.2%}")
    print(f"연환산 변동성: {s['vol']:.2%}")
    print(f"샤프지수(무위험 0%): {s['sharpe']:.2f}")
    print(f"최대낙폭(MDD): {s['mdd']:.2%}  고점 {s['peak_day']:%Y-%m-%d} → 저점 {s['mdd_day']:%Y-%m-%d}  {rec_txt}")

    section("4. 연도별 분석")
    yearly = df.groupby(df.index.year).agg(
        시가=("Close", "first"), 종가=("Close", "last"),
        최고=("High", "max"), 최저=("Low", "min"),
        평균거래량_M=("Volume", lambda v: v.mean() / 1e6),
        변동성=("Return", lambda r: r.std() * np.sqrt(252)),
    )
    # 연간 수익률: 전년도 마지막 종가 대비
    year_end = df["Close"].groupby(df.index.year).last()
    yearly["수익률"] = year_end.pct_change()
    yearly.loc[yearly.index[0], "수익률"] = year_end.iloc[0] / df["Close"].iloc[0] - 1
    yearly["MDD"] = df["Close"].groupby(df.index.year).apply(lambda s: (s / s.cummax() - 1).min())
    yearly.index.name = "연도"
    print(yearly.to_string(formatters={"수익률": "{:.2%}".format, "변동성": "{:.2%}".format,
                                       "MDD": "{:.2%}".format}))
    print(f"\n상승 연도 {int((yearly['수익률'] > 0).sum())}개 / 하락 연도 {int((yearly['수익률'] <= 0).sum())}개")

    section("5. 월별 계절성 (월간 수익률 평균)")
    monthly_ret = df["Close"].resample("ME").last().pct_change().dropna()
    season = monthly_ret.groupby(monthly_ret.index.month).agg(["mean", "median", lambda r: (r > 0).mean()])
    season.columns = ["평균", "중앙값", "상승확률"]
    print(season.to_string(formatters={c: "{:.2%}".format for c in season.columns}))

    section("6. 요일 효과")
    names = ["월", "화", "수", "목", "금"]
    wd = df.groupby(df.index.dayofweek)["Return"].agg(["mean", "std", "count", lambda r: (r > 0).mean()])
    wd.columns = ["평균", "표준편차", "일수", "상승확률"]
    wd.index = [names[i] for i in wd.index]
    print(wd.to_string(formatters={"평균": "{:.3%}".format, "표준편차": "{:.3%}".format,
                                   "상승확률": "{:.1%}".format}))

    section("7. 극단적 변동일 Top 10")
    top = df[["Close", "Return", "Volume"]].dropna()
    print("[상승]")
    print(top.nlargest(10, "Return").to_string(formatters={"Return": "{:.2%}".format}))
    print("\n[하락]")
    print(top.nsmallest(10, "Return").to_string(formatters={"Return": "{:.2%}".format}))

    section("8. 수익률 분포")
    r = df["Return"].dropna()
    print(f"왜도 {r.skew():.3f}, 첨도(초과) {r.kurt():.3f}  (첨도 > 0 이면 정규분포보다 꼬리가 두꺼움)")
    for k in (2, 3):
        p = (np.abs(r - r.mean()) > k * r.std()).mean()
        print(f"±{k}σ 밖 비율: {p:.2%}")
    print(f"일간 VaR 95% : {r.quantile(0.05):.2%},  VaR 99% : {r.quantile(0.01):.2%}")

    section("9. 이동평균 / 추세")
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    sig = np.sign(df["MA50"] - df["MA200"]).dropna()
    cross = sig.diff().fillna(0)
    above = (df["Close"] > df["MA200"]).loc[df["MA200"].notna()]
    print(f"종가 > MA200 인 날의 비율: {above.mean():.1%}" if len(above) else "MA200 계산에 필요한 200거래일이 부족합니다.")
    print(f"골든크로스 {int((cross > 0).sum())}회, 데드크로스 {int((cross < 0).sum())}회")
    print("최근 크로스 5건:")
    for d, v in cross[cross != 0].tail(5).items():
        print(f"  {d:%Y-%m-%d}  {'골든' if v > 0 else '데드'}크로스")

    section("10. 거래량-변동성 상관관계")
    df["AbsRet"] = df["Return"].abs()
    print(df[["Volume", "AbsRet", "Return"]].corr().to_string())

    df["Drawdown"] = df["Close"] / df["Close"].cummax() - 1
    df["Vol20"] = df["Return"].rolling(20).std() * np.sqrt(252)
    return df, yearly, monthly_ret


# ----------------------------------------------------------------------
# 3. 시각화 (Figure를 받아서 그린다 → GUI 캔버스와 PNG 저장에 같이 쓰인다)
# ----------------------------------------------------------------------
EVENTS = [("2002-10-09", "닷컴 버블 저점"), ("2009-03-09", "금융위기 저점")]


def plot_close(fig, df, start="2000-01-01", end="2019-12-31"):
    """요청 차트: 종가 기준 라인그래프 (기본 2000-01 ~ 2019-12)."""
    fig.clear()
    s = df.loc[start:end, "Close"]
    ax = fig.add_subplot(111)
    if s.empty:
        ax.text(0.5, 0.5, "선택한 기간에 데이터가 없습니다", ha="center", va="center", transform=ax.transAxes)
        return
    ax.plot(s.index, s.values, color=LINE_COLOR, linewidth=1.2, label="SPY 종가")
    ax.set_title(f"SPY 종가 추이 ({s.index.min():%Y.%m} ~ {s.index.max():%Y.%m})", fontsize=15, pad=12)
    ax.set_xlabel("날짜")
    ax.set_ylabel("종가 (USD)")
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.grid(alpha=0.3)
    ax.set_ylim(bottom=s.min() * 0.6)   # 저점 주석이 x축 눈금과 겹치지 않도록 여백 확보
    for d, txt in EVENTS:
        if pd.Timestamp(d) in s.index:
            ax.annotate(txt, (pd.Timestamp(d), s[d]), xytext=(0, -28), textcoords="offset points",
                        ha="center", arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9)
    ax.legend(loc="best")


def plot_dashboard(fig, df, yearly, monthly_ret):
    fig.clear()
    axes = fig.subplots(3, 2)

    ax = axes[0, 0]
    ax.plot(df.index, df["Close"], lw=1, label="종가", color=LINE_COLOR)
    ax.plot(df.index, df["MA50"], lw=1, label="MA50", color=MA50_COLOR)
    ax.plot(df.index, df["MA200"], lw=1, label="MA200", color=MA200_COLOR)
    ax.set_title("종가와 이동평균(50/200)")
    ax.legend(); ax.grid(alpha=0.3)

    ax = axes[0, 1]
    ax.fill_between(df.index, df["Drawdown"] * 100, 0, color=DOWN_BAR, alpha=0.5)
    ax.set_title("낙폭(Drawdown, %)"); ax.grid(alpha=0.3)

    ax = axes[1, 0]
    colors = [UP_BAR if v > 0 else DOWN_BAR for v in yearly["수익률"]]
    ax.bar(yearly.index.astype(str), yearly["수익률"] * 100, color=colors)
    ax.set_title("연도별 수익률(%)"); ax.tick_params(axis="x", rotation=60); ax.grid(alpha=0.3, axis="y")

    ax = axes[1, 1]
    ax.plot(df.index, df["Vol20"] * 100, lw=0.8, color="#a855f7")
    ax.set_title("20일 연환산 변동성(%)"); ax.grid(alpha=0.3)

    ax = axes[2, 0]
    r = df["Return"].dropna() * 100
    ax.hist(r, bins=120, color=LINE_COLOR, alpha=0.75, density=True)
    x = np.linspace(r.min(), r.max(), 400)
    ax.plot(x, np.exp(-(x - r.mean()) ** 2 / (2 * r.var())) / np.sqrt(2 * np.pi * r.var()),
            color=DOWN_BAR, lw=1.2, label="정규분포")
    ax.set_title("일간 수익률 분포(%)"); ax.legend(); ax.set_xlim(-8, 8)

    ax = axes[2, 1]
    heat = monthly_ret.to_frame("r").assign(Y=monthly_ret.index.year, M=monthly_ret.index.month) \
        .pivot(index="Y", columns="M", values="r").reindex(columns=range(1, 13)) * 100
    im = ax.imshow(heat, cmap="RdYlGn", vmin=-10, vmax=10, aspect="auto")
    ax.set_xticks(range(12), [f"{m}월" for m in range(1, 13)])
    ax.set_yticks(range(len(heat)), heat.index)
    ax.set_title("월별 수익률 히트맵(%)")
    fig.colorbar(im, ax=ax, fraction=0.03)

    fig.suptitle("SPY 다각도 분석 대시보드", fontsize=17)


def main():
    import matplotlib.pyplot as plt   # CLI에서만 필요 (GUI는 Figure만 쓴다)
    plt.rcParams["font.family"] = "Malgun Gothic"   # 한글 폰트 (Windows)
    plt.rcParams["axes.unicode_minus"] = False

    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    OUT.mkdir(exist_ok=True)
    df = load_and_clean(path)
    df.to_csv(OUT / "spy_cleaned.csv", encoding="utf-8-sig")
    df, yearly, monthly_ret = analyze(df)

    fig = Figure(figsize=(14, 6), layout="constrained")
    plot_close(fig, df)
    fig.savefig(OUT / "01_close_2000_2019.png", dpi=150)
    fig = Figure(figsize=(16, 14), layout="constrained")
    plot_dashboard(fig, df, yearly, monthly_ret)
    fig.savefig(OUT / "02_dashboard.png", dpi=130)
    print(f"\n차트·정제 데이터 저장 위치: {OUT}")


if __name__ == "__main__":
    main()
