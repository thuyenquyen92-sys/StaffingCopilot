"""
Streamlit Page: Skill/Will Delegation Readiness Matrix
Implements Hersey-Blanchard Situational Leadership model.
Shows quadrants and provides delegation recommendations.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from app.db.session import get_db_session
from app.services.readiness_service import (
    get_readiness_assessments,
    save_readiness_assessment,
    get_person_readiness_matrix,
    get_delegation_recommendation,
    skill_level_from_int,
    will_level_from_int,
    DelegationStyle
)
from app.models.person import Person

st.set_page_config(page_title="Delegation Readiness", page_icon="🎯", layout="wide")
st.title("🎯 Skill/Will Delegation Matrix")

# Initialize database session
db = next(get_db_session())

# Sidebar for navigation
st.sidebar.header("Navigation")
view = st.sidebar.radio(
    "Select View",
    ["📊 Readiness Matrix", "✏️ Add/Edit Assessment", "💡 Delegation Guide"]
)

if view == "📊 Readiness Matrix":
    st.header("Team Readiness Assessment Matrix")
    
    # Get matrix data
    matrix_data = get_person_readiness_matrix(db)
    
    if not matrix_data["people"]:
        st.warning("No team members found. Please add people first.")
        st.stop()
    
    if not matrix_data["domains"]:
        st.warning("No readiness assessments found. Use 'Add/Edit Assessment' to create some.")
        
        # Show example of what to do
        with st.expander("ℹ️ How to get started"):
            st.markdown("""
            1. Go to **Add/Edit Assessment** tab
            2. Select a team member
            3. Choose a domain (skill category)
            4. Rate their Skill level (1-3) and Will level (1-3)
            5. The system will automatically classify their delegation style
            """)
        st.stop()
    
    # Display as interactive cards
    for person_data in matrix_data["matrix"]:
        person = person_data["person"]
        assessments = person_data["assessments"]
        
        with st.expander(f"**{person.name}** - {person.role}"):
            # Create columns for each assessment
            if assessments:
                # Build DataFrame for this person
                df_person = pd.DataFrame([
                    {
                        "Domain": a["domain"],
                        "Skill": a["skill_level"].value if a["skill_level"] else "N/A",
                        "Will": a["will_level"].value if a["will_level"] else "N/A",
                        "Delegation Style": a["delegation_style"].value if a["delegation_style"] else "N/A",
                        "Last Updated": a["last_updated"].strftime("%Y-%m-%d") if a["last_updated"] else "Never"
                    }
                    for a in assessments if a["skill_level"] is not None
                ])
                
                if not df_person.empty:
                    # Add color coding for delegation styles
                    def style_delegation(val):
                        colors = {
                            "Direct": "background-color: #ffcccc",
                            "Guide": "background-color: #ffffcc",
                            "Motivate": "background-color:#cce5ff",
                            "Delegate": "background-color:#ccffcc"
                        }
                        return colors.get(val, "")
                    
                    # Apply styling - compatible with both old and new pandas versions
                    try:
                    # For pandas >= 2.1.0
                        styled_df = df_person.style.map(style_delegation, subset=["Delegation Style"])
                    except AttributeError:
                     # For older pandas versions
                        styled_df = df_person.style.applymap(style_delegation, subset=["Delegation Style"])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Add quick recommendation button
                    for assessment in assessments:
                        if assessment["delegation_style"]:
                            col1, col2, col3 = st.columns([2, 1, 1])
                            with col1:
                                st.markdown(f"**{assessment['domain']}** - {assessment['delegation_style'].value}")
                            with col2:
                                if st.button(f"Recommendation", key=f"rec_{person.id}_{assessment['domain']}"):
                                    st.session_state['selected_person'] = person.id
                                    st.session_state['selected_domain'] = assessment['domain']
                                    st.rerun()
                else:
                    st.info("No assessments completed yet for this person")
            else:
                st.info("No assessments found for this person")
    
    # Show recommendation if selected
    if 'selected_person' in st.session_state and 'selected_domain' in st.session_state:
        rec = get_delegation_recommendation(db, st.session_state['selected_person'], st.session_state['selected_domain'])
        if rec:
            st.markdown("---")
            st.subheader(f"Delegation Recommendation for {rec['person_name']} - {rec['domain']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Skill Level", rec['skill_level'])
            with col2:
                st.metric("Will Level", rec['will_level'])
            with col3:
                st.metric("Style", rec['delegation_style'])
            
            st.info(f"**Action:** {rec['recommendation']['action']}")
            st.success(f"**Approach:** {rec['recommendation']['approach']}")
            st.markdown(f"**Next Steps:** {rec['recommendation']['next_steps']}")

elif view == "✏️ Add/Edit Assessment":
    st.header("Add or Update Readiness Assessment")
    
    # Person selector
    people = db.query(Person).order_by(Person.name).all()
    if not people:
        st.error("No people found. Please add people first.")
        st.stop()
    
    person_map = {p.name: p.id for p in people}
    selected_person_name = st.selectbox("Select Team Member", options=list(person_map.keys()))
    person_id = person_map[selected_person_name]
    person = next(p for p in people if p.id == person_id)
    
    st.markdown(f"**Role:** {person.role}")
    
    # Domain input
    domain = st.text_input(
        "Skill Domain/Category",
        placeholder="e.g., Frontend Development, Data Analysis, Leadership",
        help="Define the skill domain for this assessment"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Skill Level")
        st.caption("Rate their competence in this domain")
        skill_level = st.slider(
            "Skill Level (1-3)",
            min_value=1,
            max_value=3,
            value=2,
            help="""
            **1 - Low:** Needs guidance, limited experience
            **2 - Medium:** Can work independently
            **3 - High:** Expert, can mentor others
            """
        )
        
        # Visual indicator for skill level
        if skill_level == 1:
            st.warning("🟠 Low Skill")
        elif skill_level == 2:
            st.info("🟡 Medium Skill")
        else:
            st.success("🟢 High Skill")
    
    with col2:
        st.markdown("#### Will/Motivation Level")
        st.caption("Rate their enthusiasm and motivation")
        will_level = st.slider(
            "Will Level (1-3)",
            min_value=1,
            max_value=3,
            value=2,
            help="""
            **1 - Low:** Unmotivated, needs encouragement
            **2 - Medium:** Generally engaged
            **3 - High:** Highly motivated, self-starter
            """
        )
        
        # Visual indicator for will level
        if will_level == 1:
            st.warning("🟠 Low Will")
        elif will_level == 2:
            st.info("🟡 Medium Will")
        else:
            st.success("🟢 High Will")
    
    # Show the delegation style that will be applied
    from app.services.readiness_service import calculate_delegation_style, skill_level_from_int, will_level_from_int
    skill_enum = skill_level_from_int(skill_level)
    will_enum = will_level_from_int(will_level)
    style = calculate_delegation_style(skill_enum, will_enum)
    
    st.markdown("---")
    st.markdown("#### 📋 Assessment Result")
    
    # Show quadrant with color coding
    style_colors = {
        "Direct": "🔴",
        "Guide": "🟡",
        "Motivate": "🔵",
        "Delegate": "🟢"
    }
    
    style_descriptions = {
        "Direct": "Provide clear instructions and close supervision",
        "Guide": "Coach and support, explain reasoning",
        "Motivate": "Inspire and involve in decisions",
        "Delegate": "Give ownership and trust their judgment"
    }
    
    col_style, col_desc = st.columns([1, 2])
    with col_style:
        st.markdown(f"### {style_colors[style.value]} {style.value}")
    with col_desc:
        st.markdown(f"**Strategy:** {style_descriptions[style.value]}")
    
    # Notes
    notes = st.text_area("Notes (optional)", placeholder="Add any observations or context...")
    
    if st.button("💾 Save Assessment", type="primary"):
        if not domain:
            st.error("Please enter a domain/category")
        else:
            assessment = save_readiness_assessment(db, person_id, domain, skill_level, will_level, notes)
            st.success(f"✅ Assessment saved for {person.name} - {domain}")
            st.balloons()
            
            # Show the quadrant visualization
            st.markdown("### 📊 Skill/Will Quadrant")
            
            # Create a simple quadrant visualization
            fig = px.scatter(
                x=[skill_level], y=[will_level],
                range_x=[0.5, 3.5], range_y=[0.5, 3.5],
                title="Current Position in Skill/Will Matrix"
            )
            
            # Add quadrant annotations
            fig.add_annotation(x=1.5, y=2.5, text="GUIDE", showarrow=False, font=dict(size=12))
            fig.add_annotation(x=2.5, y=2.5, text="DELEGATE", showarrow=False, font=dict(size=12))
            fig.add_annotation(x=1.5, y=1.5, text="DIRECT", showarrow=False, font=dict(size=12))
            fig.add_annotation(x=2.5, y=1.5, text="MOTIVATE", showarrow=False, font=dict(size=12))
            
            fig.update_xaxes(title="Skill Level", tickvals=[1, 2, 3])
            fig.update_yaxes(title="Will Level", tickvals=[1, 2, 3])
            
            st.plotly_chart(fig, use_container_width=True)

elif view == "💡 Delegation Guide":
    st.header("Understanding the Skill/Will Matrix")
    
    st.markdown("""
    ## The Situational Leadership Model
    
    The Skill/Will matrix helps you determine the best delegation approach based on 
    a person's **competence (Skill)** and **commitment (Will)**.
    """)
    
    # Create 2x2 grid for quadrants
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🟡 GUIDE (Low Skill + High Will)")
        st.info("""
        **When to use:** Person is motivated but lacks experience
        
        **Strategy:** 
        - Coach and support
        - Explain the 'why' behind tasks
        - Provide structured guidance
        - Celebrate small wins
        """)
        
        st.markdown("### 🔴 DIRECT (Low Skill + Low Will)")
        st.error("""
        **When to use:** Person lacks both ability and motivation
        
        **Strategy:**
        - Give clear, specific instructions
        - Set short-term goals
        - Provide frequent feedback
        - Build confidence through small successes
        """)
    
    with col2:
        st.markdown("### 🟢 DELEGATE (High Skill + High Will)")
        st.success("""
        **When to use:** Person is competent and motivated
        
        **Strategy:**
        - Give ownership and autonomy
        - Define outcomes, not methods
        - Step back and trust their judgment
        - Recognize achievements
        """)
        
        st.markdown("### 🔵 MOTIVATE (High Skill + Low Will)")
        st.warning("""
        **When to use:** Person has ability but lacks motivation
        
        **Strategy:**
        - Inspire and involve in decisions
        - Connect work to purpose
        - Ask for their opinion
        - Address underlying concerns
        """)
    
    st.markdown("---")
    st.subheader("Best Practices")
    
    st.markdown("""
    1. **Regular Assessments:** Update assessments quarterly or after major projects
    2. **Context Matters:** A person may be in different quadrants for different domains
    3. **Development Path:** People generally move: DIRECT → GUIDE → DELEGATE
    4. **Watch for Regression:** Skills can atrophy, motivation can fluctuate
    5. **Document Notes:** Capture observations to track patterns over time
    """)
    
    # Historical tracking section
    st.subheader("Historical Tracking")
    
    show_history = st.checkbox("Show assessment history")
    if show_history:
        people = db.query(Person).order_by(Person.name).all()
        if people:
            selected_person_name = st.selectbox("Select person", [p.name for p in people])
            person = next(p for p in people if p.name == selected_person_name)
            
            assessments = get_readiness_assessments(db, person_id=person.id)
            if assessments:
                df_history = pd.DataFrame([{
                    "Domain": a.domain,
                    "Skill": a.skill_level.value,
                    "Will": a.will_level.value,
                    "Style": a.delegation_style.value,
                    "Last Updated": a.last_updated.strftime("%Y-%m-%d"),
                    "Notes": a.notes[:50] + "..." if a.notes and len(a.notes) > 50 else a.notes
                } for a in assessments])
                
                st.dataframe(df_history, use_container_width=True)
            else:
                st.info("No history found for this person")