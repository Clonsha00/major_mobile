import streamlit as st
from collections import Counter
import math
import requests 

# ==========================================
# 1. 設定與 CSS 優化
# ==========================================
st.set_page_config(page_title="台灣麻將計算機 (AI版)", layout="centered", page_icon="🀄")

st.markdown("""
<style>
    div.stButton > button {
        height: 3.2rem; 
        width: 100%;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 10px;
        margin-bottom: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    /* 小按鈕樣式 */
    .small-btn > div > button {
        height: 2rem !important;
        font-size: 12px !important;
        padding: 0px !important;
    }
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: bold;
        padding: 0.5rem 0.5rem !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API 設定
# ==========================================
ROBOFLOW_API_KEY = "dKsZfGd1QysNKSoaIT1m"
MODEL_ID = "mahjong-baq4s-c3ovv/1"

# ==========================================
# 3. 初始化 Session State
# ==========================================
if 'hand_tiles' not in st.session_state:
    st.session_state.hand_tiles = []
if 'exposed_tiles' not in st.session_state:
    st.session_state.exposed_tiles = []
if 'winning_tile' not in st.session_state:
    st.session_state.winning_tile = None
if 'flower_tiles' not in st.session_state:
    st.session_state.flower_tiles = []
if 'input_mode' not in st.session_state:
    st.session_state.input_mode = '手牌'
if 'settings' not in st.session_state:
    st.session_state.settings = {
        'is_self_draw': False, 
        'is_dealer': False,     
        'streak': 0,            
        'wind_round': "東",     
        'wind_seat': "東"       
    }

# ==========================================
# 4. 邏輯函式
# ==========================================

def call_roboflow_api(image_file, confidence=40, overlap=30):
    upload_url = f"https://detect.roboflow.com/{MODEL_ID}?api_key={ROBOFLOW_API_KEY}&confidence={confidence}&overlap={overlap}&format=json"
    try:
        response = requests.post(upload_url, files={"file": ("image.jpg", image_file.getvalue(), "image/jpeg")})
        if response.status_code == 200:
            predictions = response.json().get('predictions', [])
            predictions.sort(key=lambda x: x['x'])
            mapping = {
                "1C": "1萬", "2C": "2萬", "3C": "3萬", "4C": "4萬", "5C": "5萬", "6C": "6萬", "7C": "7萬", "8C": "8萬", "9C": "9萬",
                "1D": "1筒", "2D": "2筒", "3D": "3筒", "4D": "4筒", "5D": "5筒", "6D": "6筒", "7D": "7筒", "8D": "8筒", "9D": "9筒",
                "1B": "1條", "2B": "2條", "3B": "3條", "4B": "4條", "5B": "5條", "6B": "6條", "7B": "7條", "8B": "8條", "9B": "9條",
                "1S": "花", "2S": "花", "3S": "花", "4S": "花", "1F": "花", "2F": "花", "3F": "花", "4F": "花",
                "EW": "東", "SW": "南", "WW": "西", "NW": "北", "RD": "中", "GD": "發", "WD": "白"
            }
            return [mapping.get(p['class'], p['class']) for p in predictions]
        return []
    except: return []

def get_total_count():
    return len(st.session_state.hand_tiles) + len(st.session_state.exposed_tiles)*3 + (1 if st.session_state.winning_tile else 0)

def reset_game():
    st.session_state.hand_tiles = []; st.session_state.winning_tile = None
    st.session_state.flower_tiles = []; st.session_state.exposed_tiles = []

def calculate_tai():
    full_hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
    counts = Counter(full_hand); details = []; total_tai = 0
    settings = st.session_state.settings

    # 莊家連莊邏輯
    if settings['is_dealer']:
        details.append("莊家 (1台)"); total_tai += 1
        if settings['streak'] > 0:
            s_tai = settings['streak'] * 2
            details.append(f"連{settings['streak']}拉{settings['streak']} ({s_tai}台)"); total_tai += s_tai

    # 暗刻邏輯
    an_ke_hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if settings['is_self_draw'] else [])
    num_an_ke = sum(1 for t in Counter(an_ke_hand).values() if t >= 3)
    if num_an_ke == 3: details.append("三暗刻 (2台)"); total_tai += 2
    elif num_an_ke == 4: details.append("四暗刻 (5台)"); total_tai += 5
    elif num_an_ke >= 5: details.append("五暗刻 (8台)"); total_tai += 8

    if st.session_state.flower_tiles:
        details.append(f"花牌x{len(st.session_state.flower_tiles)} ({len(st.session_state.flower_tiles)}台)")
        total_tai += len(st.session_state.flower_tiles)

    return total_tai, details if details else ["一般胡牌 (屁胡)"]

# ==========================================
# 5. UI 介面
# ==========================================
st.title("🀄 台麻計算機 (AI版)")

# AI 區塊
with st.expander("📸 AI 拍照 / 📂 上傳"):
    conf = st.slider("信心度", 1, 100, 40)
    img = st.file_uploader("上傳照片", type=['jpg','png']) if st.toggle("切換上傳模式") else st.camera_input("拍照")
    if img and st.button("🚀 執行辨識"):
        res = call_roboflow_api(img, conf)
        if res: 
            st.session_state.ai_res = res
            st.success(f"辨識到: {' '.join(res)}")

# 顯示看板
with st.container(border=True):
    st.subheader("🖐️ 胡牌: " + (st.session_state.winning_tile if st.session_state.winning_tile else "?"))
    
    # 明牌區取消功能
    if st.session_state.exposed_tiles:
        st.caption("🔽 明牌區 (點擊 ❌ 取消)")
        for idx, item in enumerate(st.session_state.exposed_tiles):
            cols = st.columns([3, 1])
            cols[0].info(f"{item['type']}: {''.join(item['tiles'])}")
            if cols[1].button("❌", key=f"del_exp_{idx}"):
                st.session_state.exposed_tiles.pop(idx)
                st.rerun()

    st.write(f"🎴 手牌 ({len(st.session_state.hand_tiles)}張): " + " ".join(sorted(st.session_state.hand_tiles)))
    if st.session_state.flower_tiles: st.write(f"🌸 花: {' '.join(st.session_state.flower_tiles)}")

# 輸入區
st.write("---")
mode = st.radio("模式", ["手牌", "吃", "碰/槓"], horizontal=True)
st.session_state.input_mode = mode

# 牌盤按鈕 (簡化版示意)
for cat, tiles in [("萬", [f"{i}萬" for i in range(1,10)]), ("筒", [f"{i}筒" for i in range(1,10)]), ("條", [f"{i}條" for i in range(1,10)])]:
    cols = st.columns(9)
    for i, t in enumerate(tiles):
        if cols[i].button(t, key=f"btn_{t}"):
            if mode == "手牌" and get_total_count() < 16: st.session_state.hand_tiles.append(t)
            elif mode == "手牌" and get_total_count() == 16: st.session_state.winning_tile = t
            elif mode == "碰/槓": st.session_state.exposed_tiles.append({"type":"碰","tiles":[t]*3})
            st.rerun()

# 設定區
with st.expander("⚙️ 設定", expanded=True):
    c1, c2 = st.columns(2)
    st.session_state.settings['is_self_draw'] = c1.toggle("自摸")
    is_dealer = c2.toggle("莊家", value=st.session_state.settings['is_dealer'])
    st.session_state.settings['is_dealer'] = is_dealer
    
    # 連莊連動邏輯：僅當 is_dealer 為 True 時才顯示連莊數
    if is_dealer:
        st.session_state.settings['streak'] = st.number_input("連莊數 (n)", min_value=0, step=1)
    else:
        st.session_state.settings['streak'] = 0

if st.button("🧮 計算台數", type="primary"):
    if get_total_count() != 17: st.error("牌數不對！")
    else:
        score, lines = calculate_tai()
        st.success(f"### 總計: {score} 台")
        for l in lines: st.info(l)

if st.button("🗑️ 全部清空"): reset_game(); st.rerun()
