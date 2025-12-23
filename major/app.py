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
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: bold;
        padding: 0.5rem 0.5rem !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
    }
    div[data-testid="stRadio"] > label {
        font-weight: bold;
        font-size: 16px;
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
default_states = {
    'hand_tiles': [],       
    'exposed_tiles': [],    
    'winning_tile': None,   
    'flower_tiles': [],     
    'input_mode': '手牌',    
    'settings': {           
        'is_self_draw': False, 
        'is_dealer': False,     
        'streak': 0,            
        'wind_round': "東",     
        'wind_seat': "東"       
    }
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==========================================
# 4. 定義牌資料與對應表
# ==========================================
TILES = {
    "萬": [f"{i}萬" for i in range(1, 10)],
    "筒": [f"{i}筒" for i in range(1, 10)],
    "條": [f"{i}條" for i in range(1, 10)],
    "字": ["東", "南", "西", "北", "中", "發", "白"],
    "花": ["春", "夏", "秋", "冬", "梅", "蘭", "竹", "菊"]
}

API_MAPPING = {
    "1C": "1萬", "2C": "2萬", "3C": "3萬", "4C": "4萬", "5C": "5萬", "6C": "6萬", "7C": "7萬", "8C": "8萬", "9C": "9萬",
    "1D": "1筒", "2D": "2筒", "3D": "3筒", "4D": "4筒", "5D": "5筒", "6D": "6筒", "7D": "7筒", "8D": "8筒", "9D": "9筒",
    "1B": "1條", "2B": "2條", "3B": "3條", "4B": "4條", "5B": "5條", "6B": "6條", "7B": "7條", "8B": "8條", "9B": "9條",
    "1S": "花", "2S": "花", "3S": "花", "4S": "花", "1F": "花", "2F": "花", "3F": "花", "4F": "花",
    "EW": "東", "SW": "南", "WW": "西", "NW": "北", "RD": "中", "GD": "發", "WD": "白"
}

ALL_CHECK_TILES = TILES["萬"] + TILES["筒"] + TILES["條"] + TILES["字"]

# ==========================================
# 5. 邏輯輔助函式
# ==========================================

def get_tile_usage(tile):
    """計算特定牌在全場(手、明、胡)已使用的張數"""
    count = st.session_state.hand_tiles.count(tile)
    for item in st.session_state.exposed_tiles:
        count += item['tiles'].count(tile)
    if st.session_state.winning_tile == tile:
        count += 1
    return count

def get_logic_count():
    """計算胡牌邏輯總張數 (槓牌顯示4張但邏輯佔3張)"""
    count = len(st.session_state.hand_tiles)
    for item in st.session_state.exposed_tiles:
        count += 3 
    if st.session_state.winning_tile: count += 1
    return count

def check_hu_logic(temp_counts):
    """標準胡牌檢測演算法"""
    def can_decompose(rem_counts):
        rem_list = sorted([t for t in rem_counts if rem_counts[t] > 0])
        if not rem_list: return True
        first = rem_list[0]
        if rem_counts[first] >= 3:
            rem_counts[first] -= 3
            if can_decompose(rem_counts): return True
            rem_counts[first] += 3
        if any(s in first for s in ["萬", "筒", "條"]):
            num, suit = int(first[0]), first[1]
            if num <= 7:
                t2, t3 = f"{num+1}{suit}", f"{num+2}{suit}"
                if rem_counts[t2] > 0 and rem_counts[t3] > 0:
                    rem_counts[first] -= 1; rem_counts[t2] -= 1; rem_counts[t3] -= 1
                    if can_decompose(rem_counts): return True
                    rem_counts[first] += 1; rem_counts[t2] += 1; rem_counts[t3] += 1
        return False
    for t in temp_counts:
        if temp_counts[t] >= 2:
            copy_counts = temp_counts.copy()
            copy_counts[t] -= 2
            if can_decompose(copy_counts): return True
    return False

def get_ting_list():
    """檢測目前聽什麼牌"""
    if get_logic_count() != 16: return []
    ting_res = []
    base_counts = Counter(st.session_state.hand_tiles)
    for t in ALL_CHECK_TILES:
        if get_tile_usage(t) < 4:
            test_counts = base_counts.copy()
            test_counts[t] += 1
            if check_hu_logic(test_counts): ting_res.append(t)
    return ting_res

# ==========================================
# 6. 台數計算邏輯
# ==========================================

def calculate_tai():
    hand = st.session_state.hand_tiles[:]
    win_tile = st.session_state.winning_tile
    exposed = st.session_state.exposed_tiles
    flowers = st.session_state.flower_tiles
    settings = st.session_state.settings
    
    full_hand = hand + ([win_tile] if win_tile else [])
    # 建立全牌池（包含明牌區）用來算字刻
    exposed_flat = []
    for item in exposed: exposed_flat.extend(item['tiles'])
    total_pool = Counter(full_hand + exposed_flat)
    
    details = []; total_tai = 0

    # 1. 莊家與連莊
    if settings['is_dealer']:
        details.append("莊家 (1台)"); total_tai += 1
        if settings['streak'] > 0:
            s_tai = settings['streak'] * 2
            details.append(f"連{settings['streak']}拉{settings['streak']} ({s_tai}台)"); total_tai += s_tai

    # 2. 暗刻計算 (自摸胡的那張算暗刻)
    an_ke_pool = hand + ([win_tile] if settings['is_self_draw'] else [])
    num_an_ke = sum(1 for t in Counter(an_ke_pool).values() if t >= 3)
    if num_an_ke == 3: details.append("三暗刻 (2台)"); total_tai += 2
    elif num_an_ke == 4: details.append("四暗刻 (5台)"); total_tai += 5
    elif num_an_ke >= 5: details.append("五暗刻 (8台)"); total_tai += 8

    # 3. 字刻/風刻 (含明牌區)
    for d in ["中", "發", "白"]:
        if total_pool[d] >= 3: details.append(f"{d}刻 (1台)"); total_tai += 1
    if total_pool[settings['wind_round']] >= 3: details.append(f"圈風{settings['wind_round']} (1台)"); total_tai += 1
    if total_pool[settings['wind_seat']] >= 3: details.append(f"門風{settings['wind_seat']} (1台)"); total_tai += 1

    # 4. 自摸與門清
    if settings['is_self_draw']:
        if not any(item['type'] in ['吃', '碰', '槓'] for item in exposed):
            details.append("門清自摸 (3台)"); total_tai += 3
        else: details.append("自摸 (1台)"); total_tai += 1

    # 5. 花牌
    if flowers:
        details.append(f"花牌x{len(flowers)} ({len(flowers)}台)"); total_tai += len(flowers)

    return total_tai, details if details else ["一般胡牌 (屁胡)"]

# ==========================================
# 7. UI 介面
# ==========================================

st.title("🀄 台麻計算機 (AI版)")

# AI 辨識區
with st.expander("📸 AI 拍照 / 📂 上傳辨識", expanded=False):
    col_conf, col_iou = st.columns(2)
    conf_threshold = col_conf.slider("信心度 (Confidence)", 1, 100, 40)
    overlap_threshold = col_iou.slider("重疊過濾 (Overlap)", 1, 100, 30)
    
    input_source = st.radio("輸入來源", ["📸 使用相機", "📂 上傳照片"], horizontal=True, label_visibility="collapsed")
    img_file = st.camera_input("拍照") if input_source == "📸 使用相機" else st.file_uploader("上傳照片", type=['jpg', 'png'])

    if img_file and st.button("🚀 執行辨識", type="primary"):
        # 此處呼叫 call_roboflow_api 邏輯...
        pass

# 看板
ting_list = get_ting_list()
with st.container(border=True):
    col_h1, col_h2 = st.columns([3, 1])
    col_h1.subheader("🖐️ 胡牌: " + (st.session_state.winning_tile if st.session_state.winning_tile else "?"))
    if ting_list: col_h1.warning(f"📢 聽牌：{', '.join(ting_list)}")
    
    if st.session_state.exposed_tiles:
        st.caption("🔽 明牌區 (點擊 ❌ 刪除)")
        for idx, item in enumerate(st.session_state.exposed_tiles):
            c_exp = st.columns([4, 1])
            c_exp[0].info(f"{item['type']}: {' '.join(item['tiles'])}")
            if c_exp[1].button("❌", key=f"del_exp_{idx}"):
                st.session_state.exposed_tiles.pop(idx); st.rerun()

    st.divider()
    st.write(f"🎴 手牌 ({len(st.session_state.hand_tiles)}張): " + " ".join(sorted(st.session_state.hand_tiles)))
    if st.session_state.flower_tiles: st.write(f"🌸 花: {' '.join(st.session_state.flower_tiles)}")

# 輸入區
st.write("---")
mode = st.radio("👇 輸入模式", ["手牌", "吃", "碰", "槓"], horizontal=True)

tabs = st.tabs(["🔴萬", "🔵筒", "🟢條", "⬛字", "🌸花"])
def render_buttons(tiles, cat):
    cols = st.columns(5)
    for idx, t in enumerate(tiles):
        if cols[idx % 5].button(t, key=f"btn_{t}"):
            cur_logic = get_logic_count()
            used = get_tile_usage(t)
            
            if cat == "花":
                if t not in st.session_state.flower_tiles: st.session_state.flower_tiles.append(t)
            elif cur_logic < 16:
                if used >= 4: st.toast(f"🛑 {t} 已達上限"); return
                if mode == "手牌": st.session_state.hand_tiles.append(t)
                elif mode == "碰": 
                    if used > 1: st.toast(f"🛑 {t} 數量不足以碰"); return
                    st.session_state.exposed_tiles.append({"type":"碰", "tiles":[t]*3})
                elif mode == "槓": 
                    if used > 0: st.toast(f"🛑 {t} 數量不足以槓"); return
                    st.session_state.exposed_tiles.append({"type":"槓", "tiles":[t]*4})
                elif mode == "吃":
                    num = int(t[0])
                    if num <= 7:
                        t1, t2, t3 = f"{num}{t[1]}", f"{num+1}{t[1]}", f"{num+2}{t[1]}"
                        if all(get_tile_usage(x) < 4 for x in [t1,t2,t3]):
                            st.session_state.exposed_tiles.append({"type":"吃", "tiles":[t1,t2,t3]})
            elif cur_logic == 16:
                if used >= 4: st.toast(f"🛑 {t} 已達上限"); return
                st.session_state.winning_tile = t
            st.rerun()

for i, cat in enumerate(["萬", "筒", "條", "字", "花"]):
    with tabs[i]: render_buttons(TILES[cat], cat)

st.write("---")
cc1, cc2 = st.columns(2)
if cc1.button("⬅️ 退回最後一項"):
    if st.session_state.winning_tile: st.session_state.winning_tile = None
    elif st.session_state.hand_tiles: st.session_state.hand_tiles.pop()
    st.rerun()
if cc2.button("🗑️ 全部清空", type="primary"):
    st.session_state.hand_tiles = []; st.session_state.exposed_tiles = []; st.session_state.winning_tile = None; st.session_state.flower_tiles = []
    st.rerun()

# 設定區
with st.expander("⚙️ 設定", expanded=True):
    c1, c2 = st.columns(2)
    st.session_state.settings['is_self_draw'] = c1.toggle("自摸", value=st.session_state.settings['is_self_draw'])
    is_dealer = c2.toggle("莊家", value=st.session_state.settings['is_dealer'])
    st.session_state.settings['is_dealer'] = is_dealer
    
    if is_dealer:
        st.session_state.settings['streak'] = st.number_input("連莊數 (n)", min_value=0, step=1, value=st.session_state.settings['streak'])
    else:
        st.session_state.settings['streak'] = 0
        
    sc1, sc2 = st.columns(2)
    st.session_state.settings['wind_round'] = sc1.selectbox("圈風", ["東","南","西","北"])
    st.session_state.settings['wind_seat'] = sc2.selectbox("門風", ["東","南","西","北"])

if st.button("🧮 計算台數", type="primary"):
    if get_logic_count() != 17: st.error(f"❌ 牌數錯誤：應為 17 張，目前邏輯總數 {get_logic_count()} 張")
    else:
        score, lines = calculate_tai()
        st.balloons(); st.success(f"### 總計：{score} 台"); [st.info(l) for l in lines]
