"""
Streamlit Page: AI-Powered Task Allocation
Uses AI to recommend the best team member for a new task based on
skills, readiness, capacity, and SWOT analysis.
"""
import streamlit as st
import pandas as pd
import json
import requests
from datetime import datetime
from app.db.session import get_db_session
from app.models.person import Person
from app.models.skill import Skill, PersonSkill
from app.models.capacity import Capacity
from app.models.readiness import Readiness
from app.models.swot import SWOT

st.set_page_config(page_title="AI Task Allocation", page_icon="🤖", layout="wide")
st.title("🤖 AI-Powered Task Allocation")

# Initialize database session
db = next(get_db_session())

# AI Configuration
AI_CONFIG = {
    "base_url": "https://llms.documind.bosch-app.com/v1",
    "model": "deepseek-v4-pro",
    "token": "sk-jjsrmax6YlXErSbdEEwSuyWWM5lkgCK4bZaUYoJdqAQSMSAX"
}

def get_team_member_data(db) -> list:
    """Collect all relevant data for team members"""
    people = db.query(Person).all()
    team_data = []
    
    for person in people:
        # Get skills
        skills = db.query(PersonSkill).filter(
            PersonSkill.person_id == person.id
        ).all()
        
        skill_data = []
        for skill_link in skills:
            skill = db.query(Skill).filter(Skill.id == skill_link.skill_id).first()
            if skill:
                skill_data.append({
                    "name": skill.name,
                    "category": skill.category,
                    "level": skill_link.level,
                    "target_level": skill_link.target_level
                })
        
        # Get capacity
        capacity = db.query(Capacity).filter(Capacity.person_id == person.id).first()
        capacity_data = {
            "total_hours_per_week": capacity.total_hours_per_week if capacity else 40,
            "committed_hours": capacity.committed_hours if capacity else 0,
            "available_hours": capacity.available_hours if capacity else 40
        }
        
        # Get readiness assessments
        readiness = db.query(Readiness).filter(
            Readiness.person_id == person.id
        ).all()
        
        readiness_data = []
        for r in readiness:
            readiness_data.append({
                "domain": r.domain,
                "skill_level": r.skill_level.value,
                "will_level": r.will_level.value,
                "delegation_style": r.delegation_style.value
            })
        
        # Get SWOT analysis
        swot = db.query(SWOT).filter(SWOT.person_id == person.id).all()
        swot_data = {
            "strengths": [s.description for s in swot if s.category == "Strength"],
            "weaknesses": [s.description for s in swot if s.category == "Weakness"],
            "opportunities": [s.description for s in swot if s.category == "Opportunity"],
            "threats": [s.description for s in swot if s.category == "Threat"]
        }
        
        team_data.append({
            "id": person.id,
            "name": person.name,
            "role": person.role,
            "skills": skill_data,
            "capacity": capacity_data,
            "readiness": readiness_data,
            "swot": swot_data
        })
    
    return team_data

def call_ai_for_recommendation(task_description: str, required_skills: list, 
                                timeline: str, priority: str, team_data: list) -> dict:
    """Call AI API to get task allocation recommendation"""
    
    # Prepare the prompt for AI
    prompt = f"""You are an expert team manager. Based on the following task requirements and team member data, recommend the BEST person for this task.

TASK REQUIREMENTS:
- Description: {task_description}
- Required Skills: {', '.join(required_skills)}
- Timeline: {timeline}
- Priority: {priority}

TEAM MEMBERS DATA:
{json.dumps(team_data, indent=2)}

Please analyze and recommend the best person based on:
1. Skill match (current proficiency level)
2. Available capacity (committed vs available hours)
3. Readiness (Skill/Will matrix - Direct, Guide, Motivate, Delegate)
4. SWOT analysis (strengths, weaknesses, opportunities)

Provide your response in the following JSON format:
{{
    "recommended_person": "person_name",
    "reasoning": "detailed explanation of why this person is recommended",
    "confidence_score": 0-100,
    "alternative_candidates": [
        {{
            "name": "person_name",
            "reason": "why they could also be considered"
        }}
    ],
    "delegation_advice": "specific delegation approach to use",
    "risk_factors": ["potential risks to consider"],
    "mitigation_strategies": ["how to address the risks"]
}}

Be thorough in your analysis. Consider that available capacity is critical - don't recommend someone who is overcommitted.
"""

    # API call configuration
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['token']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": AI_CONFIG["model"],
        "messages": [
            {
                "role": "system",
                "content": "You are an expert project manager and team coordinator. Provide detailed, actionable recommendations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        # Make API call
        response = requests.post(
            f"{AI_CONFIG['base_url']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Try to parse JSON from response
            # Find JSON in the response (it might have extra text)
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = ai_response[start_idx:end_idx]
                recommendation = json.loads(json_str)
                return recommendation
            else:
                # If no JSON found, return the raw response
                return {
                    "recommended_person": "Error",
                    "reasoning": ai_response,
                    "confidence_score": 0,
                    "alternative_candidates": [],
                    "delegation_advice": "Unable to parse AI response",
                    "risk_factors": [],
                    "mitigation_strategies": []
                }
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("API request timed out. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to AI service. Please check your network.")
        return None
    except Exception as e:
        st.error(f"Error calling AI service: {str(e)}")
        return None

def calculate_skill_match(required_skills: list, person_skills: list) -> dict:
    """Calculate skill match score without AI (fallback)"""
    match_score = 0
    matched_skills = []
    missing_skills = []
    
    for req_skill in required_skills:
        found = False
        for person_skill in person_skills:
            if req_skill.lower() in person_skill['name'].lower():
                match_score += person_skill['level'] / 4 * 25  # Max 25 points per skill
                matched_skills.append({
                    "skill": req_skill,
                    "level": person_skill['level']
                })
                found = True
                break
        if not found:
            missing_skills.append(req_skill)
    
    return {
        "score": min(match_score, 100),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills
    }

def get_fallback_recommendation(task_description: str, required_skills: list, 
                                 timeline: str, priority: str, team_data: list) -> dict:
    """Fallback recommendation logic when AI is unavailable"""
    
    recommendations = []
    
    for member in team_data:
        # Calculate skill match
        skill_match = calculate_skill_match(required_skills, member['skills'])
        
        # Check capacity
        available_hours = member['capacity']['available_hours']
        has_capacity = available_hours > 20  # Assume task needs at least 20h
        
        # Consider readiness (prefer Delegate/Guide over Direct/Motivate for complex tasks)
        readiness_score = 0
        for readiness in member['readiness']:
            if readiness['delegation_style'] == 'Delegate':
                readiness_score += 100
            elif readiness['delegation_style'] == 'Guide':
                readiness_score += 70
            elif readiness['delegation_style'] == 'Motivate':
                readiness_score += 40
            else:  # Direct
                readiness_score += 10
        
        # Calculate overall score
        overall_score = (
            skill_match['score'] * 0.5 +  # 50% weight on skills
            (readiness_score / 100) * 30 +  # 30% weight on readiness
            (100 if has_capacity else 0) * 0.2  # 20% weight on capacity
        )
        
        recommendations.append({
            "name": member['name'],
            "score": overall_score,
            "skill_match": skill_match['score'],
            "has_capacity": has_capacity,
            "available_hours": available_hours,
            "missing_skills": skill_match['missing_skills']
        })
    
    # Sort by score
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    if recommendations and recommendations[0]['score'] > 0:
        best = recommendations[0]
        return {
            "recommended_person": best['name'],
            "reasoning": f"""
            Recommended based on:
            - Skill match: {best['skill_match']:.1f}%
            - Available capacity: {best['available_hours']} hours/week
            - Missing skills: {', '.join(best['missing_skills']) if best['missing_skills'] else 'None'}
            """,
            "confidence_score": best['score'],
            "alternative_candidates": [
                {"name": rec['name'], "reason": f"Skill match: {rec['skill_match']:.1f}%, Capacity: {rec['available_hours']}h"}
                for rec in recommendations[1:3]
            ],
            "delegation_advice": "Use the Delegation Readiness page to determine the best management approach.",
            "risk_factors": ["Missing skills may require training", "Capacity constraints could affect delivery"],
            "mitigation_strategies": ["Provide additional training", "Adjust timeline if needed"]
        }
    else:
        return None

# ==================== UI ====================

st.markdown("""
This page uses AI to intelligently match tasks to team members based on:
- 🎯 **Skills & Proficiency** - Current and target skill levels
- 💪 **Readiness (Skill/Will)** - Delegation style assessment  
- 📊 **Capacity** - Available hours vs committed work
- 📝 **SWOT Analysis** - Strengths, weaknesses, opportunities, threats
""")

st.markdown("---")

# Task input form
st.header("📋 Task Details")

col1, col2 = st.columns(2)

with col1:
    task_name = st.text_input("Task Name", placeholder="e.g., Develop API Gateway")
    task_description = st.text_area(
        "Task Description",
        placeholder="Describe the task in detail...",
        height=150
    )
    
    priority = st.selectbox(
        "Priority",
        options=["Critical", "High", "Medium", "Low"],
        help="Task priority level"
    )

with col2:
    timeline = st.text_input("Timeline", placeholder="e.g., 2 weeks, Q1 2025, March 15-30")
    
    required_skills_input = st.text_input(
        "Required Skills (comma-separated)",
        placeholder="e.g., Python, API Design, SQL"
    )
    required_skills = [s.strip() for s in required_skills_input.split(",") if s.strip()]
    
    estimated_hours = st.number_input(
        "Estimated Hours",
        min_value=1,
        max_value=160,
        value=40,
        help="Estimated hours needed for this task"
    )
    
    complexity = st.select_slider(
        "Task Complexity",
        options=["Low", "Medium", "High", "Expert"],
        value="Medium"
    )

# Additional context
with st.expander("Additional Context (Optional)"):
    col1, col2 = st.columns(2)
    with col1:
        stakeholders = st.text_input("Key Stakeholders")
        dependencies = st.text_input("Dependencies", placeholder="e.g., Database access, API keys")
    with col2:
        budget_impact = st.selectbox("Budget Impact", ["None", "Low", "Medium", "High"])
        deadline_flexibility = st.selectbox("Deadline Flexibility", ["Fixed", "Flexible", "Very Flexible"])

# Team data preview
with st.expander("View Team Data Being Sent to AI"):
    team_data = get_team_member_data(db)
    st.json(team_data)

# Submit button
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    submit_button = st.button("🤖 Get AI Recommendation", type="primary", use_container_width=True)

# Process recommendation
if submit_button:
    if not task_name or not task_description or not required_skills:
        st.error("Please fill in the task name, description, and required skills.")
    else:
        with st.spinner("🤖 Analyzing team data and getting AI recommendation..."):
            # Get team data
            team_data = get_team_member_data(db)
            
            if not team_data:
                st.error("No team members found. Please add team members first.")
                st.stop()
            
            # Try AI recommendation first
            recommendation = call_ai_for_recommendation(
                task_description, required_skills, timeline, priority, team_data
            )
            
            # If AI fails, use fallback
            if recommendation is None or recommendation.get("recommended_person") == "Error":
                st.warning("⚠️ AI service unavailable. Using fallback recommendation logic.")
                recommendation = get_fallback_recommendation(
                    task_description, required_skills, timeline, priority, team_data
                )
            
            if recommendation:
                # Display recommendation
                st.markdown("---")
                st.header("🎯 AI Recommendation")
                
                # Main recommendation card
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.success(f"### ✅ Recommended: {recommendation['recommended_person']}")
                
                with col2:
                    confidence = recommendation.get('confidence_score', 0)
                    st.metric("Confidence Score", f"{confidence:.0f}%" if confidence else "N/A")
                
                with col3:
                    st.info(f"**Priority:** {priority}")
                
                st.markdown("---")
                
                # Reasoning
                st.subheader("💡 Reasoning")
                st.markdown(recommendation.get('reasoning', 'No reasoning provided'))
                
                # Alternative candidates
                alternatives = recommendation.get('alternative_candidates', [])
                if alternatives:
                    st.subheader("👥 Alternative Candidates")
                    for alt in alternatives:
                        st.markdown(f"**{alt.get('name', 'Unknown')}**: {alt.get('reason', 'No reason provided')}")
                
                # Delegation advice
                st.subheader("📋 Delegation Advice")
                st.info(recommendation.get('delegation_advice', 'Use standard delegation practices'))
                
                # Risk factors and mitigation
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("⚠️ Risk Factors")
                    risks = recommendation.get('risk_factors', [])
                    if risks:
                        for risk in risks:
                            st.warning(f"• {risk}")
                    else:
                        st.caption("No specific risks identified")
                
                with col2:
                    st.subheader("🛡️ Mitigation Strategies")
                    mitigations = recommendation.get('mitigation_strategies', [])
                    if mitigations:
                        for mitigation in mitigations:
                            st.success(f"• {mitigation}")
                    else:
                        st.caption("No specific mitigations suggested")
                
                # Action buttons
                st.markdown("---")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Accept Recommendation"):
                        st.balloons()
                        st.success(f"Task '{task_name}' assigned to {recommendation['recommended_person']}")
                with col2:
                    if st.button("🔄 Compare All"):
                        st.info("Navigate to Skill Matrix or Capacity Planning pages for comparison")
                with col3:
                    if st.button("📧 Notify Team"):
                        st.info("Email notification feature coming soon")
                with col4:
                    if st.button("📅 Schedule Meeting"):
                        st.info("Calendar integration coming soon")
                
                # Export recommendation
                st.markdown("---")
                export_data = {
                    "task": {
                        "name": task_name,
                        "description": task_description,
                        "required_skills": required_skills,
                        "timeline": timeline,
                        "priority": priority,
                        "estimated_hours": estimated_hours
                    },
                    "recommendation": recommendation
                }
                
                st.download_button(
                    label="📥 Download Recommendation (JSON)",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"task_recommendation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
                
            else:
                st.error("Unable to generate recommendation. Please check team data and try again.")

# Display recent tasks (mock data)
st.markdown("---")
st.subheader("📊 Recent Task Allocations")

# Show a sample of recent allocations (you could store these in a database)
sample_allocations = [
    {"task": "API Development", "assigned_to": "Alex Chen", "date": "2024-01-15", "status": "Completed"},
    {"task": "UI Redesign", "assigned_to": "Brenda Smith", "date": "2024-01-20", "status": "In Progress"},
    {"task": "Database Optimization", "assigned_to": "Charlie Day", "date": "2024-01-25", "status": "Pending"}
]

df_allocations = pd.DataFrame(sample_allocations)
st.dataframe(df_allocations, use_container_width=True)

# Tips section
with st.expander("💡 Tips for Better Recommendations"):
    st.markdown("""
    **To get the most accurate recommendations:**
    
    1. **Keep Skills Updated** - Regularly update skill levels and target levels
    2. **Maintain Capacity Data** - Keep committed hours current for accurate availability
    3. **Complete Readiness Assessments** - Fill out Skill/Will matrix for each domain
    4. **Add SWOT Items** - Document strengths and weaknesses for better matching
    5. **Be Specific in Task Description** - More details = better AI analysis
    6. **Specify Required Skills Clearly** - List all critical skills needed
    
    **What the AI considers:**
    - Skill proficiency (0-4 scale)
    - Available capacity vs committed hours
    - Delegation readiness (Skill/Will matrix)
    - SWOT strengths and opportunities
    - Historical patterns (if available)
    """)