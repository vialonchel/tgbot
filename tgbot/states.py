from aiogram.fsm.state import State, StatesGroup


class BroadcastStates(StatesGroup):
    waiting_for_message = State()


class CampaignStates(StatesGroup):
    waiting_for_name = State()


class RandomThemeStates(StatesGroup):
    waiting_for_device = State()


class CustomThemeStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_device = State()


class StickerStates(StatesGroup):
    waiting_for_source = State()


class VideoNoteStates(StatesGroup):
    waiting_for_video = State()


class FontStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_font_choice = State()
