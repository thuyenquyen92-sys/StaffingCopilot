"""
Streamlit Page: SWOT Analysis Management
View, add, edit, and delete SWOT items for team members.
SWOT = Strengths, Weaknesses, Opportunities, Threats
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from app.db.session import get_db_session
from app.models.person import Person
from app.models.swot import SWOT

st.set_page_config(page_title="SWOT Analysis", page_icon="🎯", layout="wide")
st.title("🎯 SWOT Analysis Management")

# Initialize database session
db = next(get_db_session())

# Initialize session state for editing
if 'editing_swot_id' not in st.session_state:
    st.session_state.editing_swot_id = None
if 'editing_text' not in st.session_state:
    st.session_state.editing_text = ""

# Sidebar filters
st.sidebar.header("Filters")
selected_category = st.sidebar.multiselect(
    "Filter by Category",
    options=["Strength", "Weakness", "Opportunity", "Threat"],
    default=["Strength", "Weakness", "Opportunity", "Threat"]
)

# Create tabs
tab1, tab2, tab3 = st.tabs(["📊 SWOT Matrix", "✏️ Manage SWOT", "📈 SWOT Analytics"])

# ==================== TAB 1: SWOT MATRIX ====================
with tab1:
    st.header("Team SWOT Matrix")
    
    # Get all people
    people = db.query(Person).order_by(Person.name).all()
    
    if not people:
        st.warning("No team members found. Please add people first.")
        st.stop()
    
    # Person selector
    selected_person_name = st.selectbox(
        "Select Team Member",
        options=[p.name for p in people],
        key="swot_person_select"
    )
    selected_person = next(p for p in people if p.name == selected_person_name)
    
    # Get SWOT items for selected person
    swot_items = db.query(SWOT).filter(
        SWOT.person_id == selected_person.id,
        SWOT.category.in_(selected_category)
    ).order_by(SWOT.category).all()
    
    # Display SWOT in 2x2 grid
    col1, col2 = st.columns(2)
    
    with col1:
        # Strengths
        st.markdown("### 💪 Strengths")
        strengths = [item for item in swot_items if item.category == "Strength"]
        if strengths:
            for item in strengths:
                with st.container():
                    st.markdown(f"**✓** {item.description}")
                    col_a, col_b = st.columns([4, 1])
                    with col_b:
                        if st.button(f"✏️", key=f"edit_{item.id}"):
                            st.session_state.editing_swot_id = item.id
                            st.session_state.editing_text = item.description
                            st.rerun()
                        if st.button(f"🗑️", key=f"delete_{item.id}"):
                            db.delete(item)
                            db.commit()
                            st.success("SWOT item deleted!")
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("No strengths recorded")
        
        # Weaknesses  
        st.markdown("### 🔴 Weaknesses")
        weaknesses = [item for item in swot_items if item.category == "Weakness"]
        if weaknesses:
            for item in weaknesses:
                with st.container():
                    st.markdown(f"**✗** {item.description}")
                    col_a, col_b = st.columns([4, 1])
                    with col_b:
                        if st.button(f"✏️", key=f"edit_{item.id}"):
                            st.session_state.editing_swot_id = item.id
                            st.session_state.editing_text = item.description
                            st.rerun()
                        if st.button(f"🗑️", key=f"delete_{item.id}"):
                            db.delete(item)
                            db.commit()
                            st.success("SWOT item deleted!")
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("No weaknesses recorded")
    
    with col2:
        # Opportunities
        st.markdown("### 🌟 Opportunities")
        opportunities = [item for item in swot_items if item.category == "Opportunity"]
        if opportunities:
            for item in opportunities:
                with st.container():
                    st.markdown(f"**→** {item.description}")
                    col_a, col_b = st.columns([4, 1])
                    with col_b:
                        if st.button(f"✏️", key=f"edit_{item.id}"):
                            st.session_state.editing_swot_id = item.id
                            st.session_state.editing_text = item.description
                            st.rerun()
                        if st.button(f"🗑️", key=f"delete_{item.id}"):
                            db.delete(item)
                            db.commit()
                            st.success("SWOT item deleted!")
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("No opportunities recorded")
        
        # Threats
        st.markdown("### ⚠️ Threats")
        threats = [item for item in swot_items if item.category == "Threat"]
        if threats:
            for item in threats:
                with st.container():
                    st.markdown(f"**⚠** {item.description}")
                    col_a, col_b = st.columns([4, 1])
                    with col_b:
                        if st.button(f"✏️", key=f"edit_{item.id}"):
                            st.session_state.editing_swot_id = item.id
                            st.session_state.editing_text = item.description
                            st.rerun()
                        if st.button(f"🗑️", key=f"delete_{item.id}"):
                            db.delete(item)
                            db.commit()
                            st.success("SWOT item deleted!")
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("No threats recorded")

# ==================== TAB 2: MANAGE SWOT ====================
with tab2:
    st.header("Manage SWOT Items")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("➕ Add New SWOT Item")
        with st.form("add_swot_form"):
            # Person selection
            add_person = st.selectbox(
                "Team Member",
                options=[p.name for p in people],
                key="add_swot_person"
            )
            add_person_obj = next(p for p in people if p.name == add_person)
            
            # Category selection
            add_category = st.selectbox(
                "Category",
                options=["Strength", "Weakness", "Opportunity", "Threat"],
                key="add_category"
            )
            
            # Description
            add_description = st.text_area(
                "Description",
                placeholder="Describe the strength, weakness, opportunity, or threat...",
                height=100
            )
            
            # Submit button
            submitted = st.form_submit_button("Add SWOT Item", type="primary")
            
            if submitted:
                if not add_description:
                    st.error("Please enter a description")
                else:
                    # Check for duplicate
                    existing = db.query(SWOT).filter(
                        SWOT.person_id == add_person_obj.id,
                        SWOT.category == add_category,
                        SWOT.description == add_description
                    ).first()
                    
                    if existing:
                        st.warning("This SWOT item already exists for this person")
                    else:
                        new_swot = SWOT(
                            person_id=add_person_obj.id,
                            category=add_category,
                            description=add_description
                        )
                        db.add(new_swot)
                        db.commit()
                        st.success(f"✅ Added {add_category} for {add_person}")
                        st.balloons()
                        st.rerun()
    
    with col2:
        st.subheader("✏️ Edit/Delete SWOT Items")
        
        # Select person to manage
        manage_person = st.selectbox(
            "Select Team Member",
            options=[p.name for p in people],
            key="manage_swot_person"
        )
        manage_person_obj = next(p for p in people if p.name == manage_person)
        
        # Select category
        manage_category = st.selectbox(
            "Category to manage",
            options=["Strength", "Weakness", "Opportunity", "Threat"],
            key="manage_category"
        )
        
        # Get items for this person and category
        items = db.query(SWOT).filter(
            SWOT.person_id == manage_person_obj.id,
            SWOT.category == manage_category
        ).all()
        
        if items:
            st.markdown(f"**{manage_category}s for {manage_person}:**")
            for item in items:
                col_a, col_b, col_c = st.columns([4, 1, 1])
                with col_a:
                    st.markdown(f"• {item.description}")
                with col_b:
                    if st.button(f"Edit", key=f"edit_btn_{item.id}"):
                        st.session_state.editing_swot_id = item.id
                        st.session_state.editing_text = item.description
                        st.rerun()
                with col_c:
                    if st.button(f"Delete", key=f"delete_btn_{item.id}"):
                        db.delete(item)
                        db.commit()
                        st.success(f"Deleted {manage_category} item")
                        st.rerun()
        else:
            st.info(f"No {manage_category.lower()} items found for {manage_person}")
    
    # Edit modal (appears when editing)
    if st.session_state.editing_swot_id:
        st.markdown("---")
        st.subheader("✏️ Edit SWOT Item")
        
        editing_item = db.query(SWOT).filter(SWOT.id == st.session_state.editing_swot_id).first()
        if editing_item:
            new_description = st.text_area(
                "Edit Description",
                value=st.session_state.editing_text,
                height=100,
                key="edit_description"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Changes", type="primary"):
                    editing_item.description = new_description
                    db.commit()
                    st.success("SWOT item updated!")
                    st.session_state.editing_swot_id = None
                    st.session_state.editing_text = ""
                    st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.editing_swot_id = None
                    st.session_state.editing_text = ""
                    st.rerun()

# ==================== TAB 3: SWOT ANALYTICS ====================
with tab3:
    st.header("SWOT Analytics")
    
    # Get all SWOT items
    all_swot = db.query(SWOT).all()
    
    if not all_swot:
        st.info("No SWOT data available. Add some SWOT items first.")
        st.stop()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribution by category
        st.subheader("Distribution by Category")
        category_counts = {}
        for item in all_swot:
            category_counts[item.category] = category_counts.get(item.category, 0) + 1
        
        df_categories = pd.DataFrame({
            'Category': list(category_counts.keys()),
            'Count': list(category_counts.values())
        })
        
        fig_pie = px.pie(
            df_categories,
            values='Count',
            names='Category',
            title='SWOT Distribution',
            color='Category',
            color_discrete_map={
                'Strength': '#2ecc71',
                'Weakness': '#e74c3c',
                'Opportunity': '#3498db',
                'Threat': '#e67e22'
            }
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # SWOT by person
        st.subheader("SWOT Items per Person")
        person_counts = {}
        for item in all_swot:
            person = db.query(Person).filter(Person.id == item.person_id).first()
            if person:
                person_counts[person.name] = person_counts.get(person.name, 0) + 1
        
        if person_counts:
            df_person = pd.DataFrame({
                'Person': list(person_counts.keys()),
                'Count': list(person_counts.values())
            }).sort_values('Count', ascending=True)
            
            fig_bar = px.bar(
                df_person,
                x='Count',
                y='Person',
                orientation='h',
                title='Total SWOT Items per Person',
                color='Count',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Recent additions
    st.subheader("Recent SWOT Additions")
    
    # Get recent items (last 10)
    recent_items = db.query(SWOT).order_by(SWOT.id.desc()).limit(10).all()
    
    if recent_items:
        recent_data = []
        for item in recent_items:
            person = db.query(Person).filter(Person.id == item.person_id).first()
            recent_data.append({
                "Date": item.id,  # Approximate by ID order
                "Person": person.name if person else "Unknown",
                "Category": item.category,
                "Description": item.description[:100] + "..." if len(item.description) > 100 else item.description
            })
        
        df_recent = pd.DataFrame(recent_data)
        st.dataframe(df_recent, use_container_width=True)
    
    # Word cloud style summary (text analysis)
    st.subheader("Common Themes")
    
    # Group by category and find common words
    for category in ["Strength", "Weakness", "Opportunity", "Threat"]:
        category_items = [item.description for item in all_swot if item.category == category]
        
        if category_items:
            with st.expander(f"📊 {category} Themes"):
                # Simple word frequency (top words excluding common stop words)
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'but', 'so', 'if', 'then', 'else', 'when', 'up', 'down', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'than', 'that', 'then', 'thence', 'there', 'these', 'they', 'this', 'those', 'through', 'until', 'unto', 'very', 'just', 'but', 'very', 'can', 'will', 'just', 'shall', 'should', 'now'}
                
                word_freq = {}
                for text in category_items:
                    words = text.lower().split()
                    for word in words:
                        word = word.strip('.,!?;:()[]{}"\'')
                        if word not in stop_words and len(word) > 3:
                            word_freq[word] = word_freq.get(word, 0) + 1
                
                # Show top 10 words
                top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                
                if top_words:
                    df_words = pd.DataFrame(top_words, columns=['Word', 'Frequency'])
                    st.dataframe(df_words, use_container_width=True)
                else:
                    st.info("No common themes identified")

# ==================== BONUS: SWOT Action Plan Generator ====================
st.markdown("---")
st.subheader("💡 SWOT Action Plan Generator")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**How to use SWOT for development:**")
    st.markdown("""
    - **Strengths → Leverage:** Use strengths to overcome weaknesses and seize opportunities
    - **Weaknesses → Improve:** Create development plans to address weaknesses
    - **Opportunities → Pursue:** Assign opportunities to people with relevant strengths
    - **Threats → Mitigate:** Develop contingency plans for identified threats
    """)

with col2:
    st.markdown("**Best Practices:**")
    st.markdown("""
    - Review SWOT quarterly
    - Be specific and actionable
    - Focus on quality over quantity
    - Use SWOT to inform delegation decisions
    - Connect SWOT to skill development goals
    """)

# Export functionality
if st.button("📥 Export SWOT Data (CSV)"):
    export_data = []
    for item in all_swot:
        person = db.query(Person).filter(Person.id == item.person_id).first()
        export_data.append({
            "Person": person.name if person else "Unknown",
            "Category": item.category,
            "Description": item.description,
            "ID": item.id
        })
    
    df_export = pd.DataFrame(export_data)
    csv = df_export.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"swot_export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )