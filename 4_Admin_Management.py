"""
Streamlit Page: Admin Management
Allows adding and managing team members, skills, and skill assessments.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from app.db.session import get_db_session
from app.models.person import Person
from app.models.skill import Skill, PersonSkill
from app.models.capacity import Capacity
from app.services.skill_matrix_service import get_all_categories

st.set_page_config(page_title="Admin Management", page_icon="⚙️", layout="wide")
st.title("⚙️ Admin Management")

# Initialize database session - THIS MUST BE FIRST
db = next(get_db_session())

# Create tabs for different management functions
tab1, tab2, tab3, tab4 = st.tabs(["👥 Manage People", "🎯 Manage Skills", "📊 Assign Skills", "📈 Update Skill Levels"])

# ==================== TAB 1: MANAGE PEOPLE ====================
with tab1:
    st.header("Team Member Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Add New Team Member")
        with st.form("add_person_form"):
            new_name = st.text_input("Full Name")
            new_role = st.text_input("Role (e.g., Senior Developer, Team Lead)")
            total_hours = st.number_input("Total Hours per Week", min_value=0, max_value=168, value=40)
            committed_hours = st.number_input("Currently Committed Hours", min_value=0, max_value=total_hours, value=0)
            
            submitted = st.form_submit_button("Add Team Member", type="primary")
            
            if submitted:
                if not new_name or not new_role:
                    st.error("Please fill in all fields")
                else:
                    # Check if person already exists
                    existing = db.query(Person).filter(Person.name == new_name).first()
                    if existing:
                        st.error(f"Person '{new_name}' already exists!")
                    else:
                        try:
                            # Create new person
                            new_person = Person(name=new_name, role=new_role)
                            db.add(new_person)
                            db.flush()  # Get the ID without committing
                            
                            # Add capacity
                            new_capacity = Capacity(
                                person_id=new_person.id,
                                total_hours_per_week=total_hours,
                                committed_hours=committed_hours
                            )
                            db.add(new_capacity)
                            db.commit()
                            
                            st.success(f"✅ Added {new_name} ({new_role}) successfully!")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding person: {e}")
                            db.rollback()
    
    with col2:
        st.subheader("📋 Current Team Members")
        people = db.query(Person).order_by(Person.name).all()
        
        if people:
            # Display as DataFrame
            people_data = []
            for p in people:
                capacity = db.query(Capacity).filter(Capacity.person_id == p.id).first()
                people_data.append({
                    "ID": p.id,
                    "Name": p.name,
                    "Role": p.role,
                    "Total Hours": capacity.total_hours_per_week if capacity else "N/A",
                    "Committed": capacity.committed_hours if capacity else "N/A",
                    "Available": capacity.available_hours if capacity else "N/A"
                })
            
            df_people = pd.DataFrame(people_data)
            st.dataframe(df_people, use_container_width=True)
            
            # Delete person (with caution)
            st.subheader("🗑️ Remove Team Member")
            person_to_delete = st.selectbox(
                "Select person to remove",
                options=[p.name for p in people],
                key="delete_person"
            )
            
            if st.button("Delete Person", type="secondary"):
                person = db.query(Person).filter(Person.name == person_to_delete).first()
                if person:
                    # Confirm deletion
                    st.warning(f"⚠️ Are you sure you want to delete {person.name}? This will also remove all their skills, capacity, and SWOT data.")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("Yes, Delete Permanently", key="confirm_delete"):
                            try:
                                db.delete(person)
                                db.commit()
                                st.success(f"✅ Deleted {person.name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting person: {e}")
                                db.rollback()
        else:
            st.info("No team members yet. Add your first team member!")

# ==================== TAB 2: MANAGE SKILLS ====================
with tab2:
    st.header("Skill Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("➕ Add New Skill")
        with st.form("add_skill_form"):
            new_skill_name = st.text_input("Skill Name")
            new_skill_category = st.selectbox(
                "Skill Category",
                options=["Backend", "Frontend", "Database", "DevOps", "Soft Skill", "Leadership", "Architecture", "Other"]
            )
            custom_category = st.text_input("Or specify custom category", placeholder="e.g., Data Science")
            
            submitted = st.form_submit_button("Add Skill", type="primary")
            
            if submitted:
                if not new_skill_name:
                    st.error("Please enter a skill name")
                else:
                    # Use custom category if provided, otherwise use selected
                    category = custom_category if custom_category else new_skill_category
                    
                    # Check if skill already exists
                    existing = db.query(Skill).filter(Skill.name == new_skill_name).first()
                    if existing:
                        st.error(f"Skill '{new_skill_name}' already exists!")
                    else:
                        try:
                            new_skill = Skill(name=new_skill_name, category=category)
                            db.add(new_skill)
                            db.commit()
                            st.success(f"✅ Added skill: {new_skill_name} ({category})")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error adding skill: {e}")
                            db.rollback()
    
    with col2:
        st.subheader("📋 Current Skills")
        skills = db.query(Skill).order_by(Skill.category, Skill.name).all()
        
        if skills:
            # Display skills grouped by category
            skills_by_category = {}
            for skill in skills:
                if skill.category not in skills_by_category:
                    skills_by_category[skill.category] = []
                skills_by_category[skill.category].append(skill.name)
            
            for category, skill_list in skills_by_category.items():
                with st.expander(f"📁 {category} ({len(skill_list)} skills)"):
                    for skill_name in sorted(skill_list):
                        st.write(f"• {skill_name}")
            
            # Delete skill
            st.subheader("🗑️ Remove Skill")
            skill_to_delete = st.selectbox(
                "Select skill to remove",
                options=[s.name for s in skills],
                key="delete_skill"
            )
            
            if st.button("Delete Skill", type="secondary"):
                skill = db.query(Skill).filter(Skill.name == skill_to_delete).first()
                if skill:
                    # Check if skill is assigned to anyone
                    assignments = db.query(PersonSkill).filter(PersonSkill.skill_id == skill.id).count()
                    if assignments > 0:
                        st.warning(f"⚠️ This skill is assigned to {assignments} person(s). Deleting will remove these assignments.")
                    
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("Yes, Delete Skill", key="confirm_delete_skill"):
                            try:
                                db.delete(skill)
                                db.commit()
                                st.success(f"✅ Deleted skill: {skill_to_delete}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting skill: {e}")
                                db.rollback()
        else:
            st.info("No skills added yet. Add your first skill!")

# ==================== TAB 3: ASSIGN SKILLS ====================
with tab3:
    st.header("Assign Skills to Team Members")
    
    # Get people and skills
    people = db.query(Person).order_by(Person.name).all()
    skills = db.query(Skill).order_by(Skill.name).all()
    
    if not people:
        st.warning("No team members found. Please add people first.")
    elif not skills:
        st.warning("No skills found. Please add skills first.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_person_name = st.selectbox(
                "Select Team Member",
                options=[p.name for p in people],
                key="assign_person"
            )
            selected_person = next(p for p in people if p.name == selected_person_name)
            
            # Show current skills for this person
            st.subheader(f"Current Skills for {selected_person.name}")
            current_skills = db.query(PersonSkill).filter(
                PersonSkill.person_id == selected_person.id
            ).all()
            
            if current_skills:
                current_skills_data = []
                for ps in current_skills:
                    skill = db.query(Skill).filter(Skill.id == ps.skill_id).first()
                    current_skills_data.append({
                        "Skill": skill.name if skill else "Unknown",
                        "Level": ps.level,
                        "Target": ps.target_level,
                        "Last Updated": ps.last_updated.strftime("%Y-%m-%d") if ps.last_updated else "Never"
                    })
                df_current = pd.DataFrame(current_skills_data)
                st.dataframe(df_current, use_container_width=True)
            else:
                st.info("No skills assigned yet")
        
        with col2:
            st.subheader("➕ Assign New Skill")
            with st.form("assign_skill_form"):
                # Get already assigned skill IDs
                assigned_skill_ids = [ps.skill_id for ps in current_skills]
                available_skills = [s for s in skills if s.id not in assigned_skill_ids]
                
                if available_skills:
                    skill_to_assign = st.selectbox(
                        "Select Skill",
                        options=[s.name for s in available_skills]
                    )
                    skill_obj = next(s for s in skills if s.name == skill_to_assign)
                    
                    col_level, col_target = st.columns(2)
                    with col_level:
                        current_level = st.slider(
                            "Current Proficiency Level",
                            min_value=0, max_value=4, value=0,
                            help="0=None, 1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert"
                        )
                    with col_target:
                        target_level = st.slider(
                            "Target Proficiency Level",
                            min_value=0, max_value=4, value=2,
                            help="Desired skill level"
                        )
                    
                    assigned = st.form_submit_button("Assign Skill", type="primary")
                    
                    if assigned:
                        try:
                            new_assignment = PersonSkill(
                                person_id=selected_person.id,
                                skill_id=skill_obj.id,
                                level=current_level,
                                target_level=target_level
                            )
                            db.add(new_assignment)
                            db.commit()
                            st.success(f"✅ Assigned {skill_to_assign} to {selected_person.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error assigning skill: {e}")
                            db.rollback()
                else:
                    st.info("All skills already assigned to this person")
        
        # Remove skill assignment
        current_skills = db.query(PersonSkill).filter(
            PersonSkill.person_id == selected_person.id
        ).all()
        
        if current_skills:
            st.markdown("---")
            st.subheader("🗑️ Remove Skill Assignment")
            
            skill_options = []
            for ps in current_skills:
                skill = db.query(Skill).filter(Skill.id == ps.skill_id).first()
                if skill:
                    skill_options.append(skill.name)
            
            if skill_options:
                skill_to_remove = st.selectbox(
                    "Select skill to remove",
                    options=skill_options,
                    key="remove_skill"
                )
                
                if st.button("Remove Skill Assignment", type="secondary"):
                    skill_obj = next(s for s in skills if s.name == skill_to_remove)
                    assignment = db.query(PersonSkill).filter(
                        PersonSkill.person_id == selected_person.id,
                        PersonSkill.skill_id == skill_obj.id
                    ).first()
                    
                    if assignment:
                        try:
                            db.delete(assignment)
                            db.commit()
                            st.success(f"✅ Removed {skill_to_remove} from {selected_person.name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error removing skill: {e}")
                            db.rollback()

# ==================== TAB 4: UPDATE SKILL LEVELS ====================
with tab4:
    st.header("Update Skill Levels and Targets")
    
    # Get people and their skills
    people = db.query(Person).order_by(Person.name).all()
    
    if not people:
        st.warning("No team members found")
    else:
        selected_person_name = st.selectbox(
            "Select Team Member",
            options=[p.name for p in people],
            key="update_person"
        )
        selected_person = next(p for p in people if p.name == selected_person_name)
        
        # Get all skill assignments for this person
        assignments = db.query(PersonSkill).filter(
            PersonSkill.person_id == selected_person.id
        ).all()
        
        if not assignments:
            st.info(f"No skills assigned to {selected_person.name}. Go to 'Assign Skills' tab first.")
        else:
            st.subheader(f"Update Skills for {selected_person.name}")
            st.markdown("**Skill Level Guide:** 0=None, 1=Beginner, 2=Intermediate, 3=Advanced, 4=Expert")
            
            updates_made = False
            
            for assignment in assignments:
                skill = db.query(Skill).filter(Skill.id == assignment.skill_id).first()
                if not skill:
                    continue
                
                with st.container():
                    st.markdown(f"### {skill.name}")
                    st.caption(f"Category: {skill.category}")
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        new_level = st.slider(
                            f"Current Level",
                            min_value=0, max_value=4,
                            value=assignment.level,
                            key=f"level_{assignment.person_id}_{assignment.skill_id}"
                        )
                    
                    with col2:
                        new_target = st.slider(
                            f"Target Level",
                            min_value=0, max_value=4,
                            value=assignment.target_level,
                            key=f"target_{assignment.person_id}_{assignment.skill_id}"
                        )
                    
                    with col3:
                        if st.button(f"Update", key=f"update_{assignment.person_id}_{assignment.skill_id}"):
                            assignment.level = new_level
                            assignment.target_level = new_target
                            updates_made = True
                            st.success(f"Updated {skill.name}")
                    
                    st.markdown("---")
            
            if updates_made:
                try:
                    db.commit()
                    st.success("✅ All skill levels updated successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error saving updates: {e}")
                    db.rollback()