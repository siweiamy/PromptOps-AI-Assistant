import tkinter as tk
from tkinter import ttk, messagebox
import boto3
import json
import psycopg2
import re
import os

# AWS Bedrock/LLM setup (use env vars for production)
aws_access_key_id = 'ASIA4YXUBRY5KVJRXHFQ'
aws_secret_access_key = ''
aws_session_token = ''
model_id = 'anthropic.claude-v2'

# Get AWS region from environment variable with default fallback
aws_region = os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))

client = boto3.client(
    'bedrock-runtime',
    region_name=aws_region
)

# Postgres DB credentials from environment variables
db_config = {
    'host': os.getenv('DB_HOST', 'cfapgada-cluster.cluster-cq3nyfn9rutv.us-east-1.rds.amazonaws.com'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'cfapgda'),
    'user': os.getenv('DB_USER', 'incidentuser'),
    'password': os.getenv('DB_PASSWORD')
}

# Validate that required environment variables are set
if not db_config['password']:
    raise ValueError("DB_PASSWORD environment variable is required but not set")

# Optional: Validate other critical env vars
for key, value in db_config.items():
    if value is None:
        raise ValueError(f"Database configuration '{key}' is not set")

# Add schema info for LLM prompt engineering
SCHEMA_DESCRIPTION = """
Table: incident
Columns:
incident_id,
event_id,
insurance_company_cd,
oem_company_cd,
subsidiary_company_cd,
incident_date,
incident_state,
incident_postal_code,
latitude,
longitude,
incident_status,
email_notify_request_id,
text_notify_request_id,
user_id,
appl_id,
rec_dt,
modifid_dt,
lock_id,
incident_type,
appraisr_dl_cust_id,
incident_cust_ref_id,
incident_compressd_cust_ref_id,
intend_to_file_flag,
num_of_vehicle,
incident_comments,
brand,
language_code,
coverage_type_cd,
payment_id,
incident_channel_val,
accident_type_val,
vendor_company_cd,
incident_description
"""

def get_sql_from_llm(question):
    prompt = (
        f"{SCHEMA_DESCRIPTION}\n"
        f"Human: Convert this question to a Postgres SQL query using the schema above: {question}\n\nAssistant:"
    )
    body = {"prompt": prompt, "max_tokens_to_sample": 100}
    response = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(response['body'].read())
    print(result.get('completion', result))
    return result.get('completion', '').strip()

def extract_sql_from_response(response):
    # Remove code block markers and explanations, extract SQL
    match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: try to find the first SELECT/INSERT/UPDATE/DELETE statement
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE).*?;", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return response.strip()

def execute_sql(sql):
    try:
        # Debug: Print connection attempt (without password for security)
        print(f"Attempting to connect to: {db_config['host']}:{db_config['port']}/{db_config['database']} as {db_config['user']}")

        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return columns, rows
                else:
                    return [], ["Query executed successfully (no results)."]
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"Database connection error: {error_msg}")
        if "password authentication failed" in error_msg.lower():
            return [], [f"Password authentication failed. Please check DB_PASSWORD environment variable."]
        elif "could not connect" in error_msg.lower():
            return [], [f"Could not connect to database. Please check host and port settings."]
        else:
            return [], [f"Database error: {error_msg}"]
    except Exception as e:
        print(f"Unexpected error: {e}")
        return [], [f"Error: {e}"]

def send_message(event=None):
    user_input = entry.get()
    if not user_input.strip():
        return
    chat_log.config(state=tk.NORMAL)
    chat_log.insert(tk.END, f"You: {user_input}\n", "user")
    chat_log.config(state=tk.DISABLED)
    chat_log.see(tk.END)
    entry.delete(0, tk.END)

    # Step 1: Get SQL from LLM
    llm_response = get_sql_from_llm(user_input)
    sql = extract_sql_from_response(llm_response)
    chat_log.config(state=tk.NORMAL)
    chat_log.insert(tk.END, f"Bot (SQL): {sql}\n", "bot")
    chat_log.config(state=tk.DISABLED)
    chat_log.see(tk.END)

    # Step 2: Execute SQL
    columns, result = execute_sql(sql)
    chat_log.config(state=tk.NORMAL)
    if columns:
        result_str = "\t".join(columns) + "\n"
        for row in result:
            result_str += "\t".join(str(x) for x in row) + "\n"
        chat_log.insert(tk.END, f"Bot (Result):\n{result_str}\n", "bot")
    else:
        chat_log.insert(tk.END, f"Bot (Result): {result[0]}\n", "bot")
    chat_log.config(state=tk.DISABLED)
    chat_log.see(tk.END)

def clear_chat():
    chat_log.config(state=tk.NORMAL)
    chat_log.delete(1.0, tk.END)
    chat_log.config(state=tk.DISABLED)

def save_chat():
    with open("chat_history.txt", "w", encoding="utf-8") as file:
        chat_content = chat_log.get(1.0, tk.END).strip()
        file.write(chat_content)
    messagebox.showinfo("Chat Saved", "Chat history saved to chat_history.txt")

root = tk.Tk()
root.title("Modern Chatbot UI")
root.geometry("600x450")
root.resizable(True, True)

style = ttk.Style(root)
style.theme_use('clam')
style.configure('Send.TButton', font=('Segoe UI', 10, 'bold'), foreground='white', background='#2563eb', borderwidth=1)
style.map('Send.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1e40af')], foreground=[('disabled', '#cccccc')])
style.configure('Clear.TButton', font=('Segoe UI', 10), foreground='white', background='#6b7280', borderwidth=1)
style.map('Clear.TButton', background=[('active', '#4b5563'), ('pressed', '#374151')], foreground=[('disabled', '#cccccc')])
style.configure('Save.TButton', font=('Segoe UI', 10), foreground='white', background='#22c55e', borderwidth=1)
style.map('Save.TButton', background=[('active', '#16a34a'), ('pressed', '#15803d')], foreground=[('disabled', '#cccccc')])
style.configure('TEntry', font=('Segoe UI', 10))
style.configure('TLabel', font=('Segoe UI', 12, 'bold'))

mainframe = ttk.Frame(root, padding="10 10 10 10")
mainframe.grid(row=0, column=0, sticky="NSEW")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

chat_log = tk.Text(mainframe, height=20, width=70, state=tk.DISABLED, wrap=tk.WORD, font=('Segoe UI', 10), bg="#f4f4f4")
chat_log.grid(row=0, column=0, columnspan=4, sticky="NSEW", pady=(0, 10))
chat_log.tag_configure("user", foreground="#0078D7", font=('Segoe UI', 10, 'bold'))
chat_log.tag_configure("bot", foreground="#333333", font=('Segoe UI', 10))

scrollbar = ttk.Scrollbar(mainframe, orient=tk.VERTICAL, command=chat_log.yview)
scrollbar.grid(row=0, column=4, sticky="NS", pady=(0, 10))
chat_log['yscrollcommand'] = scrollbar.set

entry = ttk.Entry(mainframe, width=50)
entry.grid(row=1, column=0, columnspan=2, sticky="EW", padx=(0, 5))
entry.bind("<Return>", send_message)

send_button = ttk.Button(mainframe, text="Send", command=send_message, style='Send.TButton')
send_button.grid(row=1, column=2, sticky="EW", padx=(0, 5))

clear_button = ttk.Button(mainframe, text="Clear", command=clear_chat, style='Clear.TButton')
clear_button.grid(row=1, column=3, sticky="EW", padx=(0, 5))

save_button = ttk.Button(mainframe, text="Save Chat", command=save_chat, style='Save.TButton')
save_button.grid(row=1, column=4, sticky="EW")

mainframe.columnconfigure(0, weight=3)
mainframe.columnconfigure(1, weight=1)
mainframe.columnconfigure(2, weight=1)
mainframe.columnconfigure(3, weight=1)
mainframe.columnconfigure(4, weight=1)
mainframe.rowconfigure(0, weight=1)

entry.focus()
root.mainloop()