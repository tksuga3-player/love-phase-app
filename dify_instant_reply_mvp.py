import html
import re

import requests
import streamlit as st
import streamlit.components.v1 as components


# ==================================================
# Dify API設定
# ==================================================

DIFY_API_URL = "https://api.dify.ai/v1/completion-messages"
DIFY_API_KEY = st.secrets["DIFY_API_KEY"]


def call_dify_api(user_text):
    """入力内容をDifyへ送り、回答文を取得する。"""

    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": {
            "user_input": user_text
        },
        "response_mode": "blocking",
        "user": "streamlit-web-user",
    }

    try:
        response = requests.post(
            DIFY_API_URL,
            headers=headers,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()
        result_data = response.json()

        return result_data.get(
            "answer",
            "エラー：回答を抽出できませんでした。"
        )

    except requests.exceptions.Timeout:
        return (
            "通信がタイムアウトしました。\n"
            "時間を置いて、もう一度お試しください。"
        )

    except requests.exceptions.RequestException as error:
        return (
            "通信エラーが発生しました。設定を確認してください。\n"
            f"詳細：{error}"
        )


# ==================================================
# Difyの機械判定用データを読み取る
# ==================================================

def parse_phase_metadata(raw_text):
    """
    Dify回答から以下を取得する。

    [[CURRENT_PHASE:3]]
    [[PHASE_PROGRESS:65]]

    機械判定用データは、表示する本文から削除する。
    """

    if not raw_text:
        return None, None, ""

    text = (
        raw_text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .replace("\u0085", "\n")
    )

    phase_match = re.search(
        r"\[\[\s*CURRENT_PHASE\s*:\s*([1-4])\s*\]\]",
        text,
        flags=re.IGNORECASE,
    )

    progress_match = re.search(
        r"\[\[\s*PHASE_PROGRESS\s*:\s*(\d{1,3})\s*\]\]",
        text,
        flags=re.IGNORECASE,
    )

    current_phase = None
    phase_progress = None

    if phase_match:
        current_phase = int(phase_match.group(1))

    if progress_match:
        phase_progress = int(progress_match.group(1))
        phase_progress = max(0, min(99, phase_progress))

    # PHASE_PROGRESSが欠けた場合は、現在フェーズの中間に置く
    if current_phase is not None and phase_progress is None:
        phase_progress = 50

    # 万一CURRENT_PHASEが欠けた場合、
    # 通常本文の「現在地：フェーズ3」などから補完する
    if current_phase is None:
        visible_phase_match = re.search(
            r"現在地[：:]\s*フェーズ\s*([1-4])",
            text
        )

        if visible_phase_match:
            current_phase = int(
                visible_phase_match.group(1)
            )
            phase_progress = 50

    # 機械判定用データを本文から削除
    cleaned_text = re.sub(
        r"\[\[\s*CURRENT_PHASE\s*:\s*[1-4]\s*\]\]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    cleaned_text = re.sub(
        r"\[\[\s*PHASE_PROGRESS\s*:\s*\d{1,3}\s*\]\]",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )

    cleaned_text = cleaned_text.strip()

    return current_phase, phase_progress, cleaned_text


# ==================================================
# 診断結果本文の整形
# ==================================================

def format_diagnosis_result(raw_text):
    """
    表示ルール：

    ・見出しの直前だけ空行を1行入れる
    ・見出し直後には空行を入れない
    ・番号や箇条書きの間には空行を入れない
    ・末尾の誘導文の直前に空行を1行入れる
    """

    if not raw_text:
        return "回答を取得できませんでした。"

    text = (
        raw_text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .replace("\u0085", "\n")
    )

    original_lines = text.splitlines()
    cleaned_lines = []

    for original_line in original_lines:
        line = original_line.strip()

        # 元の空行はいったん削除
        if not line:
            continue

        # 見出しの直前に空行を1つ入れる
        if re.fullmatch(r"【[^】]+】", line):
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        # 有料診断への誘導文の直前に空行を1つ入れる
        if line.startswith(
            "多くの男性は努力していないのではなく"
        ):
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        cleaned_lines.append(line)

    # 先頭と末尾の不要な空行を削除
    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)

    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


# ==================================================
# フェーズ図の表示
# ==================================================

def display_phase_chart(current_phase, phase_progress):
    """
    現在フェーズと、そのフェーズ内の位置を図で表示する。
    """

    if current_phase not in [1, 2, 3, 4]:
        return

    if phase_progress is None:
        phase_progress = 50

    phase_progress = max(0, min(99, phase_progress))

    if phase_progress <= 30:
        progress_label = "前半"
    elif phase_progress <= 70:
        progress_label = "中盤"
    else:
        progress_label = "後半"

    # 全体における矢印位置
    marker_position = (
        (current_phase - 1 + phase_progress / 100)
        / 4
        * 100
    )

    marker_position = max(3, min(97, marker_position))

    phase_data = [
        (1, "フェーズ1", "拒絶ライン"),
        (2, "フェーズ2", "安全ライン"),
        (3, "フェーズ3", "男としての候補"),
        (4, "フェーズ4", "長期伴侶ライン"),
    ]

    phase_cards = ""

    for phase_number, phase_title, phase_description in phase_data:

        if phase_number == current_phase:
            background = "#1268b3"
            text_color = "#ffffff"
            border_color = "#1268b3"

        elif phase_number < current_phase:
            background = "#dcecff"
            text_color = "#185b94"
            border_color = "#a7c9e9"

        else:
            background = "#f4f7fa"
            text_color = "#586979"
            border_color = "#d7dfe6"

        phase_cards += f"""
<div class="phase-item">
    <div
        class="phase-box"
        style="
            background:{background};
            color:{text_color};
            border-color:{border_color};
        "
    >
        {phase_title}
    </div>

    <div class="phase-description">
        {phase_description}
    </div>
</div>
"""

    chart_html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">

<style>
    html,
    body {{
        margin: 0;
        padding: 0;
        background: transparent;
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;
    }}

    .phase-chart {{
        box-sizing: border-box;
        width: 100%;
        background: #ffffff;
        border: 1px solid #bed3e8;
        border-radius: 10px;
        padding: 17px 12px 20px;
    }}

    .chart-title {{
        color: #07599c;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 14px;
    }}

    .phase-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 5px;
    }}

    .phase-item {{
        min-width: 0;
        text-align: center;
    }}

    .phase-box {{
        box-sizing: border-box;
        min-height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid;
        border-radius: 7px;
        padding: 7px 2px;
        font-size: 13px;
        font-weight: 700;
        line-height: 1.25;
    }}

    .phase-description {{
        min-height: 34px;
        margin-top: 5px;
        color: #4d6275;
        font-size: 11px;
        line-height: 1.35;
    }}

    .progress-area {{
        position: relative;
        height: 68px;
        margin: 4px 3px 0;
    }}

    .progress-background {{
        position: absolute;
        left: 0;
        right: 0;
        top: 8px;
        height: 4px;
        background: #d5e0ea;
        border-radius: 999px;
    }}

    .progress-completed {{
        position: absolute;
        left: 0;
        top: 8px;
        width: {marker_position}%;
        height: 4px;
        background: #1976bd;
        border-radius: 999px;
    }}

    .marker {{
        position: absolute;
        left: {marker_position}%;
        top: 2px;
        width: 14px;
        height: 14px;
        background: #e04444;
        border: 3px solid #ffffff;
        border-radius: 50%;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.22);
        transform: translateX(-50%);
    }}

    .marker-arrow {{
        position: absolute;
        left: {marker_position}%;
        top: 21px;
        transform: translateX(-50%);
        color: #c93434;
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
    }}

    .marker-label {{
        position: absolute;
        left: {marker_position}%;
        top: 40px;
        transform: translateX(-50%);
        color: #b82f2f;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.3;
        text-align: center;
        white-space: nowrap;
    }}

    .marker-detail {{
        color: #596b7a;
        font-size: 11px;
        font-weight: 500;
    }}
</style>
</head>

<body>
    <div class="phase-chart">

        <div class="chart-title">
            恋愛4フェーズ上の現在地
        </div>

        <div class="phase-grid">
            {phase_cards}
        </div>

        <div class="progress-area">

            <div class="progress-background"></div>

            <div class="progress-completed"></div>

            <div class="marker"></div>

            <div class="marker-arrow">
                ↑
            </div>

            <div class="marker-label">
                ここで詰まり
                <span class="marker-detail">
                    （フェーズ{current_phase}{progress_label}）
                </span>
            </div>

        </div>
    </div>
</body>
</html>
"""

    components.html(
        chart_html,
        height=210,
        scrolling=False,
    )


# ==================================================
# 診断結果本文の表示
# ==================================================

def display_diagnosis_result(result_text):
    """整形した診断結果を青いボックス内に表示する。"""

    formatted_result = format_diagnosis_result(
        result_text
    )

    diagnosis_url = (
        "https://tksuga3-player.github.io/"
        "diag-x7k2p9/diagnosis-pro/"
    )

    # 回答本文を安全なHTML文字列に変換
    safe_result = html.escape(
        formatted_result
    )

    # 固定URLだけクリック可能なリンクへ変換
    safe_url = html.escape(diagnosis_url)

    clickable_url = (
        f'<a href="{diagnosis_url}" '
        'target="_blank" '
        'rel="noopener noreferrer" '
        'style="'
        'color:#0055a5;'
        'text-decoration:underline;'
        'overflow-wrap:anywhere;'
        '">'
        f"{safe_url}"
        "</a>"
    )

    safe_result = safe_result.replace(
        safe_url,
        clickable_url
    )

    # 改行をHTMLの<br>へ変換
    safe_result = safe_result.replace(
        "\n",
        "<br>"
    )

    answer_html = (
        '<div style="'
        'background-color:#e8f2ff;'
        'color:#0055a5;'
        'padding:20px;'
        'border-radius:10px;'
        'line-height:1.6;'
        'font-size:16px;'
        'font-weight:400;'
        'letter-spacing:normal;'
        'font-family:-apple-system,'
        'BlinkMacSystemFont,'
        '\'Segoe UI\','
        '\'Noto Sans JP\','
        '\'Hiragino Kaku Gothic ProN\','
        '\'Yu Gothic\','
        'Meiryo,'
        'sans-serif;'
        'overflow-wrap:anywhere;'
        '">'
        f"{safe_result}"
        "</div>"
    )

    st.markdown(
        answer_html,
        unsafe_allow_html=True
    )


# ==================================================
# ページ設定
# ==================================================

st.set_page_config(
    page_title="進化心理学 恋愛フェーズ診断",
    page_icon="🧬",
    layout="centered",
)


# ==================================================
# Chrome自動翻訳対策
# ==================================================

components.html(
    """
    <script>
        const documentElement =
            window.parent.document.documentElement;

        documentElement.setAttribute("translate", "no");
        documentElement.classList.add("notranslate");
    </script>
    """,
    height=0,
    width=0,
)


# ==================================================
# UI
# ==================================================

st.title("🧬 無料！")

st.subheader(
    "恋愛を励ますAIではない。デバッグするAIだ。"
)

st.markdown(
    """
「なぜ、あのときうまくいかなかったのか」を、
進化心理学モデルで構造的に分析します。
"""
)

st.divider()


with st.expander(
    "💡 回答の精度を高めるために",
    expanded=False,
):
    st.markdown(
        """
以下の3点を含めて自由記述していただくと、
より正確にボトルネックを分析できます。

1. **相手との現在の関係性**  
   例：マッチングアプリで出会った、職場の同僚など

2. **直近の具体的な出来事**  
   例：食事に誘ったら「忙しい」と言われたなど

3. **あなたが最終的にどうなりたいか**
"""
    )


user_consultation = st.text_area(
    "📝 そのときの出来事や状況を入力してください",
    height=250,
    placeholder=(
        "例：マッチングアプリで出会ったアラサーの女性。"
        "2回目のデートの帰り道で告白したら、"
        "「今はそういうのは考えられない」と強めに言われ、"
        "そそくさと解散した。\n\n"
        "デート中、彼女は笑ってくれていたし、"
        "会話は盛り上がっていたはずなのに、"
        "何が悪かったのか分からない。\n\n"
        "次のデートに誘ったら、"
        "「今は仕事が忙しい時期だから」と言われた。"
        "脈がないなら引くべきなのか。"
    ),
)


disclaimer_text = (
    "<div style='"
    "text-align:center;"
    "font-size:12px;"
    "color:gray;"
    "margin-top:8px;"
    "'>"
    "いただいた相談は、個人が特定できない形で"
    "事例として紹介する場合があります。"
    "</div>"
)


# ==================================================
# 診断処理
# ==================================================

diagnosis_button = st.button(
    "診断する",
    use_container_width=True,
    type="primary",
)


if diagnosis_button:

    if len(user_consultation.strip()) < 20:
        st.error(
            "診断には詳細な情報が必要です。"
            "もう少し具体的に状況を教えてください。"
        )

        st.markdown(
            disclaimer_text,
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            disclaimer_text,
            unsafe_allow_html=True,
        )

        with st.spinner(
            "進化心理学のデータベースと照合中です。"
            "あなたの行動履歴からフェーズを計算しています"
            "（約10〜20秒かかります）"
        ):
            diagnosis_result = call_dify_api(
                user_consultation.strip()
            )

        st.success("✅ 分析が完了しました。")

        current_phase, phase_progress, cleaned_result = (
            parse_phase_metadata(
                diagnosis_result
            )
        )

        # フェーズ情報を取得できた場合だけ図を表示
        if current_phase is not None:
            display_phase_chart(
                current_phase,
                phase_progress
            )

        # 機械判定用データを除いた回答本文を表示
        display_diagnosis_result(
            cleaned_result
        )

else:
    st.markdown(
        disclaimer_text,
        unsafe_allow_html=True,
    )