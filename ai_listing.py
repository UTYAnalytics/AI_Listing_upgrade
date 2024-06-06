import psycopg2
import pandas as pd
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from typing import Dict, List
import os
from datetime import datetime

GROQ_API_KEY = "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"


class AILising:
    """
    This class is used to get response from Groq API
    """

    def __init__(self) -> None:
        # Initialize API KEY
        self.GROQ_API_KEY = GROQ_API_KEY

    def load_model(self):
        "Load the model from the Langchain-Groq"
        self.chat = ChatGroq(
            temperature=0, groq_api_key=self.GROQ_API_KEY, model_name="llama3-8b-8192"
        )

    def get_prompt(
        self,
        product_name: str,
        pack: str,
        organic_keys: List[str],
        auto_keys: List[str],
        customers: List[str],
    ):
        "Build the prompt template"

        system = "You are doing the role of an Amazon Product Listing expert"
        human = f"""
                    Giving a product with {product_name} together with information of pack or size as {pack},
                    and with some ORGANIC IMPORTANT KEYS: {organic_keys} which need to be listed,
                    and reference keys: {auto_keys} which can be used to improve the listing performance.

                    Write a whole LISTING product for me to sell on Amazon US. 

                    The listing MUST push the brand "AMAZIN CHOICES" in the first place in the title, to make the branding.
                    The information of pack and product size should be at the end of the title.

                    All information of KEYS listing should be covered.

                    There are rules you MUST follow:
                    - Title does not contain symbols or emojis
                    - Title contains around 150 characters
                    - Description has greater than 5 and less than 10 bullet points
                    - Description has greater than 150 characters in each bullet point
                    - MUST USE the icons, emojis, and symbols at the beginning of each bullet point.
                    - First letter of bullet points is capitalized
                    - Bullet points are not in all caps or contain icons
                    - 1000+ characters in description or A+ content
                    - NOT using words or term phrases which I need to verify. Example: Guaranteed, Approved, Verified, ...
                    

                    The response in format:

                    ## Title: 
                    Appropriate title of product using best keyword list, format as a header
                    ## Description: 
                        - description of the product, in bullet points, contains the best keyword list to increase the highest possibility of keyword search on Amazon
                        - description MUST adapt the style of sentences to target the group of customers on Amazon: {customers}.
                    The return will be in MARKDOWN format. Each of bullet point MUST BE SEPARATED BY END OF PARAGRAPH.
                    ALL OF THE NOTES NEED TO BE SKIPPED

                    Example:
                    product_name: \'Amazin Choices Snack Viet'
                    pack:  Pack of 4 (7.05oz)
                    organic_keys: Snack Viet, Healthy Snack, Study Snack, Party Snack, Lotus Root Seaweed Flavor Snack
                    auto_keys: Amazin Choices, Snack Viet, Healthy Snack, Study Snack, Party Snack, Lotus Root Seaweed Flavor Snack
                    customers: gift for everyone
                    ## Title: 
                    Amazin Choices Snack Viet- Healthy Snack- Study Snack- Party Snack- An Delicious Vietnamese Lotus Root Seaweed Flavor Snack Variety Pack- Pack of 4 (7.05oz)

                    ## Description:
                    ✅ DELICIOUS VIETNAMESE SNACK: Indulge in the flavors of Vietnam with our Lotus Root Seaweed flavor Snack, a unique and exotic treat for your taste buds. Huong vi Viet Nam, an vat cu sen rong bien den tu Co do Hue, nang tam nong san Viet Nam vuon tam quoc te
                    ✅ CRISPY AND CRUNCHY: Enjoy the satisfying crunch of crispy seaweed flavor sheets and lotus root chips in every bite. Dac san Viet Nam voi huong vị truyen thong, mon ngon, vi rong bien
                    ✅ HEALTHY OPTION: Our gourmet seaweed snack is a healthy, amazing choice for those looking for on-the-go snack. Giup cai thien giac ngu, an ngon, san pham chat luong cao tu Viet Nam
                    ✅ SEA SALT PERFECTION: Seasoned with sea salt, our lotus seaweed flavor snacks provide the perfect balance of savory flavor. Gia vi Viet Nam, muoi an, rong bien, cu sen… su ket hop hai hoa giua sang tao va truyen thong
                    ✅ PARTY SNACK FAVORITE: These lotus root crisps and seaweed chips are a hit at parties and gatherings, making them the ideal party snack. Qua Tet nguoi Viet, mon an tien loi, an voi uong tra Viet Nam tang vị thom cua sen    
                """
        self.prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("human", human)]
        )

    def get_response(
        self,
        product_name: str,
        pack: str,
        organic_keys: List[str],
        auto_keys: List[str],
        customers: List[str],
    ) -> Dict[str, str]:
        "Get the response from Groq API"
        self.load_model()
        self.get_prompt(
            product_name=product_name,
            pack=pack,
            organic_keys=organic_keys,
            auto_keys=auto_keys,
            customers=customers,
        )
        self.chain = self.prompt | self.chat
        self.result = self.chain.invoke(
            {
                "product_name": product_name,
                "pack": pack,
                "organic_keys": organic_keys,
                "auto_keys": auto_keys,
                "customers": customers,
            }
        )
        return self.parse_result(self.result.content)

    def parse_result(self, content: str) -> Dict[str, str]:
        "Parse the result to extract title and description"
        try:
            title = content.split("## Title:")[1].split("## Description:")[0].strip()
            description = content.split("## Description:")[1].strip()
        except IndexError:
            title = ""
            description = ""
            st.error("Failed to parse response from Groq API")
        return {"title": title, "description": description}

    def fetch_data(self, session_id: str) -> pd.DataFrame:
        "Fetch data from the database based on session_id"
        conn = None
        try:
            # Connect to your database
            conn = psycopg2.connect(
                dbname="postgres",
                user="postgres.sxoqzllwkjfluhskqlfl",
                password="5giE*5Y5Uexi3P2",
                host="aws-0-us-west-1.pooler.supabase.com",
            )
            cur = conn.cursor()
            # Execute a query
            cur.execute(
                """
                    SELECT id, sys_run_date, asin, name, customer, insert_date, keyword, pack, session_id, organic_keywords 
                    FROM auto_listing_table 
                    WHERE session_id=%s
                """,
                (session_id,),
            )
            # Fetch all results
            rows = cur.fetchall()
            headers = [
                "id",
                "sys_run_date",
                "asin",
                "name",
                "customer",
                "insert_date",
                "keyword",
                "pack",
                "session_id",
                "organic_keywords",
            ]
            df = pd.DataFrame(rows, columns=headers)
            return df
        except Exception as e:
            st.error(f"Database error: {e}")
            return pd.DataFrame(columns=headers)
        finally:
            if conn:
                conn.close()

    def process_data(self, session_id: str) -> List[Dict[str, str]]:
        "Process data to use in get_response for all rows"
        df = self.fetch_data(session_id)
        if df.empty:
            return []

        results = []

        for _, row in df.iterrows():
            product_name = row["name"]
            pack = row["pack"]
            organic_keys = row["organic_keywords"].split(", ")
            auto_keys = row["keyword"].split(", ")
            customers = row["customer"].split(", ")

            result = self.get_response(
                product_name=product_name,
                pack=pack,
                organic_keys=organic_keys,
                auto_keys=auto_keys,
                customers=customers,
            )
            results.append(
                {
                    "id": row["id"],
                    "sys_run_date": row["sys_run_date"],
                    "asin": row["asin"],
                    "name": row["name"],
                    "customer": row["customer"],
                    "insert_date": row["insert_date"],
                    "keyword": row["keyword"],
                    "pack": row["pack"],
                    "session_id": row["session_id"],
                    "organic_keywords": row["organic_keywords"],
                    "title": result["title"],
                    "description": result["description"],
                }
            )

        return results

    def upsert_results(self, results: List[Dict[str, str]]):
        "Upsert results into the database"
        conn = None
        try:
            # Connect to your database
            conn = psycopg2.connect(
                dbname="postgres",
                user="postgres.sxoqzllwkjfluhskqlfl",
                password="5giE*5Y5Uexi3P2",
                host="aws-0-us-west-1.pooler.supabase.com",
            )
            cur = conn.cursor()
            for result in results:
                cur.execute(
                    """
                    INSERT INTO auto_listing_table (id, sys_run_date, asin, name, customer, insert_date, keyword, pack, session_id, organic_keywords, title, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        sys_run_date = EXCLUDED.sys_run_date,
                        asin = EXCLUDED.asin,
                        name = EXCLUDED.name,
                        customer = EXCLUDED.customer,
                        insert_date = EXCLUDED.insert_date,
                        keyword = EXCLUDED.keyword,
                        pack = EXCLUDED.pack,
                        session_id = EXCLUDED.session_id,
                        organic_keywords = EXCLUDED.organic_keywords;
                    """,
                    (
                        result["id"],
                        result["sys_run_date"],
                        result["asin"],
                        result["name"],
                        result["customer"],
                        result["insert_date"],
                        result["keyword"],
                        result["pack"],
                        result["session_id"],
                        result["organic_keywords"],
                        result["title"],
                        result["description"],
                    ),
                )
            conn.commit()
        # except Exception as e:
        # st.error(f"Database error: {e}")
        finally:
            if conn:
                conn.close()


def listing(session_id):
    ai_system = AILising()
    results = ai_system.process_data(session_id=session_id)
    ai_system.upsert_results(results)

    formatted_results = ""
    for result in results:
        formatted_results += f"\n\nTitle: {result['title']}\n\n"
        formatted_results += f"\n\nDescription: {result['description']}\n\n"

    return results, formatted_results


# Example usage
# if __name__ == '__main__':
#     session_id = "decfbc45-e13c-4565-bcd1-970303c69bee"
#     results = listing(session_id)

#     with open("output.txt", "w", encoding="utf-8") as f:
#         for result in results:
#             f.write(f"Title: {result['title']}\n")
#             f.write(f"Description: {result['description']}\n\n")

#     print("Results have been written to output.txt")
