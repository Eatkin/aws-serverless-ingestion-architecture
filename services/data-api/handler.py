import os
import boto3

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from mangum import Mangum
from pydantic import BaseModel
from boto3.dynamodb.conditions import Key

from common.models import LeadStorage

TABLE_NAME = os.environ.get("TABLE_NAME", "data-table")

app = FastAPI(title="CRM Egress API")

dynamodb = None
def get_db():
    global dynamodb
    if dynamodb is None:
        dynamodb = boto3.resource("dynamodb")
    return dynamodb

table = None
def get_table():
    global table
    if table is None:
        table = dynamodb.Table(TABLE_NAME)
    return table

@app.get("/leads")
async def get_leads(email: str = Query(..., description="The user email to query")):
    try:
        # Query by PK (Partition Key)
        response = get_table().query(
            KeyConditionExpression=Key("PK").eq(f"USER#{email}")
        )
        
        items = response.get("Items", [])
        if not items:
            return []
            
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "Operational"}

handler = Mangum(app)