from ninja_extra import ControllerBase, api_controller, http_post, http_get
from ninja import Schema
from myapi.auth_controller import JWTAuth
from myapi.models import Customer
from typing import List

class CustomerSchema(Schema):
    customer_name: str
    industry: str = ""
    website: str = ""
    status: str = "Lead"

class CustomerOutSchema(Schema):
    id: int
    customer_name: str
    industry: str
    website: str
    status: str

@api_controller("/customers", tags=["Customer CRM"])
class CustomerController(ControllerBase):

    @http_post("/create", auth=JWTAuth(), response=CustomerOutSchema)
    def create_customer(self, request, payload: CustomerSchema):
        # Create customer linked to the salesperson and their organisation
        customer = Customer.objects.create(
            organisation=request.user.organisation,
            salesperson=request.user,
            customer_name=payload.customer_name,
            industry=payload.industry,
            website=payload.website,
            status=payload.status
        )
        return customer

    @http_get("/list", auth=JWTAuth(), response=List[CustomerOutSchema])
    def list_customers(self, request):
        # Salesperson can strictly only see their own assigned customers
        return Customer.objects.filter(salesperson=request.user)
