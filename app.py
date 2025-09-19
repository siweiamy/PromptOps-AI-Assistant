import asyncio
from botframework.connector.auth import JwtTokenValidation
from flask import Flask, render_template, request, jsonify, Response
import json
import psycopg2
import os
from datetime import datetime, timezone
from adapter_with_error_handler import adapter
from botbuilder.schema import Activity
from common_function import orchestrate_prompt, db_config
from incident_bot import IncidentBot
import logging

logging.basicConfig(level=logging.INFO)

# Monkey patch to log token validation
original_validate_auth_header = JwtTokenValidation.validate_auth_header

async def debug_validate_auth_header(auth_header, credentials, channel_id, channel_service, channel_auth_tenant=None):
    print("🔐 [MonkeyPatch] Validating token...")
    print("    • auth_header:", auth_header[:50] + "..." if auth_header else "None")
    print("    • credentials.app_id:", credentials.app_id)
    print("    • channel_auth_tenant:", channel_auth_tenant)

    try:
        identity = await original_validate_auth_header(
            auth_header, credentials, channel_id, channel_service, channel_auth_tenant
        )
        print("✅ Token validated. Identity claims:")
        for key, value in identity.claims.items():
            print(f"    • {key}: {value}")
        return identity
    except Exception as e:
        print("❌ Token validation failed:", str(e))
        raise e

JwtTokenValidation.validate_auth_header = debug_validate_auth_header


# Validate that required environment variables are set
if not db_config['password']:
    raise ValueError("DB_PASSWORD environment variable is required but not set")

# Optional: Validate other critical env vars
for key, value in db_config.items():
    if value is None:
        raise ValueError(f"Database configuration '{key}' is not set")
app = Flask(__name__)
loop = asyncio.get_event_loop()
bot = IncidentBot()

# Get context path from environment variable with default to root
context_path = os.getenv('CONTEXT_PATH', '').rstrip('/')

@app.route(f'{context_path}/')
def index():
    return render_template('chat.html', context_path=context_path)

@app.route(f'{context_path}/health')
def health():
    print("/health endpoint called", flush=True)
    app.logger.info("/health endpoint called")
    """Health endpoint for Kubernetes probes"""
    try:
        # Test database connection
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        # Test AWS Bedrock connection (optional - might want to skip for readiness)
        # This is commented out as it might be too heavy for frequent health checks
        # try:
        #     client.list_foundation_models()
        # except Exception as aws_error:
        #     return jsonify({
        #         'status': 'unhealthy',
        #         'error': f'AWS Bedrock connection failed: {str(aws_error)}'
        #     }), 503

        from datetime import datetime
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'connected'
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': f'Database connection failed: {str(e)}'
        }), 503

@app.route(f'{context_path}/ready')
def ready():
    app.logger.info("/ready endpoint called")
    print("/ready endpoint called", flush=True)
    """Readiness endpoint for Kubernetes probes - checks if the service is ready to receive traffic"""
    return jsonify({
        'status': 'ready',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

@app.route(f'{context_path}/chat', methods=['POST'])
def chat():
    try:
        print(f"Chat endpoint called with context_path: '{context_path}'", flush=True)
        app.logger.info(f"Chat endpoint called with context_path: '{context_path}'")
        user_input = request.json.get('message', '') if request.json else ''
        print(f"Received input: '{user_input}'")

        if not user_input.strip():
            return jsonify({'error': 'Empty input'}), 400

        response = orchestrate_prompt(user_input)
        print(f"Generated response: {response}")

        # Ensure result is always a string for the UI
        if isinstance(response.get('result'), dict):
            response['result'] = json.dumps(response['result'], indent=2)
        return jsonify(response)
    except Exception as e:
        print(f"Error in chat endpoint: {e}", flush=True)
        app.logger.error(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route(f'{context_path}/api/messages', methods=["POST"])
def messages():
    app.logger.info("********************* messages endpoint called with request.json: %s, headers: %s, data: %s", request.json, request.headers, request.data)
    if "application/json" not in request.headers.get("Content-Type", ""):
        return Response(status=415)

    auth_header = request.headers.get("Authorization", "")
    # auth_header = ""
    print(f"Authorization header:{auth_header}", flush=True)
    body = request.json
    activity = Activity().deserialize(body)

    # APP_ID = os.getenv("MICROSOFT_APP_ID")
    # APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")
    # APP_TYPE = os.getenv("MICROSOFT_APP_TYPE", "SingleTenant")
    # TENANT_ID = os.getenv("MICROSOFT_TENANT_ID")
    #
    # app.logger.info("Creating BotFrameworkAdapter with APP_ID: %s, APP_PASSWORD: %s, APP_TYPE: %s, TENANT_ID: %s", APP_ID, APP_PASSWORD, APP_TYPE, TENANT_ID)
    async def turn_call():
        await adapter.process_activity(activity, auth_header, bot.on_turn)

    task = loop.create_task(turn_call())
    loop.run_until_complete(task)

    return Response(status=201)

original_validate_auth_header = JwtTokenValidation.validate_auth_header


if __name__ == '__main__':
    # Get port from environment variable with default fallback
    port = int(os.getenv('PORT', '5000'))
    # Get host from environment variable with default to bind to all interfaces
    host = os.getenv('HOST', '0.0.0.0')

    print(f"Starting Flask app on {host}:{port}")
    if context_path:
        print(f"Context path: {context_path}")
        print(f"Access the app at: http://{host}:{port}{context_path}/")
    else:
        print(f"Access the app at: http://{host}:{port}/")

    # Debug: Print all registered routes
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
    print()

    app.run(host=host, port=port, debug=False)
