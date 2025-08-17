import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px 

# --- Load token ---
mapbox_token = st.secrets["mapbox_token"]

# --- Load site data ---
sites_df = pd.read_csv("Overall.csv")
sites_df.columns = sites_df.columns.str.strip()
sites_df["Latitude"] = pd.to_numeric(sites_df["Latitude"], errors="coerce")
sites_df["Longitude"] = pd.to_numeric(sites_df["Longitude"], errors="coerce")

# --- Load route data ---
routes_df = pd.read_csv("Route.csv")
routes_df.columns = routes_df.columns.str.strip()

st.set_page_config(layout="wide")
st.title("🗺️ Bản đồ Site & Route tại Việt Nam (Mapbox Streets)")

# --- Sidebar filters ---
region_filter = st.sidebar.multiselect("Chọn Region", sites_df["Region"].dropna().unique())
province_filter = st.sidebar.multiselect("Chọn Tỉnh/Thành", sites_df["Province"].dropna().unique())
status_filter = st.sidebar.multiselect("Chọn Site Status", sites_df["Site Status"].dropna().unique())
show_route = st.sidebar.checkbox("Hiển thị Route", value=False)

# --- Apply filters ---
filtered_sites = sites_df.copy()
if region_filter:
    filtered_sites = filtered_sites[filtered_sites["Region"].isin(region_filter)]
if province_filter:
    filtered_sites = filtered_sites[filtered_sites["Province"].isin(province_filter)]
if status_filter:
    filtered_sites = filtered_sites[filtered_sites["Site Status"].isin(status_filter)]

filtered_sites = filtered_sites.dropna(subset=["Latitude", "Longitude"])

# --- Plot ---
try:
    if not filtered_sites.empty:
        fig = go.Figure()

        # Màu theo Site Status
        site_statuses = filtered_sites["Site Status"].unique()
        colors = px.colors.qualitative.Safe  # Màu sắc có sẵn trong plotly
        color_map = {status: colors[i % len(colors)] for i, status in enumerate(site_statuses)}

        # Vẽ từng nhóm Site Status
        for status in site_statuses:
            group = filtered_sites[filtered_sites["Site Status"] == status]
            fig.add_trace(go.Scattermapbox(
                lat=group["Latitude"],
                lon=group["Longitude"],
                mode="markers",
                marker=dict(size=8, color=color_map[status]),
                text=group["Name"],
                hoverinfo="text",
                name=status
            ))

        # Vẽ Route nếu bật
        if show_route:
            colors = px.colors.qualitative.Set2
            color_map = {file: colors[i % len(colors)] for i, file in enumerate(routes_df["Source_File"].unique())}
        
            for source_file, group in routes_df.groupby("Source_File"):
                # Sắp xếp theo Name order (nếu có số trong tên)
                group_sorted = group.copy()
                group_sorted["order"] = group_sorted["Name"].str.extract(r'(\d+)').fillna(0).astype(int)
                group_sorted = group_sorted.sort_values(["order"]).reset_index(drop=True)
        
                # Marker cho tất cả điểm
                fig.add_trace(go.Scattermapbox(
                    lat=group_sorted["latitude"],
                    lon=group_sorted["longitude"],
                    mode="markers",
                    marker=dict(size=6, color=color_map[source_file]),
                    text=group_sorted["Name"] + " (" + source_file + ")",
                    hoverinfo="text",
                    name=source_file
                ))
        
                # Nối line theo từng Name
                lat_lines = []
                lon_lines = []
        
                for name, subgroup in group_sorted.groupby("Name"):
                    subgroup = subgroup.reset_index(drop=True)
        
                    # nối tất cả điểm liên tiếp trong cùng Name
                    for i in range(len(subgroup) - 1):
                        lat_lines += [subgroup.loc[i, "latitude"], subgroup.loc[i+1, "latitude"], None]
                        lon_lines += [subgroup.loc[i, "longitude"], subgroup.loc[i+1, "longitude"], None]
        
                    # khi kết thúc 1 Name, nối điểm cuối của Name này với điểm đầu của Name tiếp theo
                    # (nếu chưa phải là Name cuối cùng)
                    next_names = group_sorted["Name"].unique()
                    current_idx = list(next_names).index(name)
                    if current_idx < len(next_names) - 1:
                        next_name = next_names[current_idx + 1]
                        first_next = group_sorted[group_sorted["Name"] == next_name].iloc[0]
                        lat_lines += [subgroup.iloc[-1]["latitude"], first_next["latitude"], None]
                        lon_lines += [subgroup.iloc[-1]["longitude"], first_next["longitude"], None]
        
                # Add line trace
                fig.add_trace(go.Scattermapbox(
                    lat=lat_lines,
                    lon=lon_lines,
                    mode="lines",
                    line=dict(width=2, color=color_map[source_file]),
                    hoverinfo="skip",
                    showlegend=False
                ))

        fig.update_layout(
            mapbox=dict(
                accesstoken=mapbox_token,
                style="mapbox://styles/mapbox/streets-v12",
                zoom=5,
                center=dict(lat=16, lon=107)
            ),
            legend=dict(title="Loại hiển thị", itemsizing="constant"),
            margin=dict(l=0, r=0, t=0, b=0),
            height=700
        )

        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("⚠️ Không có dữ liệu phù hợp để hiển thị trên bản đồ.")

except Exception as e:
    st.error("❌ Đã xảy ra lỗi khi hiển thị bản đồ.")
    st.exception(e)
