import json
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.schema import Activity
from common_function import orchestrate_prompt


class IncidentBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        text = turn_context.activity.text
        print(f"@@@@@@@@@@@@@ Received message: {text}", flush=True)  # Debugging output
        response = orchestrate_prompt(text)
        print(f"&&&&&&&&&&&&&&&& Received response: {response}", flush=True)
        if isinstance(response.get('result'), dict):
            response['result'] = json.dumps(response['result'], indent=2)
        print(f"Response: {response}", flush=True)  # Debugging output

        await turn_context.send_activity(response.get('result', 'No result found'))

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                # Replace the HTML with Markdown and set text_format to "markdown"
                await turn_context.send_activity(
                    Activity(
                        type="message",
                        text=(
                            "**Prompt Engineering Guide:**\n"
                            "- **[General]:** Uses Bedrock LLM for general Q&A.\n\n"
                            "  _Example:_ [General] Benefits of AI\n"
                            "- **[Database]:** Converts natural language to SQL and queries the DB.\n\n"
                            "  _Example:_ [Database] Show all incidents from last week.\n"
                            "- **[API]:** Uses Bedrock LLM to build a JSON payload, calls the specified API, and returns the response.\n\n"
                            "  _Example:_ [API][Create Incident API]: Create an incident for company code OEM1 and VIN 1GYKPGRS4MZ153770."
                        ),
                        text_format="markdown"
                    )
                )
