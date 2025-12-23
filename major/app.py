import streamlit as st
from collections import Counter
import math

# --- 1. 設定頁面配置 ---
st.set_page_config(page_title="台灣麻將計算機(含明牌)", layout="centered", page_icon="🀄")

# --- CSS樣式優化 ---
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
    /* 強調目前選中的模式 */
    div[data-testid="stRadio"] > label {
        font-weight: bold;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 初始化 Session State ---
default_states = {
    'hand_tiles': [],       # 手牌 (暗牌)
    'exposed_tiles': [],    # 明牌 (吃/碰/槓) -> 儲存格式: [{"type": "碰", "tiles": ["1萬","1萬","1萬"]}, ...]
    'winning_tile': None,   # 胡的那張
    'flower_tiles': [],     # 花牌
    'input_mode': '手牌',    # 當前輸入模式: 手牌 / 碰 / 吃
    'settings': {           
        'is_self_draw': False, 
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

# --- 4. 邏輯函式區域 ---

def get_total_count():
    # 計算目前牌數：手牌 + 明牌*3 + 胡牌
    # 這裡簡化計算：每個明牌組視為佔用3張空間
    count = len(st.session_state.hand_tiles)
    count += len(st.session_state.exposed_tiles) * 3
    if st.session_state.winning_tile:
        count += 1
    return count

def add_tile(tile, category):
    mode = st.session_state.input_mode
    
    # === 花牌處理 (獨立) ===
    if category == "花":
        if tile in st.session_state.flower_tiles:
            st.toast(f"⚠️ 花牌「{tile}」重複！")
            return
        st.session_state.flower_tiles.append(tile)
        st.toast(f"🌸 新增：{tile}")
        return

    # === 檢查總張數上限 ===
    if get_total_count() >= 17:
        st.toast("⚠️ 牌數已滿 (17張)！請先刪除。", icon="🛑")
        return

    # === 模式 A: 新增手牌 ===
    if mode == '手牌':
        # 檢查手牌內重複 (最多4張)
        current_hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
        if current_hand.count(tile) >= 4:
            st.toast("⚠️ 手牌已達4張上限")
            return
            
        # 判斷是加入手牌還是成為胡牌
        if get_total_count() < 16:
            st.session_state.hand_tiles.append(tile)
        elif get_total_count() == 16:
            st.session_state.winning_tile = tile
        else:
            st.toast("牌數已滿")

    # === 模式 B: 新增 碰/槓 (明牌) ===
    elif mode == '碰/槓':
        # 碰需要該牌剩餘張數足夠
        # 這裡簡化檢查，直接加入
        new_set = {"type": "碰", "tiles": [tile, tile, tile]}
        st.session_state.exposed_tiles.append(new_set)
        st.toast(f"⬇️ 碰：{tile}")
        st.session_state.input_mode = '手牌' # 自動切回手牌模式方便操作

    # === 模式 C: 新增 吃 (明牌) ===
    elif mode == '吃':
        # 邏輯：點擊的是順子的「第一張」 (例如點 2萬 -> 吃 234萬)
        if category == "字":
            st.toast("❌ 字牌不能吃")
            return
        
        try:
            num = int(tile[:-1])
            suit = tile[-1]
            if num > 7:
                st.toast(f"❌ {tile} 無法當作順子開頭 (最大只能吃到 789)")
                return
            
            t1 = f"{num}{suit}"
            t2 = f"{num+1}{suit}"
            t3 = f"{num+2}{suit}"
            
            new_set = {"type": "吃", "tiles": [t1, t2, t3]}
            st.session_state.exposed_tiles.append(new_set)
            st.toast(f"⬇️ 吃：{t1}{t2}{t3}")
            st.session_state.input_mode = '手牌'
        except:
            st.toast("❌ 格式錯誤")

def remove_last_item():
    # 優先移除胡牌 -> 手牌 -> 最後才是明牌
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

# --- 5. 核心演算法 (平胡與胡牌判斷) ---

def try_remove_sets(counts):
    """遞迴：檢查是否能組成 3+3+3...+2"""
    available = sorted([t for t in counts if counts[t] > 0])
    if not available: return True
    first = available[0]
    
    # 試刻子
    if counts[first] >= 3:
        counts[first] -= 3
        if try_remove_sets(counts): return True
        counts[first] += 3
        
    # 試順子 (無字)
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
    """標準胡牌：5面子+1眼"""
    if sum(counts.values()) % 3 != 2: return False # 剩餘牌數必須是 3N+2
    
    for tile in counts:
        if counts[tile] >= 2:
            counts[tile] -= 2
            if try_remove_sets(counts):
                counts[tile] += 2
                return True
            counts[tile] += 2
    return False

def check_seven_pairs(counts, exposed_len):
    """七對子：不能有明牌"""
    if exposed_len > 0: return False
    if sum(counts.values()) != 17: return False
    pairs = 0
    for t in counts:
        if counts[t] == 2: pairs += 1
        elif counts[t] == 4: pairs += 2
    return pairs == 8

def check_ping_hu(counts, flowers, exposed_list):
    """
    平胡檢查 (嚴格版)：
    1. 無花
    2. 無字 (手牌與明牌都不能有字)
    3. 無碰/槓 (明牌區不能有碰，手牌區不能有刻子)
    4. 手牌必須全順子
    5. 必須聽雙頭 (這裡假設成立，顯示時備註)
    """
    # 1. 無花
    if flowers: return False
    
    # 2. 明牌區檢查
    for item in exposed_list:
        if item['type'] == '碰': return False # 平胡不可有碰
        for t in item['tiles']:
            if "字" in t: return False # 平胡不可有字
            
    # 3. 手牌區檢查 (無字)
    for t in counts:
        if "字" in t: return False
        
    # 4. 手牌結構檢查：必須是 1眼 + 全順子 (不能有刻子)
    # 邏輯：嘗試拔掉每一種眼，剩下的必須能「只用順子」組完
    for tile in counts:
        if counts[tile] >= 2:
            temp = counts.copy()
            temp[tile] -= 2
            if can_form_only_sequences(temp):
                return True
    return False

def can_form_only_sequences(counts):
    """遞迴：剩下的牌只能組順子"""
    available = sorted([t for t in counts if counts[t] > 0])
    if not available: return True
    first = available[0]
    
    # 強制順子邏輯
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

def calculate_tai():
    hand = st.session_state.hand_tiles + ([st.session_state.winning_tile] if st.session_state.winning_tile else [])
    exposed_sets = st.session_state.exposed_tiles
    flowers = st.session_state.flower_tiles
    settings = st.session_state.settings
    
    # 門清狀態：若有明牌，強制非門清
    is_actually_men_qing = (len(exposed_sets) == 0)
    
    counts = Counter(hand)
    details = []
    total_tai = 0
    
    # 1. 胡牌判斷
    is_seven = check_seven_pairs(counts, len(exposed_sets))
    is_standard = check_standard_hu(counts.copy()) # 只檢查手牌部分能否湊成面子
    
    if not (is_seven or is_standard):
        return 0, ["❌ 尚未胡牌 (手牌未湊齊)"]

    # 2. 算台邏輯
    
    # --- 碰碰胡偵測 ---
    # 定義：所有面子都是刻子 (包含明牌的碰 和 手牌的刻)
    is_peng_peng = False
    if is_standard:
        # 檢查明牌是否全為碰
        exposed_all_pong = all(item['type'] == '碰' for item in exposed_sets)
        if exposed_all_pong:
            # 檢查手牌去掉眼後，是否全為刻子
            # 這裡簡化：若能胡且無順子結構，大機率是碰碰胡 (嚴格來說要寫遞迴check only triplets)
            # 為了效能，這裡暫時假設：如果不是平胡，且明牌都是碰，且手牌無明顯順子(這裡難判斷)，就判斷碰碰胡？
            # 修正：寫一個 check_only_triplets 比較保險
            is_peng_peng = check_only_triplets_remain(counts.copy())
            
    # --- 平胡偵測 ---
    is_ping_hu = False
    if is_standard and not is_peng_peng:
        if check_ping_hu(counts.copy(), flowers, exposed_sets):
            is_ping_hu = True

    # --- 花色判斷 ---
    # 收集手牌 + 明牌的所有花色
    all_tiles = hand + [t for s in exposed_sets for t in s['tiles']]
    suits = set()
    has_honors = False
    for t in all_tiles:
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

    # --- 牌型台數 ---
    if is_seven:
        details.append("七對子 (8台)")
        total_tai += 8
    elif is_peng_peng:
        details.append("碰碰胡 (4台)")
        total_tai += 4
    elif is_ping_hu:
        details.append("平胡 (2台) *非獨聽")
        total_tai += 2
        
    # --- 三元牌與風牌 ---
    # 需統計手牌 + 明牌
    total_counts = Counter(all_tiles)
    for dragon in ["中", "發", "白"]:
        if total_counts[dragon] >= 3:
            details.append(f"{dragon}刻 (1台)")
            total_tai += 1
    if total_counts[settings['wind_round']] >= 3:
        details.append(f"圈風{settings['wind_round']} (1台)")
        total_tai += 1
    if total_counts[settings['wind_seat']] >= 3:
        details.append(f"門風{settings['wind_seat']} (1台)")
        total_tai += 1

    # --- 狀態台數 (門清/自摸) ---
    # 門清條件：無明牌
    if is_actually_men_qing:
        if settings['is_self_draw']:
            details.append("門清自摸 (3台)") # 1+1+1
            total_tai += 3
        else:
            # 只有門清，沒自摸
            details.append("門清 (1台)")
            total_tai += 1
    else:
        # 非門清，只有自摸算台
        if settings['is_self_draw']:
            details.append("自摸 (1台)")
            total_tai += 1

    # --- 花牌 ---
    if flowers:
        details.append(f"花牌 x{len(flowers)} ({len(flowers)}台)")
        total_tai += len(flowers)

    if total_tai == 0:
        details.append("一般胡牌 (屁胡)")

    return total_tai, details

def check_only_triplets_remain(counts):
    """檢查手牌是否全為刻子+1眼"""
    # 拔眼
    for tile in counts:
        if counts[tile] >= 2:
            temp = counts.copy()
            temp[tile] -= 2
            # 剩下的必須全都能被3整除 (簡單檢查)
            if all(temp[t] % 3 == 0 for t in temp):
                return True
    return False

# --- 6. UI 介面 ---

st.title("🀄 台麻計算機 (Pro)")

# === 區塊 A: 狀態顯示 ===
with st.container(border=True):
    # 1. 顯示胡的那張
    c1, c2 = st.columns([3, 1])
    c1.subheader("🖐️ 胡牌")
    if st.session_state.winning_tile:
        c2.button(st.session_state.winning_tile, key="win_btn", type="primary")
    else:
        c2.button("?", disabled=True)
    
    st.divider()
    
    # 2. 明牌區 (吃碰槓)
    if st.session_state.exposed_tiles:
        st.caption("🔽 明牌區 (落地)")
        cols_ex = st.columns(4)
        for i, item in enumerate(st.session_state.exposed_tiles):
            label = "".join(item['tiles'])
            cols_ex[i % 4].info(f"{label}")
        st.divider()

    # 3. 手牌區 (暗牌)
    st.subheader(f"🎴 手牌 (暗) {len(st.session_state.hand_tiles)}張")
    sorted_hand = sorted(st.session_state.hand_tiles)
    if sorted_hand:
        tiles_per_row = 8 
        num_rows = math.ceil(len(sorted_hand) / tiles_per_row)
        for r in range(num_rows):
            cols = st.columns(tiles_per_row)
            for i in range(tiles_per_row):
                idx = r * tiles_per_row + i
                if idx < len(sorted_hand):
                    cols[i].button(sorted_hand[idx], key=f"h_{idx}", disabled=True)
    else:
        st.info("請輸入手牌")

    # 4. 花牌
    if st.session_state.flower_tiles:
        st.divider()
        st.write(f"🌸 花: {' '.join(st.session_state.flower_tiles)}")

# === 區塊 B: 輸入模式切換 (關鍵) ===
# ==========================================
# [新增功能] 📸 AI 拍照辨識模組
# ==========================================
import base64
from PIL import Image
import io

# 模擬的 AI 辨識結果 (當沒有 API Key 時使用)
def mock_ai_recognition(image_bytes):
    """
    這裡模擬 AI 看到了什麼。
    實際專案中，這裡會呼叫 OpenAI GPT-4o 或 YOLO 模型。
    """
    import time
    time.sleep(1.5) # 模擬運算時間
    # 假設 AI 辨識出一副聽牌
    return {
        "hand": ["1萬", "2萬", "3萬", "4筒", "5筒", "6筒", "7條", "8條", "9條", "東", "東", "發", "發"],
        "exposed": [], # 假設沒拍到吃碰
        "winning": "發" # 假設最後一張是發
    }

# 真實的 OpenAI GPT-4o 呼叫範本 (需填入 API Key)
def call_gpt4o_vision(image_bytes):
    # import openai
    # client = openai.OpenAI(api_key="你的_OPENAI_API_KEY")
    # base64_image = base64.b64encode(image_bytes).decode('utf-8')
    # response = client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": [
    #                 {"type": "text", "text": "Identify all mahjong tiles in this image. Return JSON format with keys: 'hand_tiles' (list of strings like '1萬', '2筒', '東'), 'exposed_tiles' (list of lists for pong/chow), and 'winning_tile' (string or null). Only return JSON."},
    #                 {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
    #             ]
    #         }
    #     ],
    #     response_format={"type": "json_object"}
    # )
    # return json.loads(response.choices[0].message.content)
    return mock_ai_recognition(image_bytes) # 暫時用模擬的

with st.expander("📸 AI 拍照自動填入 (Beta)", expanded=False):
    st.info("💡 提示：請將牌排成一列，光線充足，避免反光。")
    
    # 啟動相機
    img_file = st.camera_input("點擊拍照")
    
    if img_file is not None:
        # 顯示預覽
        # st.image(img_file, caption="已拍攝", width=300)
        
        if st.button("🚀 開始 AI 辨識", type="primary"):
            with st.spinner("🤖 AI 正在看這張照片... (模擬中)"):
                try:
                    # 讀取圖片 bytes
                    bytes_data = img_file.getvalue()
                    
                    # === 呼叫 AI 核心 ===
                    result = mock_ai_recognition(bytes_data) 
                    # 如果你有 API Key，改成: result = call_gpt4o_vision(bytes_data)
                    # ===================

                    # 解析結果並填入 Session State
                    if result:
                        # 1. 清空目前狀態
                        reset_game()
                        
                        # 2. 填入手牌
                        st.session_state.hand_tiles = result.get("hand", [])
                        
                        # 3. 填入明牌 (如果有的話)
                        # 格式轉換: AI回傳的可能是單純 list，需轉成我們的 [{"type":"碰", "tiles":...}] 結構
                        # 這裡暫時略過複雜轉換，假設 AI 很聰明直接回傳對的格式
                        
                        # 4. 填入胡牌
                        st.session_state.winning_tile = result.get("winning")
                        
                        st.success("✅ 辨識成功！已自動填入。")
                        st.rerun()
                except Exception as e:
                    st.error(f"辨識失敗：{e}")

# ==========================================
# [結束] AI 拍照模組
# ==========================================
st.write("---")
mode_cols = st.columns(3)
mode_options = ["手牌", "吃", "碰/槓"]
st.session_state.input_mode = st.radio("👇 選擇輸入模式：", mode_options, horizontal=True, label_visibility="collapsed")

if st.session_state.input_mode == "吃":
    st.caption("💡 提示：點擊「2萬」會自動加入「234萬」")
elif st.session_state.input_mode == "碰/槓":
    st.caption("💡 提示：點擊「中」會自動加入「中中中」")

# === 區塊 C: 牌型鍵盤 ===
tab_names = ["🔴萬", "🔵筒", "🟢條", "⬛字", "🌸花"]
tabs = st.tabs(tab_names)

def render_numpad(tiles, category_key):
    for row in range(3):
        cols = st.columns(3)
        for col in range(3):
            idx = row * 3 + col
            if idx < len(tiles):
                tile = tiles[idx]
                if cols[col].button(tile, key=f"btn_{category_key}_{tile}"):
                    add_tile(tile, category_key)
                    st.rerun()

with tabs[0]: render_numpad(TILES["萬"], "萬")
with tabs[1]: render_numpad(TILES["筒"], "筒")
with tabs[2]: render_numpad(TILES["條"], "條")
with tabs[3]: 
    c1 = st.columns(4); 
    for i in range(4): 
        t=TILES["字"][i]
        if c1[i].button(t): add_tile(t,"字"); st.rerun()
    c2 = st.columns(4)
    for i in range(4,7): 
        t=TILES["字"][i]
        if c2[i-4].button(t): add_tile(t,"字"); st.rerun()
with tabs[4]:
    c1 = st.columns(4)
    for i in range(8):
        t = TILES["花"][i]
        if c1[i%4].button(t): add_tile(t, "花"); st.rerun()

# === 區塊 D: 控制與計算 ===
st.write("---")
c_ctrl1, c_ctrl2 = st.columns(2)
if c_ctrl1.button("⬅️ 退回"): remove_last_item(); st.rerun()
if c_ctrl2.button("🗑️ 清空", type="primary"): reset_game(); st.rerun()

with st.expander("⚙️ 設定 (自摸/風位)", expanded=True):
    st.session_state.settings['is_self_draw'] = st.toggle("自摸", value=st.session_state.settings['is_self_draw'])
    c1, c2 = st.columns(2)
    st.session_state.settings['wind_round'] = c1.selectbox("圈風", ["東", "南", "西", "北"])
    st.session_state.settings['wind_seat'] = c2.selectbox("門風", ["東", "南", "西", "北"])

if st.button("🧮 計算台數", type="primary"):
    total_cnt = get_total_count()
    if total_cnt != 17:
        st.error(f"❌ 牌數錯誤：目前 {total_cnt} 張 (應為 17)")
    else:
        score, details = calculate_tai()
        if "❌" in details[0]:
            st.error(details[0])
        else:
            st.balloons()
            st.success(f"### 總計：{score} 台")
            for d in details:
                st.info(d)
