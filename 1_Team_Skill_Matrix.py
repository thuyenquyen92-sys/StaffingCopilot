"""
Streamlit Page: Team Skill Matrix
Interactive matrix showing skill levels for all team members.
Supports filtering by category and minimum skill level.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.db.session import get_db_session
from app.services.skill_matrix_service import (
    get_skill_matrix_data,
    get_person_detail_skills,
    get_all_categories
)

st.set_page_config(page_title="Skill Matrix", page_icon="📊", layout="wide")
st.title("📊 Team Skill Matrix")

# Initialize database session
db = next(get_db_session())

# Sidebar filters
st.sidebar.header("🔍 Filters")

# Get all categories for filter
categories = get_all_categories(db)
category_filter = st.sidebar.selectbox(
    "Skill Category",
    options=["All"] + categories,
    help="Filter skills by category/domain"
)

# Minimum skill level filter
min_level = st.sidebar.slider(
    "Minimum Skill Level",
    min_value=0,
    max_value=4,
    value=0,
    help="Show only skills with level >= this value"
)

# Convert "All" to None for service function
category_param = None if category_filter == "All" else category_filter

# Load skill matrix data
matrix_data = get_skill_matrix_data(db, category_param, min_level)

if not matrix_data["people"]:
    st.warning("No team members found. Please add people to the database.")
    st.stop()

if not matrix_data["skills"]:
    st.warning("No skills found. Please add skills to the database.")
    st.stop()

# Display interactive matrix
st.subheader(f"Skill Matrix ({len(matrix_data['people'])} people × {len(matrix_data['skills'])} skills)")

# Create DataFrame for display
df_matrix = pd.DataFrame(
    matrix_data["matrix"],
    index=[p.name for p in matrix_data["people"]],
    columns=[s.name for s in matrix_data["skills"]]
)

# Replace None with '-' for display
df_display = df_matrix.fillna('-')

# Add color styling function
def color_skill_level(val):
    """Color code skill levels for better visualization"""
    if val == '-':
        return 'background-color: #f0f0f0'
    try:
        level = int(val)
        if level == 0:
            return 'background-color: #ffcccc'
        elif level == 1:
            return 'background-color: #ffe6cc'
        elif level == 2:
            return 'background-color: #ffffcc'
        elif level == 3:
            return 'background-color: #ccffcc'
        elif level == 4:
            return 'background-color: #99ff99'
    except:
        pass
    return ''

# Apply styling - use map() instead of applymap() for newer pandas versions
try:
    # For pandas >= 2.1.0
    styled_df = df_display.style.map(color_skill_level)
except AttributeError:
    # For older pandas versions
    styled_df = df_display.style.applymap(color_skill_level)

# Display the matrix
st.dataframe(
    styled_df,
    use_container_width=True,
    height=400
)

# Add legend
st.markdown("""
**Skill Level Legend:**
- 🔴 **0**: No knowledge/experience
- 🟠 **1**: Beginner (requires supervision)
- 🟡 **2**: Intermediate (works independently)
- 🟢 **3**: Advanced (can mentor others)
- 🟢 **4**: Expert (recognized authority)
""")

# Person detail viewer
st.subheader("👤 Person Skill Details")
st.markdown("Click on any person below to see detailed skill information")

# Create selection for person detail view
person_names = [p.name for p in matrix_data["people"]]
selected_person = st.selectbox("Select a person to view details:", person_names)

if selected_person:
    person = next(p for p in matrix_data["people"] if p.name == selected_person)
    skills_detail = get_person_detail_skills(db, person.id)
    
    if skills_detail:
        # Create detailed view
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### {person.name}")
            st.markdown(f"**Role:** {person.role}")
            
            # Create DataFrame for skills
            df_skills = pd.DataFrame(skills_detail)
            
            # Add progress bars for skill gaps
            st.markdown("#### Current vs Target Skills")
            for skill in skills_detail:
                col_a, col_b, col_c = st.columns([2, 2, 1])
                with col_a:
                    st.markdown(f"**{skill['skill_name']}**")
                    st.caption(f"Category: {skill['skill_category']}")
                with col_b:
                    # Progress bar showing current vs target
                    progress = skill['current_level'] / 4 if skill['current_level'] > 0 else 0
                    st.progress(progress)
                    st.caption(f"Current: {skill['current_level']}/4")
                with col_c:
                    st.metric("Target", f"{skill['target_level']}/4", 
                             delta=f"{skill['gap']}" if skill['gap'] != 0 else None)
            
            # Display as table as well
            st.markdown("#### Detailed Skill Breakdown")
            st.dataframe(df_skills[['skill_name', 'skill_category', 'current_level', 'target_level', 'last_updated']])
        
        with col2:
            st.markdown("#### Development Summary")
            # Calculate average skill level
            avg_skill = sum(s['current_level'] for s in skills_detail) / len(skills_detail) if skills_detail else 0
            st.metric("Average Skill Level", f"{avg_skill:.1f}/4")
            
            # Skills needing improvement (target > current)
            needs_improvement = [s for s in skills_detail if s['gap'] > 0]
            if needs_improvement:
                st.markdown("**Skills to develop:**")
                for skill in needs_improvement:
                    st.markdown(f"- {skill['skill_name']}: {skill['gap']} level(s) to reach target")
            else:
                st.success("All skills at target levels! 🎉")
            
            # Last updated info
            st.markdown("**Last Assessments:**")
            for skill in skills_detail[:3]:  # Show last 3
                st.caption(f"{skill['skill_name']}: {skill['last_updated']}")
    else:
        st.info("No skills assigned to this person yet.")