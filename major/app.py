import streamlit as st
from collections import Counter
import math
import requests 

# ==========================================
# 1. 設定與 CSS 優化 (完全復原)
# ==========================================
st.set_page_config(page_title="台灣麻將計算機 (AI版)", layout="centered", page_icon="🀄")

st.markdown("""
<style>
    div.stButton > button {
        height: 3.2rem; width: 100%;
        font-size: 18px !important; font-weight: bold;
        border-radius: 10px; margin-bottom: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    button[data-baseweb="tab"] {
        font-size: 16px !important; font-weight: bold;
        padding: 0.5rem 0.5rem !important;
    }
    .block-container { padding-top: 1rem; padding-bottom: 5rem; }
    div[data-testid="stRadio"] > label { font-weight: bold; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API 設定 (修正模型版本為 v2)
# ==========================================
# 您的私有 API Key (來自您的截圖)
ROBOFLOW_API_KEY = "dKsZfGd1QysNKSoaIT1m"
# 修正：將 /1 改為 /2 (因為您的截圖顯示目前是 v2 版本)
MODEL_ID = "mahjong-baq4s-c3ovv/2"

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

# 用於聽牌檢查
ALL_CHECK_TILES = TILES["萬"] + TILES["筒"] + TILES["條"] + TILES["字"]

API_MAPPING = {
    "1C": "1萬", "2C": "2萬", "3C": "3萬", "4C": "4萬", "5C": "5萬", "6C": "6萬", "7C": "7萬", "8C": "8萬", "9C": "9萬",
    "1D": "1筒", "2D": "2筒", "3D": "3筒", "4D": "4筒", "5D": "5筒", "6D": "6筒", "7D": "7筒", "8D": "8筒", "9D": "9筒",
    "1B": "1條", "2B": "2條", "3B": "3條", "4B": "4條", "5B": "5條", "6B": "6條", "7B": "7條", "8B": "8條", "9B": "9條",
    "1S": "花", "2S": "花", "3S": "花", "4S": "花", "1F": "花", "2F": "花", "3F": "花", "4F": "花",
    "EW": "東", "SW": "南", "WW": "西", "NW": "北", "RD": "中", "GD": "發", "WD": "白"
}

# ==========================================
# 5. 邏輯函式
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
    """計算胡牌邏輯總張數 (槓牌視覺4張但邏輯佔3張)"""
    count = len(st.session_state.hand_tiles)
    count += len(st.session_state.exposed_tiles) * 3 
    if st.session_state.winning_tile: count += 1
    return count

def call_roboflow_api(image_file, confidence=40, overlap=30):
    upload_url = "".join([
        "https://detect.roboflow.com/",
        MODEL_ID,
        "?api_key=", ROBOFLOW_API_KEY,
        f"&confidence={confidence}&overlap={overlap}&format=json"
    ])

    try:
        filename = getattr(image_file, 'name', 'image.jpg')
        file_bytes = image_file.getvalue()
        
        response = requests.post(
            upload_url,
            files={"file": (filename, file_bytes, "image/jpeg")}
        )
        
        if response.status_code != 200:
            st.error(f"API 錯誤 ({response.status_code}): {response.text}")
            return []

        result = response.json()
        
        if 'predictions' in result:
            predictions = result['predictions']
            predictions.sort(key=lambda x: x['x'])
            
            detected_tiles = []
            for p in predictions:
                raw = p['class']
                app_name = API_MAPPING.get(raw, raw)
                if "萬" in app_name or "筒" in app_name or "條" in app_name or app_name in TILES["字"] or app_name in TILES["花"]:
                    detected_tiles.append(app_name)
            return detected_tiles
        return []

    except Exception as e:
        st.error(f"連線錯誤: {e}")
        return []

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
        if item['type'] == '碰' or item['type'] == '槓': return False
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

def check_hu_logic_for_ting(temp_counts):
    # 用於聽牌檢測的簡化版胡牌判斷
    if sum(temp_counts.values()) % 3 != 2: return False
    # 標準胡
    for tile in temp_counts:
        if temp_counts[tile] >= 2:
            copy_counts = temp_counts.copy()
            copy_counts[tile] -= 2
            if try_remove_sets(copy_counts): return True
    # 七對子 (聽牌時手牌13+1=14張)
    if sum(temp_counts.values()) == 14:
        pairs = 0
        for t in temp_counts:
            if temp_counts[t] == 2: pairs += 1
            elif temp_counts[t] == 4: pairs += 2
        if pairs == 7: return True
    return False

def get_ting_list():
    """檢測目前聽什麼牌"""
    if get_logic_count() != 16: return []
    ting_res = []
    base_counts = Counter(st.session_state.hand_tiles)
    for t in ALL_CHECK_TILES:
        # 該牌未達4張才可能聽
        if get_tile_usage(t) < 4:
            test_counts = base_counts.copy()
            test_counts[t] += 1
            if check_hu_logic_for_ting(test_counts): ting_res.append(t)
    return ting_res

def calculate_tai():
    hand = st.session_state.hand_tiles[:]
    win_tile = st.session_state.winning_tile
    exposed = st.session_state.exposed_tiles
    flowers = st.session_state.flower_tiles
    settings = st.session_state.settings
    
    full_hand = hand + ([win_tile] if win_tile else [])
    
    # 建立全牌池（包含明牌區）用來算字刻與花色
    exposed_flat = []
    for item in exposed: exposed_flat.extend(item['tiles'])
    total_pool = Counter(full_hand + exposed_flat)
    
    counts = Counter(full_hand)
    details = []
    total_tai = 0
    
    is_seven = check_seven_pairs(counts, len(exposed))
    is_standard = check_standard_hu(counts.copy())
    
    if not (is_seven or is_standard):
        return 0, ["❌ 尚未胡牌"]

    # --- 1. 莊家與連莊 ---
    if settings.get('is_dealer', False):
        details.append("莊家 (1台)"); total_tai += 1
        if settings.get('streak', 0) > 0:
            s_tai = settings['streak'] * 2
            details.append(f"連{settings['streak']}拉{settings['streak']} ({s_tai}台)")
            total_tai += s_tai

    # --- 2. 暗刻計算 ---
    an_ke_pool = hand[:]
    if settings['is_self_draw'] and win_tile:
        an_ke_pool.append(win_tile)
    an_ke_counts = Counter(an_ke_pool)
    num_an_ke = sum(1 for t in an_ke_counts if an_ke_counts[t] >= 3)
    
    if num_an_ke == 3: details.append("三暗刻 (2台)"); total_tai += 2
    elif num_an_ke == 4: details.append("四暗刻 (5台)"); total_tai += 5
    elif num_an_ke >= 5: details.append("五暗刻 (8台)"); total_tai += 8

    # --- 3. 牌型台數 ---
    is_peng_peng = False
    is_ping_hu = False
    if is_standard:
        exposed_all_pong = all(item['type'] in ['碰', '槓'] for item in exposed)
        for tile in counts:
            if counts[tile] >= 2:
                temp = counts.copy()
                temp[tile] -= 2
                if all(temp[t] % 3 == 0 for t in temp) and exposed_all_pong:
                    is_peng_peng = True
                    break
    if is_standard and not is_peng_peng:
        if check_ping_hu(counts.copy(), flowers, exposed):
            is_ping_hu = True

    # --- 4. 花色台數 ---
    all_tiles_list = full_hand + exposed_flat
    suits = set()
    has_honors = False
    for t in all_tiles_list:
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

    # --- 5. 字刻/風刻 (含明牌) ---
    for d in ["中", "發", "白"]:
        if total_pool[d] >= 3: details.append(f"{d}刻 (1台)"); total_tai += 1
    if total_pool[settings['wind_round']] >= 3: details.append(f"圈風{settings['wind_round']} (1台)"); total_tai += 1
    if total_pool[settings['wind_seat']] >= 3: details.append(f"門風{settings['wind_seat']} (1台)"); total_tai += 1

    # --- 6. 自摸/門清 ---
    if settings['is_self_draw']:
        if not any(item['type'] in ['吃', '碰', '槓'] for item in exposed):
            details.append("門清自摸 (3台)"); total_tai += 3
        else: details.append("自摸 (1台)"); total_tai += 1

    # --- 7. 花牌 ---
    if flowers:
        details.append(f"花牌x{len(flowers)} ({len(flowers)}台)"); total_tai += len(flowers)

    if total_tai == 0: details.append("一般胡牌 (屁胡)")
    return total_tai, details

# ==========================================
# 7. UI 介面
# ==========================================

st.title("🀄 台麻計算機 (AI版)")

with st.expander("📸 AI 拍照 / 📂 上傳辨識", expanded=False):
    st.caption(f"目前模型: {MODEL_ID}")
    
    with st.expander("🛠️ 進階參數設定 (辨識不準請點我)", expanded=False):
        col_conf, col_iou = st.columns(2)
        conf_threshold = col_conf.slider("信心度 (Confidence)", 1, 100, 40)
        overlap_threshold = col_iou.slider("重疊過濾 (Overlap)", 1, 100, 30)

    input_source = st.radio("輸入來源", ["📸 使用相機", "📂 上傳照片"], horizontal=True, label_visibility="collapsed")
    img_file = st.camera_input("拍照") if input_source == "📸 使用相機" else st.file_uploader("上傳照片", type=['jpg', 'jpeg', 'png'])

    if 'ai_temp_result' not in st.session_state:
        st.session_state['ai_temp_result'] = []

    if img_file is not None:
        if st.button("🚀 傳送辨識", type="primary"):
            with st.spinner("☁️ AI 運算中..."):
                try:
                    result_list = call_roboflow_api(img_file, confidence=conf_threshold, overlap=overlap_threshold)
                    if result_list:
                        st.session_state['ai_temp_result'] = result_list
                        st.success(f"成功辨識 {len(result_list)} 張")
                    else:
                        st.session_state['ai_temp_result'] = []
                        st.warning("⚠️ 未偵測到牌，請嘗試調低「信心度」。")
                except Exception as e:
                    st.error(f"API 錯誤: {e}")

    if st.session_state['ai_temp_result']:
        st.write("結果：", " ".join(st.session_state['ai_temp_result']))
        c1, c2 = st.columns(2)
        if c1.button("📥 全部填入 (含胡)"):
            result = st.session_state['ai_temp_result']
            reset_game()
            if len(result) > 1:
                st.session_state.winning_tile = result[-1]
                st.session_state.hand_tiles = result[:-1]
            else:
                st.session_state.hand_tiles = result
            st.session_state['ai_temp_result'] = []
            st.rerun()
        if c2.button("📥 僅填手牌"):
            result = st.session_state['ai_temp_result']
            reset_game()
            st.session_state.hand_tiles = result
            st.session_state['ai_temp_result'] = []
            st.rerun()

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
st.session_state.input_mode = st.radio("👇 輸入模式", ["手牌", "吃", "碰", "槓"], horizontal=True, label_visibility="collapsed")
if st.session_state.input_mode == "吃": st.caption("💡 點擊「2萬」加入「234萬」")
elif st.session_state.input_mode == "碰": st.caption("💡 點擊牌加入三張")
elif st.session_state.input_mode == "槓": st.caption("💡 點擊牌加入四張 (算3張空間)")

tabs = st.tabs(["🔴萬", "🔵筒", "🟢條", "⬛字", "🌸花"])

def render_pad(tiles, cat):
    cols = st.columns(5)
    for idx, t in enumerate(tiles):
        if cols[idx % 5].button(t, key=f"btn_{t}"):
            cur_logic = get_logic_count()
            used = get_tile_usage(t)
            mode = st.session_state.input_mode
            
            if cat == "花":
                if t not in st.session_state.flower_tiles:
                    st.session_state.flower_tiles.append(t); st.rerun()
            else:
                limit_reached = False
                if mode == "手牌" and used >= 4: limit_reached = True
                elif mode == "碰" and used > 1: limit_reached = True
                elif mode == "槓" and used > 0: limit_reached = True
                
                if mode == "吃":
                    try:
                        num = int(t[0]); suit = t[1:]
                        if num <= 7:
                            t1, t2, t3 = f"{num}{suit}", f"{num+1}{suit}", f"{num+2}{suit}"
                            if any(get_tile_usage(x) >= 4 for x in [t1, t2, t3]): limit_reached = True
                    except: pass

                if limit_reached:
                    st.error(f"🛑 {t} 或其組合已達上限 (4張)！")
                elif cur_logic < 16:
                    if mode == "手牌": st.session_state.hand_tiles.append(t)
                    elif mode == "碰": st.session_state.exposed_tiles.append({"type":"碰", "tiles":[t]*3})
                    elif mode == "槓": st.session_state.exposed_tiles.append({"type":"槓", "tiles":[t]*4})
                    elif mode == "吃":
                        num = int(t[0])
                        if num <= 7:
                            st.session_state.exposed_tiles.append({"type":"吃", "tiles":[f"{num}{t[1]}", f"{num+1}{t[1]}", f"{num+2}{t[1]}"]})
                    st.rerun()
                elif cur_logic == 16:
                    if used >= 4: st.error(f"🛑 {t} 已達上限！")
                    else: st.session_state.winning_tile = t; st.rerun()

with tabs[0]: render_pad(TILES["萬"], "萬")
with tabs[1]: render_pad(TILES["筒"], "筒")
with tabs[2]: render_pad(TILES["條"], "條")
with tabs[3]: 
    c1=st.columns(4); 
    for i in range(4): 
        if c1[i].button(TILES["字"][i]): 
            if get_tile_usage(TILES["字"][i]) < 4: st.session_state.hand_tiles.append(TILES["字"][i]); st.rerun()
            else: st.error("上限")
    c2=st.columns(4); 
    for i in range(4,7): 
        if c2[i-4].button(TILES["字"][i]): 
            if get_tile_usage(TILES["字"][i]) < 4: st.session_state.hand_tiles.append(TILES["字"][i]); st.rerun()
            else: st.error("上限")
with tabs[4]:
    c1=st.columns(4)
    for i in range(8):
        if c1[i%4].button(TILES["花"][i]): 
            if TILES["花"][i] not in st.session_state.flower_tiles:
                st.session_state.flower_tiles.append(TILES["花"][i]); st.rerun()

st.write("---")
cc1, cc2 = st.columns(2)
if cc1.button("⬅️ 退回"): remove_last_item(); st.rerun()
if cc2.button("🗑️ 清空", type="primary"): reset_game(); st.rerun()

# === 設定區 ===
with st.expander("⚙️ 設定", expanded=True):
    c1, c2 = st.columns(2)
    st.session_state.settings['is_self_draw'] = c1.toggle("自摸", value=st.session_state.settings['is_self_draw'])
    is_dealer = c2.toggle("莊家", value=st.session_state.settings['is_dealer'])
    st.session_state.settings['is_dealer'] = is_dealer
    
    if is_dealer:
        st.session_state.settings['streak'] = st.number_input("連莊數 (n)", min_value=0, step=1, value=st.session_state.settings['streak'], help="連n拉n，台數加倍")
    else:
        st.session_state.settings['streak'] = 0
        
    sc1, sc2 = st.columns(2)
    st.session_state.settings['wind_round'] = sc1.selectbox("圈風", ["東","南","西","北"])
    st.session_state.settings['wind_seat'] = sc2.selectbox("門風", ["東","南","西","北"])

if st.button("🧮 計算台數", type="primary"):
    if get_logic_count() != 17:
        st.error(f"❌ 牌數錯誤：目前 {get_logic_count()} 張 (應為 17)")
    else:
        score, lines = calculate_tai()
        if "❌" in lines[0]: st.error(lines[0])
        else:
            st.balloons()
            st.success(f"### 總計：{score} 台")
            for l in lines: st.info(l)
