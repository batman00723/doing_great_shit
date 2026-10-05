from ninja_extra import ControllerBase, api_controller, http_post, http_get
from ninja import Schema, File, Form, UploadedFile
from myapi.auth_controller import JWTAuth
from myapi.models import Customer
from typing import List
from ninja.errors import HttpError

class CustomerSchema(Schema):
    customer_name: str
    email: str
    industry: str = ""
    website: str = ""
    status: str = "Lead"

class CustomerOutSchema(Schema):
    id: int
    customer_name: str
    email: str
    industry: str
    website: str
    status: str
    customer_image: str | None = None

class CustomerOutSchemaList(Schema):
    id: int
    customer_name: str
    industry: str
    status: str
    email: str | None = None
    website: str | None = None
    customer_image: str | None = None

@api_controller("/customers", tags=["Customer CRM"])
class CustomerController(ControllerBase):

    @http_post("/create", auth=JWTAuth(), response=CustomerOutSchema)
    async def create_customer(self, request, payload: CustomerSchema = Form(...), photo: UploadedFile= File(None)):

        if photo:
            if photo.size > 500*1024:
                raise HttpError(400, "Image exceeds 500 KB limit.")
            
        # Create customer linked to the salesperson and their organisation
        customer = await Customer.objects.acreate(
            organisation_id=request.user.organisation_id,
            salesperson_id=request.user.id,
            customer_name=payload.customer_name,
            email=payload.email,
            industry=payload.industry,
            website=payload.website,
            status=payload.status,
            customer_image= photo
        )
        return customer

    @http_get("/list", auth=JWTAuth(), response=List[CustomerOutSchemaList])
    async def list_customers(self, request):
        # Salesperson can strictly only see their own assigned customers
        customer= [
            c async for c in
            Customer.objects.filter(salesperson_id= request.user.id)]
        return customer
    
