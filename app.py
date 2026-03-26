
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Project Dashboard", layout="wide")

# =========================
# CONSTANTS
# =========================
COLOR_MAP = {
    "Mozambique": "#2ECC71",
    "Angola": "#FFD700"
}

# =========================
# HELPER FUNCTIONS
# =========================
def parse_date(x):
    if isinstance(x, str) and x.lower() == "now":
        return pd.Timestamp.now()
    return pd.to_datetime(x.replace('.', ''), format="%b %Y", errors="coerce")

def load_and_preprocess_data():
    data = {
        "Number": list(range(1, 16)),
        "Project Title": [
            "Enhancing Household Economic Stability via Securing Land Tenure",
            "Building Sustainable Fisheries and Enhancing Community Governance Structures",
            "Assessment of land-based Investment Needs",
            "Youth ATLAS Mozambique (YATLAS)",
            "Participatory Coastal Spatial Planning in Bazaruto",
            "Land Use Intensity for Sustainable Agriculture",
            "Community Led Spatial Planning",
            "Charcoal Value Chain Assessment (Angola)",
            "Assessment of Seine Net Transition",
            "Wildlife Conservation at Landscape Scale",
            "Protected Area System Strengthening (Angola)",
            "Rural Transformation Centres (Lobito)",
            "National Energy MRV System (Angola)",
            "Solid Waste Spatial Analysis",
            "Mapping Electricity Poles"
        ],
        "Start date": [
            "Dec. 2022","Jan. 2023","Mar. 2023","Dec. 2022","Oct. 2023",
            "Mar. 2024","Jun. 2024","Nov. 2023","Nov. 2024","Jan. 2025",
            "Aug. 2024","Nov. 2025","Dec. 2024","Jan. 2025","Feb. 2025"
        ],
        "Finish date": [
            "Aug. 2024","Jan. 2024","Sep. 2023","Now","Feb. 2024",
            "Feb. 2025","Apr. 2025","Dec. 2023","Jan. 2025","Aug. 2025",
            "Sep. 2025","Feb. 2026","Jul. 2025","Dec. 2025","Now"
        ],
        "Country": [
            "Mozambique","Mozambique","Mozambique","Mozambique","Mozambique",
            "Mozambique","Mozambique","Angola","Mozambique","Mozambique",
            "Angola","Angola","Angola","Mozambique","Mozambique"
        ],
        "Location": [
            "Nhamatanda","Bazaruto","Nationwide","Nationwide","Bazaruto",
            "Nhamatanda","Inhaminga","Angola","Bazaruto","Sofala",
            "Quicama","Lobito","Angola","Nacala","Chimoio"
        ],
        "Partner": [
            "Dorcas","African Parks","SNV","Data4Moz","CI",
            "ESA","USAID","MINAMB","African Parks","UNDP",
            "UNDP","UNDP","UNDP","Litterati","Data4Moz"
        ]
    }
    df = pd.DataFrame(data)
    df["Start"] = df["Start date"].apply(parse_date)
    df["Finish"] = df["Finish date"].apply(parse_date)
    df["Duration"] = (df["Finish"] - df["Start"]).dt.days / 30
    return df


def get_sidebar_filters_and_page(df_full):
    st.sidebar.title("Filters")
    page = st.sidebar.selectbox("Page", ["Overview", "Gantt", "Export"])

    # Country Filter
    all_countries = ['All'] + sorted(df_full["Country"].unique().tolist())
    selected_country = st.sidebar.selectbox("Country", all_countries)
    
    # Partner Filter
    all_partners = ['All'] + sorted(df_full["Partner"].unique().tolist())
    selected_partner = st.sidebar.selectbox("Partner", all_partners)

    # Start Year Filter
    all_start_years = ['All'] + sorted(df_full['Start'].dt.year.dropna().unique().astype(int).tolist())
    selected_start_year = st.sidebar.selectbox("Start Year", all_start_years)

    # Finish Year Filter
    all_finish_years = ['All'] + sorted(df_full['Finish'].dt.year.dropna().unique().astype(int).tolist())
    selected_finish_year = st.sidebar.selectbox("Finish Year", all_finish_years)

    # Apply filters
    filtered_df = df_full.copy()
    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df["Country"] == selected_country]
    if selected_partner != 'All':
        filtered_df = filtered_df[filtered_df["Partner"] == selected_partner]
    if selected_start_year != 'All':
        filtered_df = filtered_df[filtered_df['Start'].dt.year == selected_start_year]
    if selected_finish_year != 'All':
        filtered_df = filtered_df[filtered_df['Finish'].dt.year == selected_finish_year]

    return filtered_df, page

def render_overview_page(df):
    st.subheader("Overview")
    col1, col2 = st.columns(2)
    col1.metric("Total Projects", len(df))
    col2.metric("Avg Duration (months)", round(df["Duration"].mean(), 1) if not df.empty else 0)

    st.markdown("---") # Separator

    st.subheader("Projects by Country")
    fig = px.histogram(df, x="Country", color="Country", color_discrete_map=COLOR_MAP)
    st.plotly_chart(fig, use_container_width=True)

    # New section for Partner Engagement Map (not a chart)
    st.subheader(" Our Partners")
    if not df.empty:
        selected_partner = st.selectbox("Select a Partner to see their projects:", ['All'] + sorted(df['Partner'].unique().tolist()))

        if selected_partner == 'All':
            st.dataframe(df[['Partner', 'Project Title', 'Country', 'Location']])
        else:
            partner_projects = df[df['Partner'] == selected_partner]
            if not partner_projects.empty:
                st.dataframe(partner_projects[['Project Title', 'Country', 'Location']])
            else:
                st.info(f"No projects found for {selected_partner} with the current filters.")
    else:
        st.info("No project data available to display partner engagement.")

    st.markdown("---") # Separator

    st.subheader("Project Locations Map")
    coords = {
        "Nhamatanda": (-19.2, 34.8),
        "Bazaruto": (-21.6, 35.4),
        "Chimoio": (-19.1, 33.4),
        "Angola": (-12.5, 18.5),
        "Nationwide": (-18.5, 35.5),
        "Inhaminga": (-18.36, 34.88),
        "Sofala": (-16.0, 38.0),
        "Quicama": (-9.5, 13.2),
        "Lobito": (-12.4, 13.6),
        "Nacala": (-14.56, 40.68)
    }

    m = folium.Map(location=[-18, 35], zoom_start=5, tiles='Esri.WorldImagery')

    # Prepare data for markers with counts and popups
    location_data = {}
    for loc_name, group in df.groupby("Location"):
        if loc_name in coords:
            project_titles_with_countries = [
                f"{row['Project Title']} ({row['Country']})"
                for _, row in group.iterrows()
            ]
            country_for_color = group["Country"].iloc[0] if not group.empty else "Mozambique"

            location_data[loc_name] = {
                "projects": project_titles_with_countries,
                "count": len(group),
                "country_for_color": country_for_color
            }

    # Add markers to the map
    for loc_name, data in location_data.items():
        lat, lon = coords[loc_name]
        project_count = data["count"]
        popup_text = "<br>".join(data["projects"])
        marker_color = 'green' if data['country_for_color']=="Mozambique" else 'orange'

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.DivIcon(
                icon_size=(30,30),
                icon_anchor=(15,15),
                html=f'<div style="font-size: 14pt; color: white; background-color: {marker_color}; border-radius: 50%; width: 30px; height: 30px; text-align: center; line-height: 30px; font-weight: bold;">{project_count}</div>'
            )
        ).add_to(m)

    st_folium(m, width=900, height=500)

def render_gantt_page(df):
    st.subheader("Project Gantt Chart")
    gdf = df.dropna(subset=["Start", "Finish"])

    if not gdf.empty:
        fig = px.timeline(
            gdf,
            x_start="Start",
            x_end="Finish",
            y="Project Title",
            color="Country",
            color_discrete_map=COLOR_MAP,
            title="Project Timelines"
        )
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No projects with valid start and finish dates to display Gantt chart.")

def render_export_page(df):
    st.subheader("⬇️ Data & Export")
    st.dataframe(df)

    st.markdown("---") # Separator

    st.subheader("Download Options")
    st.download_button("Download CSV", df.to_csv(index=False), "projects.csv", "text/csv")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(50, 800, "Project Report")
    c.drawString(50, 780, f"Total Projects: {len(df)}")
    c.drawString(50, 760, f"Average Duration: {round(df['Duration'].mean(), 1) if not df.empty else 0} months")

    # Add a simple table to PDF
    y_position = 730
    c.drawString(50, y_position, "Project Details:")
    y_position -= 20
    for idx, row in df.head(10).iterrows():
        c.drawString(70, y_position, f"{row['Project Title']} - {row['Country']} ({round(row['Duration'], 1) if pd.notnull(row['Duration']) else 'N/A'} months)")
        y_position -= 15
        if y_position < 100:
            c.showPage()
            c.drawString(50, 800, "Project Report (cont.)")
            y_position = 780

    c.save()
    buffer.seek(0)
    st.download_button("Download PDF", buffer, "report.pdf", "application/pdf")

# =========================
# MAIN APP LOGIC
# =========================
def main():
    col1, col2 = st.columns([0.2, 0.8])
    with col1:
        st.image("D4MOZ-removebg-preview-removebg-preview.png", width=100)
    with col2:
        st.title("Our Project's Portfolio Dashboard")

    st.markdown("A clean, interactive dashboard for exploring our projects data across Mozambique and Angola.")

    df_full = load_and_preprocess_data()
    filtered_df, page = get_sidebar_filters_and_page(df_full)

    if filtered_df.empty and page != "Export":
        st.warning("No projects found matching the selected filters.")
    else:
        if page == "Overview":
            render_overview_page(filtered_df)
        elif page == "Gantt":
            render_gantt_page(filtered_df)
        elif page == "Export":
            render_export_page(filtered_df)

if __name__ == "__main__":
    main()
