import os
import json
import datetime
import calendar
import warnings

# --- SILENCE WARNINGS ---
warnings.filterwarnings("ignore")

# --- MODERN IMPORTS (Latest LangChain) ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain.memory import ConversationBufferMemory
from langchain_community.utilities import GoogleSearchAPIWrapper

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
os.environ["GOOGLE_API_KEY"] = "Gemini API Key"
os.environ["GOOGLE_CSE_ID"] = "CSE Key"
os.environ["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY") 

# ==========================================
# 🛠️ TOOLS
# ==========================================

@tool
def get_financial_status(query: str):
    """
    Reads the student's local bank data file.
    Returns current balance, budget cap, and recent spending.
    """
    try:
        # Handle the filename issue (txt vs json) automatically
        filename = "student_data.json"
        if not os.path.exists(filename) and os.path.exists("student_data.json.txt"):
            filename = "student_data.json.txt"
            
        with open(filename, "r") as f:
            data = json.load(f)
        
        bal = data["account"]["total_balance"]
        budget = data["account"]["monthly_budget_cap"]
        spent = data["account"]["spent_this_month"]
        return f"📊 FINANCIAL STATUS:\n- Current Balance: ₹{bal}\n- Monthly Limit: ₹{budget}\n- Spent: ₹{spent}"
    except Exception as e:
        return f"Error reading database: {e}"

@tool
def check_affordability_logic(expense_amount: str):
    """
    Checks if an expense is safe based on the DATE and Saturday Reserves.
    Input should be a number (e.g., '500').
    """
    try:
        clean_amount = ''.join(filter(str.isdigit, expense_amount))
        cost = int(clean_amount)
    except ValueError:
        return "Error: Please provide a valid number."

    # Handle filename automatically
    filename = "student_data.json"
    if not os.path.exists(filename) and os.path.exists("student_data.json.txt"):
        filename = "student_data.json.txt"

    with open(filename, "r") as f:
        data = json.load(f)
    
    current_balance = data["account"]["total_balance"]
    
    # --- DYNAMIC DATE LOGIC ---
    today = datetime.date.today()
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    
    saturdays_left = 0
    for day in range(today.day, last_day_of_month + 1):
        check_date = datetime.date(today.year, today.month, day)
        if check_date.weekday() == 5:
            saturdays_left += 1
            
    dinner_cost = data["constraints"]["saturday_dinner_cost"]
    safety_buffer = data["constraints"]["minimum_safety_buffer"]
    reserve_fund = (saturdays_left * dinner_cost) + safety_buffer
    
    true_disposable = current_balance - reserve_fund
    
    if cost > true_disposable:
        return (f"❌ DENIED. Balance: ₹{current_balance}, but Reserved: ₹{reserve_fund} "
                f"(for {saturdays_left} remaining Saturdays). Safe to spend: ₹{true_disposable}.")
    else:
        return (f"✅ APPROVED. Balance: ₹{current_balance}. Reserved: ₹{reserve_fund}. "
                f"Safe to spend: ₹{true_disposable}.")

# Search Tool
search = GoogleSearchAPIWrapper()

@tool
def google_price_scout(query: str):
    """
    Uses Google Search to find real prices in India.
    """
    search_query = f"{query} price in India for students 2025"
    try:
        return f"🔍 GOOGLE SEARCH RESULTS:\n{search.run(search_query)}"
    except Exception as e:
        return "Search failed."

# ==========================================
# 🧠 AGENT SETUP (MODERN & STABLE)
# ==========================================

# Use gemini-1.5-flash (It works with the new library)
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
tools = [get_financial_status, check_affordability_logic, google_price_scout]

# 1. Define the Brain's Persona
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are ScholarSave, a strict financial guardian. "
               "ALWAYS checks 'check_affordability_logic' for big purchases. "
               "Use 'google_price_scout' for shopping deals. "
               "Be concise and date-aware."),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# 2. Create the Agent
agent = create_tool_calling_agent(llm, tools, prompt)

# 3. Create the Executor
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, memory=memory)

# ==========================================
# 🚀 MAIN LOOP
# ==========================================
if __name__ == "__main__":
    print("\n🎓 SCHOLARSAVE: ONLINE (Modern Core). (Type 'quit' to exit)")
    print("---------------------------------------------")
    
    while True:
        user_input = input("\nYOU: ")
        if user_input.lower() in ["quit", "exit"]:
            break
        
        try:
            # Modern execution method
            result = agent_executor.invoke({"input": user_input})
            print(f"\nAGENT: {result['output']}")
        except Exception as e:

            print(f"Error: {e}")
