import streamlit as st
import sys
import os

# --- Path Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Import custom modules ---
from app.db.seed import seed_data
from app.db.session import SessionLocal
from app.models.person import Person
from app.models.skill import Skill
from app.models.swot import SWOT

# --- Page Configuration ---
st.set_page_config(
    page_title="People Management Hub",
    page_icon="🚀",
    layout="wide"
)

# --- Database Initialization ---
try:
    seed_data()
except Exception as e:
    st.error(f"Database initialization issue: {e}")

# --- Sidebar Quick Stats ---
db = SessionLocal()
try:
    person_count = db.query(Person).count()
    skill_count = db.query(Skill).count()
    swot_count = db.query(SWOT).count()
    
    st.sidebar.success(f"📊 **Team Stats**\n\n👥 {person_count} Members\n🎯 {skill_count} Skills\n📝 {swot_count} SWOT Items")
    
    # Quick actions
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Actions")
    if st.sidebar.button("➕ Add Team Member", use_container_width=True):
        st.switch_page("pages/4_Admin_Management.py")
    if st.sidebar.button("🏷️ Add New Skill", use_container_width=True):
        st.switch_page("pages/4_Admin_Management.py")
    if st.sidebar.button("📝 Add SWOT Item", use_container_width=True):
        st.switch_page("pages/6_SWOT_Management.py")
    
    # Recent SWOT highlights
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Recent SWOT Highlights")
    recent_swot = db.query(SWOT).order_by(SWOT.id.desc()).limit(3).all()
    if recent_swot:
        for swot in recent_swot:
            person = db.query(Person).filter(Person.id == swot.person_id).first()
            if person:
                st.sidebar.caption(f"**{person.name} - {swot.category}**")
                st.sidebar.text(swot.description[:60] + "..." if len(swot.description) > 60 else swot.description)
    else:
        st.sidebar.caption("No SWOT items yet")
finally:
    db.close()

# --- Main Page UI ---
st.title("🚀 Welcome to the People Management Hub")

st.markdown("""
This application is designed to support effective people management through
data-driven insights.

### Core Features:
- **📊 Team Skill Matrix:** View and filter team skills
- **🎯 Delegation Readiness:** Skill/Will matrix for delegation decisions  
- **👤 Person Profile:** Deep dive into individual skills and capacity
- **💡 Task Matching:** Find the best person for a task
- **⚙️ Admin Management:** Add/Edit team members, skills, and assessments
- **📅 Capacity Planning:** Track FTE allocation across months
- **📝 SWOT Analysis:** Manage Strengths, Weaknesses, Opportunities, Threats

**Navigate using the sidebar to get started.**
""")

# Feature highlights in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("📊 **Skill Matrix**\n\nInteractive table showing skill levels for all team members")

with col2:
    st.info("🎯 **Delegation**\n\nSkill/Will matrix with automatic delegation style classification")

with col3:
    st.info("📅 **Capacity**\n\nTrack monthly FTE allocation and team utilization")

with col4:
    st.info("📝 **SWOT**\n\nComprehensive SWOT analysis for each team member")