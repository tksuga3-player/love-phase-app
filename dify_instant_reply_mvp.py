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


def format_diagnosis_result(raw_text):
    """
    表示ルール：
    ・見出しの直前だけ空行を1行入れる
    ・見出し直後には空行を入れない
    ・番号や箇条書きの間には空行を入れない
    """

    if not raw_text:
        return "回答を取得できませんでした。"

    # 通常とは異なる改行文字もすべて統一
    text = (
        raw_text
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
        .replace("\u0085", "\n")
    )

    # splitlines()であらゆる改行を分割
    original_lines = text.splitlines()

    cleaned_lines = []

    for original_line in original_lines:
        line = original_line.strip()

        # 空白だけの行はすべて削除
        if not line:
            continue

        # 見出しの直前だけ空行を1つ追加
        if re.fullmatch(r"【[^】]+】", line):
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")

        cleaned_lines.append(line)

    # 先頭・末尾の空行を削除
    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)

    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def display_diagnosis_result(result_text):
    """整形した診断結果を青いボックス内に表示する。"""

    formatted_result = format_diagnosis_result(result_text)

    # AI回答を安全なHTML文字列へ変換
    safe_result = html.escape(formatted_result)

    answer_html = (
        '<div style="'
        'background-color:#e8f2ff;'
        'color:#0055a5;'
        'padding:20px;'
        'border-radius:10px;'
        'line-height:1.6;'
        'white-space:pre-wrap;'
        'font-size:16px;'
        'overflow-wrap:anywhere;'
        '">'
        f"{safe_result}"
        "</div>"
    )

    st.markdown(answer_html, unsafe_allow_html=True)


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

        display_diagnosis_result(
            diagnosis_result
        )

else:
    st.markdown(
        disclaimer_text,
        unsafe_allow_html=True,
    )