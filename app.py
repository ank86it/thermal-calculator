import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- MODEL ----------------
def thermal_model(motor_load, motor_eff, controller_eff, ambient_temp, fin_factor):
    
    # ---- LOSS CALCULATION ----
    motor_input = motor_load / motor_eff
    controller_input = motor_input / controller_eff
    mosfet_loss = controller_input - motor_input

    # ---- AREA VALUES ----
    A_bc = 0.0386   # no fin area (m²)
    A_bf = 0.0573   # fin area (m²)

    # ---- HEAT TRANSFER COEFF ----
    h_bc = 18.0   # base area (W/m²-K)
    h_bf = 18.0   # fin area (W/m²-K)

    # ---- FIN EFFECT ----
    A_fin_new = A_bf * (1 + fin_factor / 100)

    # ---- TOTAL AREA ----
    A_total = A_bc + A_fin_new

    # ---- EFFECTIVE h (AREA WEIGHTED) ----
    h_effective = (h_bc * A_bc + h_bf * A_fin_new) / A_total

    # ---- HEATSINK Rth ----
    R_hs = 1 / (h_effective * A_total)

    # ---- OTHER Rth ----
    R_pad = 0.064
    R_RearCoverCooling = -0.043
    R_correction = -0.17

    R_total = R_hs + R_pad + R_RearCoverCooling + R_correction

    R_jc = 0.38

    # ---- CASE TEMPERATURE ----
    T_case = ambient_temp + mosfet_loss * R_total

    # ---- DEVICE DISTRIBUTION ----
    N_devices = 24

    # ---- JUNCTION TEMPERATURE ----
    T_j = T_case + (mosfet_loss / N_devices) * R_jc

    return T_j


# ---------------- MAP GENERATION ----------------
def generate_map(motor_load, motor_eff, controller_eff):

    ambient_range = [25, 30, 35, 40, 50]
    fin_range = [-30, -20, -10, 0, 10, 20, 30]

    results = []

    for Ta in ambient_range:
        row = []
        for fin in fin_range:
            tj = thermal_model(
                motor_load,
                motor_eff,
                controller_eff,
                Ta,
                fin
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

motor_eff = st.number_input(
    "Motor Efficiency",
    value=0.9000,
    format="%.4f"
)

controller_eff = st.number_input(
    "Controller Efficiency",
    value=0.9767,
    format="%.4f"
)

ambient_temp = st.number_input("Ambient Temperature (°C)", value=40.0)

fin_area_factor = st.number_input("Fin Area Change (%)", value=0.0)

# ---------------- CALCULATION ----------------
if st.button("Calculate"):

    tj = thermal_model(
        motor_load,
        motor_eff,
        controller_eff,
        ambient_temp,
        fin_area_factor
    )

    Tj_limit = 125.0
    margin_percent = ((Tj_limit - tj) / Tj_limit) * 100

    st.subheader("Results")

    if tj > Tj_limit:
        st.error(f"❌ MOSFET Junction Temperature (Tj): {round(tj,2)} °C (OVERHEATING)")
    else:
        st.success(f"✅ MOSFET Junction Temperature (Tj): {round(tj,2)} °C (SAFE)")

    st.info(f"Thermal Margin: {round(margin_percent,2)} %")


# ---------------- HEATMAP ----------------
st.subheader("Thermal Design Heatmap")

amb, fin, data = generate_map(
    motor_load,
    motor_eff,
    controller_eff
)

df = pd.DataFrame(data, index=amb, columns=fin)

fig, ax = plt.subplots()

cax = ax.imshow(df, aspect='auto')

ax.set_xticks(range(len(df.columns)))
ax.set_yticks(range(len(df.index)))

ax.set_xticklabels(df.columns)
ax.set_yticklabels(df.index)

ax.set_xlabel("Fin Area Change (%)")
ax.set_ylabel("Ambient Temp (°C)")

# Show values inside cells
for i in range(len(df.index)):
    for j in range(len(df.columns)):
        ax.text(j, i, f"{df.iloc[i, j]}%", ha='center', va='center')

fig.colorbar(cax)

st.pyplot(fig)
