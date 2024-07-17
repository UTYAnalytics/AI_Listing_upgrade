import requests
import json
import pandas as pd
from datetime import datetime
from config import config
import numpy as np

# Initialize Supabase client
supabase = config.supabase

# Get timezone offset and calculate current time in GMT+7
current_time_gmt7 = config.current_time_gmt7

# Get database configuration
db_config = config.get_database_config()

url = "https://developer.junglescout.com/api/keywords/keywords_by_keyword_query?marketplace=us&sort=-relevancy_score&page[size]=100"

def keyword_to_keyword(keyword_input):
    payload = json.dumps({
        "data": {
            "type": "keywords_by_keyword_query",
            "attributes": {
                "categories": [
                    "Grocery & Gourmet Food",
                ],
                "search_terms": keyword_input,
                "min_monthly_search_volume_exact": 1,
                "max_monthly_search_volume_exact": 99999,
                "min_monthly_search_volume_broad": 1,
                "max_monthly_search_volume_broad": 99999,
                "min_word_count": 1,
                "max_word_count": 99999,
                "min_organic_product_count": 1,
                "max_organic_product_count": 99999
            }
        }
    })
    headers = {
        'Content-Type': 'application/vnd.api+json',
        'Accept': 'application/vnd.junglescout.v1+json',
        'Authorization': 'APIdata:4kOtlDRyc1KhX_6CEnUUyJW0AyHILmbHISvKZ0_XxLQ',
        'X-API-Type': 'junglescout'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response to JSON
        response_json = response.json()
        attributes = [item["attributes"] for item in response_json["data"]]

        # Add sys_run_date and keyword_parent to each attribute dictionary
        for attribute in attributes:
            attribute["sys_run_date"] = current_time_gmt7.strftime("%Y-%m-%d")
            attribute["keyword_parent"] = keyword_input

        # # Export the attributes to a JSON file
        # with open('response.json', 'w') as json_file:
        #     json.dump(attributes, json_file, indent=4)
        # print("Response has been exported to 'response.json'.")

        # Create DataFrame from attributes
        data = pd.DataFrame(attributes)

        # Replace NaN with None
        data = data.where(pd.notnull(data), None)
        # Replace NaN with None
        data = data.replace({pd.NA: None, np.nan: None})

        headers = [
            'country',
            'name',
            'monthly_trend',
            'monthly_search_volume_exact',
            'quarterly_trend',
            'monthly_search_volume_broad',
            'dominant_category',
            'recommended_promotions',
            'sp_brand_ad_bid',
            'ppc_bid_broad',
            'ppc_bid_exact',
            'ease_of_ranking_score',
            'relevancy_score',
            'organic_product_count',
            'sponsored_product_count',
            'sys_run_date',
            'keyword_parent',
        ]
        data = data[headers]  # Ensure correct column order

        try:
            response = supabase.table("keyword_to_jungle_scount").upsert(data.to_dict(orient="records")).execute()
            if hasattr(response, "error") and response.error is not None:
                raise Exception(f"Error inserting rows: {response.error}")
            print("Rows inserted successfully")
        except Exception as e:
            print(f"Error with rows: {e}")
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(response.text)

# keyword_to_keyword("Seaweed crisps with pumpkin seeds and sesame seeds")
