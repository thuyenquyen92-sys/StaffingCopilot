"""
Streamlit Page: Detailed view of a single person.

This page consolidates all information about a selected individual: their
skills, capacity, and SWOT analysis. It serves as a single source of truth for
understanding a team member's current status and development areas.
"""
import streamlit as st
from app.db.session import get_db_session
from app.ui.components.person_selector import person_selector
from app.services import skill_service, capacity_service, swot_service

st.title("👤 Person Profile")

db = next(get_db_session())

# Use the reusable component to select a person
person_id = person_selector(db, key="profile_person_selector")

if person_id:
    # --- Skills Section ---
    st.subheader("Skills & Interests")
    skills = skill_service.get_person_skills(db, person_id)
    if not skills:
        st.info("No skills assigned to this person yet.")
    else:
        for link in skills:
            col1, col2, col3 = st.columns(3)
            col1.metric(label="Skill", value=link.skill.name)
            col2.metric(label="Proficiency (1-5)", value=link.proficiency)
            col3.metric(label="Interest (1-5)", value=link.interest)
    
    st.markdown("---")

    # --- Capacity Section ---
    st.subheader("Work Capacity")
    capacity = db.query(capacity_service.Capacity).filter(capacity_service.Capacity.person_id == person_id).one_or_none()
    if capacity:
        total_hours = st.number_input("Total Hours/Week", value=capacity.total_hours_per_week, min_value=0, step=1)
        committed_hours = st.number_input("Committed Hours", value=capacity.committed_hours, min_value=0, max_value=total_hours, step=1)
        
        if st.button("Update Capacity"):
            capacity_service.update_person_capacity(db, person_id, committed_hours, total_hours)
            st.success("Capacity updated!")
            st.experimental_rerun()
        
        available = total_hours - committed_hours
        st.metric("Available Hours", f"{available} hours")
        st.progress(committed_hours / total_hours if total_hours > 0 else 0)
    else:
        st.warning("Capacity information not set for this person.")

    st.markdown("---")
    
    # --- SWOT Section ---
    st.subheader("SWOT Analysis")
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Add New SWOT Item")
        category = st.selectbox("Category", ["Strength", "Weakness", "Opportunity", "Threat"])
        description = st.text_area("Description")
        if st.button("Add SWOT Item"):
            if description:
                swot_service.add_swot_item(db, person_id, category, description)
                st.success("SWOT item added!")
                st.experimental_rerun()
            else:
                st.error("Description cannot be empty.")

    with col2:
        st.write("#### Current SWOTs")
        swots = swot_service.get_swot_for_person(db, person_id)
        if not swots:
            st.info("No SWOT items recorded yet.")
        else:
            for item in swots:
                st.markdown(f"**{item.category}:** {item.description}")

