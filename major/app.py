import streamlit as st
from collections import Counter
import math

# --- 1. 設定頁面配置 ---
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
        border-radius: 12px;
        margin-bottom: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 調整 Tabs 的字體大小與間距 */
    button[data-baseweb="tab"] {
        font-size: 18px !important;
        font-weight: bold;
        padding: 0.5rem 1rem !important;
    }

    /* 隱藏預設的 padding 讓畫面更滿 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* Toast 樣式 */
    div[data-baseweb="toast"] {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 初始化 Session State ---
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

# --- 3. 定義牌資料 ---
TILES = {
    "萬": [f"{i}萬" for i in range(1, 10)],
    "筒": [f"{i}筒" for i in range(1, 10)],
    "條": [f"{i}條" for i in range(1, 10)],
    "字": ["東", "南", "西", "北", "中", "發", "白"],
    "花": ["春", "夏", "秋", "冬", "梅", "蘭", "竹", "菊"]
}

# --- 4. 邏輯函式區域 (狀態操作) ---

def add_tile(tile, category):
    # 花牌邏輯
    if category == "花":
        if tile in st.session_state.flower_tiles:
            st.toast(f"⚠️ 花牌「{tile}」重複！", icon="🚫")
            return
        st.session_state.flower_tiles.append(tile)
        st.toast(f"已新增花牌：{tile}", icon="🌸")
        return

    # 手牌邏輯
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
        st.toast("⚠️ 牌數已滿 (16+1張)！", icon="🛑")

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

# --- 5. 核心演算法區域 (包含遞迴檢查) ---

def check_seven_pairs(counts):
    """檢查七對子 (嚦咕嚦咕): 8個對子 + 1張眼 (共17張，但這裡只看結構)"""
    # 注意：台灣麻將七對子通常是特殊牌型 (8對 + 1單)，或是 7對 + 1刻 (16張) 的特殊變體
    # 這裡採用標準判斷：必須全部由對子或四張組成
    total_count = sum(counts.values())
    if total_count != 17: return False
    
    pairs = 0
    threes = 0
    fours = 0
    
    for tile, num in counts.items():
        if num == 2: pairs += 1
        elif num == 3: threes += 1 # 嚦咕嚦咕允許刻子當作3張單牌? 嚴格來說七對子不能有刻子
        elif num == 4: fours += 1
        else: return False # 單張或超過4張都不行
        
    # 寬鬆判定：只要能組成8個pair和1個單張即可
    # 但標準七對子是 8個pair (其中可能有4張一樣算2個pair)
    # 這裡簡化：檢查是否只有對子和四張，且總數對
    # 為了簡化，若符合 pair*N + four*M 且總數17，就算過
    # 實際上台灣麻將的嚦咕嚦咕規則複雜，這裡只做基礎檢查
    valid_groups = pairs + fours * 2
    return valid_groups == 8 and sum(counts.values()) == 17

def check_peng_peng_hu(counts):
    """檢查碰碰胡：由 5 個刻子 + 1 個對子組成"""
    # 這裡只檢查形狀是否為 AAA, BBB, CCC, DDD, EEE, FF
    # 實際上需要遞迴檢查，因為可能有一對眼，剩下的全是刻子
    
    # 簡單過濾：如果這副牌是碰碰胡，那它一定符合 Standard Hu，且沒有順子
    # 所以我們只需要檢查：是不是所有面子都是刻子？
    
    # 這裡用一個取巧的方法：先用 standard_hu 確保能胡，再來算是不是全刻子
    # 但為了獨立性，我們先寫一個簡單檢查
    
    # 嘗試把每一張當眼，剩下的必須全都能被3整除
    for tile in counts:
        if counts[tile] >= 2:
            temp = counts.copy()
            temp[tile] -= 2
            
            all_triplets = True
            for t, num in temp.items():
                if num % 3 != 0:
                    all_triplets = False
                    break
            if all_triplets:
                return True
    return False

def try_remove_sets(counts):
    """
    [遞迴核心] 檢查剩下的牌是否能完全組成 順子 或 刻子
    """
    # 1. 找出目前還有剩餘的牌，並排序 (確保處理順序固定)
    available_tiles = sorted([t for t in counts if counts[t] > 0])
    
    # Base Case: 如果沒有牌了，代表全部配對成功 -> True
    if not available_tiles:
        return True
    
    first = available_tiles[0]
    
    # 情況 A: 嘗試組「刻子」 (AAA)
    if counts[first] >= 3:
        counts[first] -= 3
        if try_remove_sets(counts):
            return True
        counts[first] += 3 # 回溯 (復原)

    # 情況 B: 嘗試組「順子」 (ABC) - 字牌與花牌不能組順子
    if "字" not in first and "花" not in first: 
        try:
            # 解析：例如 "1萬" -> 1, "萬"
            num = int(first[:-1])
            suit = first[-1]
            
            # 順子需要 num+1, num+2
            if num <= 7: # 只有 1~7 能當順子開頭
                t2 = f"{num+1}{suit}"
                t3 = f"{num+2}{suit}"
                
                if counts[t2] > 0 and counts[t3] > 0:
                    counts[first] -= 1
                    counts[t2] -= 1
                    counts[t3] -= 1
                    if try_remove_sets(counts):
                        return True
                    # 回溯
                    counts[first] += 1
                    counts[t2] += 1
                    counts[t3] += 1
        except:
            pass 

    return False

def check_standard_hu(counts):
    """
    檢查一般胡牌型：5組面子 + 1對眼
    """
    # 總張數檢查 (16張手牌 + 1張胡牌 = 17)
    if sum(counts.values()) != 17:
        return False

    # 嘗試每一種牌當作「眼」
    for tile in counts:
        if counts[tile] >= 2:
            counts[tile] -= 2 # 拔掉眼
            if try_remove_sets(counts):
                counts[tile] += 2 # 復原
                return True
            counts[tile] += 2 # 復原，換下一張試試
            
    return False

def calculate_tai():
    hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
    flowers = st.session_state.flower_tiles
    settings = st.session_state.settings
    
    counts = Counter(hand)
    details = []
    total_tai = 0
    
    # === 步驟 1: 判斷是否胡牌 ===
    # 注意：七對子不需要標準胡牌結構，所以分開判斷
    is_seven = check_seven_pairs(counts)
    is_standard = check_standard_hu(counts.copy())
    
    # 如果完全不符合胡牌規則
    if not (is_seven or is_standard):
        return 0, ["❌ 尚未胡牌 (相公或牌型不符)"]

    # === 步驟 2: 計算台數 ===
    
    # --- 特殊牌型偵測 ---
    is_peng_peng = False
    if is_standard:
        # 只有在標準牌型下才檢查碰碰胡
        is_peng_peng = check_peng_peng_hu(counts.copy())

    # 花色判斷 (清一色/混一色/字一色)
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

    # 牌型加台
    if is_seven:
        details.append("七對子 (8台)") # 嚦咕嚦咕
        total_tai += 8
    elif is_peng_peng:
        details.append("碰碰胡 (4台)")
        total_tai += 4
    
    # 平胡判定 (非常簡化版：若是標準胡且無花、無字、非碰碰胡、非獨聽... 這裡暫時只給標準底台概念)
    # 真實平胡邏輯太複雜(涉及聽牌方式)，這裡不做嚴格平胡檢查
    if is_standard and not is_peng_peng and len(details) == 0:
        pass # 普通牌型

    # --- 三元牌與風牌 ---
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

    # --- 狀態台數 ---
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

    # --- 花牌 ---
    if flowers:
        details.append(f"花牌 x{len(flowers)} ({len(flowers)}台)")
        total_tai += len(flowers)
        
    # 若計算結果為 0 台，但已確認胡牌
    if total_tai == 0:
        details.append("一般胡牌 (無特殊台數)")

    return total_tai, details


# --- 6. UI 介面 (手機版重構) ---

st.title("🀄 台麻計算機")

# === 區塊 A: 狀態顯示 Dashboard ===
with st.container(border=True):
    # 1. 顯示胡的那張牌
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

    # 2. 顯示手牌
    st.subheader(f"🎴 手牌 ({len(st.session_state.hand_tiles)}/16)")
    sorted_hand = sorted(st.session_state.hand_tiles)
    
    if sorted_hand:
        tiles_per_row = 8 
        num_rows = math.ceil(len(sorted_hand) / tiles_per_row)
        
        for r in range(num_rows):
            cols = st.columns(tiles_per_row)
            start_idx = r * tiles_per_row
            end_idx = min(start_idx + tiles_per_row, len(sorted_hand))
            
            for i in range(start_idx, end_idx):
                col_idx = i - start_idx
                cols[col_idx].button(sorted_hand[i], key=f"h_{i}", disabled=True)
    else:
        st.info("尚未新增手牌")

    # 3. 花牌顯示
    if st.session_state.flower_tiles:
        st.divider()
        st.write(f"🌸 花牌 ({len(st.session_state.flower_tiles)}) - 點擊移除")
        f_cols = st.columns(8)
        for i, f in enumerate(st.session_state.flower_tiles):
            if f_cols[i % 8].button(f, key=f"f_del_{i}"):
                remove_flower(f)
                st.rerun()

# === 區塊 B: 控制按鈕 ===
c_ctrl1, c_ctrl2 = st.columns(2)
with c_ctrl1:
    if st.button("⬅️ 退回", use_container_width=True):
        remove_last_tile()
        st.rerun()
with c_ctrl2:
    if st.button("🗑️ 清空", type="primary", use_container_width=True):
        reset_game()
        st.rerun()

# === 區塊 C: 遊戲設定 (Expander) ===
with st.expander("⚙️ 設定 (圈風/門風/門清)", expanded=False):
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.session_state.settings['is_self_draw'] = st.checkbox("自摸", value=st.session_state.settings['is_self_draw'])
    with c_s2:
        st.session_state.settings['is_men_qing'] = st.checkbox("門清", value=st.session_state.settings['is_men_qing'])
    
    c_w1, c_w2 = st.columns(2)
    with c_w1:
        st.session_state.settings['wind_round'] = st.selectbox("圈風", ["東", "南", "西", "北"])
    with c_w2:
        st.session_state.settings['wind_seat'] = st.selectbox("門風", ["東", "南", "西", "北"])

# === 區塊 D: 計算按鈕 ===
if st.button("🧮 計算台數", type="primary", use_container_width=True):
    valid_len = len(st.session_state.hand_tiles) == 16 and st.session_state.winning_tile is not None
    if not valid_len:
        st.error("❌ 牌數不足 (需 16+1 張)")
    else:
        score, details = calculate_tai()
        if "❌" in details[0]:
            st.error(details[0])
        else:
            st.balloons()
            st.success(f"### 總計：{score} 台")
            for d in details:
                st.info(d)

# === 區塊 E: 牌型鍵盤 (5個分頁) ===
st.markdown("---")
st.write("👇 **點擊新增牌型**")

tab_names = ["🔴萬", "🔵筒", "🟢條", "⬛字", "🌸花"]
tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)

def render_numpad(tiles, category_key):
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

with tab5:
    cols_h1 = st.columns(4)
    for i in range(4):
        t = TILES["花"][i]
        if cols_h1[i].button(t, key=f"h_{t}", use_container_width=True):
            add_tile(t, "花")
            st.rerun()
    cols_h2 = st.columns(4)
    for i in range(4, 8):
        t = TILES["花"][i]
        if cols_h2[i-4].button(t, key=f"h_{t}", use_container_width=True):
            add_tile(t, "花")
            st.rerun()
