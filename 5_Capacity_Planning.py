"""
Streamlit Page: Capacity Planning
Shows team member capacity and activity assignments across months.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from app.db.session import get_db_session
from app.models.person import Person
from app.models.capacity import Capacity  # Add this import
from app.services.capacity_planning_service import (
    get_team_capacity_matrix,
    get_all_work_packages,
    create_work_package,
    create_or_update_assignment,
    delete_assignment,
    get_monthly_utilization_report,
    get_area_summary,
    MONTHS,
    MONTH_NAMES
)

st.set_page_config(page_title="Capacity Planning", page_icon="📅", layout="wide")
st.title("📅 Capacity Planning")

# Initialize database session
db = next(get_db_session())

# Year selection
current_year = datetime.now().year
selected_year = st.sidebar.selectbox(
    "Select Year",
    options=[current_year - 1, current_year, current_year + 1],
    index=1
)

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Capacity Matrix", 
    "👤 Person View", 
    "📦 Work Packages",
    "📈 Utilization Report",
    "⚙️ Admin"
])

# ==================== TAB 1: CAPACITY MATRIX ====================
with tab1:
    st.header(f"Team Capacity Matrix - {selected_year}")
    
    # Get matrix data
    matrix_data = get_team_capacity_matrix(db, selected_year)
    
    if not matrix_data["people"]:
        st.warning("No team members found. Please add people first.")
        st.stop()
    
    # Create capacity matrix DataFrame
    capacity_data = []
    for person_data in matrix_data["matrix"]:
        row = {
            "Team Member": person_data["person"].name,
            "Role": person_data["person"].role,
            "Capacity (FTE)": person_data["capacity_fte"]
        }
        # Add monthly totals
        for month in MONTHS:
            row[MONTH_NAMES[month]] = person_data["monthly_totals"][month]
            row[f"{MONTH_NAMES[month]} %"] = person_data["utilization"][month]
        
        capacity_data.append(row)
    
    df_capacity = pd.DataFrame(capacity_data)
    
    # Display main capacity table
    st.subheader("Monthly FTE Allocation")
    
    # Select columns to show
    show_columns = ["Team Member", "Role", "Capacity (FTE)"] + [MONTH_NAMES[m] for m in MONTHS]
    st.dataframe(df_capacity[show_columns], use_container_width=True)
    
    # Visualization: Heatmap of FTE allocation
    st.subheader("Capacity Heatmap")
    
    heatmap_data = []
    for person_data in matrix_data["matrix"]:
        for month in MONTHS:
            heatmap_data.append({
                "Team Member": person_data["person"].name,
                "Month": MONTH_NAMES[month],
                "FTE Allocated": person_data["monthly_totals"][month],
                "Utilization %": person_data["utilization"][month]
            })
    
    df_heatmap = pd.DataFrame(heatmap_data)
    
    fig = px.density_heatmap(
        df_heatmap,
        x="Month",
        y="Team Member",
        z="FTE Allocated",
        title="FTE Allocation Heatmap",
        color_continuous_scale="Viridis",
        labels={"FTE Allocated": "FTE (0-1)"}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Bar chart: Total FTE per person
    st.subheader("Total Annual FTE per Person")
    df_capacity["Total Annual FTE"] = df_capacity[[MONTH_NAMES[m] for m in MONTHS]].sum(axis=1)
    
    fig_bar = px.bar(
        df_capacity,
        x="Team Member",
        y="Total Annual FTE",
        title="Total Workload Distribution",
        color="Total Annual FTE",
        color_continuous_scale="Blues",
        text="Total Annual FTE"
    )
    fig_bar.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig_bar, use_container_width=True)

# ==================== TAB 2: PERSON VIEW ====================
with tab2:
    st.header(f"Individual Capacity Details - {selected_year}")
    
    # Person selector
    people = db.query(Person).order_by(Person.name).all()
    if people:
        selected_person_name = st.selectbox(
            "Select Team Member",
            options=[p.name for p in people],
            key="person_select"
        )
        selected_person = next(p for p in people if p.name == selected_person_name)
        
        # Get assignments for this person
        from app.services.capacity_planning_service import get_person_assignments
        assignments = get_person_assignments(db, selected_person.id, selected_year)
        
        # Get capacity info
        capacity = db.query(Capacity).filter(Capacity.person_id == selected_person.id).first()
        capacity_fte = capacity.total_hours_per_week / 40 if capacity else 1.0
        
        st.subheader(f"Activities for {selected_person.name}")
        
        if assignments:
            # Display assignments in a table
            assignment_data = []
            for assignment in assignments:
                wp = assignment.work_package
                monthly_fte = {MONTH_NAMES[m]: getattr(assignment, f'fte_{m}', 0.0) for m in MONTHS}
                total_fte = sum(monthly_fte.values())
                
                assignment_data.append({
                    "Work Package": wp.name,
                    "Area": wp.area or "N/A",
                    "Total FTE": total_fte,
                    **monthly_fte,
                    "Notes": assignment.notes or ""
                })
            
            df_assignments = pd.DataFrame(assignment_data)
            st.dataframe(df_assignments, use_container_width=True)
            
            # Monthly visualization for this person
            st.subheader("Monthly Workload Breakdown")
            
            # Calculate monthly totals
            monthly_totals = {month: 0.0 for month in MONTHS}
            for assignment in assignments:
                for month in MONTHS:
                    monthly_totals[month] += getattr(assignment, f'fte_{month}', 0.0)
            
            # Create area chart
            monthly_data = []
            for idx, assignment in enumerate(assignments):
                wp = assignment.work_package
                for month in MONTHS:
                    fte = getattr(assignment, f'fte_{month}', 0.0)
                    if fte > 0:
                        monthly_data.append({
                            "Month": MONTH_NAMES[month],
                            "Work Package": wp.name,
                            "FTE": fte
                        })
            
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)
                fig_area = px.area(
                    df_monthly,
                    x="Month",
                    y="FTE",
                    color="Work Package",
                    title=f"Monthly FTE Allocation - {selected_person.name}",
                    groupnorm=None
                )
                st.plotly_chart(fig_area, use_container_width=True)
            
            # Capacity vs Allocation
            st.subheader("Capacity vs Allocation")
            months_list = [MONTH_NAMES[m] for m in MONTHS]
            allocation = [monthly_totals[m] for m in MONTHS]
            
            fig_compare = go.Figure()
            fig_compare.add_trace(go.Bar(
                x=months_list,
                y=allocation,
                name='Allocated FTE',
                marker_color='lightblue'
            ))
            fig_compare.add_trace(go.Scatter(
                x=months_list,
                y=[capacity_fte] * 12,
                name=f'Capacity ({capacity_fte} FTE)',
                line=dict(color='red', width=2, dash='dash')
            ))
            fig_compare.update_layout(
                title="Resource Allocation vs Capacity",
                yaxis_title="FTE",
                barmode='group'
            )
            st.plotly_chart(fig_compare, use_container_width=True)
            
        else:
            st.info(f"No activities assigned to {selected_person.name} for {selected_year}")
    else:
        st.warning("No team members found")

# ==================== TAB 3: WORK PACKAGES ====================
with tab3:
    st.header(f"Work Packages and Assignments - {selected_year}")
    
    # Get all work packages
    work_packages = get_all_work_packages(db)
    
    if work_packages:
        # Display work packages
        for wp in work_packages:
            with st.expander(f"📦 {wp.name} - {wp.area or 'No Area'}"):
                st.markdown(f"**Description:** {wp.description or 'No description'}")
                st.markdown(f"**Team:** {wp.team or 'Not specified'}")
                
                # Show assignments for this work package
                from app.services.capacity_planning_service import get_work_package_assignments
                assignments = get_work_package_assignments(db, wp.id, selected_year)
                
                if assignments:
                    assignment_list = []
                    for assignment in assignments:
                        person = assignment.person
                        total_fte = sum(getattr(assignment, f'fte_{m}', 0.0) for m in MONTHS)
                        assignment_list.append({
                            "Person": person.name,
                            "Total FTE": total_fte,
                            "Notes": assignment.notes or ""
                        })
                    
                    st.dataframe(pd.DataFrame(assignment_list), use_container_width=True)
                    
                    # Show monthly breakdown for this work package
                    monthly_data = {MONTH_NAMES[m]: 0.0 for m in MONTHS}
                    for assignment in assignments:
                        for month in MONTHS:
                            monthly_data[MONTH_NAMES[month]] += getattr(assignment, f'fte_{month}', 0.0)
                    
                    st.markdown("**Monthly FTE Distribution:**")
                    df_monthly = pd.DataFrame([monthly_data])
                    st.dataframe(df_monthly, use_container_width=True)
                else:
                    st.info("No assignments for this work package")
    else:
        st.info("No work packages created yet")

# ==================== TAB 4: UTILIZATION REPORT ====================
with tab4:
    st.header(f"Team Utilization Report - {selected_year}")
    
    # Get utilization report
    utilization_report = get_monthly_utilization_report(db, selected_year)
    
    if utilization_report:
        # Create utilization DataFrame
        util_data = []
        for report in utilization_report:
            person = report["person"]
            for month, values in report["monthly"].items():
                util_data.append({
                    "Team Member": person.name,
                    "Month": month,
                    "FTE Allocated": values["fte"],
                    "FTE Capacity": values["capacity"],
                    "Utilization %": values["utilization"]
                })
        
        df_util = pd.DataFrame(util_data)
        
        # Heatmap of utilization
        st.subheader("Utilization Heatmap (%)")
        pivot_util = df_util.pivot(index="Team Member", columns="Month", values="Utilization %")
        
        fig_heatmap = px.imshow(
            pivot_util,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="RdYlGn",
            title="Monthly Utilization Percentage",
            labels={"color": "Utilization %"}
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Warning for over/under utilization
        st.subheader("Capacity Alerts")
        for report in utilization_report:
            person = report["person"]
            alerts = []
            for month, values in report["monthly"].items():
                util = values["utilization"]
                if util > 100:
                    alerts.append(f"⚠️ {month}: Over capacity ({util:.0f}%)")
                elif util < 50 and util > 0:
                    alerts.append(f"💡 {month}: Underutilized ({util:.0f}%)")
                elif util == 0:
                    alerts.append(f"❄️ {month}: No allocation")
            
            if alerts:
                with st.expander(f"{person.name}"):
                    for alert in alerts:
                        st.write(alert)
        
        # Area summary
        st.subheader("FTE Summary by Work Area")
        area_summary = get_area_summary(db, selected_year)
        
        if area_summary:
            area_data = []
            for area, monthly_fte in area_summary.items():
                area_data.append({
                    "Area": area,
                    **{MONTH_NAMES[m]: monthly_fte[m] for m in MONTHS},
                    "Total FTE": sum(monthly_fte.values())
                })
            
            df_area = pd.DataFrame(area_data)
            st.dataframe(df_area, use_container_width=True)
    else:
        st.info("No data available for utilization report")

# ==================== TAB 5: ADMIN ====================
with tab5:
    st.header("Manage Work Packages and Assignments")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Create New Work Package")
        with st.form("create_work_package"):
            wp_name = st.text_input("Work Package Name")
            wp_description = st.text_area("Description")
            wp_area = st.selectbox("Area", ["Data Quality Check", "YEC", "Push", "Process documentation", "Other"])
            if wp_area == "Other":
                wp_area = st.text_input("Specify Area")
            wp_team = st.text_input("Team", value="C/TXI-PX service team")
            
            if st.form_submit_button("Create Work Package"):
                if wp_name:
                    create_work_package(db, wp_name, wp_description, wp_area, wp_team)
                    st.success(f"Created work package: {wp_name}")
                    st.rerun()
                else:
                    st.error("Work package name is required")
    
    with col2:
        st.subheader("📋 Add/Edit Assignment")
        
        # Get people and work packages
        people = db.query(Person).order_by(Person.name).all()
        work_packages = get_all_work_packages(db)
        
        if people and work_packages:
            selected_person = st.selectbox("Select Person", options=[p.name for p in people], key="assign_person")
            selected_wp = st.selectbox("Select Work Package", options=[wp.name for wp in work_packages], key="assign_wp")
            
            person_obj = next(p for p in people if p.name == selected_person)
            wp_obj = next(wp for wp in work_packages if wp.name == selected_wp)
            
            # Get existing assignment
            from app.services.capacity_planning_service import get_person_assignments
            existing_assignments = get_person_assignments(db, person_obj.id, selected_year)
            existing = next((a for a in existing_assignments if a.work_package_id == wp_obj.id), None)
            
            st.markdown("**Monthly FTE Allocation**")
            fte_values = {}
            cols = st.columns(4)
            for idx, month in enumerate(MONTHS):
                with cols[idx % 4]:
                    default_value = getattr(existing, f'fte_{month}', 0.0) if existing else 0.0
                    fte_values[month] = st.number_input(
                        MONTH_NAMES[month],
                        min_value=0.0,
                        max_value=1.0,
                        value=default_value,
                        step=0.05,
                        format="%.2f",
                        key=f"fte_{person_obj.id}_{wp_obj.id}_{month}"
                    )
            
            notes = st.text_area("Notes", value=existing.notes if existing else "")
            
            if st.button("Save Assignment"):
                create_or_update_assignment(
                    db, person_obj.id, wp_obj.id, fte_values, selected_year, notes
                )
                st.success("Assignment saved successfully!")
                st.rerun()
            
            # Delete assignment if exists
            if existing:
                if st.button("Delete Assignment", type="secondary"):
                    delete_assignment(db, existing.id)
                    st.success("Assignment deleted!")
                    st.rerun()
        else:
            if not people:
                st.warning("No people found. Add people first.")
            if not work_packages:
                st.warning("No work packages found. Create some first.")