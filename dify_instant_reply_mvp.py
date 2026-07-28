import streamlit as st
import requests
import streamlit.components.v1 as components

# --- Dify API設定 ---
DIFY_API_URL = "https://api.dify.ai/v1/completion-messages"
# 🛑 修正箇所: APIキーを直接書かず、StreamlitのSecretsから読み込むように変更
DIFY_API_KEY = st.secrets["DIFY_API_KEY"]

def call_dify_api(user_text):
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {"user_input": user_text},
        "response_mode": "blocking", 
        "user": "streamlit-web-user" 
    }
    try:
        response = requests.post(DIFY_API_URL, headers=headers, json=payload)
        response.raise_for_status() 
        result_data = response.json()
        return result_data.get("answer", "エラー：回答を抽出できませんでした。")
    except requests.exceptions.RequestException as e:
        return f"通信エラーが発生しました。設定を確認してください。\n詳細: {e}"

# --- ページ設定と翻訳ブロック ---
# page_title はブラウザのタブに表示される名前です。自由に変更してください。
st.set_page_config(page_title="進化心理学 恋愛フェーズ診断", page_icon="🧬", layout="centered")

# 【修正版】自動翻訳暴走対策
# lang="ja" の動的付与はChromeを混乱させるため行わず、シンプルな翻訳禁止指定のみに留めます。
components.html(
    """
    <script>
        var doc = window.parent.document.documentElement;
        doc.setAttribute("translate", "no");
        doc.classList.add("notranslate");
    </script>
    """,
    height=0,
    width=0,
)

# --- UI設計 ---
st.title(" 🧬 無料！ あなたの恋愛現在地")
st.markdown("""
「なぜ、あのときうまくいかなかったのか」を、進化心理学モデルで構造的に分析します。
""")

st.divider()

# expanderのデフォルトを閉じた状態に変更 (expanded=False)
with st.expander("💡 回答の精度を高めるために", expanded=False):
    st.markdown("""
    以下の3点を含めて自由記述していただくと、より残酷なまでにボトルネックが判明します。
    1. **相手との現在の関係性**（例：マチアプで出会った、職場で普段話してる同僚等）
    2. **直近の具体的な出来事**（例：ご飯に誘ったら「忙しい」と言われた、デート中の言動等）
    3. **あなたが最終的にどうなりたいか**
    """)

user_consultation = st.text_area(
    "📝 そのときの出来事や状況を入力してください",
    height=250,
    placeholder="""例：マチアプで出会ったアラサーの女性。2回目のデートの帰り道で意を決して告白したら「今はそういうのは考えられない」と強めに言われてそそくさと解散した。  
デート中、彼女は笑ってくれてたし、会話は盛り上がっていたはずなのに何が悪かったのか分からない。誠実さが足りなかったのか、もう少し会う回数を重ねるべきだったのか。  
次のデートに誘ったら「今は仕事が忙しい時期だから」と言われる。脈がないなら引くべきなのか。"""
)

# 注意書き（ディスクレーマー）を変数として定義
disclaimer_text = "<div style='text-align: center; font-size: 12px; color: gray; margin-top: 8px;'>いただいた相談は、個人が特定できない形で事例として紹介する場合があります。</div>"

if st.button("診断する", use_container_width=True, type="primary"):
    if len(user_consultation) < 20:
        st.error("診断には詳細な情報が必要です。もう少し具体的に状況を教えてください。")
        # エラー時にも注意書きを表示
        st.markdown(disclaimer_text, unsafe_allow_html=True)
    else:
        # 処理中にもボタンの下に注意書きを表示
        st.markdown(disclaimer_text, unsafe_allow_html=True)
        
        with st.spinner("進化心理学のデータベースと照合中... \nあなたの行動履歴からフェーズを計算しています（約10〜20秒かかります）"):
            diagnosis_result = call_dify_api(user_consultation)
        
        st.success("✅ 分析が完了しました。")
        st.info(diagnosis_result)
        
else:
    # 初期状態（ボタンが押される前）にボタンの下に表示
    st.markdown(disclaimer_text, unsafe_allow_html=True)