from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
import pymongo
import pyodbc
import os


mongo_client_string = os.getenv("MONGO_CLIENT_STRING")

"Mongo Database Functions"


# Initialize Message Thread


async def thread_init(conversation_id: str, email: str, subject: str):
    client = pymongo.AsyncMongoClient(mongo_client_string)
    db = client["powersales"]
    collection = db["messages"]
    doc = await collection.find_one({"conversation_id": conversation_id})
    if not doc:
        await collection.insert_one({
            "conversation_id": conversation_id,
            "email": email,
            "subject": subject,
            "messages": []
        })
    await client.close()

# Retrieve Message Thread


async def thread_retrieve(conversation_id: str):
    client = pymongo.AsyncMongoClient(mongo_client_string)
    db = client["powersales"]
    collection = db["messages"]
    doc = await collection.find_one({"conversation_id": conversation_id}, {"_id": 0})
    await client.close()
    return doc


async def thread_insert_user_message(conversation_id: str, content: str):
    client = pymongo.AsyncMongoClient(mongo_client_string)
    db = client["powersales"]
    collection = db["messages"]
    await collection.update_one({"conversation_id": conversation_id}, {"$push": {"messages": {
        "roles": "user", "content": content}}}, upsert=True)
    await client.close()


async def thread_insert_ai_message(conversation_id: str, content: str, tool_calls: list = None
                                   ):
    client = pymongo.AsyncMongoClient(mongo_client_string)
    db = client["powersales"]
    collection = db["messages"]
    if tool_calls is None:
        await collection.update_one({"conversation_id": conversation_id}, {"$push": {"messages": {
            "roles": "ai", "content": content}}}, upsert=True)
    else:
        await collection.update_one({"conversation_id": conversation_id}, {"$push": {"messages": {
            "roles": "ai", "content": content, "kwargs": {"tool_calls": tool_calls}}}}, upsert=True)
    await client.close()


async def thread_insert_system_message(conversation_id: str, content: str):
    client = pymongo.AsyncMongoClient(mongo_client_string)
    db = client["powersales"]
    collection = db["messages"]
    await collection.update_one({"conversation_id": conversation_id}, {"$push": {"messages": {
        "roles": "system", "content": content}}}, upsert=True)
    await client.close()


async def thread_insert_tool_message(conversation_id: str, content: str, tool_call_id: str, name: str):
    client = pymongo.AsyncMongoClient(mongo_client_string)
    db = client["powersales"]
    collection = db["messages"]
    await collection.update_one({"conversation_id": conversation_id}, {"$push": {"messages": {
        "roles": "tool", "content": {"result": str(content), "id": tool_call_id, "name": name}}}}, upsert=True)
    await client.close()


async def parse_history(messages_history_db: list):
    messages = []
    for message in messages_history_db:
        if message['roles'] == "user":
            messages.append(HumanMessage(message['content']))
        elif message['roles'] == "ai":
            if 'kwargs' in message:
                messages.append(
                    AIMessage(message['content'], tool_calls=message['kwargs']['tool_calls']))
            else:
                messages.append(AIMessage(message['content']))
            # messages.append(AIMessage(message['content'], message['kwargs']['tool_calls']))
        elif message['roles'] == "system":
            messages.append(SystemMessage(message['content']))
        elif message['roles'] == "tool":
            messages.append(ToolMessage(
                message['content']['result'], name=message['content']['name'], tool_call_id=message['content']['id']))
    return messages


"SQL Database Functions"


def _get_sql_connection():
    driver = os.getenv("ODBC_STRING")
    return pyodbc.connect(driver)


async def get_product(SKU: str):
    """
    Get product from SQL database using SKU

    ARGS:
        SKU: Product SKU (String)
    """
    conn = _get_sql_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE SKU = '{SKU}'")
    row = cursor.fetchone()
    conn.close()

    if row:
        return {'id': row[0], 'SKU': row[1], 'name': row[2], 'description': row[3], 'price': row[4]}
    else:
        return None


async def search_products(product_name: str = None, SKU: str = None) -> list | None:
    """
    Search products from SQL database using product name or SKU
    Only use to search the product name, for an example "Lenovo Yoga"

    ARGS:
        product_name: Product Name (String) (Optional)
        SKU: Product SKU (String) (Optional)

    Returns:
        Data (list): Search Result

    """

    conn = _get_sql_connection()
    cursor = conn.cursor()
    if product_name:
        cursor.execute(
            f"SELECT * FROM products WHERE name LIKE '%{product_name}%'")
    elif SKU:
        cursor.execute(f"SELECT * FROM products WHERE SKU = '{SKU}'")
    row = cursor.fetchall()
    conn.close()

    if row:
        data = []
        for i in row:
            o = {
                "SKU": i[1],
                "Name": i[2],
                "Description": i[3],
                "Price": i[4]
            }
            data.append(o)
        return data
    else:
        return None


async def get_price_from_sku(SKU: str) -> int | None:
    """
    Get product price from SQL database using SKU

    Args:
        SKU (str): Product SKU

    Returns:
        price (int): Product price


    """
    conn = _get_sql_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM products WHERE SKU = '{SKU}'")
    row = cursor.fetchone()
    # Row Output (15, '7007-814-X', 'Lenovo Yoga Slim 9i', 'Custom Model Starting Price At', 1499, 1)
    conn.close()

    if row:
        try:
            return int(row[4])
        except Exception as e:
            print(str(row))
            return None
    else:
        return None


async def get_price_from_product_name(product_name: str) -> list | None:
    """
    Get product price from SQL database using product name

    The data is in list 
    [
        {
            sku:"",
            name:"",
            description:"",
            price:00
        }
    ]
    Args:
        product_name (str): product name keyword

    Returns:
        Data (list): Search Result
    """
    conn = _get_sql_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM products WHERE name LIKE '%{product_name}%'")
    row = cursor.fetchall()
    conn.close()

    if row:
        try:
            data = []
            for i in row:
                o = {
                    "SKU": i[1],
                    "Name": i[2],
                    "Description": i[3],
                    "Price": i[4]
                }
                data.append(o)
            return data
        except Exception as e:
            print(str(row))
            return None
    else:
        return None


async def save_user(email: str, first_name: str, last_name: str, country: str, industry: str = None, company: str = None):
    """
    Save user to SQL database

    Args:
        email: User email (String)
        first_name: User first name (String)
        last_name: User last name (String)
        country: User country (String)
        industry: User industry (String) (Optional)
        company: User company (String)  (Optional)
    """
    conn = _get_sql_connection()
    cursor = conn.cursor()
    try:
        # check if user is already exist
        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        row = cursor.fetchone()
        if row:
            print(f"User {email} already exist.")
            return {"status": "User already exist."}
        cursor.execute(
            f"INSERT INTO users (email, first_name, last_name, country, industry, company_name) VALUES ('{email}', '{first_name}', '{last_name}', '{country}', '{industry}', '{company}')")
        conn.commit()
        conn.close()
        print(f"User {email} saved successfully.")
    except Exception as e:
        print(f"Error saving user {email}: {e}")
        return {"status": "Error saving user."}

    return {"status": "User saved successfully."}


async def get_user(email: str):
    """
    Get user from SQL database using email

    ARGS:
        email: User email (String)

    """
    conn = _get_sql_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
    row = cursor.fetchone()
    conn.close()

    if row is not None:
        return dict(zip([column[0] for column in cursor.description], row))
    return None
