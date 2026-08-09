import jwt
import datetime
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from ninja_extra import api_controller, http_post, http_get
from ninja import Schema
from ninja.security import HttpBearer
from .models import User, Organisation

# ── JWT Config ──────────────────────────────────────────────────────────────
JWT_SECRET = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_EXPIRATION_MINUTES = 30
REFRESH_EXPIRATION_DAYS = 7

# ── Custom JWT Auth Bearer ──────────────────────────────────────────────────
class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            token_type = payload.get("type")
            
            # We only accept access tokens for regular API requests
            if token_type != "access":
                return None
                
            user = User.objects.get(id=user_id)
            # Attach the user to the request for easy access in endpoints
            request.user = user
            return token
        except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
            return None

# ── Helper Functions ────────────────────────────────────────────────────────
def create_access_token(user_id: int):
    payload = {
        "user_id": user_id,
        "type": "access",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_EXPIRATION_MINUTES),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(user_id: int):
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_EXPIRATION_DAYS),
        "iat": datetime.datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

# ── Schemas ─────────────────────────────────────────────────────────────────
class OrgRegisterSchema(Schema):
    organisation_name: str
    admin_name: str
    email: str
    password: str

class SalespersonRegisterSchema(Schema):
    salesperson_name: str
    email: str
    password: str

class LoginSchema(Schema):
    email: str
    password: str

class RefreshSchema(Schema):
    refresh_token: str

# ── Controller ──────────────────────────────────────────────────────────────
@api_controller("/auth", tags=["Authentication"])
class AuthController:

    @http_post("/register-org")
    def register_org(self, request, payload: OrgRegisterSchema):
        # Check if email exists
        if User.objects.filter(email=payload.email).exists():
            return self.create_response("Email already registered", status_code=400)
            
        # 1. Create Organisation
        org = Organisation.objects.create(
            organisation_name=payload.organisation_name,
            subscription_tier="Free"
        )
        
        # 2. Create User (Admin)
        user = User.objects.create(
            organisation=org,
            salesperson_name=payload.admin_name,
            email=payload.email,
            password_hash=make_password(payload.password),
            role="Admin"
        )
        
        return {
            "message": "Organisation and Admin created successfully",
            "org_id": org.id,
            "admin_id": user.id
        }

    @http_post("/register-salesperson", auth=JWTAuth())
    def register_salesperson(self, request, payload: SalespersonRegisterSchema):
        # Only Admins should be able to do this (optional safety check)
        if request.user.role != "Admin":
            return self.create_response("Only Admins can register salespeople", status_code=403)
            
        # Check if email exists
        if User.objects.filter(email=payload.email).exists():
            return self.create_response("Email already registered", status_code=400)
            
        # 1. Grab the Admin's organisation automatically
        org = request.user.organisation
        
        # 2. Create the Salesperson
        user = User.objects.create(
            organisation=org,
            manager=request.user, # The admin is the manager
            salesperson_name=payload.salesperson_name,
            email=payload.email,
            password_hash=make_password(payload.password),
            role="Salesperson"
        )
        
        return {
            "message": f"Salesperson added to {org.organisation_name}",
            "salesperson_id": user.id
        }

    @http_post("/login")
    def login(self, request, payload: LoginSchema):
        try:
            user = User.objects.get(email=payload.email)
        except User.DoesNotExist:
            return self.create_response("Invalid credentials", status_code=401)
            
        # Check password hash
        if not check_password(payload.password, user.password_hash):
            return self.create_response("Invalid credentials", status_code=401)
            
        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_id": user.id,
            "organisation": user.organisation.organisation_name,
            "role": user.role
        }
        
    @http_post("/refresh")
    def refresh(self, request, payload: RefreshSchema):
        try:
            # Decode the refresh token
            decoded = jwt.decode(payload.refresh_token, JWT_SECRET, algorithms=[ALGORITHM])
            
            # Ensure it's actually a refresh token
            if decoded.get("type") != "refresh":
                return self.create_response("Invalid token type", status_code=401)
                
            user_id = decoded.get("user_id")
            
            # Ensure user still exists
            if not User.objects.filter(id=user_id).exists():
                return self.create_response("User not found", status_code=401)
                
            # Issue a brand new access token!
            new_access_token = create_access_token(user_id)
            
            return {
                "access_token": new_access_token
            }
            
        except (jwt.ExpiredSignatureError, jwt.DecodeError):
            return self.create_response("Invalid or expired refresh token", status_code=401)
