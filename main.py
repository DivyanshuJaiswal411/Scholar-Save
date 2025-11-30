import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import tool, initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
# NEW IMPORTS FOR GOOGLE SEARCH
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain.tools import Tool

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
# 1. Your Gemini Key
os.environ["GOOGLE_API_KEY"] = "PASTE_YOUR_GEMINI_KEY_HERE"

# 2. Your Google Search Keys (NEW)
os.environ["GOOGLE_CSE_ID"] = "PASTE_YOUR_SEARCH_ENGINE_ID_HERE"
# Note: Usually the same API key works for both if enabled in the same project, 
# but if you have a separate one, paste it here:
# os.environ["GOOGLE_API_KEY"] = "PASTE_YOUR_SEARCH_API_KEY_HERE" 

# ==========================================
# 🛠️ TOOLS
# ==========================================

@tool
def get_financial_status(query: str):
    """Reads the student's local bank data file."""
    try:
        with open("student_data.json", "r") as f:
            data = json.load(f)
        bal = data["account"]["total_balance"]
        budget = data["account"]["monthly_budget_cap"]
        return f"📊 STATUS: Balance: ₹{bal} | Budget: ₹{budget}"
    except Exception as e:
        return f"Error reading database: {e}"

@tool
def check_affordability_logic(expense_amount: str):
    """
    Checks if an expense is safe by subtracting 'Saturday Reserves'.
    Input: Expense amount as a number (e.g., '500').
    """
    try:
        clean_amount = ''.join(filter(str.isdigit, expense_amount))
        cost = int(clean_amount)
    except ValueError:
        return "Error: Please provide a number."

    with open("student_data.json", "r") as f:
        data = json.load(f)
    
    current_balance = data["account"]["total_balance"]
    reserve_fund = (data["constraints"]["saturdays_left_in_month"] * data["constraints"]["saturday_dinner_cost"]) + \
                    data["constraints"]["minimum_safety_buffer"]
    
    true_disposable = current_balance - reserve_fund
    
    if cost > true_disposable:
        return (f"❌ DENIED. Balance: ₹{current_balance}, but Reserved: ₹{reserve_fund}. "
                f"Safe to spend: ₹{true_disposable}.")
    else:
        return f"✅ APPROVED. Safe to spend: ₹{true_disposable}."

# --- NEW GOOGLE SEARCH TOOL ---
search = GoogleSearchAPIWrapper()

@tool
def google_price_scout(query: str):
    """
    Uses GOOGLE SEARCH to find real prices in India.
    Use this for pens, books, trains, or food prices.
    """
    # Force context for Indian students
    search_query = f"{query} price in India for students 2025"
    try:
        results = search.run(search_query)
        return f"🔍 GOOGLE RESULTS:\n{results}"
    except Exception as e:
        return f"Google Search Error: {e}"

# ==========================================
# 🧠 AGENT SETUP
# ==========================================

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

# Updated tool list
tools = [get_financial_status, check_affordability_logic, google_price_scout]

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

system_message = """
You are 'ScholarSave', a strict financial guardian.
1. ALWAYS check affordability logic before approving purchases.
2. Use Google Search to find cheaper alternatives for items.
3. Keep answers short and numeric.
"""

agent_chain = initialize_agent(
    tools,
    llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    memory=memory,
    agent_kwargs={"system_message": system_message},
    handle_parsing_errors=True
)

if __name__ == "__main__":
    print("🤖 SCHOLARSAVE (POWERED BY GOOGLE) IS ONLINE...")
    while True:
        user = input("\nYOU: ")
        if user.lower() in ["quit", "exit"]: break
        try:
            print(f"AGENT: {agent_chain.run(user)}")
        except Exception as e:
            print(f"Error: {e}")