import os
import urllib.parse
import markdown
import warnings
from fastapi import APIRouter
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, trim_messages, BaseMessage
from langchain_openai import AzureChatOpenAI
from bs4 import BeautifulSoup
from dotenv import find_dotenv, load_dotenv
from src.model.requestBodyModel import InvokeModel
from src.utility.database import get_price_from_product_name, get_price_from_sku, get_product, get_user, parse_history, save_user, search_products, thread_init, thread_insert_ai_message, thread_insert_system_message, thread_insert_tool_message, thread_insert_user_message, thread_retrieve
from src.utility.rag import get_document
from src.utility.transaction import Cart
load_dotenv(find_dotenv())

warnings.filterwarnings(
    "ignore", message="You appear to be connected to a CosmosDB cluster")


router = APIRouter()

llm_model = AzureChatOpenAI(
    api_key=os.getenv("API_KEY"),
    azure_endpoint=os.getenv("ENDPOINT"),
    api_version=os.getenv("VERSION"),
    model=os.getenv("DEPLOYMENT_NAME"),
    max_tokens=8096
)


SYS_MESSAGE = SystemMessage(content="""
You are an AI ChatBot representing Contoso Electronics, assisting customers via email.
Your responsibilities include answering questions, providing product details, and generating leads.
Always use polite language.

At the beginning of the conversation:
1.  Ask the user for their name, email, and country.
2.  If they represent a company, also ask for the company's name and industry. 
3.  Save this information to database with using function call. Always do this, always save to the database.
3.  If the user doesn't represent a company or omits company information, do not ask for it.
4.  Ask the user to describe their inquiry. If needed, ask clarifying questions to fully understand their needs.
5.  Do not suggest any products unless explicitly instructed by the system messages.
                            
""")


cart = Cart()


@router.post("/invoke")
async def invoke(invoke: InvokeModel):

    message_query = invoke.content
    if "-----" in message_query:
        message_query = message_query.split(
            "--------------------------------------------------------------------------------")[0]

    messages_history_db = await thread_retrieve(invoke.conversation_id)
    user_data = await get_user(invoke.email)

    if not messages_history_db:
        await thread_init(invoke.conversation_id, invoke.email, invoke.subject)
        await thread_insert_system_message(invoke.conversation_id, SYS_MESSAGE.content)

        user_info_message = f"User Email: {invoke.email}, Inquiry: {invoke.subject}"
        if user_data:
            user_info_message = f"Verify this saved data from DB {user_data['name']}. We have your information. Email: {invoke.email}, Inquiry: {invoke.subject}"

        await thread_insert_system_message(invoke.conversation_id, user_info_message)
        await thread_insert_user_message(invoke.conversation_id, message_query)

    else:
        docs = get_document(message_query)
        if docs:
            for i in docs:
                await thread_insert_system_message(invoke.conversation_id, i[0].page_content)
        await thread_insert_user_message(invoke.conversation_id, message_query)

        messages_history_db = await thread_retrieve(invoke.conversation_id)

    messages_history_db = await thread_retrieve(invoke.conversation_id)

    llm_tools = llm_model.bind_tools(
        [save_user, cart.add_to_cart, cart.get_cart,
         cart.modify_cart, cart.remove_from_cart, cart.checkout, get_price_from_sku, get_price_from_product_name],
        parallel_tool_calls=True)

    tool_mapping = {
        "save_user": save_user,
        "get_price_from_sku": get_price_from_sku,
        "get_price_from_product_name": get_price_from_product_name,
        "add_to_cart": cart.add_to_cart,
        "get_cart": cart.get_cart,
        "modify_cart": cart.modify_cart,
        "remove_from_cart": cart.remove_from_cart,
        "checkout": cart.checkout
    }

    hist = await parse_history(messages_history_db['messages'])

    hist = trim_messages(
        hist,
        strategy="last",
        token_counter=llm_model,
        max_tokens=1200,
        allow_partial=False,
        include_system=False
    )
    messages = hist if messages_history_db else []

    system_messages_to_add = [
        "If user asking for a price then, check the price of the product using the SKU from System message if any",
        f"Current User Email Address: {invoke.email}",
    ]

    print(type(messages[0]))

    for message_content in system_messages_to_add:
        if not any(msg.content == message_content and type(msg) == SystemMessage for msg in messages):
            await thread_insert_system_message(invoke.conversation_id, message_content)

    invoker: BaseMessage = await llm_tools.ainvoke(hist)
    print(
        f"Token Usage: {invoker.response_metadata['token_usage']['total_tokens']}")

    if len(invoker.tool_calls) != 0:
        print(f"Function Calling | {invoker.tool_calls}")
        await thread_insert_ai_message(invoke.conversation_id, invoker.content, invoker.tool_calls)

        for tool_call in invoker.tool_calls:
            tool = tool_mapping[tool_call['name'].lower()]
            tool_output = await tool(**tool_call['args'])

            print(f"Tool Output | {tool_output}")
            await thread_insert_tool_message(invoke.conversation_id, tool_output, tool_call['id'], tool_call['name'])

        messages_history_db = await thread_retrieve(invoke.conversation_id)
        hist = await parse_history(messages_history_db['messages'])

        hist = trim_messages(
            hist,
            strategy="last",
            token_counter=llm_model,
            max_tokens=2000,
            allow_partial=False,
            include_system=False
        )

        invoker = await llm_model.ainvoke(hist)

    await thread_insert_ai_message(invoke.conversation_id, invoker.content)

    return markdown.markdown(invoker.content)
