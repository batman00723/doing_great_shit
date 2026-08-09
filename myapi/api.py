from ninja_extra import NinjaExtraAPI

from .meeting_controller import MeetingOperationController, AudioController, ChatController
from .auth_controller import AuthController
from .bot_controller import BotController
from .customer_controller import CustomerController

api_v1 = NinjaExtraAPI(version="1.0.0")

api_v1.register_controllers(MeetingOperationController, AudioController, ChatController, AuthController, BotController, CustomerController)

