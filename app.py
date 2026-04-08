import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ---------------- INTERPOLATION ----------------
def interpolate_h(v, v_points, h_points):
    if v <= v_points[0]:
        return h_points[0]
    elif v >= v_points[-1]:
        return h_points[-1]
    else:
        for i in range(len(v_points)-1):
            if v_points[i] <= v <= v_points[i+1]:
                v1, v2 = v_points[i], v_points[i+1]
                h1, h2 = h_points[i], h_points[i+1]
                return h1 + (v - v1) * (h2 - h1) / (v2 - v1)

# ---------------- MODEL ----------------
def thermal_model(motor_load, motor_eff, controller_eff, ambient_temp, fin_factor, air_velocity):
    
    motor_input = motor_load / motor_eff
    controller_input = motor_input / controller_eff
    mosfet_loss = controller_input - motor_input

    A_bc = 0.0386
    A_bf = 0.0573

    v_points = [2, 5, 10]
    h_fin_points = [11, 18, 23]
    h_no_fin_points = [13, 18, 21]

    h_bf = interpolate_h(air_velocity, v_points, h_fin_points)
    h_bc = interpolate_h(air_velocity, v_points, h_no_fin_points)

    A_fin_new = A_bf * (1 + fin_factor / 100)
    A_total = A_bc + A_fin_new

    h_effective = (h_bc * A_bc + h_bf * A_fin_new) / A_total

    R_hs = 1 / (h_effective * A_total)

    R_pad = 0.064
    R_RearCoverCooling = -0.043
    R_correction = -0.17

    R_total = R_hs + R_pad + R_RearCoverCooling + R_correction

    R_jc = 0.38

    T_case = ambient_temp + mosfet_loss * R_total
    N_devices = 24
    T_j = T_case + (mosfet_loss / N_devices) * R_jc

    return T_j

# ---------------- MAP ----------------
def generate_map(motor_load, motor_eff, controller_eff, air_velocity):

    ambient_range = [25, 30, 35, 40, 50]
    fin_range = [-20, -10, 0, 10, 20]

    results = []

    for Ta in ambient_range:
        row = []
        for fin in fin_range:
            tj = thermal_model(
                motor_load,
                motor_eff,
                controller_eff,
                Ta,
                fin,
                air_velocity
            )

            margin = ((125 - tj) / 125) * 100
            row.append(round(margin, 1))
        results.append(row)

    return ambient_range, fin_range, results

# ---------------- UI ----------------
st.set_page_config(page_title="Thermal Calculator", layout="centered")

st.title("GPM50 Separate Controller Heatsink Thermal Calculator")

st.subheader("Input Parameters")

motor_load = st.number_input("Motor Load (W)", value=6000.0)
motor_eff = st.number_input("Motor Efficiency", value=0.9000, format="%.4f")
controller_eff = st.number_input("Controller Efficiency", value=0.9767, format="%.4f")
ambient_temp = st.number_input("Ambient Temperature (°C)", value=40.0)
fin_area_factor = st.number_input("Fin Area Change (%)", value=0.0)

air_velocity = st.number_input(
    "Air Velocity (m/s)",
    value=5.0,
    min_value=2.0,
    max_value=10.0,
    step=0.1,
    format="%.2f"
)

# ---------------- CALC ----------------
if st.button("Calculate"):

    tj = thermal_model(
        motor_load,
        motor_eff,
        controller_eff,
        ambient_temp,
        fin_area_factor,
        air_velocity
    )

    margin = ((125 - tj) / 125) * 100

    st.subheader("Results")

    if tj > 125:
        st.error(f"❌ Tj: {round(tj,2)} °C (OVERHEATING)")
    else:
        st.success(f"✅ Tj: {round(tj,2)} °C (SAFE)")

    st.info(f"Thermal Margin: {round(margin,2)} %")

# ---------------- HEATMAP ----------------
st.subheader("Thermal Design Heatmap")

amb, fin, data = generate_map(
    motor_load,
    motor_eff,
    controller_eff,
    air_velocity
)

df = pd.DataFrame(data, index=amb, columns=fin)

fig, ax = plt.subplots()

def get_color(value):
    if value > 20:
        return 2   # Green → Over Design
    elif value > 10:
        return 1   # Light Green → Safe Design
    else:
        return 0   # Red → Risk

color_matrix = df.copy()

for i in range(len(df.index)):
    for j in range(len(df.columns)):
        color_matrix.iloc[i, j] = get_color(df.iloc[i, j])

cmap = ListedColormap(["red", "lightgreen", "green"])

ax.imshow(color_matrix, cmap=cmap, aspect='auto')

ax.set_xticks(range(len(fin)))
ax.set_yticks(range(len(amb)))

ax.set_xticklabels(fin)
ax.set_yticklabels(amb)

ax.set_xlabel("Fin Area Change (%)")
ax.set_ylabel("Ambient Temp (°C)")

for i in range(len(amb)):
    for j in range(len(fin)):
        ax.text(j, i, f"{df.iloc[i,j]}%", ha='center', va='center')

st.pyplot(fig)
