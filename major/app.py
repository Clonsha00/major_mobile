import streamlit as st
from collections import Counter
import math

# --- 1. 設定頁面配置 ---
# layout="centered" 在手機上顯示效果通常比 wide 好，因為會集中內容
st.set_page_config(page_title="台灣麻將計算機(手機版)", layout="centered", page_icon="🀄")

# --- CSS樣式優化 (手機專用) ---
st.markdown("""
<style>
    /* 全域按鈕樣式：加大高度，適合手指點擊 */
    div.stButton > button {
        height: 3.5rem; 
        width: 100%;
        font-size: 18px !important;
        font-weight: bold;
        border-radius: 10px;
        margin-bottom: 5px;
    }
    
    /* 調整 Tabs 的字體大小 */
    button[data-baseweb="tab"] {
        font-size: 20px !important;
        font-weight: bold;
    }

    /* 隱藏預設的 padding 讓畫面更滿 */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 初始化 Session State (與原版相同) ---
default_states = {
    'hand_tiles': [],       
    'winning_tile': None,   
    'flower_tiles': [],     
    'settings': {           
        'is_self_draw': False, 
        'is_men_qing': False,  
        'wind_round': "東",    
        'wind_seat': "東"      
    }
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- 3. 定義牌資料 (與原版相同) ---
TILES = {
    "萬": [f"{i}萬" for i in range(1, 10)],
    "筒": [f"{i}筒" for i in range(1, 10)],
    "條": [f"{i}條" for i in range(1, 10)],
    "字": ["東", "南", "西", "北", "中", "發", "白"],
    "花": ["春", "夏", "秋", "冬", "梅", "蘭", "竹", "菊"]
}

# --- 4. 邏輯函式區域 (與原版相同) ---

def add_tile(tile, category):
    if category == "花":
        if tile in st.session_state.flower_tiles:
            st.toast(f"⚠️ 花牌「{tile}」重複！", icon="🚫")
            return
        st.session_state.flower_tiles.append(tile)
        return

    count_in_hand = st.session_state.hand_tiles.count(tile)
    count_in_winning = 1 if st.session_state.winning_tile == tile else 0
    
    if (count_in_hand + count_in_winning) >= 4:
        st.toast(f"⚠️ 「{tile}」已達4張上限！", icon="🚫")
        return

    current_len = len(st.session_state.hand_tiles)
    has_winning = st.session_state.winning_tile is not None

    if current_len < 16:
        st.session_state.hand_tiles.append(tile)
    elif current_len == 16 and not has_winning:
        st.session_state.winning_tile = tile
    else:
        st.toast("⚠️ 牌數已滿！", icon="🛑")

def remove_last_tile():
    if st.session_state.winning_tile:
        st.session_state.winning_tile = None
    elif st.session_state.hand_tiles:
        st.session_state.hand_tiles.pop()

def remove_flower(tile):
    if tile in st.session_state.flower_tiles:
        st.session_state.flower_tiles.remove(tile)

def reset_game():
    st.session_state.hand_tiles = []
    st.session_state.winning_tile = None
    st.session_state.flower_tiles = []

# --- 5. 核心演算法區域 (保留原邏輯，省略重複部分以節省篇幅，功能不變) ---
# ... (這裡直接沿用你原本的 check_seven_pairs, check_peng_peng_hu, calculate_tai) ...
def check_seven_pairs(counts):
    total_count = sum(counts.values())
    if total_count != 17: return False
    pairs = 0
    for tile, num in counts.items():
        if num == 2: pairs += 1
        elif num == 4: pairs += 2
        else: return False
    return pairs == 8

def check_peng_peng_hu(counts):
    for tile in counts:
        if counts[tile] >= 2: 
            temp_counts = counts.copy()
            temp_counts[tile] -= 2
            is_all_triplets = True
            for t, num in temp_counts.items():
                if num == 0: continue
                if num not in [3, 4]:
                    is_all_triplets = False
                    break
            if is_all_triplets: return True
    return False

def calculate_tai():
    hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
    flowers = st.session_state.flower_tiles
    settings = st.session_state.settings
    
    counts = Counter(hand)
    details = []
    total_tai = 0
    
    # 簡化邏輯呈現：花色
    suits = set()
    has_honors = False
    for t in hand:
        if "萬" in t: suits.add("萬")
        elif "筒" in t: suits.add("筒")
        elif "條" in t: suits.add("條")
        else: has_honors = True

    if len(suits) == 0 and has_honors:
        details.append("字一色 (16台)")
        total_tai += 16
    elif len(suits) == 1 and not has_honors:
        details.append("清一色 (8台)")
        total_tai += 8
    elif len(suits) == 1 and has_honors:
        details.append("混一色 (4台)")
        total_tai += 4

    # 牌型
    if check_seven_pairs(counts):
        details.append("七對子 (8台)")
        total_tai += 8
    elif check_peng_peng_hu(counts):
        details.append("碰碰胡 (4台)")
        total_tai += 4

    # 三元牌與風牌
    for dragon in ["中", "發", "白"]:
        if counts[dragon] >= 3:
            details.append(f"{dragon}刻 (1台)")
            total_tai += 1
            
    if counts[settings['wind_round']] >= 3:
        details.append(f"圈風{settings['wind_round']} (1台)")
        total_tai += 1
    if counts[settings['wind_seat']] >= 3:
        details.append(f"門風{settings['wind_seat']} (1台)")
        total_tai += 1

    # 狀態
    if settings['is_men_qing'] and settings['is_self_draw']:
        details.append("門清自摸 (3台)")
        total_tai += 3
    else:
        if settings['is_men_qing']:
            details.append("門清 (1台)")
            total_tai += 1
        if settings['is_self_draw']:
            details.append("自摸 (1台)")
            total_tai += 1

    # 花牌
    if flowers:
        details.append(f"花牌 x{len(flowers)} ({len(flowers)}台)")
        total_tai += len(flowers)

    return total_tai, details


# --- 6. UI 介面 (手機版重構) ---

st.title("🀄 麻將台數計算")

# === 區塊 A: 狀態顯示 Dashboard ===
# 使用 border=True 框起來，視覺比較集中
with st.container(border=True):
    # 1. 顯示胡的那張牌 (最重要，放上面)
    c_win_label, c_win_tile = st.columns([2, 1])
    with c_win_label:
        st.subheader("🖐️ 胡牌")
        if not st.session_state.winning_tile:
            st.caption("請點選第17張")
    with c_win_tile:
        if st.session_state.winning_tile:
            st.button(st.session_state.winning_tile, key="win_display", type="primary")
        else:
            st.button("?", disabled=True)

    st.divider()

    # 2. 顯示手牌 (重點：手機要自動換行)
    st.subheader(f"🎴 手牌 ({len(st.session_state.hand_tiles)}/16)")
    sorted_hand = sorted(st.session_state.hand_tiles)
    
    if sorted_hand:
        # 手機技巧：每行顯示 8 張，兩行解決
        tiles_per_row = 8 
        num_rows = math.ceil(len(sorted_hand) / tiles_per_row)
        
        for r in range(num_rows):
            cols = st.columns(tiles_per_row)
            start_idx = r * tiles_per_row
            end_idx = min(start_idx + tiles_per_row, len(sorted_hand))
            
            for i in range(start_idx, end_idx):
                # 這裡計算 col 的索引，避免超出範圍
                col_idx = i - start_idx
                cols[col_idx].button(sorted_hand[i], key=f"h_{i}", disabled=True)
    else:
        st.info("尚未新增手牌")

    # 3. 花牌顯示
    if st.session_state.flower_tiles:
        st.divider()
        st.write(f"🌸 花牌 ({len(st.session_state.flower_tiles)})")
        f_cols = st.columns(8) # 花牌較小，一行8個可以
        for i, f in enumerate(st.session_state.flower_tiles):
            if f_cols[i % 8].button(f, key=f"f_del_{i}"):
                remove_flower(f)
                st.rerun()

# === 區塊 B: 控制與設定 ===
c_ctrl1, c_ctrl2 = st.columns(2)
with c_ctrl1:
    if st.button("⬅️ 退回上一張", use_container_width=True):
        remove_last_tile()
        st.rerun()
with c_ctrl2:
    if st.button("🗑️ 全部清空", type="primary", use_container_width=True):
        reset_game()
        st.rerun()

# 設定摺疊區 (節省空間)
with st.expander("⚙️ 遊戲設定 (圈風/門風/門清)", expanded=False):
    st.caption("勾選狀態")
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.session_state.settings['is_self_draw'] = st.checkbox("自摸", value=st.session_state.settings['is_self_draw'])
    with c_s2:
        st.session_state.settings['is_men_qing'] = st.checkbox("門清", value=st.session_state.settings['is_men_qing'])
    
    st.caption("風位設定")
    c_w1, c_w2 = st.columns(2)
    with c_w1:
        st.session_state.settings['wind_round'] = st.selectbox("圈風", ["東", "南", "西", "北"])
    with c_w2:
        st.session_state.settings['wind_seat'] = st.selectbox("門風", ["東", "南", "西", "北"])

# === 區塊 C: 計算結果 ===
if st.button("🧮 計算台數", type="primary", use_container_width=True):
    valid_len = len(st.session_state.hand_tiles) == 16 and st.session_state.winning_tile is not None
    if not valid_len:
        st.error("❌ 牌數不足 (需 16+1 張)")
    else:
        score, details = calculate_tai()
        st.balloons()
        st.success(f"### 總計：{score} 台")
        for d in details:
            st.info(d)

# === 區塊 D: 牌型鍵盤 (Tabs 優化版) ===
st.markdown("---")
st.write("👇 **點擊新增牌型**")

# 使用 Tabs 分類，大幅減少垂直捲動
tab1, tab2, tab3, tab4 = st.tabs(["🔴 萬子", "🔵 筒子", "🟢 條子", "🀄 字/花"])

# 定義數字牌的 3x3 網格顯示函式
def render_numpad(tiles, category_key):
    # 將 1-9 分成 3x3
    for row in range(3):
        cols = st.columns(3)
        for col in range(3):
            idx = row * 3 + col
            if idx < len(tiles):
                tile = tiles[idx]
                if cols[col].button(tile, key=f"btn_{category_key}_{tile}", use_container_width=True):
                    add_tile(tile, category_key)
                    st.rerun()

with tab1:
    render_numpad(TILES["萬"], "萬")

with tab2:
    render_numpad(TILES["筒"], "筒")

with tab3:
    render_numpad(TILES["條"], "條")

with tab4:
    st.write("字牌")
    # 字牌 7 張，用 4+3 排列
    cols_z1 = st.columns(4)
    for i in range(4):
        t = TILES["字"][i]
        if cols_z1[i].button(t, key=f"z_{t}", use_container_width=True):
            add_tile(t, "字")
            st.rerun()
    cols_z2 = st.columns(4)
    for i in range(4, 7):
        t = TILES["字"][i]
        if cols_z2[i-4].button(t, key=f"z_{t}", use_container_width=True):
            add_tile(t, "字")
            st.rerun()
            
    st.divider()
    st.write("花牌")
    # 花牌 8 張，4x2
    cols_h1 = st.columns(4)
    for i in range(4):
        t = TILES["花"][i]
        if cols_h1[i].button(t, key=f"h_{t}"):
            add_tile(t, "花")
            st.rerun()
    cols_h2 = st.columns(4)
    for i in range(4, 8):
        t = TILES["花"][i]
        if cols_h2[i-4].button(t, key=f"h_{t}"):
            add_tile(t, "花")
            st.rerun()
