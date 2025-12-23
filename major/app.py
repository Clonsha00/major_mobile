import streamlit as st
from collections import Counter
import math
import tempfile
import os
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
# 2. API 設定 (已填入你的資料)
# ==========================================
ROBOFLOW_API_KEY = "dKsZfGd1QysNKSoaIT1m"

# 你的模型 ID (保持不變)
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

# 專屬 mahjong-baq4s 資料集的對應表
API_MAPPING = {
    # === 萬子 (Characters) ===
    "1C": "1萬", "2C": "2萬", "3C": "3萬", "4C": "4萬", "5C": "5萬", "6C": "6萬", "7C": "7萬", "8C": "8萬", "9C": "9萬",
    
    # === 筒子 (Dots) ===
    "1D": "1筒", "2D": "2筒", "3D": "3筒", "4D": "4筒", "5D": "5筒", "6D": "6筒", "7D": "7筒", "8D": "8筒", "9D": "9筒",
    
    # === 條子 (Bamboo/Sticks) ===
    "1B": "1條", "2B": "2條", "3B": "3條", "4B": "4條", "5B": "5條", "6B": "6條", "7B": "7條", "8B": "8條", "9B": "9條",
    "1S": "1條", "2S": "2條", "3S": "3條", "4S": "4條", "5S": "5條", "6S": "6條", "7S": "7條", "8S": "8條", "9S": "9條",
    
    # === 風牌 ===
    "EW": "東", "SW": "南", "WW": "西", "NW": "北",
    
    # === 三元牌 ===
    "RD": "中", "GD": "發", "WD": "白",
    
    # === 花牌 ===
    "1F": "花", "2F": "花", "3F": "花", "4F": "花", 
    "5F": "花", "6F": "花", "7F": "花", "8F": "花"
}

# ==========================================
# 5. 邏輯函式
# ==========================================

def call_roboflow_api(image_file):
    """使用 requests 直接呼叫 API (multipart/form-data)"""
    upload_url = "".join([
        "https://detect.roboflow.com/",
        MODEL_ID,
        "?api_key=", ROBOFLOW_API_KEY,
        "&confidence=40&overlap=30&format=json"
    ])

    try:
        # 使用 multipart 上傳圖片，避免 500 錯誤
        filename = getattr(image_file, 'name', 'image.jpg')
        file_bytes = image_file.getvalue()
        
        response = requests.post(
            upload_url,
            files={
                "file": (filename, file_bytes, "image/jpeg")
            }
        )
        
        if response.status_code != 200:
            st.error(f"API 錯誤 ({response.status_code}): {response.text}")
            return []

        result = response.json()

        if 'predictions' in result:
            predictions = result['predictions']
            # 依 x 軸排序 (由左到右)
            predictions.sort(key=lambda x: x['x'])
            
            detected_tiles = []
            for p in predictions:
                raw = p['class']
                app_name = API_MAPPING.get(raw, raw)
                # 過濾合法牌名
                if "萬" in app_name or "筒" in app_name or "條" in app_name or app_name in TILES["字"] or app_name in TILES["花"]:
                    detected_tiles.append(app_name)
            return detected_tiles
        return []

    except Exception as e:
        st.error(f"連線錯誤: {e}")
        return []

def get_total_count():
    count = len(st.session_state.hand_tiles)
    count += len(st.session_state.exposed_tiles) * 3
    if st.session_state.winning_tile:
        count += 1
    return count

def add_tile(tile, category):
    mode = st.session_state.input_mode
    if category == "花":
        if tile not in st.session_state.flower_tiles:
            st.session_state.flower_tiles.append(tile)
            st.toast(f"🌸 新增：{tile}")
        return

    if get_total_count() >= 17:
        st.toast("⚠️ 牌數已滿 (17張)！", icon="🛑")
        return

    if mode == '手牌':
        current_hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
        if current_hand.count(tile) >= 4:
            st.toast("⚠️ 手牌已達4張上限")
            return
        if get_total_count() < 16:
            st.session_state.hand_tiles.append(tile)
        elif get_total_count() == 16:
            st.session_state.winning_tile = tile
    elif mode == '碰/槓':
        st.session_state.exposed_tiles.append({"type": "碰", "tiles": [tile]*3})
        st.toast(f"⬇️ 碰：{tile}")
        st.session_state.input_mode = '手牌'
    elif mode == '吃':
        if category == "字": return
        try:
            num = int(tile[:-1])
            suit = tile[-1]
            if num <= 7:
                t1, t2, t3 = f"{num}{suit}", f"{num+1}{suit}", f"{num+2}{suit}"
                st.session_state.exposed_tiles.append({"type": "吃", "tiles": [t1, t2, t3]})
                st.toast(f"⬇️ 吃：{t1}{t2}{t3}")
                st.session_state.input_mode = '手牌'
        except: pass

def remove_last_item():
    if st.session_state.winning_tile:
        st.session_state.winning_tile = None
    elif st.session_state.hand_tiles:
        st.session_state.hand_tiles.pop()
    elif st.session_state.exposed_tiles:
        st.session_state.exposed_tiles.pop()

def reset_game():
    st.session_state.hand_tiles = []
    st.session_state.winning_tile = None
    st.session_state.flower_tiles = []
    st.session_state.exposed_tiles = []
    st.session_state.input_mode = '手牌'

# ==========================================
# 6. 台數計算邏輯
# ==========================================

def try_remove_sets(counts):
    available = sorted([t for t in counts if counts[t] > 0])
    if not available: return True
    first = available[0]
    if counts[first] >= 3:
        counts[first] -= 3
        if try_remove_sets(counts): return True
        counts[first] += 3
    if "字" not in first:
        try:
            num = int(first[:-1])
            suit = first[-1]
            t2, t3 = f"{num+1}{suit}", f"{num+2}{suit}"
            if counts[t2] > 0 and counts[t3] > 0:
                counts[first]-=1; counts[t2]-=1; counts[t3]-=1
                if try_remove_sets(counts): return True
                counts[first]+=1; counts[t2]+=1; counts[t3]+=1
        except: pass
    return False

def check_standard_hu(counts):
    if sum(counts.values()) % 3 != 2: return False
    for tile in counts:
        if counts[tile] >= 2:
            counts[tile] -= 2
            if try_remove_sets(counts):
                counts[tile] += 2
                return True
            counts[tile] += 2
    return False

def check_seven_pairs(counts, exposed_len):
    if exposed_len > 0: return False
    if sum(counts.values()) != 17: return False
    pairs = 0
    for t in counts:
        if counts[t] == 2: pairs += 1
        elif counts[t] == 4: pairs += 2
    return pairs == 8

def can_form_only_sequences(counts):
    available = sorted([t for t in counts if counts[t] > 0])
    if not available: return True
    first = available[0]
    try:
        num = int(first[:-1])
        suit = first[-1]
        t2, t3 = f"{num+1}{suit}", f"{num+2}{suit}"
        if counts[t2] > 0 and counts[t3] > 0:
            counts[first]-=1; counts[t2]-=1; counts[t3]-=1
            if can_form_only_sequences(counts): return True
            counts[first]+=1; counts[t2]+=1; counts[t3]+=1
    except: pass
    return False

def check_ping_hu(counts, flowers, exposed_list):
    if flowers: return False
    for item in exposed_list:
        if item['type'] == '碰': return False
        for t in item['tiles']:
            if "字" in t: return False
    for t in counts:
        if "字" in t: return False
    for tile in counts:
        if counts[tile] >= 2:
            temp = counts.copy()
            temp[tile] -= 2
            if can_form_only_sequences(temp):
                return True
    return False

def calculate_tai():
    hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
    exposed_sets = st.session_state.exposed_tiles
    flowers = st.session_state.flower_tiles
    settings = st.session_state.settings
    
    counts = Counter(hand)
    details = []
    total_tai = 0
    
    is_seven = check_seven_pairs(counts, len(exposed_sets))
    is_standard = check_standard_hu(counts.copy())
    
    if not (is_seven or is_standard):
        return 0, ["❌ 尚未胡牌"]

    is_peng_peng = False
    is_ping_hu = False
    
    if is_standard:
        exposed_all_pong = all(item['type'] == '碰' for item in exposed_sets)
        # 簡易判斷碰碰胡
        for tile in counts:
            if counts[tile] >= 2:
                temp = counts.copy()
                temp[tile] -= 2
                # 檢查剩下是否全被3整除
                if all(temp[t] % 3 == 0 for t in temp) and exposed_all_pong:
                    is_peng_peng = True
                    break
        
    if is_standard and not is_peng_peng:
        if check_ping_hu(counts.copy(), flowers, exposed_sets):
            is_ping_hu = True

    all_tiles = hand + [t for s in exposed_sets for t in s['tiles']]
    suits = set()
    has_honors = False
    for t in all_tiles:
        if "萬" in t: suits.add("萬")
        elif "筒" in t: suits.add("筒")
        elif "條" in t: suits.add("條")
        else: has_honors = True

    if len(suits) == 0 and has_honors: details.append("字一色 (16台)"); total_tai += 16
    elif len(suits) == 1 and not has_honors: details.append("清一色 (8台)"); total_tai += 8
    elif len(suits) == 1 and has_honors: details.append("混一色 (4台)"); total_tai += 4

    if is_seven: details.append("七對子 (8台)"); total_tai += 8
    elif is_peng_peng: details.append("碰碰胡 (4台)"); total_tai += 4
    elif is_ping_hu: details.append("平胡 (2台)"); total_tai += 2

    total_counts = Counter(all_tiles)
    for d in ["中", "發", "白"]:
        if total_counts[d] >= 3: details.append(f"{d}刻 (1台)"); total_tai += 1
    if total_counts[settings['wind_round']] >= 3: details.append(f"圈風{settings['wind_round']} (1台)"); total_tai += 1
    if total_counts[settings['wind_seat']] >= 3: details.append(f"門風{settings['wind_seat']} (1台)"); total_tai += 1

    is_actually_men_qing = (len(exposed_sets) == 0)
    if is_actually_men_qing:
        if settings['is_self_draw']: details.append("門清自摸 (3台)"); total_tai += 3
        else: details.append("門清 (1台)"); total_tai += 1
    else:
        if settings['is_self_draw']: details.append("自摸 (1台)"); total_tai += 1

    if flowers: details.append(f"花牌x{len(flowers)} ({len(flowers)}台)"); total_tai += len(flowers)
    if total_tai == 0: details.append("一般胡牌 (屁胡)")
    return total_tai, details

# ==========================================
# 7. UI 介面
# ==========================================

st.title("🀄 台麻計算機 (AI版)")

with st.expander("📸 AI 拍照辨識", expanded=False):
    st.caption(f"目前模型: {MODEL_ID}")
    img_file = st.camera_input("請將牌排成一列拍攝")
    
    if img_file and st.button("🚀 傳送辨識", type="primary"):
        with st.spinner("☁️ AI 運算中..."):
            result_list = call_roboflow_api(img_file)
            if result_list:
                st.success(f"成功辨識 {len(result_list)} 張")
                st.write("結果：", " ".join(result_list))
                
                c1, c2 = st.columns(2)
                if c1.button("📥 全部填入 (含胡)"):
                    reset_game()
                    if len(result_list) > 1:
                        st.session_state.winning_tile = result_list[-1]
                        st.session_state.hand_tiles = result_list[:-1]
                    else:
                        st.session_state.hand_tiles = result_list
                    st.rerun()
                if c2.button("📥 僅填手牌"):
                    reset_game()
                    st.session_state.hand_tiles = result_list
                    st.rerun()
            else:
                st.warning("⚠️ 未偵測到牌，請確認模型是否已部屬 (Deployed) 且照片清晰。")

# Dashboard
with st.container(border=True):
    c1, c2 = st.columns([3, 1])
    c1.subheader("🖐️ 胡牌")
    if st.session_state.winning_tile:
        c2.button(st.session_state.winning_tile, key="w_btn", type="primary")
    else:
        c2.button("?", disabled=True)
    
    if st.session_state.exposed_tiles:
        st.divider()
        st.caption("🔽 明牌區")
        cols = st.columns(4)
        for i, item in enumerate(st.session_state.exposed_tiles):
            cols[i%4].info("".join(item['tiles']))
            
    st.divider()
    st.subheader(f"🎴 手牌 {len(st.session_state.hand_tiles)}張")
    sorted_hand = sorted(st.session_state.hand_tiles)
    if sorted_hand:
        tiles_per_row = 8
        rows = math.ceil(len(sorted_hand)/tiles_per_row)
        for r in range(rows):
            cols = st.columns(tiles_per_row)
            for i in range(tiles_per_row):
                idx = r*tiles_per_row + i
                if idx < len(sorted_hand):
                    cols[i].button(sorted_hand[idx], key=f"h_{idx}", disabled=True)
    else:
        st.info("請輸入手牌")
        
    if st.session_state.flower_tiles:
        st.divider()
        st.write(f"🌸 花: {' '.join(st.session_state.flower_tiles)}")

st.write("---")
st.session_state.input_mode = st.radio("👇 輸入模式", ["手牌", "吃", "碰/槓"], horizontal=True, label_visibility="collapsed")
if st.session_state.input_mode == "吃": st.caption("💡 點擊「2萬」加入「234萬」")
elif st.session_state.input_mode == "碰/槓": st.caption("💡 點擊牌加入三張")

tabs = st.tabs(["🔴萬", "🔵筒", "🟢條", "⬛字", "🌸花"])
def render_pad(tiles, cat):
    for r in range(3):
        cols = st.columns(3)
        for c in range(3):
            idx = r*3+c
            if idx < len(tiles):
                t = tiles[idx]
                if cols[c].button(t, key=f"b_{cat}_{t}"):
                    add_tile(t, cat)
                    st.rerun()

with tabs[0]: render_pad(TILES["萬"], "萬")
with tabs[1]: render_pad(TILES["筒"], "筒")
with tabs[2]: render_pad(TILES["條"], "條")
with tabs[3]: 
    c1=st.columns(4); 
    for i in range(4): 
        if c1[i].button(TILES["字"][i]): add_tile(TILES["字"][i],"字"); st.rerun()
    c2=st.columns(4); 
    for i in range(4,7): 
        if c2[i-4].button(TILES["字"][i]): add_tile(TILES["字"][i],"字"); st.rerun()
with tabs[4]:
    c1=st.columns(4)
    for i in range(8):
        if c1[i%4].button(TILES["花"][i]): add_tile(TILES["花"][i],"花"); st.rerun()

st.write("---")
cc1, cc2 = st.columns(2)
if cc1.button("⬅️ 退回"): remove_last_item(); st.rerun()
if cc2.button("🗑️ 清空", type="primary"): reset_game(); st.rerun()

with st.expander("⚙️ 設定", expanded=True):
    st.session_state.settings['is_self_draw'] = st.toggle("自摸", value=st.session_state.settings['is_self_draw'])
    sc1, sc2 = st.columns(2)
    st.session_state.settings['wind_round'] = sc1.selectbox("圈風", ["東","南","西","北"])
    st.session_state.settings['wind_seat'] = sc2.selectbox("門風", ["東","南","西","北"])

if st.button("🧮 計算台數", type="primary"):
    total = get_total_count()
    if total != 17:
        st.error(f"❌ 牌數錯誤：目前 {total} 張 (應為 17)")
    else:
        score, lines = calculate_tai()
        if "❌" in lines[0]: st.error(lines[0])
        else:
            st.balloons()
            st.success(f"### 總計：{score} 台")
            for l in lines: st.info(l)
