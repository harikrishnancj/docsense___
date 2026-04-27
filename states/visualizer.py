import os
import matplotlib.pyplot as plt
from wordcloud import WordCloud

def is_actually_numeric(val):
    """Deep check for numeric values in messy strings."""
    if val is None or str(val).strip() == "":
        return False
    # Remove common distractions
    clean = str(val).replace(",", "").replace("%", "").replace("$", "").replace("£", "").replace("€", "").strip()
    try:
        float(clean)
        return True
    except ValueError:
        return False

def clean_to_float(val):
    """Clean and convert string value to float."""
    if val is None or str(val).strip() == "":
        return 0.0
    clean = str(val).replace(",", "").replace("%", "").replace("$", "").replace("£", "").replace("€", "").strip()
    try:
        return float(clean)
    except ValueError:
        return 0.0

def auto_chart_from_table(table_data, table_name="Table"):
    """
    Intelligent chart selection for messy document tables.
    """
    if not table_data or not isinstance(table_data, list) or len(table_data) < 2:
        return None

    # Get sample to find columns
    all_keys = list(table_data[0].keys())
    
    # Analyze columns
    numeric_cols = []
    categorical_cols = []
    
    for col in all_keys:
        vals = [row.get(col) for row in table_data]
        # Skip columns that are entirely empty or None
        if all(v is None or str(v).strip() == "" for v in vals):
            continue
            
        # If > 70% of non-empty values are numeric, we treat it as numeric
        non_empty_vals = [v for v in vals if v is not None and str(v).strip() != ""]
        if not non_empty_vals:
            continue
            
        num_numeric = sum(1 for v in non_empty_vals if is_actually_numeric(v))
        if num_numeric / len(non_empty_vals) > 0.7:
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    if not numeric_cols:
        return None

    # Decision Logic
    # 1. Bar Chart: Category + Numeric
    if categorical_cols and numeric_cols:
        cat = categorical_cols[0]
        num = numeric_cols[0]
        return {
            "type": "bar",
            "title": f"{num} by {cat}",
            "labels": [str(row.get(cat, ""))[:20] for row in table_data], # Truncate labels
            "values": [clean_to_float(row.get(num)) for row in table_data]
        }
        
    # 2. Line Chart: Numeric only (assume sequence or time)
    if len(numeric_cols) >= 1 and len(table_data) > 3:
        num = numeric_cols[0]
        return {
            "type": "line",
            "title": f"Trend: {num}",
            "labels": list(range(1, len(table_data) + 1)),
            "values": [clean_to_float(row.get(num)) for row in table_data]
        }

    # 3. Histogram: One numeric column
    if len(numeric_cols) == 1:
        num = numeric_cols[0]
        return {
            "type": "histogram",
            "title": f"Distribution of {num}",
            "values": [clean_to_float(row.get(num)) for row in table_data]
        }

    return None

def render_chart(chart, file_path):
    """State-of-the-art Matplotlib rendering."""
    ctype = chart["type"]
    title = chart.get("title", "Analysis")

    # Set modern style
    plt.style.use('ggplot')
    plt.figure(figsize=(12, 7))
    plt.title(title, fontsize=16, fontweight='bold', pad=20)
    plt.grid(True, linestyle='--', alpha=0.6)

    if ctype == "bar":
        labels = chart["labels"]
        values = chart["values"]
        colors = plt.cm.viridis(plt.Normalize(min(values) if values else 0, max(values) if values else 1)(values))
        plt.bar(labels, values, color=colors)
        plt.xticks(rotation=45, ha='right')

    elif ctype == "line":
        plt.plot(chart["labels"], chart["values"], marker='o', linewidth=2, color='#3498db')
        plt.fill_between(chart["labels"], chart["values"], alpha=0.2, color='#3498db')

    elif ctype == "histogram":
        plt.hist(chart["values"], bins=10, color='#e67e22', edgecolor='white', alpha=0.8)

    plt.tight_layout()
    plt.savefig(file_path, facecolor='white', dpi=120)
    plt.close()

def Visualizer(state, user_request=None):
    """
    DocSense Visualizer for PDF/PPT/Word.
    Focuses on extracted tables and textual summaries.
    """
    text = state.summary or state.rag_response or ""
    tables = getattr(state, "extracted_tables", [])
    
    # Import LLM for dynamic generation
    from model.model import model1
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    os.makedirs("visuals", exist_ok=True)
    # Ensure visuals state is robustly initialized
    if not hasattr(state, "visuals") or not isinstance(state.visuals, dict):
        state.visuals = {"charts": []}
    if "charts" not in state.visuals:
        state.visuals["charts"] = []
    
    # --- 1) Dynamic LLM Visualization (if requested) ---
    if user_request and text:
        print(f"🎨 Generating dynamic chart for: {user_request}")
        try:
            # specialized prompt for chart generation
            prompt = ChatPromptTemplate.from_template("""
            You are a Data Visualization expert.
            Your task is to generate Python code using Matplotlib/Seaborn to create a chart based on the [USER REQUEST] and [CONTEXT].
            
            [CONTEXT]
            {context}
            
            [USER REQUEST]
            {request}
            
            [INSTRUCTIONS]
            1. Write complete, executable Python code.
            2. Use 'visuals/dynamic_chart.png' as the save path (plt.savefig).
            3. Aesthetic: Use sns.set_style("whitegrid"). 
            4. Seborn rules: If using palette, ALWAYS assign the x or y variable to 'hue' and set 'legend=False' to avoid warnings.
            5. Handle data extraction manually within the code (e.g., hardcode the lists based on the context).
            6. IMPORTANT: All list arrays MUST have the same length. Pad with None if necessary.
            7. Do NOT assume any external CSVs (create dataframes or lists on the fly).
            8. Output ONLY the python code inside ```python``` blocks.
            
            CODE:
            """)
            
            chain = prompt | model1 | StrOutputParser()
            code_response = chain.invoke({"context": text[:3000], "request": user_request})
            
            # Extract code
            import re
            code_match = re.search(r"```python(.*?)```", code_response, re.DOTALL)
            if code_match:
                code_str = code_match.group(1).strip()
                
                # Execute Code
                local_scope = {}
                exec(code_str, {}, local_scope)
                
                # Verify File Creation
                if os.path.exists("visuals/dynamic_chart.png"):
                    chart_title = user_request.split("about")[-1].strip().title() if "about" in user_request else "Custom Analysis"
                    state.visuals["charts"].append({
                        "type": "dynamic",
                        "file": "visuals/dynamic_chart.png",
                        "title": chart_title,
                        "code": code_str # transparency
                    })
                    return state
                    
        except Exception as e:
            print(f"⚠️ Dynamic viz failed: {e}")
            import traceback
            traceback.print_exc()

    # --- 2) Standard Table Visualization (Fallback) ---
    chart_found = False
    
    # Check if we already have charts (from dynamic step), if so, we can skip or append.
    # If dynamic succeeded, we probably returned already.

    for i, table in enumerate(tables, start=1):
        table_data = table.get("data", table) if isinstance(table, dict) else table
        source = table.get("source", "Document") if isinstance(table, dict) else "Document"
        
        chart = auto_chart_from_table(table_data, table_name=f"Table {i}")
        if chart:
            file_path = f"visuals/doc_chart_{i}.png"
            render_chart(chart, file_path)
            chart["file"] = file_path
            chart["source"] = source
            state.visuals["charts"].append(chart)
            chart_found = True

    # --- 3) NO WordCloud Fallback (User Request) ---
    # User explicitly requested to remove "useless" wordcloud.
    # if not chart_found and text: ... (Deleted)

    if not chart_found and not state.visuals.get("charts"):
        print("⚠️ No charts could be generated (Dynamic failed, and tables empty).")

    return state

