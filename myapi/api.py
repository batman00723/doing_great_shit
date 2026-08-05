from ninja_extra import NinjaExtraAPI

from .meeting_controller import MeetingOperationController, AudioController

api_v1 = NinjaExtraAPI(version="1.0.0")

api_v1.register_controllers(MeetingOperationController, AudioController)

