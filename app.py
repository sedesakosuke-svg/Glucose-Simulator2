import streamlit as st
import matplotlib.pyplot as plt
import math

plt.rcParams['font.family'] = 'MS Gothic'

if "insulins" not in st.session_state:
    st.session_state.insulins = [
        {"time": 7 * 60, "dose": 6, "type": "rapid"},
        {"time": 19 * 60, "dose": 6, "type": "rapid"},
        {"time": 0, "dose": 20, "type": "basal"},
    ]


# -----------------------------
# Dawn phenomenon（個人差モデル）
# -----------------------------
def dawn_phenomenon(t, strength, peak_time, width, variability):
    import random
    daily_factor = 1 + variability * (random.random() - 0.5)
    effective_strength = strength * daily_factor
    return effective_strength * math.exp(-((t - peak_time) ** 2) / (2 * width ** 2))


# -----------------------------
# GLP-1 週1製剤
# -----------------------------
def glp1_effect(t, inj_time, dose):
    tau = 3 * 24 * 60
    if t < inj_time:
        return 0
    return dose * math.exp(-(t - inj_time) / tau)


# -----------------------------
# 食事イベント
# -----------------------------
def meal_glucose(t, meal_time, carb, GI, glp1_level):
    k = 1.2
    GI_effective = GI * (1 - 0.3 * glp1_level)
    peak_rise = carb * GI_effective * k
    peak_time = meal_time + 45 * (1 + 0.2 * glp1_level)
    width = 30
    return peak_rise * math.exp(-((t - peak_time) ** 2) / (2 * width ** 2))


# -----------------------------
# 運動イベント
# -----------------------------
def exercise_glucose(t, start, duration, intensity):
    end = start + duration
    if start <= t <= end:
        return -0.5 * intensity
    return 0


# -----------------------------
# 睡眠（インスリン感受性）
# -----------------------------
def insulin_sensitivity(t, sleep_start, sleep_end):
    if sleep_start > sleep_end:
        return 0.9 if (t >= sleep_start or t <= sleep_end) else 1.0
    return 0.9 if sleep_start <= t <= sleep_end else 1.0


# -----------------------------
# インスリン作用
# -----------------------------
def insulin_action(t, inj_time, dose, insulin_type="rapid"):
    if insulin_type == "rapid":
        peak = inj_time + 60
        width = 50
        return -dose * math.exp(-((t - peak) ** 2) / (2 * width ** 2))
    if insulin_type == "basal":
        return -dose * 0.02
    return 0


# -----------------------------
# イベント設定
# -----------------------------
meals = [
    {"time": 8 * 60,  "carb": 50, "GI": 0.7},
    {"time": 12 * 60, "carb": 70, "GI": 0.8},
    {"time": 15 * 60, "carb": 20, "GI": 0.6},
    {"time": 19 * 60, "carb": 80, "GI": 0.75},
]

exercises = [
    {"start": 18 * 60, "duration": 30, "intensity": 2},
]

sleep = {"start": 23 * 60, "end": 7 * 60}

baseline = 100


# -----------------------------
# Streamlit UI
# -----------------------------
st.title("全部入り：1日の血糖シミュレーション")

strength = st.slider("Dawn phenomenon の強さ (mg/dL)", 10, 50, 25)

glp1_dose = st.slider("GLP-1 週1製剤の用量", 0.0, 2.0, 1.0)
glp1 = {"time": 7 * 60, "dose": glp1_dose}


st.subheader("インスリン投与を追加")

with st.form("add_insulin_form"):
    insulin_type = st.selectbox("インスリンの種類", ["rapid", "basal"])
    insulin_time = st.slider("投与時刻（時）", 0, 23, 7)
    insulin_dose = st.number_input("投与量（単位）", 0.0, 50.0, 6.0, step=0.5)

    submitted = st.form_submit_button("追加する")

if submitted:
    st.session_state.insulins.append({
        "time": insulin_time * 60,
        "dose": insulin_dose,
        "type": insulin_type
    })
    st.success(f"{insulin_time}時に {insulin_dose} 単位の {insulin_type} を追加しました")


# -----------------------------
# 計算
# -----------------------------
time = list(range(0, 24 * 60))
bg_values = []

for t in time:
    bg = baseline

    glp1_level = glp1_effect(t, glp1["time"], glp1["dose"])

    for m in meals:
        bg += meal_glucose(t, m["time"], m["carb"], m["GI"], glp1_level)

    for ex in exercises:
        bg += exercise_glucose(t, ex["start"], ex["duration"], ex["intensity"])

    for ins in st.session_state.insulins:
        bg += insulin_action(t, ins["time"], ins["dose"], ins["type"])


    bg += dawn_phenomenon(t, strength, 6*60, 90, 0.1)

    sens = insulin_sensitivity(t, sleep["start"], sleep["end"])
    bg = baseline + (bg - baseline) * sens

    bg_values.append(bg)

# -----------------------------
# グラフ表示
# -----------------------------
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(time, bg_values)
ax.set_xlabel("時間（分）")
ax.set_ylabel("血糖値（mg/dL）")
ax.set_title("1日の血糖変動")
ax.grid(True)

st.pyplot(fig)
st.write("### 現在のインスリン投与一覧")

for i, ins in enumerate(st.session_state.insulins):
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

    with col1:
        st.write(ins["type"])

    with col2:
        st.write(f"{ins['time']//60} 時")

    with col3:
        st.write(f"{ins['dose']} 単位")

    with col4:
        if st.button("削除", key=f"delete_{i}"):
            st.session_state.insulins.pop(i)
            st.rerun()
