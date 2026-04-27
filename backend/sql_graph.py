import os
import duckdb
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from states.doc_state import DocState
from model.model import model1
import logging
logger=logging.getLogger(__name__)

class AnalyticsWorkspace:
    def __init__(self):
        self.con = duckdb.connect(database=':memory:')
        self.tables = []
        self.last_df = None

    def load_data(self, folder, filename):
        file_path = os.path.join(folder, filename)
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.csv', '.xlsx', '.xls']:
            table_name = os.path.splitext(filename)[0].replace(' ', '_').replace('-', '_')
            
            if table_name in self.tables:
                logger.info("Table %s already in workspace. Skipping load.", table_name)
                return True
                
            try:
                df = pd.read_csv(file_path) if ext == '.csv' else pd.read_excel(file_path)
                df.columns = [c.replace(' ', '_').replace('.', '_').replace('-', '_').replace('(', '').replace(')', '') for c in df.columns]
                self.con.register(table_name, df)
                self.con.execute(f"CREATE TABLE {table_name}_stable AS SELECT * FROM {table_name}")
                self.con.execute(f"DROP VIEW {table_name}")
                self.con.execute(f"ALTER TABLE {table_name}_stable RENAME TO {table_name}")
                if table_name not in self.tables:
                    self.tables.append(table_name)
                return True
            except Exception as e:
                logger.error("Error loading %s: %s", filename, e)
        return False


    def get_schema_context(self):
        ctx = ""
        for table in self.tables:
            cols = self.con.execute(f"PRAGMA table_info('{table}')").fetchall()
            col_desc = ", ".join([f"{c[1]} ({c[2]})" for c in cols])
            sample = self.con.execute(f"SELECT * FROM {table} LIMIT 2").df().to_string(index=False)
            ctx += f"Table: {table}\nColumns: {col_desc}\nSample:\n{sample}\n\n"
        return ctx

workspace = AnalyticsWorkspace()

# --- SQL Nodes ---

def sql_prepare_node(state: DocState):
    """Initializes the DuckDB workspace for the current file."""
    if workspace.load_data(state.folder_path, state.filename):
        state.schema_context = workspace.get_schema_context()
    return state

def sql_planner_node(state: DocState):
    """Generates initial SQL and detects if visualization is needed."""
    viz_keywords = ["chart", "plot", "graph", "visualize", "trend", "histogram", "bar"]
    state.viz_requested = any(kw in state.user_query.lower() for kw in viz_keywords)
    
    prompt = ChatPromptTemplate.from_template("""
You are an expert Data Engineer and Senior SQL Developer specializing in DuckDB.
Your task is to generate a high-performance, syntactically correct DuckDB SQL query that answers the user's question using ONLY the provided schema.

[SCHEMA CONTEXT]
{schema}

[USER QUERY]
{query}

[STRICT RULES]

OUTPUT FORMAT
1. Output ONLY the raw SQL query.
2. No markdown, no explanations, no comments, no backticks.
3. The query must be directly executable in DuckDB.

IDENTIFIERS
4. Always wrap ALL table and column names in double quotes.
   Example: SELECT "Column_Name" FROM "Table_Name".

STRINGS
5. Always use single quotes for string literals.

TEXT MATCHING
6. For searching within text columns, ALWAYS use:
   "column" ILIKE '%value%'
7. For exact categorical matches, ALWAYS use:
   "column" = 'value'
8. NEVER combine '=' and ILIKE in the same predicate.

TABLE AND COLUMN USAGE
9. Use ONLY the tables and columns present in the schema context.
10. Never invent tables or columns.
11. If multiple tables are required, create proper JOINs using available key columns.

AGGREGATIONS
12. When the question implies total, count, average, maximum, or minimum, use:
   SUM(), COUNT(), AVG(), MAX(), MIN().
13. When aggregation is used, include correct GROUP BY clauses.

DATES (DuckDB)
14. For date columns use DuckDB functions:
   year("Date")
   month("Date")
   day("Date")
   date_trunc('month',"Date")

DATA CLEANING
15. If numeric values are stored as text, convert using:
   CAST("column" AS DOUBLE)

PERFORMANCE
16. Select only required columns.
17. Avoid SELECT * unless explicitly required.
18. Apply filtering before aggregation when possible.

FINAL VALIDATION
19. Ensure the SQL:
   - Uses correct tables
   - Uses correct column names
   - Has valid JOIN logic
   - Is fully executable in DuckDB

SQL:
""")


    chain = prompt | model1
    response = chain.invoke({"schema": state.schema_context, "query": state.user_query or "Select top 5 rows"})
    state.sql = response.content.replace("```sql", "").replace("```", "").strip()
    logger.info(f"Generated SQL: {state.sql}")
    state.iteration += 1
    return state

def sql_executor_node(state: DocState):
    """Runs the SQL and stores the result or error."""
    sql = state.sql.strip()
    try:
        df = workspace.con.execute(sql).df()
        workspace.last_df = df
        state.data_head = df.head(10).to_string()
        logger.info(f"SQL Execution Success. Rows returned: {len(df)}")
        state.error = ""
    except Exception as e:
        logger.error(f"SQL Execution Failed: {e}")
        state.error = str(e)
    return state

def sql_refiner_node(state: DocState):
    """Fixes SQL if there was an error."""
    prompt = ChatPromptTemplate.from_template("""
    You are a Senior SQL Troubleshooter. The previous SQL query failed, and you must fix it while adhering strictly to the DuckDB dialect.
    
    [SCHEMA]
    {schema}
    
    [FAILED SQL]
    {sql}
    
    [ERROR MESSAGE]
    {error}
    
    [REPAIR INSTRUCTIONS]
    1. Analyze the ERROR and the SCHEMA carefully.
    2. Common Fixes: Check for misspelled column names, missing double-quotes on identifiers, or data type mismatches.
    3. Ensure IDENTIFIERS (columns/tables) are always double-quoted: "Table_Name"."Column_Name".
    4. Provide ONLY the corrected SQL query. No explanation or markdown.
    
    FIXED SQL:
    """)
    chain = prompt | model1
    response = chain.invoke({"schema": state.schema_context, "sql": state.sql, "error": state.error})
    state.sql = response.content.strip()
    state.iteration += 1
    state.error = ""
    return state

def sql_visualizer_node(state: DocState):
    """Generates chart code for the analytical finding."""
    prompt = ChatPromptTemplate.from_template("""
    You are a Data Visualization Expert. Generate professional, publication-quality Python Matplotlib code for the following visual request.
    
    [DATA CONTEXT]
    DataFrame 'df' Columns: {columns}
    Data Snippet:
    {data_head}
    
    [USER GOAL]
    {query}
    
    [CODE CONSTRAINTS]
    1. Use 'df' as the source. 
    2. Return ONLY the Python code. No text, no markdown.
    3. Aesthetics: Use sns.set_style("whitegrid"). If using palette, ALWAYS assign the x or y variable to 'hue' and set 'legend=False' to avoid warnings.
    4. Contrast: Background must be white (facecolor='white').
    5. Clarity: Include proper labels, a clear title, and call plt.tight_layout().
    6. Safety: Handle potential empty data or NaNs by calling df.dropna() before plotting if needed.
    7. No Displays: DO NOT call plt.show() or plt.savefig().
    
    PYTHON CODE:
    """)
    cols = list(workspace.last_df.columns) if workspace.last_df is not None else "Unknown"
    chain = prompt | model1
    response = chain.invoke({"data_head": state.data_head, "query": state.user_query, "columns": cols})
    code = response.content.replace("```python", "").replace("```", "").strip()
    
    try:
        plt.clf()
        plt.close('all')
        exec_globals = {"plt": plt, "sns": sns, "pd": pd, "df": workspace.last_df}
        exec(code, exec_globals)
        fig = plt.gcf()
        fig.set_facecolor('white')
        os.makedirs("visuals", exist_ok=True)
        file_path = f"visuals/analytics_{state.filename}.png"
        plt.savefig(file_path, dpi=100, bbox_inches='tight', facecolor='white')
        plt.close()
        state.visuals.setdefault("charts", []).append({"type": "analytics", "file": file_path, "code": code})
    except Exception as e:
        state.error = f"Viz Error: {e}"
    return state
def sql_reporter_node(state: DocState):
    """Summarizes SQL findings into a natural language response."""
    if state.error:
        state.rag_response = f"I encountered an error while analyzing the data: {state.error}"
        return state

    prompt = ChatPromptTemplate.from_template("""
    You are a Data Analyst. The SYSTEM has already generated any requested charts. 
    Your job is to strictly interpret the [SQL RESULTS] below and answer the data-specific parts of the [USER QUERY] (e.g., counts, averages, names).
    
    [USER QUERY]
    {query}
    
    [SQL RESULTS]
    {data}
    
    [INSTRUCTIONS]
    - IGNORE requests to "visualize", "plot", or "chart" in the query (it's already done).
    - Do NOT critique the user's spelling or grammar (e.g., "relased" instead of "released"). Assume the SQL engine executed the intent correctly.
    - Focus ONLY on the [SQL RESULTS].
    - IF the user asked for a LIST (e.g., "list of...", "show me..."), you MUST list the items (names/titles) found in the data, formatted as a markdown list (bullets).
    - If there are many rows (>20), list the top 10 and add a summary like "...and 163 more."
    - If the user asked for counts/aggregations, simply report the numbers.
    - Keep it concise and professional.
    
    ANSWER:
    """)
    chain = prompt | model1
    response = chain.invoke({"query": state.user_query, "data": state.data_head})
    state.rag_response = response.content.strip()
    logger.info(f"Reporter Output: {state.rag_response}")
    return state

# --- Router Logic ---

def post_sql_executor_router(state: DocState):
    if state.error and state.iteration < 3:
        return "sql_refine"
    if state.viz_requested and not state.error:
        return "sql_visualize"
    return "sql_reporter"

# --- Sub-graph Definition ---

builder = StateGraph(DocState)
builder.add_node("sql_prepare", sql_prepare_node)
builder.add_node("sql_planner", sql_planner_node)
builder.add_node("sql_executor", sql_executor_node)
builder.add_node("sql_refine", sql_refiner_node)
builder.add_node("sql_visualize", sql_visualizer_node)
builder.add_node("sql_reporter", sql_reporter_node)

builder.add_edge(START, "sql_prepare")
builder.add_edge("sql_prepare", "sql_planner")
builder.add_edge("sql_planner", "sql_executor")
builder.add_conditional_edges(
    "sql_executor",
    post_sql_executor_router,
    {
        "sql_refine": "sql_refine",
        "sql_visualize": "sql_visualize",
        "sql_reporter": "sql_reporter"
    }
)
builder.add_edge("sql_refine", "sql_executor")
builder.add_edge("sql_visualize", "sql_reporter")
builder.add_edge("sql_reporter", END)

sql_graph = builder.compile()
