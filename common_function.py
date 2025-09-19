import boto3
import json
import psycopg2
import re
import os
import requests
import uuid
from datetime import datetime, timezone


# Get AWS region from environment variable with default fallback
aws_region = os.getenv('AWS_REGION', os.getenv('AWS_DEFAULT_REGION', 'us-east-1'))

client = boto3.client(
    'bedrock-runtime',
    region_name=aws_region
)

model_id = 'anthropic.claude-3-haiku-20240307-v1:0'

# Postgres DB credentials from environment variables
db_config = {
    'host': os.getenv('DB_HOST', 'cfapgada-cluster.cluster-cq3nyfn9rutv.us-east-1.rds.amazonaws.com'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'cfapgda'),
    'user': os.getenv('DB_USER', 'incidentuser'),
    'password': os.getenv('DB_PASSWORD')
}

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

def orchestrate_prompt(user_input):
    user_input = user_input.strip()
    if user_input.lower().startswith("[database]"):
        print(f"Processing database prompt: {user_input}", flush=True)  # Debugging output
        return handle_database_prompt(user_input)
    elif user_input.lower().startswith("[general]"):
        print(f"Processing general prompt: {user_input}", flush=True)
        return handle_general_prompt(user_input)
    elif user_input.lower().startswith("[api]"):
        print(f"Processing API prompt: {user_input}", flush=True)
        return handle_api_prompt(user_input)
    else:
        print(f"Unknown prompt type: {user_input}", flush=True)
        return {'llm_sql': None, 'result': "Unknown prompt type. Please use [Database], [General], or [API] prefix."}

def handle_database_prompt(user_input):
    """Handle database queries"""
    question = re.sub(r"^\[Database\]\s*", "", user_input, flags=re.IGNORECASE)
    llm_response = get_sql_from_llm(question)
    sql = extract_sql_from_response(llm_response)
    columns, result = execute_sql(sql)
    if columns:
        result_str = "\t".join(columns) + "\n\n"
        for row in result:
            result_str += "\t".join(str(x) for x in row) + "\n\n"
    else:
        result_str = result[0]
    return {
        'llm_sql': sql,
        'result': result_str
    }

def handle_general_prompt(user_input):
    question = re.sub(r"^\[General\]\s*", "", user_input, flags=re.IGNORECASE)
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": question}]
    }
    response = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(response['body'].read())
    answer = result['content'][0]['text'].strip()
    return {
        'llm_sql': None,
        'result': answer
    }

def handle_api_prompt(user_input):
    # Allow colon to be optional after API name
    match = re.match(r"^\[API\]\s*\[(.*?)\]\s*:?\s*(.*)", user_input, re.IGNORECASE)
    if not match:
        return {'llm_sql': None, 'result': "Invalid API prompt format."}
    api_name, question = match.groups()
    if api_name.strip().lower() == "create incident api":
        payload = build_api_payload_with_llm(api_name, question)
        api_response = call_create_incident_api(payload)
        return {
            'llm_sql': None,
            'result': api_response
        }
    else:
        return {'llm_sql': None, 'result': f"API '{api_name}' not supported."}

def get_sql_from_llm(question):
    instruction = (
        f"{SCHEMA_DESCRIPTION}\n"
        "Convert this question to a Postgres SQL query using the schema above: "
        f"{question}\n"
        "When generating SQL for date intervals, always use single quotes around the interval value. "
        "Example: INTERVAL '1 week'"
    )
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": instruction}]
    }
    response = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(response['body'].read())
    return result['content'][0]['text'].strip()

def extract_sql_from_response(response):
    match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE).*?;", response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return response.strip()

def execute_sql(sql):
    try:
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                    return columns, rows
                else:
                    return [], ["Query executed successfully (no results)."]
    except Exception as e:
        return [], [f"Error: {e}"]


def build_api_payload_with_llm(api_name, question):
    prompt = (
        'You are an assistant that extracts parameters from user requests and builds JSON payloads for API calls.\n'
        f'API: {api_name}\n'
        f'User request: {question}\n'
        'Extract the company code and VIN from the request and fill them in the following JSON template. '
        'Return only the JSON.\n'
        'Template:\n'
        '{\n'
        '  "transactionHeader": {\n'
        '    "uniqueTransactionID": "<uuid>",\n'
        '    "companyCode": "<companycode>",\n'
        '    "companyType": "OEM",\n'
        '    "transactionDateTime": "<datetime>"\n'
        '  },\n'
        '  "incidentDetails": {\n'
        '    "incidentDate": "<incidentdate>",\n'
        '    "incidentType": "AA",\n'
        '    "communicationConsent": "Y",\n'
        '    "sendInvite": "Y",\n'
        '    "brand": "CADI",\n'
        '    "incidentLocation": {"longitude":"-88.069", "latitude":"42.026"},\n'
        '    "incidentVehicleDetails": [{\n'
        '      "vin": "<vin>",\n'
        '      "incidentPerson": [{"incidentPersonType": "Owner", "lastName": "HP-test-124"}]\n'
        '    }]\n'
        '  }\n'
        '}'
    )

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }
    response = client.invoke_model(modelId=model_id, body=json.dumps(body))
    result = json.loads(response['body'].read())

    # Parse the LLM's JSON output
    completion = result['content'][0]['text'].strip()
    try:
        payload = json.loads(completion)
    except Exception:
        match = re.search(r'({.*})', completion, re.DOTALL)
        payload = json.loads(match.group(1)) if match else {}

    # Set or replace placeholders with real values
    now_iso = datetime.now(timezone.utc).isoformat()
    today_iso = datetime.now(timezone.utc).date().isoformat() + "T12:00:00.000Z"
    payload.setdefault("transactionHeader", {})
    payload["transactionHeader"]["uniqueTransactionID"] = str(uuid.uuid4())
    payload["transactionHeader"]["transactionDateTime"] = now_iso

    # Replace any lingering <datetime> placeholders in the entire payload
    def replace_placeholders(obj):
        if isinstance(obj, dict):
            return {k: replace_placeholders(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_placeholders(i) for i in obj]
        elif isinstance(obj, str):
            if obj == "<datetime>":
                return now_iso
            if obj == "<incidentdate>":
                return today_iso
            if obj == "<uuid>":
                return str(uuid.uuid4())
            return obj
        else:
            return obj

    payload = replace_placeholders(payload)

    # Ensure incidentDetails and incidentDate are set
    payload.setdefault("incidentDetails", {})
    payload["incidentDetails"].setdefault("incidentDate", today_iso)

    return payload

def call_create_incident_api(payload):
    url = "http://intfinservicescrashsvc-dea.cccis.com/interfaces-create-incident/v1/incident"
    headers = {"Content-Type": "application/json"}
    print('Calling API with payload:', payload)
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        print('API response status:', resp.status_code)
        print('API response body:', resp.text)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}
