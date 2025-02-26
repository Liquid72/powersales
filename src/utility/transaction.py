import asyncio
import os
import random
import pyodbc
import requests
import datetime
from dotenv import find_dotenv, load_dotenv
from langchain_core.tools import tool

load_dotenv(find_dotenv())


class Cart:
    def __init__(self):
        self.driver = os.getenv("ODBC_STRING")

    def __connect(self):
        self.conn = pyodbc.connect(self.driver)
        self.cursor = self.conn.cursor()

    def __close(self):
        self.conn.close()

    async def add_to_cart(self, email: str, sku: str, quantity: int) -> dict[str, str]:
        """
        Add Product to Cart based on SKU and Quantity

        Args:
            email: User Email (String)
            sku: Product SKU (String)
            quantity: Quantity (Int)

        Return:
            status: Status of the operation (String)

        """
        self.__connect()
        self.cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
        user_id = self.cursor.fetchone()
        print(f"User ID: {user_id}")
        try:
            self.cursor.execute(
                f"INSERT INTO cart (user_id, sku, quantity) VALUES ({user_id[0]}, '{sku}', {quantity})")
            self.conn.commit()
            self.__close()
        except Exception as e:
            print(e)
            print(
                f"User ID: {user_id[0]} - SKU: {sku} - Quantity: {quantity} - Email: {email}")
            print(f"Error adding to cart: {e}")
            return {"status": "Error adding to cart."}

        return {"status": "Added to cart successfully."}

    async def get_cart(self, email: str) -> dict[str, str] | None:
        """
        Get Cart based on User Email

        Args:
            email: User Email (String)

        Return:
            cart: Cart Items (List)
            total_price: Total Price (Float)

        """
        self.__connect()
        self.cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
        user_id = self.cursor.fetchone()
        self.cursor.execute(f"SELECT * FROM cart WHERE user_id = {user_id[0]}")
        rows = self.cursor.fetchall()
        self.__close()

        if rows is not None:
            total_price = 0
            for row in rows:
                price = await self.get_price(row[2])
                total_price += price * row[3]
            return {
                "cart": [dict(zip([column[0] for column in self.cursor.description], row)) for row in rows],
                "total_price": total_price
            }
        return None

    async def modify_cart(self, email: str, sku: str, quantity: int) -> dict[str, str]:
        """
        Modify Cart based on SKU and Quantity

        Args:
            email: User Email (String)
            sku: Product SKU (String)
            quantity: Quantity (Int)

        Return:
            status: Status of the operation (String)


        """
        self.__connect()
        self.cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
        user_id = self.cursor.fetchone()
        try:
            self.cursor.execute(
                f"UPDATE cart SET quantity = {quantity} WHERE user_id = {user_id[0]} AND sku = '{sku}'")
            self.conn.commit()
            self.__close()
        except Exception as e:
            print(f"Error modifying cart: {e}")
            return {"status": "Error modifying cart."}

        return {"status": "Modified cart successfully."}

    async def remove_from_cart(self, email: str, sku: str) -> dict[str, str]:
        """
        Remove Product from Cart based on SKU

        Args:
            email: User Email (String)
            sku: Product SKU (String)

        Return:
            status: Status of the operation (String)
        """
        self.__connect()
        self.cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
        user_id = self.cursor.fetchone()
        try:
            self.cursor.execute(
                f"DELETE FROM cart WHERE user_id = {user_id[0]} AND sku = '{sku}'")
            self.conn.commit()
            self.__close()
        except Exception as e:
            print(f"Error removing from cart: {e}")
            return {"status": "Error removing from cart."}

        return {"status": "Removed from cart successfully."}

    async def clear_cart(self, email: str) -> dict[str, str]:
        """
        Clear Cart based on User Email

        Args:
            email: User Email (String)

        Return:
            status: Status of the operation (String)

        """

        self.__connect()
        self.cursor.execute(f"SELECT id FROM users WHERE email = '{email}'")
        user_id = self.cursor.fetchone()
        try:
            self.cursor.execute(
                f"DELETE FROM cart WHERE user_id = {user_id[0]}")
            self.conn.commit()
            self.__close()
        except Exception as e:
            print(f"Error clearing cart: {e}")
            return {"status": "Error clearing cart."}

        return {"status": "Cleared cart successfully."}

    async def get_price(self, sku: str, close_conn=False) -> int | None:
        """
        Get Price of Product based on SKU

        Args:
            sku: Product SKU (String)
            close_conn: Close Connection (Boolean)

        """
        self.__connect()
        self.cursor.execute(f"SELECT price FROM products WHERE sku = '{sku}'")
        price = self.cursor.fetchone()
        if close_conn:
            self.__close()
        return price[0] if price is not None else None

    async def get_shipping(self, country: str, address: str):
        """
        Get Shipping Options based on Country and Address
        (For now, only return flat rate shipping options)

        ARGS:
            country: Country (String)
            address: Address (String)

        RETURN:
            pricing_type: Pricing Type (String)
            option: Shipping Options (List)

        """
        return {
            "pricing_type": "flat_rate",
            "option": [
                {
                    "name": "Standard Shipping",
                    "price": 10.00
                },
                {
                    "name": "Express Shipping",
                    "price": 20.00
                }
            ]
        }

    async def __create_payment(self, items: list, customer_detail: dict, order_id: int, total_price: int):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Basic {os.getenv("PAYMENT_GATEWAY_KEY")}',
        }

        json_data = {
            'transaction_details': {
                'order_id': f'{order_id}',
                'gross_amount': total_price,
                'payment_link_id': 'contoso-payment-link-' + str(order_id),
            },
            'credit_card': {
                'secure': True,
            },
            'usage_limit': 1,
            'expiry': {
                'duration': 1,
                'unit': 'hours',
            },
            'item_details': items,

            'customer_details': {
                'first_name': customer_detail['first_name'],
                'last_name': customer_detail['last_name'],
                'email': customer_detail['email'],
                'notes': 'Thank you for your order. Please follow the instructions to complete payment.',
            },
        }

        response = requests.post(
            f"{os.getenv('PAYMENT_GATEWAY_ENDPOINT')}/v1/payment-links", headers=headers, json=json_data)

        return response.json()

    async def checkout(self, email: str, shipping_address: str, shipping_option: str,  customer_email: str):
        """
        Checkout Features for Cart, Return Payment Link for payment

        ARGS:
            email: User email (String)
            shipping_address: Shipping Address (String)
            shipping_option: Shipping Option (String)
            customer_email: Customer Email (String)

        RETURN:


        """

        self.__connect()
        self.cursor.execute(
            f"SELECT id, first_name, last_name FROM users WHERE email = '{email}'")
        user_data = self.cursor.fetchone()
        self.cursor.execute(
            f"SELECT * FROM cart WHERE user_id = {user_data[0]}")
        rows = self.cursor.fetchall()
        total_price = 0
        transaction_items = []
        for row in rows:
            price = await self.get_price(row[2], close_conn=False)
            print(price)
            self.cursor.execute(
                f"SELECT * FROM products WHERE sku = '{row[2]}'")
            product = self.cursor.fetchone()
            total_price += price * row[3]
            item = {
                'id': row[2],
                'name': f"{product[2]} (SKU: {row[1]})",
                'price': price,
                'quantity': row[3],
            }
            transaction_items.append(item)
        self.cursor.execute(f"DELETE FROM cart WHERE user_id = {user_data[0]}")
        self.conn.commit()

        rand_tx_id = random.randint(100000000, 999999999)

        self.cursor.execute(
            f"INSERT INTO orders (transaction_id, user_id, order_date, total_price, status, shipping_address) VALUES ('contoso-transaction-{str(rand_tx_id)}', {user_data[0]}, GETDATE(), {total_price}, 'pending', '{shipping_address}')")
        order_id = self.cursor.execute("SELECT @@IDENTITY").fetchone()[0]
        for item in transaction_items:
            self.cursor.execute(
                f"INSERT INTO OrderDetails (order_id, SKU, quantity, price) VALUES ({order_id}, '{item['id']}', {item['quantity']}, {item['price']})")
        self.conn.commit()
        payment_url = await self.__create_payment(customer_detail={
            'first_name': str(user_data[1]),
            'last_name': str(user_data[2]),
            'email': customer_email
        }, items=transaction_items, order_id='contoso-transaction-' + str(rand_tx_id),
            total_price=total_price)

        self.__close()

        print(f"payment_url: {payment_url} - Type: {type(payment_url)}")

        return {"status": "Checkout successful.", "total_price": total_price, "payment_link": payment_url['payment_url'], "transaction_id": f"contoso-transaction-{rand_tx_id}",
                "payment_url_validity": "1 Hours"}


def check_transaction(payment_link_id):
    headers = {
        'Authorization': 'Basic ',
    }
    response = requests.get(
        f'https://api.sandbox.midtrans.com/v1/payment-links/{payment_link_id}', headers=headers)
    purchase = response.json()['purchases']

    expires_at = datetime.datetime.strptime(
        response.json()['expires_at'], '%Y-%m-%dT%H:%M:%S.%fZ')

    current_time = datetime.datetime.now(datetime.timezone.utc)
    current_time = current_time.replace(tzinfo=None)

    if expires_at < current_time:
        return {
            'status': 'error',
            'data': 'Payment Expired'
        }

    if len(purchase) == 0 or not purchase[0] or purchase[0]['payment_status'] != 'CAPTURE' and purchase[0]['payment_status'] != 'SETTLEMENT':
        return {
            'status': 'error',
            'data': "Payment not completed or started"
        }

    result = {
        "status": "success",
        "data": {
            "payment_method": purchase[0]['payment_method'],
            "payment_status": purchase[0]['payment_status'],
        }
    }

    return result


async def check_transaction_jobs():
    while True:
        driver = os.getenv("ODBC_STRING")
        conn = pyodbc.connect(driver)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders where status = 'pending'")
        cursor.fetchall()
        for row in cursor:
            result = check_transaction(row[1])
            if result['status'] == 'success':
                cursor.execute(
                    f"UPDATE orders SET status = 'success' WHERE id = {row[0]}")
            elif result['data'] == 'Payment Expired':
                cursor.execute(
                    f"UPDATE orders SET status = 'expired' WHERE id = {row[0]}")

        conn.commit()
        conn.close()
        await asyncio.sleep(60)
