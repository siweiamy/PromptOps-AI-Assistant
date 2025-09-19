import os
import traceback

from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("MICROSOFT_APP_ID")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")
APP_TYPE = os.getenv("MICROSOFT_APP_TYPE", "SingleTenant")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID")

# adapter_settings = BotFrameworkAdapterSettings(app_id=APP_ID, app_password=APP_PASSWORD, channel_auth_tenant=TENANT_ID)
adapter_settings = BotFrameworkAdapterSettings("", "", "")
adapter = BotFrameworkAdapter(adapter_settings)

# Error handling
async def on_error(context: TurnContext, error: Exception):
    print(f"\n [on_turn_error] unhandled error: {error}", flush=True)
    traceback.print_exc()
    await context.send_activity("Sorry, something went wrong.")

adapter.on_turn_error = on_error
